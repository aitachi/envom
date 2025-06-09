#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import requests
import time
import urllib3
import datetime
from collections import defaultdict

import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from utils.logger import setup_logger
from utils.database import get_connection

logger = setup_logger(__name__)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BK_APP_CODE = "bk_monitorv3"
BK_APP_SECRET = "6d637229-236f-42a7-8fc3-c2125fdc5040"
BK_USERNAME = "admin"
BK_PAAS_HOST = "http://paas.howso.cn"
API_URL = f"{BK_PAAS_HOST}/api/c/compapi/v2/monitor_v3/get_ts_data/"

BIZ_ID = 3
TIME_RANGE = "1h"
MAX_RECORDS = 300

THRESHOLDS = {
    'cpu': 70.0,
    'memory': 70.0,
    'disk': 80.0,
    'network': 95.0
}

EXPECTED_IPS = [
    "192.168.10.141", "192.168.10.174", "192.168.10.49", "192.168.101.101",
    "192.168.101.116", "192.168.101.127", "192.168.101.14", "192.168.101.158",
    "192.168.101.160", "192.168.101.162", "192.168.101.169", "192.168.101.189",
    "192.168.101.19", "192.168.101.194", "192.168.101.211", "192.168.101.212",
    "192.168.101.214", "192.168.101.217", "192.168.101.30", "192.168.101.42",
    "192.168.101.43", "192.168.101.6", "192.168.101.7", "192.168.101.72",
    "192.168.101.74", "192.168.101.8", "192.168.121.21", "192.168.121.23",
    "192.168.121.25", "192.168.121.26", "192.168.121.54", "192.168.101.152"
]


def convert_datetime_to_string(obj):
    if isinstance(obj, datetime.datetime):
        return obj.strftime("%Y-%m-%d %H:%M:%S")
    elif isinstance(obj, datetime.date):
        return obj.strftime("%Y-%m-%d")
    elif isinstance(obj, dict):
        return {key: convert_datetime_to_string(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_datetime_to_string(item) for item in obj]
    else:
        return obj


def get_ts_data(sql, prefer_storage=None):
    data = {
        "bk_app_code": BK_APP_CODE,
        "bk_app_secret": BK_APP_SECRET,
        "bk_username": BK_USERNAME,
        "sql": sql
    }

    if prefer_storage:
        data["prefer_storage"] = prefer_storage

    print(f"    📊 向监控平台发送性能数据查询请求...")
    logger.info(f"🔍 执行监控数据查询: {sql}")

    try:
        response = requests.post(
            API_URL,
            json=data,
            verify=False,
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            if result.get("result"):
                print(f"    ✅ 监控数据获取成功: {result.get('message')}")
                logger.info(f"📈 查询成功: {result.get('message')}")
                return result
            else:
                print(f"    ❌ 监控数据查询失败: {result.get('message')}")
                logger.error(f"🚨 查询失败: {result.get('message')}")
                return None
        else:
            print(f"    ⚠️ 监控API响应异常: HTTP {response.status_code}")
            logger.error(f"🚨 HTTP错误: {response.status_code}")
            return None
    except Exception as e:
        print(f"    💥 监控数据请求异常: {e}")
        logger.error(f"🚨 请求异常: {e}")
        return None


def get_performance_data(time_range=None):
    if time_range is None:
        time_range = TIME_RANGE

    print(f"    🔍 开始采集 {time_range} 时间段内的性能监控数据...")

    sql_cpu = f"""
    SELECT mean(usage) AS cpu_usage 
    FROM {BIZ_ID}_system_cpu_detail 
    WHERE time > now() - {time_range} 
    GROUP BY ip
    ORDER BY time DESC 
    LIMIT {MAX_RECORDS}
    """

    sql_memory = f"""
    SELECT max(pct_used) AS memory_usage 
    FROM {BIZ_ID}_system_mem 
    WHERE time > now() - {time_range} 
    GROUP BY ip, bk_cloud_id
    ORDER BY time DESC 
    LIMIT {MAX_RECORDS}
    """

    sql_disk = f"""
    SELECT max(in_use) AS disk_usage
    FROM {BIZ_ID}_system_disk 
    WHERE time > now() - {time_range}
    GROUP BY ip, bk_cloud_id, device_name
    ORDER BY time DESC 
    LIMIT {MAX_RECORDS}
    """

    print(f"    📈 正在获取CPU性能指标...")
    cpu_data = get_ts_data(sql_cpu)

    print(f"    💾 正在获取内存使用指标...")
    memory_data = get_ts_data(sql_memory)

    print(f"    💿 正在获取磁盘使用指标...")
    disk_data = get_ts_data(sql_disk)

    return cpu_data, memory_data, disk_data


def evaluate_status(value, threshold, metric_type=None):
    if value is None:
        return "丢失"

    try:
        if isinstance(value, str):
            value = float(value)

        status = "异常" if value > threshold else "正常"

        if metric_type:
            logger.debug(f"📊 {metric_type}状态评估: 值={value}, 阈值={threshold}, 结果={status}")

        return status
    except (ValueError, TypeError) as e:
        logger.warning(f"⚠️ 状态评估失败，值={value}, 类型={type(value)}, 错误={e}")
        return "丢失"


def aggregate_performance_data(cpu_data, memory_data, disk_data):
    result = {}
    current_time_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print(f"    🔧 开始聚合和分析 {len(EXPECTED_IPS)} 台服务器的性能数据...")

    for ip in EXPECTED_IPS:
        result[ip] = {
            "collect_time": current_time_str,
            "cpu_usage": 0.0,
            "cpu_status": "丢失",
            "memory_usage": 0.0,
            "memory_status": "丢失",
            "disk_usage": 0.0,
            "disk_status": "丢失",
            "bk_cloud_id": 0
        }

    if cpu_data and cpu_data.get("data", {}).get("list"):
        print(f"    📈 处理CPU性能数据，共 {len(cpu_data['data']['list'])} 条记录...")
        for item in cpu_data["data"]["list"]:
            ip = item.get("ip")
            if ip and ip in EXPECTED_IPS:
                cpu_usage = item.get("cpu_usage")
                if cpu_usage is not None:
                    try:
                        cpu_usage = float(cpu_usage)
                        result[ip]["cpu_usage"] = round(cpu_usage, 2)
                        result[ip]["cpu_status"] = evaluate_status(cpu_usage, THRESHOLDS['cpu'], f"CPU-{ip}")

                        if "time" in item and isinstance(item["time"], (int, float)):
                            result[ip]["collect_time"] = datetime.datetime.fromtimestamp(item["time"] / 1000).strftime(
                                "%Y-%m-%d %H:%M:%S")
                    except (ValueError, TypeError) as e:
                        logger.warning(f"⚠️ CPU数据处理失败，IP={ip}, 值={cpu_usage}, 错误={e}")

    if memory_data and memory_data.get("data", {}).get("list"):
        print(f"    💾 处理内存使用数据，共 {len(memory_data['data']['list'])} 条记录...")
        for item in memory_data["data"]["list"]:
            ip = item.get("ip")
            if ip and ip in EXPECTED_IPS:
                memory_usage = item.get("memory_usage")
                if memory_usage is not None:
                    try:
                        memory_usage = float(memory_usage)
                        result[ip]["memory_usage"] = round(memory_usage, 2)
                        result[ip]["memory_status"] = evaluate_status(memory_usage, THRESHOLDS['memory'], f"内存-{ip}")
                        result[ip]["bk_cloud_id"] = item.get("bk_cloud_id", 0)

                        if "time" in item and isinstance(item["time"], (int, float)) and result[ip][
                            "collect_time"] == current_time_str:
                            result[ip]["collect_time"] = datetime.datetime.fromtimestamp(item["time"] / 1000).strftime(
                                "%Y-%m-%d %H:%M:%S")
                    except (ValueError, TypeError) as e:
                        logger.warning(f"⚠️ 内存数据处理失败，IP={ip}, 值={memory_usage}, 错误={e}")

    disk_by_ip = defaultdict(list)
    if disk_data and disk_data.get("data", {}).get("list"):
        print(f"    💿 处理磁盘使用数据，共 {len(disk_data['data']['list'])} 条记录...")
        for item in disk_data["data"]["list"]:
            ip = item.get("ip")
            if ip and ip in EXPECTED_IPS:
                device_name = item.get("device_name", "")
                if device_name and not device_name.startswith("loop") and item.get("disk_usage"):
                    disk_by_ip[ip].append(item)

    for ip in EXPECTED_IPS:
        if ip in disk_by_ip and disk_by_ip[ip]:
            try:
                valid_disks = [d for d in disk_by_ip[ip] if d.get("disk_usage") is not None]
                if valid_disks:
                    max_disk = max(valid_disks, key=lambda x: float(x.get("disk_usage", 0)))
                    disk_usage = max_disk.get("disk_usage")

                    if disk_usage is not None:
                        disk_usage = float(disk_usage)
                        result[ip]["disk_usage"] = round(disk_usage, 2)
                        result[ip]["disk_status"] = evaluate_status(disk_usage, THRESHOLDS['disk'], f"磁盘-{ip}")

                        if "time" in max_disk and isinstance(max_disk["time"], (int, float)) and result[ip][
                            "collect_time"] == current_time_str:
                            result[ip]["collect_time"] = datetime.datetime.fromtimestamp(
                                max_disk["time"] / 1000).strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError) as e:
                logger.warning(f"⚠️ 磁盘数据处理失败，IP={ip}, 错误={e}")

    print(f"    ✅ 性能数据聚合完成，已处理 {len(result)} 台服务器的监控指标")
    return result


def save_performance_data_to_db(aggregated_data):
    try:
        print(f"    💾 准备将监控数据写入数据库...")
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SHOW TABLES LIKE 'howso_server_performance_metrics'")
        if not cursor.fetchone():
            print(f"    🔧 创建性能监控数据表...")
            create_table_sql = """
                               CREATE TABLE `howso_server_performance_metrics` \
                               ( \
                                   `id`             varchar(20) NOT NULL COMMENT '主键ID', \
                                   `ip`             varchar(50) NOT NULL COMMENT '服务器IP', \
                                   `collect_time`   datetime    NOT NULL COMMENT '采集时间', \
                                   `cpu_usage`      decimal(5, 2) DEFAULT NULL COMMENT 'CPU使用率(%)', \
                                   `cpu_status`     varchar(20)   DEFAULT NULL COMMENT 'CPU状态', \
                                   `memory_usage`   decimal(5, 2) DEFAULT NULL COMMENT '内存使用率(%)', \
                                   `memory_status`  varchar(20)   DEFAULT NULL COMMENT '内存状态', \
                                   `disk_usage`     decimal(5, 2) DEFAULT NULL COMMENT '磁盘使用率(%)', \
                                   `disk_status`    varchar(20)   DEFAULT NULL COMMENT '磁盘状态', \
                                   `network_status` varchar(20)   DEFAULT NULL COMMENT '网络状态', \
                                   `bk_cloud_id`    int           DEFAULT NULL COMMENT '云区域ID', \
                                   `insert_time`    datetime    NOT NULL COMMENT '插入时间', \
                                   PRIMARY KEY (`id`), \
                                   KEY              `idx_ip` (`ip`), \
                                   KEY              `idx_collect_time` (`collect_time`)
                               ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='服务器性能监控指标表' \
                               """
            cursor.execute(create_table_sql)
            conn.commit()
            print(f"    ✅ 性能监控数据表创建成功")
            logger.info("📊 成功创建 howso_server_performance_metrics 表")

        now = datetime.datetime.now()
        timestamp = now.strftime('%Y%m%d%H%M%S')
        batch_id = f"res{timestamp}"

        print(f"    📝 开始批量插入监控数据，批次ID: {batch_id}")

        insert_sql = """
                     INSERT INTO howso_server_performance_metrics
                     (id, ip, collect_time, cpu_usage, cpu_status, memory_usage, memory_status,
                      disk_usage, disk_status, network_status, bk_cloud_id, insert_time)
                     VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) \
                     """

        records = []
        for count, (ip, info) in enumerate(aggregated_data.items()):
            record_id = f"{batch_id}{count:03d}"
            collect_time = info.get("collect_time")

            if isinstance(collect_time, str):
                try:
                    collect_time = datetime.datetime.strptime(collect_time, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    collect_time = now
            elif not isinstance(collect_time, datetime.datetime):
                collect_time = now

            record = (
                record_id,
                ip,
                collect_time,
                info.get("cpu_usage"),
                info.get("cpu_status"),
                info.get("memory_usage"),
                info.get("memory_status"),
                info.get("disk_usage"),
                info.get("disk_status"),
                "正常",
                info.get("bk_cloud_id", 0),
                now
            )
            records.append(record)

        cursor.executemany(insert_sql, records)
        conn.commit()

        print(f"    ✅ 监控数据存储完成，成功保存 {len(records)} 条性能记录")
        logger.info(f"📊 成功保存 {len(records)} 条性能监控记录到数据库")

        conn.close()
        return True, batch_id

    except Exception as e:
        print(f"    ❌ 数据存储失败: {e}")
        logger.error(f"🚨 保存性能数据到数据库失败: {e}")
        return False, None


def platform_performance_monitoring(params=None):
    try:
        print("🚀 启动平台性能监控服务...")
        logger.info("📊 开始执行平台性能监控...")
        start_time = datetime.datetime.now()

        time_range = params.get("time_range", TIME_RANGE) if params else TIME_RANGE
        save_to_db = params.get("save_to_db", True) if params else True

        print(f"⏰ 监控时间范围: {time_range}")
        logger.info(f"📅 监控时间范围: {time_range}")

        print("📊 开始采集各项性能监控指标...")
        cpu_data, memory_data, disk_data = get_performance_data(time_range)

        print("🔧 开始聚合分析性能数据...")
        aggregated_data = aggregate_performance_data(cpu_data, memory_data, disk_data)

        if not aggregated_data:
            print("⚠️ 未获取到任何性能监控数据")
            logger.warning("📊 未获取到任何性能数据")
            return {
                "success": False,
                "error": "未获取到任何性能数据",
                "timestamp": start_time.strftime("%Y-%m-%d %H:%M:%S"),
                "time_range": time_range
            }

        server_count = len(aggregated_data)
        active_servers = len([ip for ip, info in aggregated_data.items() if
                              info.get("cpu_status") != "丢失" or
                              info.get("memory_status") != "丢失" or
                              info.get("disk_status") != "丢失"])

        print(f"📈 性能数据统计分析...")
        anomaly_stats = {
            "cpu_anomalies": len([ip for ip, info in aggregated_data.items() if info.get("cpu_status") == "异常"]),
            "memory_anomalies": len(
                [ip for ip, info in aggregated_data.items() if info.get("memory_status") == "异常"]),
            "disk_anomalies": len([ip for ip, info in aggregated_data.items() if info.get("disk_status") == "异常"])
        }

        anomaly_servers = {
            "cpu_anomaly_ips": [ip for ip, info in aggregated_data.items() if info.get("cpu_status") == "异常"],
            "memory_anomaly_ips": [ip for ip, info in aggregated_data.items() if info.get("memory_status") == "异常"],
            "disk_anomaly_ips": [ip for ip, info in aggregated_data.items() if info.get("disk_status") == "异常"]
        }

        db_saved = False
        batch_id = None
        if save_to_db:
            print("💾 准备将监控数据持久化存储...")
            db_saved, batch_id = save_performance_data_to_db(aggregated_data)

        print(f"✅ 平台性能监控完成，预期监控 {server_count} 台服务器，实际获取到 {active_servers} 台服务器数据")
        logger.info(f"📊 平台性能监控完成，预期监控 {server_count} 台服务器，实际获取到 {active_servers} 台服务器数据")

        result = {
            "success": True,
            "message": f"平台性能监控完成，监控了 {active_servers}/{server_count} 台服务器",
            "timestamp": start_time.strftime("%Y-%m-%d %H:%M:%S"),
            "time_range": time_range,
            "server_count": server_count,
            "active_server_count": active_servers,
            "missing_server_count": server_count - active_servers,
            "anomaly_statistics": anomaly_stats,
            "anomaly_servers": anomaly_servers,
            "thresholds": THRESHOLDS,
            "database_saved": db_saved,
            "batch_id": batch_id,
            "summary": {
                "total_anomalies": sum(anomaly_stats.values()),
                "health_score": round((active_servers - sum(anomaly_stats.values())) / active_servers * 100,
                                      2) if active_servers > 0 else 0
            }
        }

        result = convert_datetime_to_string(result)

        return result

    except Exception as e:
        print(f"❌ 平台性能监控服务执行异常: {e}")
        logger.error(f"🚨 平台性能监控过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }


if __name__ == "__main__":
    test_params = {
        "time_range": "1h",
        "save_to_db": True
    }

    result = platform_performance_monitoring(test_params)
    print(f"测试结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
