#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import re
from datetime import datetime, timedelta, time as dt_time
import requests
from decimal import Decimal

import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from utils.logger import setup_logger
from utils.database import get_connection
from config.config import LLM_CONFIG

logger = setup_logger(__name__)


def convert_decimal(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: convert_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimal(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(convert_decimal(item) for item in obj)
    return obj


def safe_float(value, default=0.0):
    try:
        if value is None:
            return default
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_int(value, default=0):
    try:
        if value is None:
            return default
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_datetime_format(dt_obj, format_str='%Y-%m-%d %H:%M:%S'):
    try:
        if dt_obj is None:
            return ''
        if isinstance(dt_obj, str):
            try:
                parsed_dt = datetime.strptime(dt_obj, '%Y-%m-%d %H:%M:%S')
                return parsed_dt.strftime(format_str)
            except:
                return str(dt_obj)
        elif isinstance(dt_obj, datetime):
            return dt_obj.strftime(format_str)
        else:
            return str(dt_obj)
    except Exception as e:
        logger.warning(f"⚠️ 日期格式化失败: {dt_obj}, 错误: {e}")
        return str(dt_obj) if dt_obj else ''


def safe_date_format(date_obj, format_str='%Y-%m-%d'):
    try:
        if date_obj is None:
            return ''
        if isinstance(date_obj, str):
            return str(date_obj)
        elif hasattr(date_obj, 'strftime'):
            return date_obj.strftime(format_str)
        else:
            return str(date_obj)
    except Exception as e:
        logger.warning(f"⚠️ 日期格式化失败: {date_obj}, 错误: {e}")
        return str(date_obj) if date_obj else ''


def get_daily_date_range():
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    yesterday_start = datetime.combine(yesterday, dt_time.min)
    yesterday_end = datetime.combine(yesterday, dt_time.max)
    return yesterday_start, yesterday_end, yesterday


def generate_unique_id(prefix='oas'):
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    return f"{prefix}{timestamp}"


def fetch_server_metrics(conn, start_time, end_time):
    print(f"    📊 启动数据库连接，查询服务器性能指标...")
    with conn.cursor() as cursor:
        query = """
                SELECT ip,
                       cpu_usage,
                       cpu_status,
                       memory_usage,
                       memory_status,
                       disk_usage,
                       disk_status,
                       network_status,
                       packet_loss_status,
                       user_load_status,
                       collect_time
                FROM howso_server_performance_metrics
                WHERE collect_time BETWEEN %s AND %s
                """
        cursor.execute(query, (start_time, end_time))
        results = cursor.fetchall()
        print(f"    ✅ 服务器性能数据采集完成，共获取 {len(results)} 条性能记录")
        return [dict(zip([desc[0] for desc in cursor.description], convert_decimal(row))) for row in results]


def fetch_service_status(conn, start_time, end_time):
    print(f"    🔧 查询服务状态监控数据...")
    with conn.cursor() as cursor:
        query = """
                SELECT platform,
                       server_name,
                       server_ip,
                       service_name,
                       status,
                       process_status,
                       response_time,
                       insert_time
                FROM plat_service_monitoring
                WHERE insert_time BETWEEN %s AND %s
                """
        cursor.execute(query, (start_time, end_time))
        results = cursor.fetchall()
        print(f"    ✅ 服务状态数据采集完成，共获取 {len(results)} 条服务记录")
        return [dict(zip([desc[0] for desc in cursor.description], convert_decimal(row))) for row in results]


def fetch_nas_pools(conn, start_date, end_date):
    print(f"    💾 查询存储池监控数据...")
    with conn.cursor() as cursor:
        query = """
                SELECT server_name,
                       pool_name,
                       used_space,
                       used_space_unit,
                       available_space,
                       available_space_unit,
                       usage_percentage,
                       status,
                       inspection_date,
                       inspection_time
                FROM nas_pools_detail
                WHERE inspection_date BETWEEN %s AND %s
                """
        cursor.execute(query, (start_date, end_date))
        results = cursor.fetchall()
        print(f"    ✅ 存储池数据采集完成，共获取 {len(results)} 条存储记录")
        return [dict(zip([desc[0] for desc in cursor.description], convert_decimal(row))) for row in results]


def fetch_power_monitoring(conn, start_time, end_time):
    try:
        print(f"    ⚡ 查询电力监控数据...")
        with conn.cursor() as cursor:
            twelve_hours_ago = datetime.now() - timedelta(hours=12)
            query = """
                    SELECT battery_status,
                           ups_supply_time,
                           avg_input_voltage,
                           avg_input_voltage_status,
                           avg_output_voltage,
                           avg_output_voltage_status,
                           avg_input_current,
                           avg_input_current_status,
                           avg_output_current,
                           avg_output_current_status,
                           avg_temperature,
                           avg_temperature_status,
                           avg_humidity,
                           avg_humidity_status,
                           inspection_time
                    FROM power_monitoring_avg_data
                    WHERE inspection_time >= %s
                    ORDER BY inspection_time DESC
                    """
            cursor.execute(query, (twelve_hours_ago,))
            results = cursor.fetchall()
            print(f"    ✅ 电力监控数据采集完成，共获取 {len(results)} 条电力记录")
            return [dict(zip([desc[0] for desc in cursor.description], convert_decimal(row))) for row in results]
    except Exception as e:
        print(f"    ⚠️ 电力监控数据采集遇到问题: {e}")
        logger.error(f"🚨 Error fetching power monitoring data: {e}")
        return []


def format_timedelta_as_time(td):
    total_seconds = int(td.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def get_exceptions(server_metrics, service_status, nas_pools, power_monitoring):
    print(f"    🔍 开始识别和分析异常数据...")
    
    exceptions = {
        "服务器异常": [],
        "服务异常": [],
        "存储异常": [],
        "电力异常": []
    }

    for metric in server_metrics:
        if (metric.get('cpu_status') != '正常' or
                metric.get('memory_status') != '正常' or
                metric.get('disk_status') != '正常' or
                metric.get('network_status') != '正常' or
                metric.get('packet_loss_status') != '正常' or
                metric.get('user_load_status') != '正常'):

            exception_item = {
                "IP": metric.get('ip', ''),
                "时间": safe_datetime_format(metric.get('collect_time'))
            }

            if metric.get('cpu_status') != '正常':
                exception_item["CPU状态"] = f"{metric.get('cpu_usage')}% ({metric.get('cpu_status')})"
            if metric.get('memory_status') != '正常':
                exception_item["内存状态"] = f"{metric.get('memory_usage')}% ({metric.get('memory_status')})"
            if metric.get('disk_status') != '正常':
                exception_item["磁盘状态"] = f"{metric.get('disk_usage')}% ({metric.get('disk_status')})"
            if metric.get('network_status') != '正常':
                exception_item["网络状态"] = metric.get('network_status')
            if metric.get('packet_loss_status') != '正常':
                exception_item["丢包状态"] = metric.get('packet_loss_status')
            if metric.get('user_load_status') != '正常':
                exception_item["用户负载状态"] = metric.get('user_load_status')

            exceptions["服务器异常"].append(exception_item)

    for service in service_status:
        if service.get('status') != '正常' or service.get('process_status') == '未运行':
            exceptions["服务异常"].append({
                "平台": service.get('platform', ''),
                "服务器": f"{service.get('server_name', '')}({service.get('server_ip', '')})",
                "服务名称": service.get('service_name', ''),
                "状态": service.get('status', ''),
                "进程状态": service.get('process_status', ''),
                "响应时间": service.get('response_time', ''),
                "检测时间": safe_datetime_format(service.get('insert_time'))
            })

    for pool in nas_pools:
        if pool.get('status') != '正常':
            inspection_time_str = ""
            if isinstance(pool.get('inspection_time'), timedelta):
                inspection_time_str = format_timedelta_as_time(pool.get('inspection_time'))
            else:
                try:
                    if hasattr(pool.get('inspection_time'), 'strftime'):
                        inspection_time_str = pool.get('inspection_time').strftime('%H:%M:%S')
                    else:
                        inspection_time_str = str(pool.get('inspection_time', ''))
                except:
                    inspection_time_str = str(pool.get('inspection_time', ''))

            exceptions["存储异常"].append({
                "服务器": pool.get('server_name', ''),
                "存储池": pool.get('pool_name', ''),
                "已用空间": f"{pool.get('used_space', '')} {pool.get('used_space_unit', '')}",
                "可用空间": f"{pool.get('available_space', '')} {pool.get('available_space_unit', '')}",
                "使用率": f"{pool.get('usage_percentage', '')}%",
                "状态": pool.get('status', ''),
                "检测日期": safe_date_format(pool.get('inspection_date')),
                "检测时间": inspection_time_str
            })

    for power in power_monitoring:
        if (power.get('battery_status') != '正常' or
                power.get('avg_input_voltage_status') != '正常' or
                power.get('avg_output_voltage_status') != '正常' or
                power.get('avg_input_current_status') != '正常' or
                power.get('avg_output_current_status') != '正常' or
                power.get('avg_temperature_status') != '正常' or
                power.get('avg_humidity_status') != '正常'):

            power_item = {
                "检测时间": safe_datetime_format(power.get('inspection_time')),
                "电池状态": power.get('battery_status', ''),
                "UPS供电时间": f"{power.get('ups_supply_time', '')}分钟"
            }

            if power.get('avg_input_voltage_status') != '正常':
                power_item["输入电压"] = f"{power.get('avg_input_voltage')}V ({power.get('avg_input_voltage_status')})"
            if power.get('avg_output_voltage_status') != '正常':
                power_item[
                    "输出电压"] = f"{power.get('avg_output_voltage')}V ({power.get('avg_output_voltage_status')})"
            if power.get('avg_input_current_status') != '正常':
                power_item["输入电流"] = f"{power.get('avg_input_current')}A ({power.get('avg_input_current_status')})"
            if power.get('avg_output_current_status') != '正常':
                power_item[
                    "输出电流"] = f"{power.get('avg_output_current')}A ({power.get('avg_output_current_status')})"
            if power.get('avg_temperature_status') != '正常':
                power_item["温度"] = f"{power.get('avg_temperature')}°C ({power.get('avg_temperature_status')})"
            if power.get('avg_humidity_status') != '正常':
                power_item["湿度"] = f"{power.get('avg_humidity')}% ({power.get('avg_humidity_status')})"

            exceptions["电力异常"].append(power_item)

    filtered_exceptions = {k: v for k, v in exceptions.items() if v}
    print(f"    ✅ 异常数据识别完成，发现 {len(filtered_exceptions)} 类异常情况")
    
    return filtered_exceptions


def limit_exception_data(exception_data, max_items_per_category=50):
    print(f"    🔧 优化异常数据结构，避免AI模型token限制...")
    
    limited_data = {}
    total_limited = 0

    for category, exceptions in exception_data.items():
        if exceptions:
            original_count = len(exceptions)
            limited_exceptions = exceptions[:max_items_per_category]
            limited_data[category] = limited_exceptions

            if original_count > max_items_per_category:
                limited_count = original_count - max_items_per_category
                total_limited += limited_count
                print(f"    📊 {category}: 原有{original_count}条异常，优化为{max_items_per_category}条")
                logger.info(
                    f"📊 {category}: 原有{original_count}条异常，限制为{max_items_per_category}条，省略了{limited_count}条")

    if total_limited > 0:
        print(f"    ✅ 数据优化完成，共优化{total_limited}条异常数据")
        logger.info(f"📊 总共省略了{total_limited}条异常数据以适应AI模型限制")

    return limited_data


def format_exception_data_for_storage(exception_data):
    if not exception_data:
        return json.dumps({"summary": "无异常数据", "details": {}}, ensure_ascii=False)

    summary = {}
    formatted_details = {}

    for category, exceptions in exception_data.items():
        if exceptions:
            summary[category] = f"{len(exceptions)}条异常"
            formatted_details[category] = []

            for i, exc in enumerate(exceptions, 1):
                formatted_exc = {
                    "序号": i,
                    "详情": exc
                }
                formatted_details[category].append(formatted_exc)

    result = {
        "异常摘要": summary,
        "异常总数": sum(len(exceptions) for exceptions in exception_data.values()),
        "生成时间": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "详细信息": formatted_details
    }

    return json.dumps(result, ensure_ascii=False, indent=2)


def prepare_data_summary(server_metrics, service_status, nas_pools, power_monitoring):
    print(f"    📈 开始聚合和分析日度监控数据...")
    
    server_ips = set([m.get('ip') for m in server_metrics if m.get('ip')])
    abnormal_cpu = sum(1 for m in server_metrics if m.get('cpu_status') != '正常')
    abnormal_memory = sum(1 for m in server_metrics if m.get('memory_status') != '正常')
    abnormal_disk = sum(1 for m in server_metrics if m.get('disk_status') != '正常')
    abnormal_network = sum(1 for m in server_metrics if m.get('network_status') != '正常')
    abnormal_packet_loss = sum(1 for m in server_metrics if m.get('packet_loss_status') != '正常')
    abnormal_user_load = sum(1 for m in server_metrics if m.get('user_load_status') != '正常')

    services = len(service_status)
    abnormal_services = sum(1 for s in service_status if s.get('status') != '正常')
    stopped_processes = sum(1 for s in service_status if s.get('process_status') == '未运行')
    platforms = set([s.get('platform') for s in service_status if s.get('platform')])

    total_pools = len(nas_pools)
    abnormal_pools = sum(1 for p in nas_pools if p.get('status') != '正常')
    high_usage_pools = sum(1 for p in nas_pools if safe_float(p.get('usage_percentage', 0)) > 80)

    power_records = len(power_monitoring)
    abnormal_battery = sum(1 for p in power_monitoring if p.get('battery_status') != '正常')
    abnormal_voltage = sum(1 for p in power_monitoring if
                           p.get('avg_input_voltage_status') != '正常' or p.get('avg_output_voltage_status') != '正常')
    abnormal_current = sum(1 for p in power_monitoring if
                           p.get('avg_input_current_status') != '正常' or p.get('avg_output_current_status') != '正常')
    abnormal_env = sum(
        1 for p in power_monitoring if
        p.get('avg_temperature_status') != '正常' or p.get('avg_humidity_status') != '正常')

    print(f"    ✅ 日度数据聚合完成，生成统计分析结果")

    return {
        "服务器状态": {
            "总服务器数": len(server_ips),
            "监控记录数": len(server_metrics),
            "CPU异常": abnormal_cpu,
            "内存异常": abnormal_memory,
            "磁盘异常": abnormal_disk,
            "网络异常": abnormal_network,
            "丢包异常": abnormal_packet_loss,
            "用户负载异常": abnormal_user_load
        },
        "服务状态": {
            "平台数量": len(platforms),
            "服务总数": services,
            "异常服务": abnormal_services,
            "未运行进程": stopped_processes
        },
        "存储状态": {
            "存储池总数": total_pools,
            "异常存储池": abnormal_pools,
            "高使用率存储池(>80%)": high_usage_pools
        },
        "电力状态": {
            "监控记录数": power_records,
            "电池异常": abnormal_battery,
            "电压异常": abnormal_voltage,
            "电流异常": abnormal_current,
            "环境异常(温度/湿度)": abnormal_env
        }
    }


def parse_ai_response(ai_response):
    print(f"    🧠 开始解析AI分析结果...")
    
    sections = {
        "运维日报": "",
        "异常分析": "",
        "风险预测": "",
        "运维建议": "",
        "重点关注": "",
        "中度关注": ""
    }

    pattern = r"#{1,3}\s*(?:\d+\.\s*)?([\u4e00-\u9fa5]+)(?:\s*[（\(].*[）\)])?(?:（\d+字）)?\s*([\s\S]*?)(?=#{1,3}\s*(?:\d+\.\s*)?[\u4e00-\u9fa5]+|---+|\n\n\n|$)"
    matches = re.findall(pattern, ai_response)

    for title, content in matches:
        for section in sections.keys():
            if section in title:
                clean_content = content.strip()
                clean_content = re.sub(r'^\s*\d+\.\s*', '', clean_content, flags=re.MULTILINE)
                clean_content = re.sub(r'[\*\-]{1,3}\s+', '', clean_content, flags=re.MULTILINE)
                clean_content = re.sub(r'\n+', ' ', clean_content)
                clean_content = re.sub(r'\s+', ' ', clean_content)
                clean_content = clean_content.replace('---', '')
                sections[section] = clean_content.strip()
                break

    if not any(sections.values()):
        current_section = None
        content_buffer = []
        lines = ai_response.split('\n')
        for line in lines:
            line = line.strip()
            if not line or line.startswith('---'):
                continue
            section_match = False
            for section in sections.keys():
                if section in line and (
                        line.startswith(section) or
                        re.search(r'\d+\.\s+' + section, line) or
                        re.match(r'^#+\s*' + section, line) or
                        re.match(r'^#+\s*\d+\.\s*' + section, line) or
                        re.match(r'^' + section + r'\s*[（(]', line)
                ):
                    if current_section and content_buffer:
                        sections[current_section] = ' '.join(content_buffer).strip()
                    current_section = section
                    content_buffer = []
                    section_match = True
                    break
            if not section_match and current_section:
                if not line.startswith('#'):
                    content_buffer.append(line)
        if current_section and content_buffer:
            sections[current_section] = ' '.join(content_buffer).strip()

    print(f"    ✅ AI分析结果解析完成，生成结构化报告")
    return sections


def test_ai_connection():
    try:
        print(f"    🔗 测试AI运维大脑连接状态...")
        
        url = f"{LLM_CONFIG['base_url']}{LLM_CONFIG['chat_endpoint']}"

        test_payload = {
            "model": LLM_CONFIG['model_name'],
            "messages": [
                {"role": "user", "content": "你好，请回复'连接正常'"}
            ],
            "max_tokens": 10
        }

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        logger.info(f"🔍 测试AI连接: {url}")
        response = requests.post(url, json=test_payload, headers=headers, timeout=30, verify=False)

        if response.status_code == 200:
            result = response.json()
            if "choices" in result and result["choices"]:
                print(f"    ✅ AI运维大脑连接正常")
                logger.info("🎯 AI服务连接测试成功")
                return True, "连接正常"
            else:
                print(f"    ❌ AI运维大脑响应格式异常")
                logger.error(f"🚨 AI服务响应格式异常: {result}")
                return False, f"响应格式异常: {result}"
        else:
            print(f"    ❌ AI运维大脑连接失败，状态码: {response.status_code}")
            logger.error(f"🚨 AI服务连接测试失败，状态码: {response.status_code}")
            logger.error(f"🚨 响应内容: {response.text}")
            return False, f"状态码: {response.status_code}, 响应: {response.text}"

    except Exception as e:
        print(f"    ❌ AI运维大脑连接测试异常: {e}")
        logger.error(f"🚨 AI服务连接测试异常: {e}")
        return False, str(e)


def estimate_token_count(text):
    chinese_chars = len(re.findall(r'[\u4e00-\u9fa5]', text))
    english_words = len(re.findall(r'\b[a-zA-Z]+\b', text))
    other_chars = len(text) - chinese_chars - english_words

    estimated_tokens = chinese_chars * 1.5 + english_words * 1 + other_chars * 0.5
    return int(estimated_tokens)


def get_ai_analysis(data_summary, exception_data):
    print(f"    🧠 启动QWEN3-32B AI引擎进行深度分析...")
    
    limited_exception_data = limit_exception_data(exception_data, max_items_per_category=50)

    simplified_summary = {
        "服务器状态": {
            "总服务器数": data_summary["服务器状态"]["总服务器数"],
            "CPU异常": data_summary["服务器状态"]["CPU异常"],
            "内存异常": data_summary["服务器状态"]["内存异常"],
            "磁盘异常": data_summary["服务器状态"]["磁盘异常"],
            "网络异常": data_summary["服务器状态"]["网络异常"]
        },
        "服务状态": {
            "服务总数": data_summary["服务状态"]["服务总数"],
            "异常服务": data_summary["服务状态"]["异常服务"],
            "未运行进程": data_summary["服务状态"]["未运行进程"]
        },
        "存储状态": {
            "存储池总数": data_summary["存储状态"]["存储池总数"],
            "异常存储池": data_summary["存储状态"]["异常存储池"],
            "高使用率存储池(>80%)": data_summary["存储状态"]["高使用率存储池(>80%)"]
        },
        "电力状态": {
            "监控记录数": data_summary["电力状态"]["监控记录数"],
            "电池异常": data_summary["电力状态"]["电池异常"],
            "电压异常": data_summary["电力状态"]["电压异常"]
        }
    }

    simplified_exceptions = {}
    for category, exceptions in limited_exception_data.items():
        if exceptions:
            if len(exceptions) <= 10:
                simplified_exceptions[category] = exceptions
            else:
                simplified_exceptions[category] = {
                    "详细信息": exceptions[:10],
                    "总数": len(exception_data.get(category, [])),
                    "显示数": 10,
                    "说明": f"共{len(exception_data.get(category, []))}条异常，仅显示前10条"
                }

    prompt = f"""
    请作为数据中心运维专家，根据以下昨天的数据中心监控数据，分别提供以下分析（注意字数限制）：

    1. 运维日报(300字)：包括整体运行状况概述、主要指标、关键事件等
    2. 异常分析(200字)：对发现的异常情况进行原因分析
    3. 风险预测(200字)：根据当前数据预测可能出现的风险
    4. 运维建议(200字)：针对发现的问题提出具体可行的运维建议
    5. 重点关注(200字)：需要重点关注和处理的问题
    6. 中度关注(200字)：需要持续监控但暂不需要立即处理的问题

    数据概况：
    {json.dumps(simplified_summary, ensure_ascii=False, indent=2)}

    主要异常信息（已限制数量）：
    {json.dumps(simplified_exceptions, ensure_ascii=False, indent=2)}

    请确保每个部分的内容专业、简洁且有针对性，不要超出字数限制。
    请用小标题标示每个部分，确保可以清晰区分。
    """

    estimated_tokens = estimate_token_count(prompt)
    print(f"    📊 AI输入数据预估token数量: {estimated_tokens}")
    logger.info(f"📊 估算的输入token数量: {estimated_tokens}")

    if estimated_tokens > 35000:
        print(f"    🔧 输入数据过大，启用智能压缩...")
        logger.warning(f"⚠️ 输入数据仍然过大（估算{estimated_tokens} tokens），进一步简化")
        
        simplified_exceptions = {
            category: f"共{len(exception_data.get(category, []))}条异常"
            for category in limited_exception_data.keys()
        }

        prompt = f"""
        请作为数据中心运维专家，根据以下昨天的数据中心监控数据概况，提供运维分析：

        数据概况：{json.dumps(simplified_summary, ensure_ascii=False)}
        异常统计：{json.dumps(simplified_exceptions, ensure_ascii=False)}

        请分别提供：
        1. 运维日报(300字)：整体运行状况概述
        2. 异常分析(200字)：异常情况原因分析
        3. 风险预测(200字)：可能出现的风险
        4. 运维建议(200字)：具体可行的建议
        5. 重点关注(200字)：需要重点关注的问题
        6. 中度关注(200字)：需要持续监控的问题

        请用小标题区分各部分。
        """

    url = f"{LLM_CONFIG['base_url']}{LLM_CONFIG['chat_endpoint']}"

    payload = {
        "model": LLM_CONFIG['model_name'],
        "messages": [
            {
                "role": "system",
                "content": "你是一位资深的数据中心运维专家，负责分析昨天的监控数据并提供专业的运维建议。请确保回答中的六个部分用明确的标题隔开，便于解析。"
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.7,
        "max_tokens": 1500,
        "stream": False
    }

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    try:
        print(f"    🌐 向AI运维大脑发送深度分析请求...")
        logger.info(f"🔍 正在连接AI服务: {url}")
        logger.info(f"🧠 使用模型: {LLM_CONFIG['model_name']}")

        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=120,
            verify=False
        )

        print(f"    📡 AI运维大脑响应状态: {response.status_code}")
        logger.info(f"📡 响应状态码: {response.status_code}")

        if response.status_code != 200:
            print(f"    ❌ AI运维大脑请求失败: {response.status_code}")
            logger.error(f"🚨 API请求失败，状态码: {response.status_code}")
            logger.error(f"🚨 响应内容: {response.text}")
            raise Exception(f"API请求失败，状态码: {response.status_code}, 响应: {response.text}")

        try:
            result = response.json()
            print(f"    ✅ AI运维大脑分析完成，生成专业日报")
            logger.info("🎯 成功接收到AI API响应")
            logger.debug(f"🔍 响应结构: {result.keys() if isinstance(result, dict) else 'Not a dict'}")

            if "choices" not in result:
                logger.error(f"🚨 响应中缺少choices字段: {result}")
                raise Exception(f"API响应格式异常: {result}")

            if not result["choices"] or len(result["choices"]) == 0:
                logger.error("🚨 响应中choices为空")
                raise Exception("API响应中choices为空")

            if "message" not in result["choices"][0]:
                logger.error(f"🚨 响应中缺少message字段: {result['choices'][0]}")
                raise Exception(f"API响应格式异常，缺少message字段")

            if "content" not in result["choices"][0]["message"]:
                logger.error(f"🚨 响应中缺少content字段: {result['choices'][0]['message']}")
                raise Exception(f"API响应格式异常，缺少content字段")

            ai_response = result["choices"][0]["message"]["content"]

            if not ai_response or ai_response.strip() == "":
                logger.error("🚨 AI响应内容为空")
                raise Exception("AI响应内容为空")

            print(f"    📝 AI分析结果长度: {len(ai_response)} 字符")
            logger.info(f"📈 AI响应长度: {len(ai_response)} 字符")
            logger.debug(f"📄 AI响应前200字符: {ai_response[:200]}")

            sections = parse_ai_response(ai_response)

            if not any(sections.values()):
                print(f"    ⚠️ AI分析结果解析后所有部分都为空，使用原始响应")
                logger.warning("⚠️ AI响应解析后所有部分都为空，使用原始响应")
                return {
                    "运维日报": ai_response[:500] if len(ai_response) > 500 else ai_response,
                    "异常分析": "",
                    "风险预测": "",
                    "运维建议": "",
                    "重点关注": "",
                    "中度关注": ""
                }

            return sections

        except json.JSONDecodeError as e:
            print(f"    ❌ AI响应JSON格式错误: {e}")
            logger.error(f"🚨 JSON解析失败: {e}")
            logger.error(f"🚨 响应内容: {response.text}")
            raise Exception(f"API响应JSON格式错误: {e}")

    except requests.exceptions.Timeout:
        print(f"    ⏰ AI运维大脑请求超时")
        logger.error("🚨 请求超时")
        return {
            "运维日报": "AI分析服务请求超时，请检查网络连接或稍后重试。",
            "异常分析": "",
            "风险预测": "",
            "运维建议": "",
            "重点关注": "",
            "中度关注": ""
        }
    except requests.exceptions.ConnectionError as e:
        print(f"    🌐 AI运维大脑连接错误: {e}")
        logger.error(f"🚨 连接错误: {e}")
        return {
            "运维日报": f"无法连接到AI分析服务 ({url})，请检查服务状态和网络连接。",
            "异常分析": "",
            "风险预测": "",
            "运维建议": "",
            "重点关注": "",
            "中度关注": ""
        }
    except requests.exceptions.RequestException as e:
        print(f"    🚨 AI运维大脑请求异常: {e}")
        logger.error(f"🚨 请求异常: {e}")
        return {
            "运维日报": f"AI分析服务请求失败: {str(e)}",
            "异常分析": "",
            "风险预测": "",
            "运维建议": "",
            "重点关注": "",
            "中度关注": ""
        }
    except Exception as e:
        print(f"    💥 AI运维大脑分析异常: {e}")
        logger.error(f"🚨 AI分析调用失败: {e}")
        logger.error(f"🚨 错误详情: {type(e).__name__}: {str(e)}")
        return {
            "运维日报": f"AI分析服务异常: {str(e)}",
            "异常分析": "",
            "风险预测": "",
            "运维建议": "",
            "重点关注": "",
            "中度关注": ""
        }


def save_analysis_summary(conn, analysis_data, report_date, exception_data):
    print(f"    💾 准备将日报分析结果存储到数据库...")
    unique_id = generate_unique_id()

    formatted_exception_data = format_exception_data_for_storage(exception_data)

    insert_query = """
                   INSERT INTO operation_analysis_summary
                   (id, report_date, report_type, operation_daily, exception_analysis,
                    exception_data, risk_prediction, operation_suggestion, key_focus,
                    moderate_focus, created_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   """

    with conn.cursor() as cursor:
        cursor.execute(insert_query, (
            unique_id,
            report_date,
            'daily',
            analysis_data.get('运维日报', ''),
            analysis_data.get('异常分析', ''),
            formatted_exception_data,
            analysis_data.get('风险预测', ''),
            analysis_data.get('运维建议', ''),
            analysis_data.get('重点关注', ''),
            analysis_data.get('中度关注', ''),
            datetime.now()
        ))
    conn.commit()
    print(f"    ✅ 日报分析结果已成功存储，记录ID: {unique_id}")
    logger.info(f"📊 分析结果已保存到数据库，ID: {unique_id}")
    return unique_id


def daily_monitoring_report(params=None):
    try:
        print("🚀 启动AI智能日报生成系统...")
        logger.info("📊 开始生成日报监控报告...")

        print("🔗 测试AI运维大脑连接状态...")
        logger.info("🔍 测试AI服务连接...")
        connection_ok, connection_msg = test_ai_connection()
        if not connection_ok:
            print(f"⚠️ AI运维大脑连接异常: {connection_msg}")
            logger.error(f"🚨 AI服务连接失败: {connection_msg}")
        else:
            print(f"✅ AI运维大脑连接正常")
            logger.info("🎯 AI服务连接正常")

        conn = get_connection()

        start_time, end_time, report_date = get_daily_date_range()
        print(f"📅 设定日报分析时间范围: {start_time.strftime('%Y-%m-%d')} ({report_date.strftime('%A')})")
        logger.info(f"📅 报告日期范围: {start_time} 到 {end_time}")

        print(f"📊 开始采集多维度监控数据...")
        server_metrics = fetch_server_metrics(conn, start_time, end_time)
        logger.info(f"📈 获取到 {len(server_metrics)} 条服务器指标数据")

        service_status = fetch_service_status(conn, start_time, end_time)
        logger.info(f"🔧 获取到 {len(service_status)} 条服务状态数据")

        nas_pools = fetch_nas_pools(conn, start_time.date(), end_time.date())
        logger.info(f"💾 获取到 {len(nas_pools)} 条NAS存储池数据")

        power_monitoring = fetch_power_monitoring(conn, start_time, end_time)
        logger.info(f"⚡ 获取到 {len(power_monitoring)} 条电力监控数据")

        if not server_metrics and not service_status and not nas_pools and not power_monitoring:
            print("⚠️ 未发现可分析的日报数据")
            logger.warning("⚠️ 没有可用于分析的数据")
            conn.close()
            return {"success": False, "message": "没有可用于分析的数据"}

        print(f"🔧 开始数据聚合和异常识别...")
        exception_data = get_exceptions(server_metrics, service_status, nas_pools, power_monitoring)
        data_summary = prepare_data_summary(server_metrics, service_status, nas_pools, power_monitoring)

        print(f"🧠 启动AI深度分析引擎...")
        analysis_result = get_ai_analysis(data_summary, exception_data)
        logger.info("🎯 AI分析完成")

        print(f"💾 保存分析结果到运维数据库...")
        summary_id = save_analysis_summary(conn, analysis_result, report_date, exception_data)

        conn.close()

        result = {
            "success": True,
            "summary_id": summary_id,
            "report_date": report_date.strftime('%Y-%m-%d'),
            "report_type": "daily",
            "analysis": analysis_result,
            "data_summary": data_summary,
            "exception_data": exception_data,
            "exception_count": {
                "server_exceptions": len(exception_data.get("服务器异常", [])),
                "service_exceptions": len(exception_data.get("服务异常", [])),
                "storage_exceptions": len(exception_data.get("存储异常", [])),
                "power_exceptions": len(exception_data.get("电力异常", []))
            },
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ai_connection_status": connection_msg
        }

        print(f"✅ AI智能日报生成完成")
        print(f"📊 分析日期: {report_date.strftime('%Y-%m-%d')}")
        print(f"📋 报告ID: {summary_id}")
        print(f"📈 发现异常: {sum(result['exception_count'].values())} 项")

        logger.info(f"📊 日报生成完成，共发现 {sum(result['exception_count'].values())} 项异常")
        return result

    except Exception as e:
        print(f"❌ AI智能日报系统执行异常: {e}")
        logger.error(f"🚨 生成日报监控报告时发生错误: {e}")
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    result = daily_monitoring_report()
    print(f"测试结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
