#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import re
import json
import requests
from datetime import datetime
from collections import Counter

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from utils.logger import setup_logger
from config.config import LLM_CONFIG

logger = setup_logger(__name__)


class LogAnalyzer:
    def __init__(self, ai_config=None):
        self.ai_config = ai_config or LLM_CONFIG
        self.default_error_keywords = [
            'error', 'ERROR', 'Error',
            'exception', 'Exception', 'EXCEPTION',
            'fail', 'FAIL', 'Failed', 'FAILED',
            'timeout', 'TIMEOUT', 'Timeout',
            'connection refused', 'connection failed',
            'unable to connect', 'cannot connect',
            'permission denied', 'access denied',
            'no such file', 'file not found',
            'out of memory', 'memory error',
            'disk full', 'no space left',
            'traceback', 'Traceback',
            'warning', 'WARNING', 'Warning',
            'critical', 'CRITICAL', 'Critical',
            'fatal', 'FATAL', 'Fatal'
        ]

    def read_file_content(self, file_path, line_limit=1000, encoding='utf-8'):
        try:
            print(f"    📁 验证日志文件路径: {file_path}")
            
            if not os.path.exists(file_path):
                print(f"    ❌ 日志文件不存在")
                return {
                    "success": False,
                    "error": f"文件不存在: {file_path}"
                }

            file_size = os.path.getsize(file_path)
            file_stat = os.stat(file_path)
            
            print(f"    📊 文件大小: {file_size} 字节")
            print(f"    📅 修改时间: {datetime.fromtimestamp(file_stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"    📖 开始读取日志内容，限制行数: {line_limit}")

            content_lines = []
            with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                for i, line in enumerate(f):
                    if i >= line_limit:
                        break
                    content_lines.append(line.rstrip('\n\r'))

            print(f"    ✅ 日志文件读取完成，实际读取 {len(content_lines)} 行")

            return {
                "success": True,
                "file_path": file_path,
                "file_size": file_size,
                "file_modified": datetime.fromtimestamp(file_stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                "lines_read": len(content_lines),
                "lines_limited": len(content_lines) >= line_limit,
                "content": content_lines
            }

        except UnicodeDecodeError:
            print(f"    🔄 UTF-8编码失败，尝试GBK编码...")
            try:
                with open(file_path, 'r', encoding='gbk', errors='ignore') as f:
                    content_lines = []
                    for i, line in enumerate(f):
                        if i >= line_limit:
                            break
                        content_lines.append(line.rstrip('\n\r'))

                print(f"    ✅ GBK编码读取成功，获取 {len(content_lines)} 行")

                return {
                    "success": True,
                    "file_path": file_path,
                    "encoding_used": "gbk",
                    "lines_read": len(content_lines),
                    "content": content_lines
                }
            except Exception as e:
                print(f"    ❌ 多种编码尝试失败: {e}")
                return {
                    "success": False,
                    "error": f"文件编码读取失败: {str(e)}"
                }
        except Exception as e:
            print(f"    ❌ 文件读取失败: {e}")
            return {
                "success": False,
                "error": f"文件读取失败: {str(e)}"
            }

    def find_error_patterns(self, content_lines, error_keywords=None, context_lines=3):
        print(f"    🔍 开始错误模式识别和关键词匹配...")
        
        if error_keywords is None:
            error_keywords = self.default_error_keywords

        error_matches = []
        keyword_counts = Counter()

        for i, line in enumerate(content_lines):
            line_lower = line.lower()

            found_keywords = []
            for keyword in error_keywords:
                if keyword.lower() in line_lower:
                    found_keywords.append(keyword)
                    keyword_counts[keyword] += 1

            if found_keywords:
                start_idx = max(0, i - context_lines)
                end_idx = min(len(content_lines), i + context_lines + 1)
                context = content_lines[start_idx:end_idx]

                error_matches.append({
                    'line_number': i + 1,
                    'line_content': line,
                    'found_keywords': found_keywords,
                    'context': context,
                    'context_start_line': start_idx + 1
                })

        print(f"    ✅ 错误模式识别完成，发现 {len(error_matches)} 个错误匹配项")

        return {
            'error_matches': error_matches,
            'keyword_counts': dict(keyword_counts),
            'total_errors': len(error_matches)
        }

    def analyze_log_patterns(self, content_lines):
        print(f"    📈 开始日志模式分析和特征提取...")
        
        patterns = {
            'timestamp_formats': [],
            'log_levels': Counter(),
            'ip_addresses': [],
            'common_services': Counter(),
            'file_extensions': Counter()
        }

        timestamp_patterns = [
            r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}',
            r'\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}',
            r'\w{3} \d{2} \d{2}:\d{2}:\d{2}',
        ]

        ip_pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
        log_level_pattern = r'\b(DEBUG|INFO|WARN|WARNING|ERROR|FATAL|CRITICAL)\b'

        sample_size = min(100, len(content_lines))
        print(f"    🔬 分析样本大小: {sample_size} 行")
        
        for line in content_lines[:sample_size]:
            for pattern in timestamp_patterns:
                if re.search(pattern, line):
                    patterns['timestamp_formats'].append(pattern)
                    break

            ips = re.findall(ip_pattern, line)
            patterns['ip_addresses'].extend(ips)

            levels = re.findall(log_level_pattern, line, re.IGNORECASE)
            for level in levels:
                patterns['log_levels'][level.upper()] += 1

            services = ['mysql', 'nginx', 'apache', 'ssh', 'docker', 'systemd', 'kernel']
            for service in services:
                if service in line.lower():
                    patterns['common_services'][service] += 1

        patterns['timestamp_formats'] = list(set(patterns['timestamp_formats']))
        patterns['ip_addresses'] = list(set(patterns['ip_addresses']))
        patterns['log_levels'] = dict(patterns['log_levels'])
        patterns['common_services'] = dict(patterns['common_services'])

        print(f"    ✅ 日志模式分析完成")
        print(f"        🕐 时间戳格式: {len(patterns['timestamp_formats'])} 种")
        print(f"        📊 日志级别: {len(patterns['log_levels'])} 种")
        print(f"        🌐 IP地址: {len(patterns['ip_addresses'])} 个")
        print(f"        🔧 涉及服务: {len(patterns['common_services'])} 个")

        return patterns

    def call_ai_analysis(self, prompt, temperature=0.7, max_tokens=1500, timeout=60):
        try:
            print(f"    🧠 启动AI智能分析引擎...")
            
            url = f"{self.ai_config['base_url']}{self.ai_config['chat_endpoint']}"
            payload = {
                "model": self.ai_config['model_name'],
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
                "max_tokens": max_tokens
            }

            headers = {'Content-Type': 'application/json'}
            
            print(f"    🌐 向AI运维大脑发送日志分析请求...")
            response = requests.post(url, json=payload, headers=headers, timeout=timeout)

            if response.status_code == 200:
                response_data = response.json()
                if 'choices' in response_data and len(response_data['choices']) > 0:
                    print(f"    ✅ AI分析完成，生成专业诊断报告")
                    return response_data['choices'][0]['message']['content']
                else:
                    print(f"    ❌ AI响应格式异常: {response_data}")
                    return f"AI分析响应格式错误: {response_data}"
            else:
                print(f"    ❌ AI分析请求失败: HTTP {response.status_code}")
                return f"AI分析请求失败: HTTP {response.status_code}, {response.text}"
        except requests.exceptions.Timeout:
            print(f"    ⏰ AI分析超时")
            return "AI分析超时，请检查网络连接和AI服务状态"
        except requests.exceptions.ConnectionError:
            print(f"    🌐 AI分析连接失败")
            return "AI分析连接失败，请检查AI服务地址和端口"
        except Exception as e:
            print(f"    💥 AI分析异常: {e}")
            return f"AI分析失败: {str(e)}"

    def analyze_log(self, file_path, line_limit=1000, error_keywords=None,
                    context_lines=3, ai_analysis=True, ai_temperature=0.7, ai_max_tokens=1500):
        try:
            print(f"    🚀 启动智能日志分析系统...")
            
            file_result = self.read_file_content(file_path, line_limit)
            if not file_result['success']:
                return file_result

            content_lines = file_result['content']
            print(f"    🔍 开始多维度日志分析...")
            
            error_analysis = self.find_error_patterns(content_lines, error_keywords, context_lines)
            log_patterns = self.analyze_log_patterns(content_lines)

            ai_result = None
            if ai_analysis:
                print(f"    🧠 准备AI深度分析数据...")
                
                sample_errors = error_analysis['error_matches'][:10]
                sample_content = content_lines[:50]

                prompt = f"""
请分析以下日志文件内容：

=== 文件信息 ===
文件路径: {file_path}
文件大小: {file_result.get('file_size', 0)} 字节
修改时间: {file_result.get('file_modified', 'Unknown')}
读取行数: {len(content_lines)} 行

=== 错误统计 ===
总错误数: {error_analysis['total_errors']}
错误关键词统计: {error_analysis['keyword_counts']}

=== 日志模式 ===
时间戳格式: {log_patterns['timestamp_formats']}
日志级别: {log_patterns['log_levels']}
涉及服务: {log_patterns['common_services']}
IP地址: {log_patterns['ip_addresses'][:10]}

=== 错误样例 ===
{json.dumps(sample_errors, ensure_ascii=False, indent=2)}

=== 日志内容样例 ===
{chr(10).join(sample_content)}

请按以下格式分析：

1. 【日志类型判断】
   - 系统日志/应用日志/错误日志等
   - 主要记录的服务或组件

2. 【错误分析】
   - 主要错误类型和原因
   - 错误的严重程度
   - 是否存在重复错误

3. 【问题诊断】
   - 可能的根本原因
   - 需要关注的异常模式
   - 系统健康状况评估

4. 【解决建议】
   - 立即需要处理的问题
   - 预防性措施
   - 监控改进建议

请保持专业性，建议具体可操作。
"""
                ai_result = self.call_ai_analysis(prompt, ai_temperature, ai_max_tokens)

            print(f"    ✅ 智能日志分析完成")

            return {
                "success": True,
                "file_info": file_result,
                "error_analysis": error_analysis,
                "log_patterns": log_patterns,
                "ai_analysis": ai_result,
                "analysis_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "summary": {
                    "file_path": file_path,
                    "lines_analyzed": len(content_lines),
                    "errors_found": error_analysis['total_errors'],
                    "main_error_types": list(error_analysis['keyword_counts'].keys()),
                    "log_levels_found": list(log_patterns['log_levels'].keys()),
                    "services_mentioned": list(log_patterns['common_services'].keys())
                }
            }

        except Exception as e:
            print(f"    ❌ 智能日志分析系统异常: {e}")
            return {
                "success": False,
                "error": f"日志分析异常: {str(e)}",
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }


def log_file_analysis(params=None):
    try:
        print("🚀 启动AI智能日志分析服务...")
        logger.info("📊 开始执行日志文件分析")

        if not params or 'file_path' not in params:
            print("❌ 缺少必需参数: file_path")
            return {
                "success": False,
                "error": "缺少必需参数: file_path",
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

        file_path = params['file_path']
        line_limit = params.get('line_limit', 1000)
        error_keywords = params.get('error_keywords', [])
        context_lines = params.get('context_lines', 3)
        ai_analysis = params.get('ai_analysis', True)
        ai_temperature = params.get('ai_temperature', 0.7)
        ai_max_tokens = params.get('ai_max_tokens', 1500)

        print(f"📁 目标日志文件: {file_path}")
        print(f"📊 分析参数配置:")
        print(f"    📖 读取行数限制: {line_limit}")
        print(f"    🔍 上下文行数: {context_lines}")
        print(f"    🧠 AI分析: {'启用' if ai_analysis else '禁用'}")
        
        if error_keywords:
            print(f"    🎯 自定义关键词: {len(error_keywords)} 个")

        analyzer = LogAnalyzer()
        result = analyzer.analyze_log(
            file_path=file_path,
            line_limit=line_limit,
            error_keywords=error_keywords,
            context_lines=context_lines,
            ai_analysis=ai_analysis,
            ai_temperature=ai_temperature,
            ai_max_tokens=ai_max_tokens
        )

        if result and result.get('success'):
            print(f"✅ 智能日志分析服务完成: {file_path}")
            print(f"📊 分析结果:")
            print(f"    📝 读取行数: {result['analysis_result']['summary']['lines_analyzed']}")
            print(f"    🚨 发现错误: {result['analysis_result']['summary']['errors_found']} 个")
            print(f"    🔧 涉及服务: {len(result['analysis_result']['summary']['services_mentioned'])} 个")
            
            logger.info(f"📊 日志文件分析完成: {file_path}")
            return {
                "success": True,
                "message": f"日志文件分析完成: {file_path}",
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "file_path": file_path,
                "analysis_result": result
            }
        else:
            error_msg = result.get('error', '分析失败') if result else '分析失败'
            print(f"❌ 智能日志分析失败: {error_msg}")
            logger.error(f"🚨 日志文件分析失败: {error_msg}")
            return {
                "success": False,
                "error": f"日志文件分析失败: {error_msg}",
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

    except Exception as e:
        print(f"❌ AI智能日志分析服务异常: {e}")
        logger.error(f"🚨 日志文件分析服务异常: {e}")
        return {
            "success": False,
            "error": f"日志文件分析服务异常: {str(e)}",
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }


if __name__ == "__main__":
    test_params = {
        'file_path': '/var/log/syslog',
        'line_limit': 500,
        'ai_analysis': True
    }
    result = log_file_analysis(test_params)
    print(f"测试结果: {result}")
