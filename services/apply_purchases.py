#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import time
from datetime import datetime
import requests
import re


def extract_memory_upgrade_info_from_inspection(memory_inspection_path):
    """从内存巡检JSON文件中提取内存升级建议信息"""
    print(f"开始从文件提取内存升级信息: {memory_inspection_path}")

    with open(memory_inspection_path, 'r', encoding='utf-8') as f:
        inspection_data = json.load(f)

    results = inspection_data.get("results", {})
    print(f"巡检结果中包含 {len(results)} 个服务器")

    memory_upgrade_records = []

    for server_ip, server_data in results.items():
        print(f"处理服务器: {server_ip}, 状态: {server_data.get('status', '未知')}")

        if server_data.get("status") != "巡检成功":
            print(f"跳过服务器 {server_ip}: 巡检状态不是成功")
            continue

        memory_usage = server_data.get("memory_usage", {})
        hardware_info = server_data.get("hardware_info", {})
        motherboard_info = server_data.get("motherboard_info", {})
        top_processes = server_data.get("top_processes", [])
        analysis = server_data.get("analysis", {})

        upgrade_reasons = []
        usage_percent = memory_usage.get("usage_percent", 0)

        print(f"服务器 {server_ip} 内存使用率: {usage_percent}%")

        if usage_percent > 70:
            upgrade_reasons.append(f"内存使用率{usage_percent}%，远超安全阈值70%")

        current_memory_gb = hardware_info.get("total_installed_memory_gb", 0)
        max_memory_str = motherboard_info.get("max_total_memory", "32GB")
        max_memory_gb = int(max_memory_str.replace("GB", "").replace(" (估算)", ""))

        if current_memory_gb < max_memory_gb:
            upgrade_reasons.append(f"主板支持最大{max_memory_gb}GB，当前仅安装{current_memory_gb}GB")

        memory_modules = hardware_info.get("memory_modules", [])
        if len(memory_modules) > 1:
            sizes = [int(module.get("size", "0 GB").replace(" GB", "")) for module in memory_modules]
            if len(set(sizes)) > 1:
                upgrade_reasons.append("当前使用不同容量内存条，影响性能和扩展性")

        high_memory_processes = []
        for process in top_processes:
            mem_percent = float(process.get("memory_percent", 0))
            if mem_percent > 10:
                high_memory_processes.append({
                    "command": process.get("command", ""),
                    "pid": process.get("pid", ""),
                    "user": process.get("user", ""),
                    "memory_percent": mem_percent,
                    "memory_usage_kb": int(process.get("memory_usage", 0))
                })

        recommended_capacity = min(max_memory_gb, 32)
        slots = hardware_info.get("total_slots", 2)
        single_capacity = recommended_capacity // slots

        supported_types = motherboard_info.get("supported_memory_types", [])
        highest_speed = "DDR4-2666"
        if "DDR4-2666" in supported_types:
            highest_speed = "DDR4-2666"
        elif "DDR4-2400" in supported_types:
            highest_speed = "DDR4-2400"
        else:
            highest_speed = "DDR4-2133"

        priority = "中等"
        if usage_percent > 90:
            priority = "紧急"
        elif usage_percent > 80:
            priority = "高"
        elif usage_percent > 70:
            priority = "中等"
        else:
            priority = "低"

        current_time = time.time()
        current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        memory_upgrade_data = {
            "time": current_time,
            "datetime": current_datetime,
            "inspection_source_time": inspection_data.get("generation_time", ""),
            "server_ip": server_ip,
            "applied": 0,
            "appliedtime": None,
            "solved": 0,
            "solvedtime": None,
            "pricing_request": 0,
            "current_memory_status": {
                "total_capacity_gb": current_memory_gb,
                "total_capacity_display": memory_usage.get("total_memory", ""),
                "used_memory": memory_usage.get("used_memory", ""),
                "available_memory": memory_usage.get("available_memory", ""),
                "usage_percentage": usage_percent,
                "usage_status": analysis.get("status", "正常"),
                "memory_modules": memory_modules,
                "slots_info": {
                    "total_slots": hardware_info.get("total_slots", 0),
                    "installed_slots": hardware_info.get("installed_slots", 0),
                    "empty_slots": hardware_info.get("empty_slots", 0)
                }
            },
            "motherboard_info": {
                "manufacturer": motherboard_info.get("manufacturer", ""),
                "product_name": motherboard_info.get("product_name", ""),
                "version": motherboard_info.get("version", ""),
                "chipset": motherboard_info.get("chipset", "未知"),
                "max_memory_capacity_gb": max_memory_gb,
                "max_memory_per_slot_gb": int(
                    motherboard_info.get("max_memory_per_slot", "16GB").replace("GB", "").replace(" (估算)", "")),
                "total_slots": hardware_info.get("total_slots", 0),
                "supported_memory_types": supported_types,
                "recommended_slots": motherboard_info.get("recommended_slots", 2)
            },
            "system_performance": {
                "ssh_connection_status": server_data.get("ssh_connection", {}).get("status", ""),
                "system_uptime": server_data.get("system_info", {}).get("uptime", ""),
                "high_memory_processes": high_memory_processes,
                "warnings": analysis.get("warnings", []),
                "analysis_recommendations": analysis.get("recommendations", [])
            },
            "recommended_upgrade": {
                "memory_model": f"推荐 {highest_speed} {single_capacity}GB 内存条",
                "memory_type": "DDR4",
                "frequency": highest_speed.replace("DDR4-", "") + " MHz",
                "single_capacity_gb": single_capacity,
                "quantity": slots,
                "total_capacity_after_upgrade_gb": recommended_capacity,
                "priority": priority,
                "upgrade_method": "替换现有内存条" if hardware_info.get("empty_slots", 0) == 0 else "增加内存条",
                "compatibility_notes": f"确保选择与主板{motherboard_info.get('product_name', '')}兼容的内存"
            },
            "pricing_info": {
                "suggest_price": "",
                "currency": "CNY",
                "suggest_user": "",
                "suggest_time": ""
            },
            "upgrade_reasons": upgrade_reasons,
            "upgrade_impact_analysis": {
                "expected_performance_improvement": f"预计性能提升{max(20, min(100 - usage_percent, 50))}%",
                "memory_pressure_relief": f"内存压力将从{usage_percent}%降低到{max(30, usage_percent * current_memory_gb / recommended_capacity)}%",
                "system_stability": "提升系统稳定性，减少内存不足导致的应用崩溃",
                "multitasking_capability": "增强多任务处理能力"
            },
            "upgrade_timeline": {
                "procurement_time": "1-3个工作日",
                "installation_time": "30分钟",
                "testing_time": "2小时",
                "total_downtime": "2.5小时",
                "recommended_maintenance_window": "非工作时间或周末"
            }
        }

        print(f"为服务器 {server_ip} 生成升级建议，优先级: {priority}")
        memory_upgrade_records.append(memory_upgrade_data)

    print(f"共生成 {len(memory_upgrade_records)} 条内存升级记录")
    return memory_upgrade_records


def extract_json_from_response(content):
    """从响应内容中提取JSON数据"""
    try:
        # 清理响应内容
        content = content.strip()

        # 方法1：查找完整的JSON数组
        json_array_pattern = r'\[[\s\S]*\]'
        array_matches = re.findall(json_array_pattern, content)

        for match in array_matches:
            try:
                result = json.loads(match)
                if isinstance(result, list) and len(result) > 0:
                    return result
            except json.JSONDecodeError:
                continue

        # 方法2：查找单个JSON对象
        json_object_pattern = r'\{[\s\S]*?\}'
        object_matches = re.findall(json_object_pattern, content)

        valid_objects = []
        for match in object_matches:
            try:
                obj = json.loads(match)
                if isinstance(obj, dict) and 'server_ip' in obj:
                    valid_objects.append(obj)
            except json.JSONDecodeError:
                continue

        if valid_objects:
            return valid_objects

        # 方法3：尝试分行解析JSON对象
        lines = content.split('\n')
        current_json = ""
        bracket_count = 0
        valid_objects = []

        for line in lines:
            if '{' in line or current_json:
                current_json += line.strip()
                bracket_count += line.count('{') - line.count('}')

                if bracket_count == 0 and current_json:
                    try:
                        obj = json.loads(current_json)
                        if isinstance(obj, dict) and 'server_ip' in obj:
                            valid_objects.append(obj)
                    except json.JSONDecodeError:
                        pass
                    current_json = ""

        if valid_objects:
            return valid_objects

        # 方法4：尝试修复JSON格式
        try:
            # 移除可能的前后缀文本
            start_idx = content.find('[')
            if start_idx == -1:
                start_idx = content.find('{')

            end_idx = content.rfind(']')
            if end_idx == -1:
                end_idx = content.rfind('}')

            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                json_part = content[start_idx:end_idx + 1]
                return json.loads(json_part)
        except:
            pass

        return None

    except Exception as e:
        print(f"JSON提取失败: {str(e)}")
        return None


def call_qwen_api(inspection_data):
    """调用千问大模型API分析内存巡检数据"""
    BASE_URL = "http://192.168.101.214:6007"
    CHAT_ENDPOINT = "/v1/chat/completions"
    MODEL_NAME = "Qwen3-32B-AWQ"

    url = BASE_URL + CHAT_ENDPOINT

    headers = {
        "Content-Type": "application/json"
    }

    prompt = f"""
请分析以下内存巡检数据，为每个服务器生成详细的内存升级建议。

内存巡检数据：
{json.dumps(inspection_data, ensure_ascii=False, indent=2)}

请为每个服务器生成包含以下信息的JSON格式数据，确保返回的是有效的JSON数组格式：

要求：
1. 基本信息：时间戳（必须是数字类型的Unix时间戳）、服务器IP、申请和解决状态
2. pricing_request：必须设置为0
3. 当前内存状态：容量、使用率、内存条详情、插槽信息
4. 主板信息：制造商、型号、支持的最大内存、插槽数量
5. 系统性能：高内存占用进程、系统运行时间、连接状态
6. 推荐升级方案：内存型号、规格、数量、优先级（不包含价格信息）
7. 价格信息：包含suggest_price（空）、currency（CNY）、suggest_user（空）、suggest_time（空）
8. 升级理由：具体的升级必要性分析
9. 影响分析：预期性能提升、内存压力缓解程度
10. 升级时间规划：采购、安装、测试时间

注意：
- 价格相关字段请留空，用于后续手动填写
- pricing_request字段必须设置为0
- time字段必须是数字类型的Unix时间戳，不要使用字符串
- 请只返回JSON数组，不要包含其他解释文字
- 确保JSON格式正确，可以被直接解析

请返回格式如下的JSON数组，必须包含pricing_request字段：
[
  {{
    "time": 1717747294.123,
    "datetime": "2025-06-07 15:21:34",
    "server_ip": "服务器IP",
    "applied": 0,
    "solved": 0,
    "pricing_request": 0,
    "pricing_info": {{
      "suggest_price": "",
      "currency": "CNY",
      "suggest_user": "",
      "suggest_time": ""
    }},
    ...其他字段
  }}
]
"""

    data = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.1,
        "max_tokens": 4000,
        "stream": False
    }

    try:
        print(f"正在调用API: {url}")
        response = requests.post(url, headers=headers, json=data, timeout=60)
        response.raise_for_status()

        result = response.json()
        print(f"API响应状态: {response.status_code}")

        if "choices" in result and len(result["choices"]) > 0:
            content = result["choices"][0]["message"]["content"]
            print(f"API返回内容长度: {len(content)}")
            print(f"API返回内容前500字符: {content[:500]}")

            # 使用改进的JSON提取方法
            result_data = extract_json_from_response(content)

            if result_data:
                print(f"成功解析JSON，记录数: {len(result_data) if isinstance(result_data, list) else 1}")

                # 确保返回列表格式
                if not isinstance(result_data, list):
                    result_data = [result_data]

                # 更新价格字段和修正时间戳格式
                for item in result_data:
                    print(f"处理API返回的记录: {item.get('server_ip', '未知')}")
                    # 修正时间戳格式问题
                    fix_timestamp_format(item)
                    # 确保所有必要字段存在
                    ensure_required_fields(item)

                return result_data
            else:
                print("JSON解析失败，返回None")
                return None
        else:
            print("API响应中没有找到choices字段")
            return None

    except requests.exceptions.RequestException as e:
        print(f"API请求失败: {str(e)}")
        return None
    except json.JSONDecodeError as e:
        print(f"API响应JSON解析失败: {str(e)}")
        return None
    except Exception as e:
        print(f"API调用发生未知错误: {str(e)}")
        return None


def fix_timestamp_format(data):
    """修正时间戳格式问题"""
    try:
        # 如果time字段是字符串，尝试转换
        if "time" in data:
            time_value = data["time"]
            if isinstance(time_value, str):
                try:
                    # 尝试解析日期时间字符串
                    dt = datetime.strptime(time_value, "%Y-%m-%d %H:%M:%S")
                    data["time"] = dt.timestamp()
                    print(f"修正时间戳: {time_value} -> {data['time']}")
                except ValueError:
                    # 如果解析失败，使用当前时间
                    data["time"] = time.time()
                    print(f"时间戳解析失败，使用当前时间: {data['time']}")
            elif not isinstance(time_value, (int, float)):
                # 如果既不是字符串也不是数字，使用当前时间
                data["time"] = time.time()
                print(f"时间戳格式错误，使用当前时间: {data['time']}")
        else:
            # 如果没有time字段，添加当前时间戳
            data["time"] = time.time()
            print(f"添加时间戳字段: {data['time']}")
    except Exception as e:
        print(f"修正时间戳时发生错误: {str(e)}")
        data["time"] = time.time()


def ensure_required_fields(data):
    """确保所有必需字段存在并重置指定字段为空或0"""
    print(f"检查记录字段完整性: {data.get('server_ip', '未知')}")

    # 强制重置指定字段
    data["applied"] = 0
    data["solved"] = 0
    data["pricing_request"] = 0
    data["appliedtime"] = None
    data["solvedtime"] = None

    # 确保pricing_info字段存在且为空
    data["pricing_info"] = {
        "suggest_price": "",
        "currency": "CNY",
        "suggest_user": "",
        "suggest_time": ""
    }

    # 如果recommended_upgrade字段存在，删除价格相关的子字段
    if "recommended_upgrade" in data:
        price_related_keys = ["estimated_cost_range", "cost", "price", "estimated_unit_price", "estimated_total_cost"]
        for key in price_related_keys:
            if key in data["recommended_upgrade"]:
                del data["recommended_upgrade"][key]
                print(f"删除价格相关字段: {key}")

    print(f"字段重置完成，pricing_request = {data.get('pricing_request', '缺失')}")


def safe_timestamp_conversion(time_value):
    """安全地转换时间戳"""
    try:
        if isinstance(time_value, str):
            # 尝试解析日期时间字符串
            try:
                dt = datetime.strptime(time_value, "%Y-%m-%d %H:%M:%S")
                return dt.timestamp()
            except ValueError:
                try:
                    # 尝试其他格式
                    dt = datetime.strptime(time_value, "%Y-%m-%d")
                    return dt.timestamp()
                except ValueError:
                    # 如果都解析失败，返回当前时间
                    return time.time()
        elif isinstance(time_value, (int, float)):
            return float(time_value)
        else:
            return time.time()
    except:
        return time.time()


def generate_memory_id(server_ip, current_time, existing_data):
    """生成MEM开头的唯一编号，不包含特殊符号"""
    ip_parts = server_ip.split('.')
    ip_suffix = ip_parts[-1] if len(ip_parts) == 4 else "000"

    # 安全地转换时间戳
    timestamp = safe_timestamp_conversion(current_time)
    current_date = datetime.fromtimestamp(timestamp).strftime("%Y%m%d")

    # 获取所有现有的memory_id
    existing_memory_ids = set()
    for record in existing_data:
        memory_id = record.get("memory_id", "")
        if memory_id:
            existing_memory_ids.add(memory_id)

    # 生成基础ID格式：MEM + IP后缀(3位) + 日期(8位) + 序号(3位)
    sequence = 1
    while True:
        memory_id = f"MEM{ip_suffix.zfill(3)}{current_date}{sequence:03d}"
        if memory_id not in existing_memory_ids:
            return memory_id
        sequence += 1
        # 防止无限循环
        if sequence > 999:
            # 如果当天序号超过999，使用时间戳的后几位
            timestamp_suffix = str(int(timestamp))[-3:]
            memory_id = f"MEM{ip_suffix.zfill(3)}{current_date}{timestamp_suffix}"
            if memory_id not in existing_memory_ids:
                return memory_id
            # 最后的备选方案
            return f"MEM{ip_suffix.zfill(3)}{current_date}{int(timestamp) % 1000:03d}"


def generate_record_id(existing_data, current_date):
    """生成记录ID：日期+编号格式，不包含特殊符号"""
    # 获取所有现有的record_id
    existing_record_ids = set()
    for record in existing_data:
        record_id = record.get("record_id", "")
        if record_id:
            existing_record_ids.add(record_id)

    # 生成格式：日期(8位) + 序号(3位)
    sequence = 1
    while True:
        record_id = f"{current_date}{sequence:03d}"
        if record_id not in existing_record_ids:
            return record_id
        sequence += 1
        # 防止无限循环
        if sequence > 999:
            # 使用当前时间戳的后几位作为序号
            timestamp_suffix = int(time.time()) % 1000
            record_id = f"{current_date}{timestamp_suffix:03d}"
            if record_id not in existing_record_ids:
                return record_id
            # 最后的备选方案
            return f"{current_date}{int(time.time()) % 10000:04d}"


def save_json_overwrite(json_file_path, new_records):
    """完全覆盖保存JSON数据 - 清空原有数据并写入最新数据"""
    print(f"\n开始覆盖保存数据到: {json_file_path}")
    print(f"待写入的新记录数: {len(new_records)}")

    current_date = datetime.now().strftime("%Y%m%d")

    # 处理新记录，为每条记录生成唯一ID
    processed_records = []

    for index, new_data in enumerate(new_records):
        server_ip = new_data.get("server_ip")
        print(f"处理服务器 {index + 1}/{len(new_records)}: {server_ip}")

        # 确保所有必需字段存在并重置指定字段
        ensure_required_fields(new_data)

        # 安全地获取和转换时间戳
        current_time = new_data.get("time", time.time())
        current_time = safe_timestamp_conversion(current_time)
        new_data["time"] = current_time

        # 生成唯一的memory_id和record_id
        memory_id = generate_memory_id(server_ip, current_time, processed_records)
        new_data["memory_id"] = memory_id

        record_id = generate_record_id(processed_records, current_date)
        new_data["record_id"] = record_id
        new_data["inspection_date"] = current_date

        processed_records.append(new_data)

        print(f"  记录ID: {record_id}")
        print(f"  内存编号: {memory_id}")
        print(f"  applied: {new_data.get('applied', 0)}")
        print(f"  solved: {new_data.get('solved', 0)}")
        print(f"  pricing_request: {new_data.get('pricing_request', 0)}")
        print(f"  suggest_price: '{new_data.get('pricing_info', {}).get('suggest_price', '')}'")

    # 按记录ID排序（最新的在前）
    processed_records.sort(key=lambda x: x.get("record_id", ""), reverse=True)

    # 确保目录存在
    os.makedirs(os.path.dirname(json_file_path), exist_ok=True)

    # 完全覆盖写入文件
    try:
        print(f"正在覆盖写入文件: {json_file_path}")
        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(processed_records, f, ensure_ascii=False, indent=2)
        print(f"文件写入成功！")

        # 验证文件是否真的存在
        if os.path.exists(json_file_path):
            file_size = os.path.getsize(json_file_path)
            print(f"文件验证成功，大小: {file_size} 字节")
        else:
            print("警告：文件写入后仍然不存在！")

    except Exception as e:
        print(f"文件写入失败: {str(e)}")
        raise

    print(f"\n处理结果统计:")
    print(f"  写入的记录数: {len(processed_records)}")
    print(f"  总记录数: {len(processed_records)}")

    return processed_records


def print_generated_json_content(json_file_path):
    """打印生成的JSON文件完整内容"""
    print(f"\n{'=' * 60}")
    print("生成的JSON文件完整内容:")
    print(f"{'=' * 60}")

    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            print(content)
    except Exception as e:
        print(f"读取文件失败: {str(e)}")

    print(f"{'=' * 60}")


def display_record_summary(json_file_path):
    """显示记录摘要信息"""
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"读取文件失败: {str(e)}")
        return

    if not data:
        print("暂无历史记录")
        return

    print("\n=== 内存升级记录摘要 ===")
    print(f"总记录数: {len(data)}")

    ip_stats = {}
    for record in data:
        server_ip = record.get("server_ip", "未知")
        if server_ip not in ip_stats:
            ip_stats[server_ip] = {
                "total": 0,
                "applied": 0,
                "solved": 0,
                "latest_record": "",
                "latest_memory_id": "",
                "latest_priority": "",
                "price_filled": False,
                "price_suggest_user": "",
                "pricing_request": 0
            }

        ip_stats[server_ip]["total"] += 1
        if record.get("applied", 0) == 1:
            ip_stats[server_ip]["applied"] += 1
        if record.get("solved", 0) == 1:
            ip_stats[server_ip]["solved"] += 1

        # 更新pricing_request状态
        ip_stats[server_ip]["pricing_request"] = record.get("pricing_request", 0)

        pricing_info = record.get("pricing_info", {})
        if pricing_info.get("suggest_price") and pricing_info.get("suggest_price") != "":
            ip_stats[server_ip]["price_filled"] = True
            ip_stats[server_ip]["price_suggest_user"] = pricing_info.get("suggest_user", "")

        if not ip_stats[server_ip]["latest_record"]:
            ip_stats[server_ip]["latest_record"] = record.get("record_id", "")
            ip_stats[server_ip]["latest_memory_id"] = record.get("memory_id", "")
            ip_stats[server_ip]["latest_priority"] = record.get("recommended_upgrade", {}).get("priority", "")

    for ip, stats in ip_stats.items():
        print(f"\n服务器IP: {ip}")
        print(f"  总记录数: {stats['total']}")
        print(f"  已申请: {stats['applied']}")
        print(f"  已解决: {stats['solved']}")
        print(f"  价格请求状态: {stats['pricing_request']}")
        print(f"  价格已填写: {'是' if stats['price_filled'] else '否'}")
        if stats['price_filled']:
            print(f"  价格建议人: {stats['price_suggest_user']}")
        print(f"  最新记录: {stats['latest_record']}")
        print(f"  最新内存编号: {stats['latest_memory_id']}")
        print(f"  升级优先级: {stats['latest_priority']}")


def update_price_suggestion(json_file_path, memory_id, suggest_price, suggest_user):
    """更新记录的价格建议"""
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"读取文件失败: {str(e)}")
        return False

    updated = False
    for record in data:
        if record.get("memory_id") == memory_id:
            record["pricing_info"]["suggest_price"] = suggest_price
            record["pricing_info"]["suggest_user"] = suggest_user
            record["pricing_info"]["suggest_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            updated = True
            break

    if updated:
        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"价格建议已更新: {memory_id} - {suggest_price} CNY (建议人: {suggest_user})")
        return True
    else:
        print(f"未找到内存编号: {memory_id}")
        return False


async def apply_purchases(params=None):
    """主函数"""
    try:
        print("【服务011】内存升级建议服务启动")

        # 获取脚本当前路径
        current_script_path = os.path.abspath(__file__)
        print(f"当前脚本路径: {current_script_path}")

        project_root = os.path.dirname(os.path.dirname(current_script_path))
        print(f"计算的项目根路径: {project_root}")

        memory_inspection_path = os.path.join(project_root, "services", "data", "memory_inspection.json")
        memory_update_json_path = os.path.join(project_root, "services", "data", "memory_update.json")

        print(f"输入文件路径: {memory_inspection_path}")
        print(f"输出文件路径: {memory_update_json_path}")

        # 检查输入文件是否存在
        if not os.path.exists(memory_inspection_path):
            print(f"错误：输入文件不存在: {memory_inspection_path}")

            # 尝试在当前目录查找
            current_dir = os.path.dirname(current_script_path)
            alt_path = os.path.join(current_dir, "data", "memory_inspection.json")
            print(f"尝试查找备选路径: {alt_path}")

            if os.path.exists(alt_path):
                memory_inspection_path = alt_path
                memory_update_json_path = os.path.join(current_dir, "data", "memory_update.json")
                print(f"使用备选路径: {memory_inspection_path}")
            else:
                return {
                    "success": False,
                    "error": f"内存巡检文件不存在: {memory_inspection_path}",
                    "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }

        try:
            with open(memory_inspection_path, 'r', encoding='utf-8') as f:
                inspection_data = json.load(f)

            print("正在分析内存巡检数据...")
            print(f"巡检时间: {inspection_data.get('generation_time', '未知')}")
            print(f"巡检服务器数量: {inspection_data.get('inspected_count', 0)}")
            print(f"成功巡检: {inspection_data.get('success_count', 0)}")

            print("\n正在调用千问大模型分析内存升级建议...")
            api_result = call_qwen_api(inspection_data)

            if api_result is not None:
                memory_records = api_result
                print("使用大模型API分析结果")
            else:
                print("大模型API调用失败，使用本地分析方法...")
                memory_records = extract_memory_upgrade_info_from_inspection(memory_inspection_path)

            if not memory_records:
                print("警告：未找到需要升级的内存记录")
                return {
                    "success": False,
                    "error": "未找到需要升级的内存记录",
                    "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }

            # 确保数据目录存在
            data_dir = os.path.dirname(memory_update_json_path)
            print(f"确保数据目录存在: {data_dir}")
            os.makedirs(data_dir, exist_ok=True)

            # 使用覆盖保存方式，清空原有数据并写入最新数据
            processed_records = save_json_overwrite(memory_update_json_path, memory_records)

            print(f"\n内存升级建议已成功保存到: {memory_update_json_path}")
            print(f"检测到记录数量: {len(memory_records)}")
            print(f"写入记录数量: {len(processed_records)}")

            # 打印生成的JSON文件完整内容
            print_generated_json_content(memory_update_json_path)

            # 显示新增记录的详细信息
            for record in processed_records:
                pricing_status = "待填写"
                if record.get("pricing_info", {}).get("suggest_price"):
                    pricing_status = f"{record['pricing_info']['suggest_price']} CNY"

                print(f"\n服务器: {record.get('server_ip', '未知')}")
                print(f"  内存编号: {record.get('memory_id', '未知')}")
                print(f"  记录ID: {record.get('record_id', '未知')}")
                print(f"  当前内存使用率: {record.get('current_memory_status', {}).get('usage_percentage', 0)}%")
                print(f"  升级优先级: {record.get('recommended_upgrade', {}).get('priority', '未知')}")
                print(f"  已申请: {record.get('applied', 0)}")
                print(f"  已解决: {record.get('solved', 0)}")
                print(f"  价格请求状态: {record.get('pricing_request', 0)}")
                print(f"  建议价格: {pricing_status}")

            display_record_summary(memory_update_json_path)

            return {
                "success": True,
                "message": "内存升级建议已生成并保存（覆盖模式）",
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "output_file": memory_update_json_path,
                "records_count": len(memory_records),
                "processed_records": len(processed_records)
            }

        except Exception as e:
            print(f"处理过程中发生错误: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": f"处理过程中发生错误: {str(e)}",
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

    except Exception as e:
        print(f"内存升级建议服务执行失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": f"内存升级建议服务执行失败: {str(e)}",
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }


if __name__ == "__main__":
    import asyncio

    asyncio.run(apply_purchases())