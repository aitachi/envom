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


def get_weekly_date_range():
    today = datetime.now().date()
    end_date = today - timedelta(days=1)
    start_date = end_date - timedelta(days=6)
    start_datetime = datetime.combine(start_date, dt_time.min)
    end_datetime = datetime.combine(end_date, dt_time.max)
    return start_datetime, end_datetime, start_date, end_date


def generate_unique_id(prefix='oas'):
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    return f"{prefix}{timestamp}"


def fetch_weekly_server_metrics(conn, start_time, end_time):
    print(f"    📊 启动数据库连接，查询服务器性能指标...")
    with conn.cursor() as cursor:
        query = """
                SELECT ip, \
                       AVG(CAST(cpu_usage AS DECIMAL(10, 2)))                  as avg_cpu, \
                       AVG(CAST(memory_usage AS DECIMAL(10, 2)))               as avg_memory, \
                       AVG(CAST(disk_usage AS DECIMAL(10, 2)))                 as avg_disk, \
                       COUNT(*)                                                as record_count,
                       SUM(CASE WHEN cpu_status != '正常' THEN 1 ELSE 0 END)    as cpu_anomalies,
                       SUM(CASE WHEN memory_status != '正常' THEN 1 ELSE 0 END) as memory_anomalies,
                       SUM(CASE WHEN disk_status != '正常' THEN 1 ELSE 0 END)   as disk_anomalies,
                       SUM(CASE WHEN network_status != '正常' THEN 1 ELSE 0 END) as network_anomalies,
                       SUM(CASE WHEN packet_loss_status != '正常' THEN 1 ELSE 0 END) as packet_loss_anomalies,
                       SUM(CASE WHEN user_load_status != '正常' THEN 1 ELSE 0 END) as user_load_anomalies
                FROM howso_server_performance_metrics
                WHERE collect_time BETWEEN %s AND %s
                GROUP BY ip
                """
        cursor.execute(query, (start_time, end_time))
        results = cursor.fetchall()
        print(f"    ✅ 服务器性能数据采集完成，共获取 {len(results)} 台服务器的周统计数据")
        return [dict(zip([desc[0] for desc in cursor.description], convert_decimal(row))) for row in results]


def fetch_weekly_service_status(conn, start_time, end_time):
    print(f"    🔧 查询服务状态监控数据...")
    with conn.cursor() as cursor:
        query = """
                SELECT platform, \
                       server_ip, \
                       service_name,
                       COUNT(*)                                                   as total_checks,
                       SUM(CASE WHEN status != '正常' THEN 1 ELSE 0 END)           as anomaly_count,
                       SUM(CASE WHEN process_status = '未运行' THEN 1 ELSE 0 END) as stop_count
                FROM plat_service_monitoring
                WHERE insert_time BETWEEN %s AND %s
                GROUP BY platform, server_ip, service_name
                """
        cursor.execute(query, (start_time, end_time))
        results = cursor.fetchall()
        print(f"    ✅ 服务状态数据采集完成，共获取 {len(results)} 个服务的周统计数据")
        return [dict(zip([desc[0] for desc in cursor.description], convert_decimal(row))) for row in results]


def fetch_weekly_nas_pools(conn, start_date, end_date):
    print(f"    💾 查询存储池监控数据...")
    with conn.cursor() as cursor:
        query = """
                SELECT server_name, \
                       pool_name, \
                       COUNT(*)                                         as check_count,
                       AVG(CAST(usage_percentage AS DECIMAL(10, 2)))    as avg_usage,
                       SUM(CASE WHEN status != '正常' THEN 1 ELSE 0 END) as anomaly_count
                FROM nas_pools_detail
                WHERE inspection_date BETWEEN %s AND %s
                GROUP BY server_name, pool_name
                """
        cursor.execute(query, (start_date, end_date))
        results = cursor.fetchall()
        print(f"    ✅ 存储池数据采集完成，共获取 {len(results)} 个存储池的周统计数据")
        return [dict(zip([desc[0] for desc in cursor.description], convert_decimal(row))) for row in results]


def fetch_weekly_power_monitoring(conn, start_time, end_time):
    try:
        print(f"    ⚡ 查询电力监控数据...")
        with conn.cursor() as cursor:
            query = """
                    SELECT COUNT(*)                                                            as record_count,
                           SUM(CASE WHEN battery_status != '正常' THEN 1 ELSE 0 END)            as battery_anomalies,
                           SUM(CASE WHEN avg_input_voltage_status != '正常' THEN 1 ELSE 0 END)  as input_voltage_anomalies,
                           SUM(CASE WHEN avg_output_voltage_status != '正常' THEN 1 ELSE 0 END) as output_voltage_anomalies,
                           SUM(CASE WHEN avg_input_current_status != '正常' THEN 1 ELSE 0 END)  as input_current_anomalies,
                           SUM(CASE WHEN avg_output_current_status != '正常' THEN 1 ELSE 0 END) as output_current_anomalies,
                           SUM(CASE WHEN avg_temperature_status != '正常' THEN 1 ELSE 0 END)    as temperature_anomalies,
                           SUM(CASE WHEN avg_humidity_status != '正常' THEN 1 ELSE 0 END)       as humidity_anomalies
                    FROM power_monitoring_avg_data
                    WHERE inspection_time BETWEEN %s AND %s
                    """
            cursor.execute(query, (start_time, end_time))
            results = cursor.fetchall()
            print(f"    ✅ 电力监控数据采集完成，共获取 {len(results)} 条电力周统计数据")
            return [dict(zip([desc[0] for desc in cursor.description], convert_decimal(row))) for row in results]
    except Exception as e:
        print(f"    ⚠️ 电力监控数据采集遇到问题: {e}")
        logger.error(f"🚨 Error fetching weekly power monitoring data: {e}")
        return []


def prepare_weekly_data_summary(server_metrics, service_status, nas_pools, power_monitoring):
    print(f"    📈 开始聚合和分析周度监控数据...")
    
    total_servers = len(server_metrics)
    total_cpu_anomalies = sum(safe_int(m.get('cpu_anomalies', 0)) for m in server_metrics)
    total_memory_anomalies = sum(safe_int(m.get('memory_anomalies', 0)) for m in server_metrics)
    total_disk_anomalies = sum(safe_int(m.get('disk_anomalies', 0)) for m in server_metrics)
    total_network_anomalies = sum(safe_int(m.get('network_anomalies', 0)) for m in server_metrics)
    total_packet_loss_anomalies = sum(safe_int(m.get('packet_loss_anomalies', 0)) for m in server_metrics)
    total_user_load_anomalies = sum(safe_int(m.get('user_load_anomalies', 0)) for m in server_metrics)
    avg_cpu = sum(safe_float(m.get('avg_cpu', 0)) for m in server_metrics) / total_servers if total_servers else 0
    avg_memory = sum(safe_float(m.get('avg_memory', 0)) for m in server_metrics) / total_servers if total_servers else 0
    avg_disk = sum(safe_float(m.get('avg_disk', 0)) for m in server_metrics) / total_servers if total_servers else 0

    total_services = len(service_status)
    total_service_anomalies = sum(safe_int(s.get('anomaly_count', 0)) for s in service_status)
    total_service_stops = sum(safe_int(s.get('stop_count', 0)) for s in service_status)
    total_checks = sum(safe_int(s.get('total_checks', 0)) for s in service_status)

    total_nas_pools = len(nas_pools)
    total_nas_anomalies = sum(safe_int(p.get('anomaly_count', 0)) for p in nas_pools)
    avg_usage = sum(safe_float(p.get('avg_usage', 0)) for p in nas_pools) / total_nas_pools if total_nas_pools else 0

    power_data = power_monitoring[0] if power_monitoring else {}
    total_power_records = safe_int(power_data.get('record_count', 0))
    total_battery_anomalies = safe_int(power_data.get('battery_anomalies', 0))
    total_voltage_anomalies = safe_int(power_data.get('input_voltage_anomalies', 0)) + safe_int(
        power_data.get('output_voltage_anomalies', 0))
    total_current_anomalies = safe_int(power_data.get('input_current_anomalies', 0)) + safe_int(
        power_data.get('output_current_anomalies', 0))
    total_env_anomalies = safe_int(power_data.get('temperature_anomalies', 0)) + safe_int(
        power_data.get('humidity_anomalies', 0))

    print(f"    ✅ 周度数据聚合完成，生成统计分析结果")

    return {
        "服务器状态": {
            "监控服务器数": total_servers,
            "平均CPU使用率": round(avg_cpu, 2),
            "平均内存使用率": round(avg_memory, 2),
            "平均磁盘使用率": round(avg_disk, 2),
            "CPU异常次数": total_cpu_anomalies,
            "内存异常次数": total_memory_anomalies,
            "磁盘异常次数": total_disk_anomalies,
            "网络异常次数": total_network_anomalies,
            "丢包异常次数": total_packet_loss_anomalies,
            "用户负载异常次数": total_user_load_anomalies
        },
        "服务状态": {
            "监控服务数": total_services,
            "总检查次数": total_checks,
            "总异常次数": total_service_anomalies,
            "总停止次数": total_service_stops
        },
        "存储状态": {
            "监控存储池数": total_nas_pools,
            "平均使用率": round(avg_usage, 2),
            "总异常次数": total_nas_anomalies
        },
        "电力状态": {
            "监控记录数": total_power_records,
            "电池异常": total_battery_anomalies,
            "电压异常": total_voltage_anomalies,
            "电流异常": total_current_anomalies,
            "环境异常": total_env_anomalies
        }
    }


def get_weekly_exceptions(server_metrics, service_status, nas_pools, power_monitoring):
    print(f"    🔍 开始识别和分析异常数据...")
    
    exceptions = {
        "高异常服务器": [m for m in server_metrics if
                         (safe_int(m.get('cpu_anomalies', 0)) + safe_int(m.get('memory_anomalies', 0)) + safe_int(
                             m.get('disk_anomalies', 0)) + safe_int(m.get('network_anomalies', 0)) + safe_int(
                             m.get('packet_loss_anomalies', 0)) + safe_int(m.get('user_load_anomalies', 0))) > 5],
        "高异常服务": [s for s in service_status if safe_int(s.get('anomaly_count', 0)) > 2],
        "高异常存储池": [p for p in nas_pools if safe_int(p.get('anomaly_count', 0)) > 1],
        "电力监控异常": power_monitoring
    }

    filtered_exceptions = {k: v for k, v in exceptions.items() if v}
    print(f"    ✅ 异常数据识别完成，发现 {len(filtered_exceptions)} 类异常情况")
    
    return filtered_exceptions


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


def get_ai_weekly_analysis(data_summary, exception_data):
    print(f"    🧠 启动QWEN3-32B AI引擎进行周度深度分析...")
    
    prompt = f"""
    请作为数据中心运维专家，根据以下过去7天的数据中心监控数据，分别提供以下分析（注意字数限制）：

    1. 运维日报(400字)：包括过去7天的整体运行状况概述、主要指标趋势、关键事件等
    2. 异常分析(300字)：对发现的异常情况进行原因分析和趋势判断
    3. 风险预测(300字)：根据一周数据预测下周可能出现的风险
    4. 运维建议(300字)：针对发现的问题提出具体可行的运维建议
    5. 重点关注(200字)：下周需要重点关注和处理的问题
    6. 中度关注(200字)：需要持续监控但暂不需要立即处理的问题

    数据概况：
    {json.dumps(data_summary, ensure_ascii=False, indent=2)}

    异常数据：
    {json.dumps(exception_data, ensure_ascii=False, indent=2)}

    请确保每个部分的内容专业、简洁且有针对性，不要超出字数限制。
    请用小标题标示每个部分，确保可以清晰区分。
    """

    url = f"{LLM_CONFIG['base_url']}{LLM_CONFIG['chat_endpoint']}"
    payload = {
        "model": LLM_CONFIG['model_name'],
        "messages": [
            {"role": "system",
             "content": "你是一位资深的数据中心运维专家，负责分析过去7天的监控数据并提供专业的运维建议。请确保回答中的六个部分用明确的标题隔开，便于解析。"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7
    }

    headers = {"Content-Type": "application/json"}

    try:
        print(f"    🌐 向AI运维大脑发送周报分析请求...")
        logger.info("🔮 发送周报AI分析请求...")
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()

        result = response.json()
        print(f"    ✅ AI运维大脑分析完成，生成专业周报")
        logger.info("🎯 成功接收周报AI分析响应")
        ai_response = result["choices"][0]["message"]["content"]

        sections = parse_ai_response(ai_response)
        return sections
    except Exception as e:
        print(f"    ❌ AI运维大脑连接异常: {e}")
        logger.error(f"🚨 周报AI分析调用失败: {e}")
        return {
            "运维日报": "无法连接AI分析服务，请手动分析监控数据。",
            "异常分析": "",
            "风险预测": "",
            "运维建议": "",
            "重点关注": "",
            "中度关注": ""
        }


def save_analysis_summary(conn, analysis_data, start_date, exception_data):
    print(f"    💾 准备将周报分析结果存储到数据库...")
    unique_id = generate_unique_id()

    insert_query = """
                   INSERT INTO operation_analysis_summary
                   (id, report_date, report_type, operation_daily, exception_analysis,
                    exception_data, risk_prediction, operation_suggestion, key_focus,
                    moderate_focus, created_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) \
                   """

    with conn.cursor() as cursor:
        cursor.execute(insert_query, (
            unique_id,
            start_date,
            'weekly',
            analysis_data.get('运维日报', ''),
            analysis_data.get('异常分析', ''),
            json.dumps(exception_data, ensure_ascii=False),
            analysis_data.get('风险预测', ''),
            analysis_data.get('运维建议', ''),
            analysis_data.get('重点关注', ''),
            analysis_data.get('中度关注', ''),
            datetime.now()
        ))
    conn.commit()
    print(f"    ✅ 周报分析结果已成功存储，记录ID: {unique_id}")
    logger.info(f"📊 周报分析结果已保存到数据库，ID: {unique_id}")
    return unique_id


def weekly_monitoring_report(params=None):
    try:
        print("🚀 启动AI智能周报生成系统...")
        logger.info("📊 开始生成周报监控报告...")
        conn = get_connection()

        start_time, end_time, start_date, end_date = get_weekly_date_range()
        print(f"📅 设定周报分析时间范围: {start_time.strftime('%Y-%m-%d')} 到 {end_time.strftime('%Y-%m-%d')}")
        logger.info(f"📅 周报日期范围: {start_time} 到 {end_time}")

        print(f"📊 开始采集多维度监控数据...")
        server_metrics = fetch_weekly_server_metrics(conn, start_time, end_time)
        logger.info(f"📈 获取到 {len(server_metrics)} 台服务器的周报数据")

        service_status = fetch_weekly_service_status(conn, start_time, end_time)
        logger.info(f"🔧 获取到 {len(service_status)} 项服务的周报数据")

        nas_pools = fetch_weekly_nas_pools(conn, start_time.date(), end_time.date())
        logger.info(f"💾 获取到 {len(nas_pools)} 个存储池的周报数据")

        power_monitoring = fetch_weekly_power_monitoring(conn, start_time, end_time)
        logger.info(f"⚡ 获取到 {len(power_monitoring)} 条电力监控周报数据")

        if not server_metrics and not service_status and not nas_pools and not power_monitoring:
            print("⚠️ 未发现可分析的周报数据")
            logger.warning("⚠️ 没有可用于分析的周报数据")
            conn.close()
            return {"success": False, "message": "没有可用于分析的周报数据"}

        print(f"🔧 开始数据聚合和统计分析...")
        data_summary = prepare_weekly_data_summary(server_metrics, service_status, nas_pools, power_monitoring)
        exception_data = get_weekly_exceptions(server_metrics, service_status, nas_pools, power_monitoring)

        print(f"🧠 启动AI深度分析引擎...")
        analysis_result = get_ai_weekly_analysis(data_summary, exception_data)
        logger.info("🎯 周报AI分析完成")

        print(f"💾 保存分析结果到运维数据库...")
        summary_id = save_analysis_summary(conn, analysis_result, start_date, exception_data)

        conn.close()

        result = {
            "success": True,
            "summary_id": summary_id,
            "report_period": f"{start_date.strftime('%Y-%m-%d')} 到 {end_date.strftime('%Y-%m-%d')}",
            "report_type": "weekly",
            "analysis": analysis_result,
            "data_summary": data_summary,
            "exception_count": {
                "high_anomaly_servers": len(exception_data.get("高异常服务器", [])),
                "high_anomaly_services": len(exception_data.get("高异常服务", [])),
                "high_anomaly_storage": len(exception_data.get("高异常存储池", [])),
                "power_anomalies": len(exception_data.get("电力监控异常", []))
            },
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        print(f"✅ AI智能周报生成完成")
        print(f"📊 分析范围: {start_date.strftime('%Y-%m-%d')} 到 {end_date.strftime('%Y-%m-%d')}")
        print(f"📋 报告ID: {summary_id}")

        return result
    except Exception as e:
        print(f"❌ AI智能周报系统执行异常: {e}")
        logger.error(f"🚨 生成周报监控报告时发生错误: {e}")
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    result = weekly_monitoring_report()
    print(f"测试结果: {result}")
