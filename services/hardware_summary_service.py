#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import requests
import os
import sys
import threading
import time
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logger import setup_logger

logger = setup_logger(__name__)

LLM_CONFIG = {
    'base_url': 'http://192.168.101.214:6007',
    'chat_endpoint': '/v1/chat/completions',
    'model_name': 'Qwen3-32B-AWQ'
}


class HardwareSummary:
    def __init__(self):
        self.ai_config = LLM_CONFIG
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.memory_file = os.path.join(current_dir, 'data', 'memory_inspection.json')
        self.disk_file = os.path.join(current_dir, 'data', 'disk_inspection.json')
        self.system_file = os.path.join(current_dir, 'data', 'system.json')
        self.output_file = os.path.join(current_dir, 'data', 'hardware_summary.txt')

    def load_json_file(self, file_path):
        try:
            if not os.path.exists(file_path):
                error_msg = f"文件不存在: {file_path}"
                logger.error(error_msg)
                raise FileNotFoundError(error_msg)

            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.info(f"成功读取文件: {file_path}")
                return data
        except json.JSONDecodeError as e:
            error_msg = f"JSON解析错误 {file_path}: {e}"
            logger.error(error_msg)
            raise json.JSONDecodeError(error_msg, file_path, 0)
        except Exception as e:
            error_msg = f"读取文件 {file_path} 失败: {e}"
            logger.error(error_msg)
            raise Exception(error_msg)

    def test_ai_connection(self):
        try:
            print("正在测试AI服务连接...")
            url = f"{self.ai_config['base_url']}{self.ai_config['chat_endpoint']}"
            test_payload = {
                "model": self.ai_config['model_name'],
                "messages": [
                    {"role": "user", "content": "你好"}
                ],
                "temperature": 0.7,
                "max_tokens": 50
            }

            headers = {"Content-Type": "application/json"}
            response = requests.post(url, json=test_payload, headers=headers, timeout=10)
            response.raise_for_status()
            print("AI服务连接测试成功")
            return True
        except Exception as e:
            print(f"AI服务连接测试失败: {e}")
            logger.error(f"AI服务连接测试失败: {e}")
            return False

    def call_ai_analysis_with_retry(self, prompt, max_retries=5, temperature=0.7, max_tokens=2000):
        for attempt in range(max_retries):
            try:
                print(f"正在尝试调用AI分析（第{attempt + 1}次尝试）...")
                result = self.call_ai_analysis_single(prompt, temperature, max_tokens)

                if "AI分析超时" in result or "无法连接到AI服务" in result or "AI分析失败" in result:
                    if attempt < max_retries - 1:
                        print(f"第{attempt + 1}次尝试失败，2秒后重试...")
                        time.sleep(2)
                        continue
                    else:
                        return result
                else:
                    print(f"第{attempt + 1}次尝试成功")
                    return result

            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"第{attempt + 1}次尝试出现异常: {e}，2秒后重试...")
                    time.sleep(2)
                    continue
                else:
                    return f"AI分析失败（尝试{max_retries}次后放弃）: {str(e)}"

        return "AI分析失败：达到最大重试次数"

    def call_ai_analysis_single(self, prompt, temperature=0.7, max_tokens=2000):
        try:
            url = f"{self.ai_config['base_url']}{self.ai_config['chat_endpoint']}"
            payload = {
                "model": self.ai_config['model_name'],
                "messages": [
                    {"role": "system",
                     "content": "你是一位专业的运维专家，负责分析服务器硬件巡检数据并提供针对不同IP服务器的具体采购建议和优化建议。请基于实际硬件数据给出详细的型号、规格和理由，包括内存的频率、容量、类型、厂商型号，以及硬盘的容量、接口、转速、厂商型号等详细参数。必须针对每台服务器IP分别给出建议，同时提供现有应用和数据的优化方案。特别关注温度异常情况的分析和处理建议。"},
                    {"role": "user", "content": prompt}
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": False
            }

            headers = {"Content-Type": "application/json"}
            response = requests.post(url, json=payload, headers=headers, timeout=180)
            response.raise_for_status()

            result = response.json()
            return result["choices"][0]["message"]["content"]
        except requests.exceptions.Timeout:
            error_msg = "AI分析超时，请检查网络连接或降低数据量"
            print(error_msg)
            logger.error(error_msg)
            return error_msg
        except requests.exceptions.ConnectionError:
            error_msg = f"无法连接到AI服务 {self.ai_config['base_url']}"
            print(error_msg)
            logger.error(error_msg)
            return error_msg
        except Exception as e:
            error_msg = f"AI分析失败: {str(e)}"
            print(error_msg)
            logger.error(error_msg)
            return error_msg

    def call_ai_analysis(self, prompt, temperature=0.7, max_tokens=2000):
        return self.call_ai_analysis_with_retry(prompt, max_retries=5, temperature=temperature, max_tokens=max_tokens)

    def categorize_servers_by_status(self, memory_data, disk_data):
        categorized_data = {
            'successful_servers': {},
            'failed_servers': {},
            'no_permission_servers': {},
            'memory_no_permission_ips': [],
            'disk_no_permission_ips': [],
            'memory_failed_ips': [],
            'disk_failed_ips': []
        }

        memory_results = memory_data.get('results', {})
        for ip, result in memory_results.items():
            status = result.get('status', 'unknown')
            ssh_status = result.get('ssh_connection', {}).get('status', 'unknown')

            if status == 'success' or status == '巡检成功':
                categorized_data['successful_servers'][ip] = {
                    'memory_data': result
                }
            elif status == 'no_permission' or ssh_status == '无权限' or '权限' in str(result.get('error', '')):
                categorized_data['no_permission_servers'][ip] = categorized_data['no_permission_servers'].get(ip, {})
                categorized_data['no_permission_servers'][ip]['memory_status'] = 'no_permission'
                categorized_data['no_permission_servers'][ip]['memory_error'] = result.get('error', '权限不足')
                categorized_data['memory_no_permission_ips'].append(ip)
            else:
                categorized_data['failed_servers'][ip] = categorized_data['failed_servers'].get(ip, {})
                categorized_data['failed_servers'][ip]['memory_status'] = status
                categorized_data['failed_servers'][ip]['memory_error'] = result.get('error', '巡检失败')
                categorized_data['memory_failed_ips'].append(ip)

        disk_results = disk_data.get('results', {})
        for ip, result in disk_results.items():
            status = result.get('status', 'unknown')
            ssh_status = result.get('ssh_connection', {}).get('status', 'unknown')

            if status == 'success' or status == '巡检成功':
                if ip in categorized_data['successful_servers']:
                    categorized_data['successful_servers'][ip]['disk_data'] = result
                else:
                    categorized_data['successful_servers'][ip] = {
                        'disk_data': result
                    }
            elif status == 'no_permission' or ssh_status == '无权限' or '权限' in str(result.get('error', '')):
                if ip not in categorized_data['no_permission_servers']:
                    categorized_data['no_permission_servers'][ip] = {}
                categorized_data['no_permission_servers'][ip]['disk_status'] = 'no_permission'
                categorized_data['no_permission_servers'][ip]['disk_error'] = result.get('error', '权限不足')
                categorized_data['disk_no_permission_ips'].append(ip)
            else:
                if ip not in categorized_data['failed_servers']:
                    categorized_data['failed_servers'][ip] = {}
                categorized_data['failed_servers'][ip]['disk_status'] = status
                categorized_data['failed_servers'][ip]['disk_error'] = result.get('error', '巡检失败')
                categorized_data['disk_failed_ips'].append(ip)

        return categorized_data

    def extract_hardware_details(self, memory_data, disk_data, system_data=None):
        hardware_details = {
            'memory_details': [],
            'disk_details': [],
            'monitoring_data': {},
            'environment_monitoring': {},
            'server_categorization': self.categorize_servers_by_status(memory_data, disk_data)
        }

        memory_results = memory_data.get('results', {})
        for ip, result in memory_results.items():
            if result.get('status') in ['success', '巡检成功']:
                memory_usage = result.get('memory_usage', {})
                hardware_info = result.get('hardware_info', {})
                top_processes = result.get('top_processes', [])

                hardware_details['memory_details'].append({
                    'ip': ip,
                    'total_memory': memory_usage.get('total_memory'),
                    'available_memory': memory_usage.get('available_memory'),
                    'used_memory': memory_usage.get('used_memory'),
                    'memory_percent': memory_usage.get('memory_percent'),
                    'memory_modules': hardware_info.get('memory_modules', []),
                    'total_slots': hardware_info.get('total_slots', 0),
                    'installed_slots': hardware_info.get('installed_slots', 0),
                    'empty_slots': hardware_info.get('empty_slots', 0),
                    'top_processes': top_processes
                })

        disk_results = disk_data.get('results', {})
        for ip, result in disk_results.items():
            if result.get('status') in ['success', '巡检成功']:
                disk_usage = result.get('disk_usage', [])
                disk_info = result.get('disk_info', [])

                hardware_details['disk_details'].append({
                    'ip': ip,
                    'disk_usage': disk_usage,
                    'disk_info': disk_info
                })

        if system_data:
            hardware_details['monitoring_data'] = {
                'generation_time': system_data.get('generation_time'),
                'query_parameters': system_data.get('query_parameters', {}),
                'abnormal_memory_ips': system_data.get('abnormal_memory_ips', []),
                'abnormal_disk_ips': system_data.get('abnormal_disk_ips', [])
            }

            server_monitoring = system_data.get('server_monitoring', {})
            hardware_details['monitoring_data']['memory_monitoring'] = server_monitoring.get('memory_details', [])
            hardware_details['monitoring_data']['disk_monitoring'] = server_monitoring.get('disk_details', [])

            environment_monitoring = system_data.get('environment_monitoring', {})
            hardware_details['environment_monitoring'] = {
                'abnormal_environment_details': environment_monitoring.get('abnormal_environment_details', [])
            }

        return hardware_details

    def summarize_data(self, memory_data, disk_data, system_data=None):
        summary = {}

        summary['memory_summary'] = {
            'inspected_count': memory_data.get('inspected_count', 0),
            'success_count': memory_data.get('success_count', 0),
            'failed_count': memory_data.get('failed_count', 0),
            'no_permission_count': memory_data.get('no_permission_count', 0)
        }

        summary['disk_summary'] = {
            'inspected_count': disk_data.get('inspected_count', 0),
            'success_count': disk_data.get('success_count', 0),
            'failed_count': disk_data.get('failed_count', 0),
            'no_permission_count': disk_data.get('no_permission_count', 0)
        }

        if system_data:
            summary['system_monitoring_summary'] = {
                'generation_time': system_data.get('generation_time'),
                'abnormal_memory_count': len(system_data.get('abnormal_memory_ips', [])),
                'abnormal_disk_count': len(system_data.get('abnormal_disk_ips', [])),
                'environment_abnormal_count': len(
                    system_data.get('environment_monitoring', {}).get('abnormal_environment_details', []))
            }

        summary['hardware_details'] = self.extract_hardware_details(memory_data, disk_data, system_data)

        return summary

    def analyze_hardware_data(self):
        memory_data = self.load_json_file(self.memory_file)
        disk_data = self.load_json_file(self.disk_file)

        system_data = None
        try:
            system_data = self.load_json_file(self.system_file)
            print(f"成功加载系统监控数据: {self.system_file}")
        except Exception as e:
            print(f"无法加载系统监控数据 {self.system_file}: {e}")
            logger.warning(f"无法加载系统监控数据: {e}")

        print("正在准备数据摘要...")
        data_summary = self.summarize_data(memory_data, disk_data, system_data)

        has_data = (memory_data.get('success_count', 0) > 0 or
                    disk_data.get('success_count', 0) > 0 or
                    len(memory_data.get('results', {})) > 0 or
                    len(disk_data.get('results', {})) > 0)

        if not has_data:
            return "## 本地分析结果\n\n未检测到服务器硬件数据，请先运行硬件巡检程序获取服务器硬件信息。\n\n**下一步操作：**\n1. 运行内存巡检程序\n2. 运行硬盘巡检程序\n3. 运行系统监控程序\n4. 重新生成硬件分析报告"

        if not self.test_ai_connection():
            return "## 本地分析结果\n\nAI服务不可用，无法生成详细分析报告。请检查AI服务连接状态。"

        prompt = f"""
请基于以下硬件巡检数据和系统监控数据，提供针对每台服务器IP的详细硬件采购建议和优化建议：

## 硬件巡检数据和系统监控数据：
{json.dumps(data_summary, ensure_ascii=False, indent=2)}

## 分析要求（必须按照以下格式输出）：

### 1. 巡检状态分析
请详细说明巡检中遇到的问题：
- **权限不足的服务器**：列出具体IP并说明影响
- **巡检失败的服务器**：列出具体IP并说明可能原因
- **成功巡检的服务器**：列出具体IP并总结状态

### 2. 环境监控异常分析
请重点分析环境监控数据中的异常情况：
- **温度异常详情**：
  - 异常温度值：具体多少度
  - 异常时间：具体的检测时间
  - 异常状态评估：是否需要紧急处理
  - **紧急处理建议**：针对温度异常的立即处理措施
  - **长期解决方案**：机房环境改善建议

### 3. 系统监控警报分析
基于监控阈值分析异常服务器：
- **内存使用异常服务器**：
  - 列出所有超过阈值(70%)的服务器IP
  - 每个IP的具体使用率和状态
  - 数据收集时间
- **硬盘使用异常服务器**：
  - 列出所有超过阈值(80%)的服务器IP
  - 每个IP的具体使用率和状态
  - 数据收集时间

### 4. 现有内存配置分析（按IP分别分析）
针对每台成功巡检的服务器，分析：
- **服务器IP: [具体IP地址]**
  - **现有内存配置详情**：
    - 当前内存总大小：XX GB
    - 内存条数：X条
    - 内存频率：XXXX MHz
    - 内存品牌和型号：具体型号
    - 内存类型：DDR4/DDR5
    - ECC支持：是/否
  - **主板内存支持详情**：
    - 主板支持的最大内存容量：XX GB
    - 当前内存插槽总数：X个
    - 已使用插槽数：X个
    - 空闲插槽数：X个
    - 主板支持的内存频率：XXXX MHz
  - **其他内存主板详细情况**：
    - 内存通道配置：双通道/四通道
    - 主板芯片组型号
    - 内存兼容性和限制
  - 当前内存使用率和性能评估
  - **监控警报状态**：如果该IP在异常列表中，特别说明

### 5. 现有应用内存占用优化分析（按IP分别分析）
针对每台成功巡检的服务器，分析：
- **服务器IP: [具体IP地址]**
  - 分析top_processes中的高内存占用进程
  - 评估这些进程是否可以优化（重启、配置调整、替换）
  - 估算优化后可释放的内存容量
  - 提供具体的优化建议和操作步骤
  - 优化的风险评估和注意事项

### 6. 内存升级建议（按IP分别建议）
结合现有配置和主板支持情况，针对每台需要升级的服务器：
- **服务器IP: [具体IP地址]**
  - **升级理由**：
    - 基于当前使用率（具体百分比）
    - 基于监控阈值状态
    - 基于性能需求分析
  - **推荐升级方案**：
    - 建议采购内存型号：具体型号
    - 内存类型：DDR4/DDR5
    - 频率：XXXX MHz（说明与主板的兼容性）
    - 单条容量：XX GB
    - 建议购买数量：X条
    - ECC支持：是/否
    - 升级后总内存：XX GB
  - **升级方案说明**：
    - 为什么选择这个容量和频率
    - 如何充分利用现有插槽
    - 是否需要替换现有内存条
    - 升级的优先级评估

### 7. 现有硬盘配置分析（按IP分别分析）
针对每台成功巡检的服务器：
- **服务器IP: [具体IP地址]**
  - 硬盘总容量和使用率
  - 硬盘详细信息（型号、接口、容量）
  - 是否存在存储空间不足或性能问题
  - **监控警报状态**：如果该IP在异常列表中，特别说明

### 8. 现有数据硬盘占用优化分析（按IP分别分析）
针对每台成功巡检的服务器，分析：
- **服务器IP: [具体IP地址]**
  - 分析disk_usage中的高占用目录和文件
  - 识别可清理的临时文件、日志文件、缓存文件
  - 分析snap分区的使用情况和清理可能性
  - 评估数据压缩、归档的可行性
  - 估算优化后可释放的硬盘空间
  - 提供具体的清理命令和操作步骤
  - 清理的风险评估和备份建议

### 9. 硬盘采购建议（按IP分别建议）
针对每台需要升级的服务器：
- **服务器IP: [具体IP地址]**
  - **建议采购硬盘型号**：（如：三星 PM9A3 1.92TB）
  - **接口类型**：SATA/NVMe/SAS
  - **容量**：（如：1TB/2TB）
  - **读写速度**：（如：7000MB/s读取）
  - **耐久性**：（如：3500TBW）
  - **升级理由**：基于使用率和性能需求

### 10. 优先级与实施建议（按紧急程度排序）
- **紧急处理（立即执行）**：
  - **温度异常处理**：温度异常需立即检查机房环境
  - 服务器IP: [具体IP] - 优先进行软件优化或温度处理
  - 建议实施时间：立即

- **紧急升级服务器**：
  - 服务器IP: [具体IP] - 内存/硬盘使用率超过监控阈值
  - 建议实施时间：立即

- **中等优先级服务器**：
  - 服务器IP: [具体IP] - 内存/硬盘使用率接近阈值
  - 建议实施时间：1-2周内

- **低优先级服务器**：
  - 服务器IP: [具体IP] - 性能优化建议
  - 建议实施时间：1-3个月内

### 11. 权限问题解决方案（按IP分别建议）
针对权限不足或巡检失败的服务器：
- **服务器IP: [具体IP]**
  - 具体权限问题描述
  - 解决方案步骤
  - 预计解决时间

**重要提醒：**
1. 必须明确指出温度异常的具体数值和异常时间
2. 对于温度异常状态，需要评估是否属于紧急情况并提供处理建议
3. 每个建议都必须明确指出针对哪台服务器（IP地址）
4. 监控数据中标记为异常的服务器需要特别关注和优先处理
5. 内存升级建议必须详细分析现有配置、主板支持情况，不需要提供价格信息
6. 必须基于实际的硬件数据给出具体可行的升级方案

请确保每个建议都明确指出针对哪台服务器（IP地址），提供具体可操作的建议。
"""

        return self.call_ai_analysis(prompt, temperature=0.3, max_tokens=6000)

    def generate_summary_report(self):
        try:
            print("硬件巡检AI分析报告生成启动")
            logger.info("开始生成硬件巡检AI分析报告")

            ai_analysis = self.analyze_hardware_data()

            temp_info = ""
            try:
                system_data = self.load_json_file(self.system_file)
                env_monitoring = system_data.get('environment_monitoring', {})
                abnormal_details = env_monitoring.get('abnormal_environment_details', [])

                for detail in abnormal_details:
                    if detail.get('type') == '温度':
                        temp_value = detail.get('value')
                        temp_status = detail.get('status')
                        temp_time = detail.get('inspection_time')
                        temp_info = f"\n- **温度异常警报**: {temp_value}度 状态:{temp_status} 检测时间:{temp_time}"
                        break
            except:
                pass

            report_content = f"""# 硬件巡检AI分析报告（含环境监控）

生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 数据来源文件
- 内存巡检数据: {self.memory_file}  
- 硬盘巡检数据: {self.disk_file}
- 系统监控数据: {self.system_file}

## 文件状态检查
- 内存数据文件存在: {'是' if os.path.exists(self.memory_file) else '否'}
- 硬盘数据文件存在: {'是' if os.path.exists(self.disk_file) else '否'}
- 系统监控数据文件存在: {'是' if os.path.exists(self.system_file) else '否'}{temp_info}

## 详细硬件分析与采购建议（含环境监控和温度异常分析）

{ai_analysis}

---"""

            os.makedirs(os.path.dirname(self.output_file), exist_ok=True)
            with open(self.output_file, 'w', encoding='utf-8') as f:
                f.write(report_content)

            print(f"硬件总结报告已保存到: {self.output_file}")
            logger.info(f"硬件总结报告已保存到: {self.output_file}")
            return report_content

        except Exception as e:
            error_msg = f"生成报告失败: {e}"
            print(error_msg)
            logger.error(error_msg)
            return None


def hardware_summary(params=None):
    try:
        print("开始执行硬件巡检AI分析（包含环境监控数据）")
        logger.info("开始生成硬件巡检AI分析报告（包含环境监控数据）")

        summary = HardwareSummary()
        report_content = summary.generate_summary_report()

        if report_content:
            print("硬件巡检AI分析报告生成完成")
            return {
                "success": True,
                "message": "硬件巡检AI分析报告生成完成（包含环境监控数据）",
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "output_file": summary.output_file,
                "report_preview": report_content[:800] + "..." if len(report_content) > 800 else report_content
            }
        else:
            return {
                "success": False,
                "error": "硬件巡检AI分析报告生成失败",
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

    except Exception as e:
        error_msg = f"硬件巡检总结服务异常: {str(e)}"
        print(error_msg)
        logger.error(error_msg)
        return {"success": False, "error": error_msg}


if __name__ == "__main__":
    result = hardware_summary()
    print(json.dumps(result, ensure_ascii=False, indent=2))