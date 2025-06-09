#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import socket
import subprocess
import platform as sys_platform
from datetime import datetime
import time

import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from utils.logger import setup_logger
from utils.database import get_connection

logger = setup_logger(__name__)


def generate_id():
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"PL{timestamp}"


def generate_record_id():
    now = datetime.now()
    timestamp = now.strftime("%y%m%d%H%M%S") + f"{now.microsecond // 1000:03d}"
    return f"PL{timestamp}"


def generate_batch_id():
    return generate_id()


def check_port(host, port, timeout=2):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        start_time = time.time()
        result = s.connect_ex((host, port))
        response_time = time.time() - start_time
        if result == 0:
            return True, response_time
        else:
            return False, 0
    except Exception as e:
        logger.error(f"🚨 检查端口 {host}:{port} 时发生错误: {e}")
        return False, 0
    finally:
        s.close()


def is_process_running_linux(service_name, is_docker=False):
    try:
        if is_docker:
            cmd = f"docker ps | grep {service_name} | grep -v grep | wc -l"
        else:
            cmd = f"ps -ef | grep '{service_name}' | grep -v grep | wc -l"

        output = subprocess.check_output(cmd, shell=True).decode('utf-8').strip()
        return int(output) > 0
    except Exception as e:
        logger.error(f"🚨 检查进程状态时发生错误: {e}")
        return False


def is_process_running_windows(service_name):
    try:
        cmd = f'tasklist /FI "IMAGENAME eq {service_name}" /FO CSV'
        output = subprocess.check_output(cmd, shell=True).decode('utf-8').strip()
        return service_name.lower() in output.lower()
    except Exception as e:
        logger.error(f"🚨 检查Windows进程状态时发生错误: {e}")
        return False


def get_server_definitions():
    return [
        {
            "ip": "192.168.101.45",
            "name": "应用服务器",
            "platform": "算法中枢平台",
            "services": [
                {"name": "系统服务", "service_name": "ai-platform-modules-system-1.0.0.jar", "port": 19201,
                 "start_cmd": "nohup java -jar ai-platform-modules-system-1.0.0.jar >logs/ai-platform-modules-system.log &",
                 "stop_cmd": "pkill -f ai-platform-modules-system-1.0.0.jar"},
                {"name": "网关服务", "service_name": "ai-platform-gateway-1.0.0.jar", "port": 8080,
                 "start_cmd": "nohup java -jar ai-platform-gateway-1.0.0.jar >logs/ai-platform-gateway.log &",
                 "stop_cmd": "pkill -f ai-platform-gateway-1.0.0.jar"},
                {"name": "认证服务", "service_name": "ai-platform-auth-1.0.0.jar", "port": 19200,
                 "start_cmd": "nohup java -jar ai-platform-auth-1.0.0.jar >logs/ai-platform-auth.log &",
                 "stop_cmd": "pkill -f ai-platform-auth-1.0.0.jar"},
                {"name": "应用服务", "service_name": "ai-platform-modules-apply-1.0.0.jar", "port": 19802,
                 "start_cmd": "nohup java -jar ai-platform-modules-apply-1.0.0.jar >logs/ai-platform-modules-apply.log &",
                 "stop_cmd": "pkill -f ai-platform-modules-apply-1.0.0.jar"},
                {"name": "告警服务", "service_name": "ai-platform-modules-alarm-1.0.0.jar", "port": 19803,
                 "start_cmd": "nohup java -jar ai-platform-modules-alarm-1.0.0.jar >logs/ai-platform-modules-alarm.log &",
                 "stop_cmd": "pkill -f ai-platform-modules-alarm-1.0.0.jar"},
                {"name": "文件服务", "service_name": "ai-platform-modules-file-1.0.0.jar", "port": 19300,
                 "start_cmd": "nohup java -jar ai-platform-modules-file-1.0.0.jar >logs/ai-platform-modules-file.log &",
                 "stop_cmd": "pkill -f ai-platform-modules-file-1.0.0.jar"},
                {"name": "调度服务", "service_name": "ai-platform-modules-schedule-1.0.0.jar", "port": 19804,
                 "start_cmd": "nohup java -jar ai-platform-modules-schedule-1.0.0.jar >logs/ai-platform-modules-schedule.log &",
                 "stop_cmd": "pkill -f ai-platform-modules-schedule-1.0.0.jar"},
                {"name": "运维服务", "service_name": "ai-platform-modules-server-1.0.0.jar", "port": 19805,
                 "start_cmd": "nohup java -jar ai-platform-modules-server-1.0.0.jar >logs/ai-platform-modules-server.log &",
                 "stop_cmd": "pkill -f ai-platform-modules-server-1.0.0.jar"},
                {"name": "消息推送服务", "service_name": "ai-platform-modules-push-1.0.0.jar", "port": 19901,
                 "start_cmd": "nohup java -jar ai-platform-modules-push-1.0.0.jar >logs/ai-platform-modules-push.log &",
                 "stop_cmd": "pkill -f ai-platform-modules-push-1.0.0.jar"},
                {"name": "流转换服务", "service_name": "platform-admin.jar", "port": 8180,
                 "start_cmd": "nohup java -jar platform-admin.jar >logs/platform-admin.log &",
                 "stop_cmd": "pkill -f platform-admin.jar"}
            ]
        },
        {
            "ip": "192.168.101.45",
            "name": "应用服务器",
            "platform": "社区平台",
            "services": [
                {"name": "网关服务", "service_name": "scene-app-gateway-1.0.0.jar", "port": 8081,
                 "start_cmd": "nohup java -jar scene-app-gateway-1.0.0.jar >logs/scene-app-gateway.log &",
                 "stop_cmd": "pkill -f scene-app-gateway-1.0.0.jar"},
                {"name": "权限服务", "service_name": "scene-app-auth-1.0.0.jar", "port": 29200,
                 "start_cmd": "nohup java -jar scene-app-auth-1.0.0.jar >logs/scene-app-auth.log &",
                 "stop_cmd": "pkill -f scene-app-auth-1.0.0.jar"},
                {"name": "文件服务", "service_name": "scene-app-modules-file-1.0.0.jar", "port": 29300,
                 "start_cmd": "nohup java -jar scene-app-modules-file-1.0.0.jar >logs/scene-app-modules-file.log &",
                 "stop_cmd": "pkill -f scene-app-modules-file-1.0.0.jar"},
                {"name": "应用服务", "service_name": "scene-app-modules-apply-1.0.0.jar", "port": 29802,
                 "start_cmd": "nohup java -jar scene-app-modules-apply-1.0.0.jar >logs/scene-app-modules-apply.log &",
                 "stop_cmd": "pkill -f scene-app-modules-apply-1.0.0.jar"},
                {"name": "系统服务", "service_name": "scene-app-modules-system-1.0.0.jar", "port": 29201,
                 "start_cmd": "nohup java -jar scene-app-modules-system-1.0.0.jar >logs/scene-app-modules-system.log &",
                 "stop_cmd": "pkill -f scene-app-modules-system-1.0.0.jar"}
            ]
        },
        {
            "ip": "192.168.101.45",
            "name": "应用服务器",
            "platform": "城管平台",
            "services": [
                {"name": "文件服务", "service_name": "chengguan-app-modules-file-1.0.0.jar", "port": 39300,
                 "start_cmd": "nohup java -jar chengguan-app-modules-file-1.0.0.jar >logs/chengguan-app-modules-file.log &",
                 "stop_cmd": "pkill -f chengguan-app-modules-file-1.0.0.jar"},
                {"name": "系统服务", "service_name": "chengguan-app-modules-system-1.0.0.jar", "port": 39201,
                 "start_cmd": "nohup java -jar chengguan-app-modules-system-1.0.0.jar >logs/chengguan-app-modules-system.log &",
                 "stop_cmd": "pkill -f chengguan-app-modules-system-1.0.0.jar"},
                {"name": "应用服务", "service_name": "chengguan-app-modules-apply-1.0.0.jar", "port": 39802,
                 "start_cmd": "nohup java -jar chengguan-app-modules-apply-1.0.0.jar >logs/chengguan-app-modules-apply.log &",
                 "stop_cmd": "pkill -f chengguan-app-modules-apply-1.0.0.jar"},
                {"name": "网关服务", "service_name": "chengguan-app-gateway-1.0.0.jar", "port": 8082,
                 "start_cmd": "nohup java -jar chengguan-app-gateway-1.0.0.jar >logs/chengguan-app-gateway.log &",
                 "stop_cmd": "pkill -f chengguan-app-gateway-1.0.0.jar"},
                {"name": "权限服务", "service_name": "chengguan-app-auth-1.0.0.jar", "port": 39200,
                 "start_cmd": "nohup java -jar chengguan-app-auth-1.0.0.jar >logs/chengguan-app-auth.log &",
                 "stop_cmd": "pkill -f chengguan-app-auth-1.0.0.jar"}
            ]
        },
        {
            "ip": "192.168.101.53",
            "name": "中间件服务器",
            "platform": "算法中枢平台",
            "services": [
                {"name": "注册中心", "service_name": "nacos", "port": 8848,
                 "start_cmd": "/opt/nacos/bin/startup.sh -m standalone",
                 "stop_cmd": "/opt/nacos/bin/startup.sh -m shutdown.sh"},
                {"name": "缓存数据库", "service_name": "redis", "port": 6379,
                 "start_cmd": "docker start some-redis",
                 "stop_cmd": "docker stop some-redis"},
                {"name": "流媒体服务", "service_name": "zlmediakit", "port": 8087,
                 "start_cmd": "docker start zlmedia",
                 "stop_cmd": "docker stop zlmedia"},
                {"name": "消息队列", "service_name": "rabbitmq", "port": 15672,
                 "start_cmd": "docker start mq",
                 "stop_cmd": "docker stop mq"},
                {"name": "数据库", "service_name": "mysql", "port": 3306,
                 "start_cmd": "docker start mysql",
                 "stop_cmd": "docker stop mysql"},
                {"name": "wvp应用服务", "service_name": "wvp", "port": 8086,
                 "start_cmd": "nohup java -jar /home/wvp/wvp-pro-2.6.9-11100828.jar --spring.config.location=application.yml &",
                 "stop_cmd": "pkill -f wvp-pro-2.6.9-11100828.jar"}
            ]
        },
        {
            "ip": "192.168.121.30",
            "name": "算力节点",
            "platform": "算法中枢平台",
            "services": [
                {"name": "图片节点", "service_name": "192.168.101.207/howso-algo-c/image_detetor_release:v1.0.26",
                 "port": 10200, "start_cmd": "docker start ServerUp_5e377feaf1904cd38db0eb3596b79d63",
                 "stop_cmd": "docker stop ServerUp_5e377feaf1904cd38db0eb3596b79d63"},
                {"name": "视频服务", "service_name": "192.168.101.207/howso-algo-c/algorun_release:v1.0.24",
                 "port": 10100,
                 "start_cmd": "docker start ServerUp_325041ed44ad4ecda0d0c14d3f8fa5eb",
                 "stop_cmd": "docker stop ServerUp_325041ed44ad4ecda0d0c14d3f8fa5eb"}
            ]
        },
        {
            "ip": "192.168.101.94",
            "name": "应用服务器",
            "platform": "数字员工平台",
            "services": [
                {"name": "数字员工服务", "service_name": "labor-admin.jar", "port": 10000,
                 "start_cmd": "nohup java -jar labor-admin.jar >logs/labor-admin.log &",
                 "stop_cmd": "pkill -f labor-admin.jar"},
                {"name": "数字员工应用服务", "service_name": "labor-app-1.0.0.jar", "port": 10001,
                 "start_cmd": "nohup java -jar labor-app-1.0.0.jar >logs/labor-app.log &",
                 "stop_cmd": "pkill -f labor-app-1.0.0.jar"},
                {"name": "执行机服务", "service_name": "labor-agent-0.9.7.jar", "port": 8000,
                 "start_cmd": "nohup java -jar labor-agent-0.9.7.jar >logs/labor-agent.log &",
                 "stop_cmd": "pkill -f labor-agent-0.9.7.jar"},
                {"name": "缓存数据库", "service_name": "redis", "port": 6379,
                 "start_cmd": "docker start redis",
                 "stop_cmd": "docker stop redis"},
                {"name": "代理", "service_name": "nginx", "port": 80,
                 "start_cmd": "docker start nginx || systemctl start nginx",
                 "stop_cmd": "docker stop nginx || systemctl stop nginx"}
            ]
        },
        {
            "ip": "192.168.101.62",
            "name": "中间件服务器",
            "platform": "",
            "services": [
                {"name": "数据库", "service_name": "mysql", "port": 3306,
                 "start_cmd": "docker start mysql || systemctl start mysql",
                 "stop_cmd": "docker stop mysql || systemctl stop mysql"},
                {"name": "文件服务", "service_name": "minio", "port": 9000,
                 "start_cmd": "docker start minio",
                 "stop_cmd": "docker stop minio"}
            ]
        },
        {
            "ip": "192.168.10.141",
            "name": "应用服务器",
            "platform": "",
            "services": [
                {"name": "AI服务", "service_name": "aiserver", "port": 5001,
                 "start_cmd": "docker start aiserver || systemctl start aiserver",
                 "stop_cmd": "docker stop aiserver || systemctl stop aiserver"}
            ]
        },
        {
            "ip": "192.168.101.162",
            "name": "应用服务器",
            "platform": "标注平台",
            "services": [
                {"name": "xtreme1标注服务", "service_name": "jeecg-xtreme-start", "port": 7010,
                 "start_cmd": "docker start jeecg-xtreme-start",
                 "stop_cmd": "docker stop jeecg-xtreme-start"},
                {"name": "系统服务", "service_name": "jeecg-system-start", "port": 7001,
                 "start_cmd": "docker start jeecg-system-start",
                 "stop_cmd": "docker stop jeecg-system-start"},
                {"name": "前端服务", "service_name": "jeecgboot-vue3-nginx", "port": 80,
                 "start_cmd": "docker start jeecgboot-vue3-nginx",
                 "stop_cmd": "docker stop jeecgboot-vue3-nginx"},
                {"name": "文件服务", "service_name": "biaozhu-minio-1", "port": 8103,
                 "start_cmd": "docker start biaozhu-minio-1",
                 "stop_cmd": "docker stop biaozhu-minio-1"},
                {"name": "数据库", "service_name": "jeecg-boot-mysql", "port": 3306,
                 "start_cmd": "docker start jeecg-boot-mysql",
                 "stop_cmd": "docker stop jeecg-boot-mysql"},
                {"name": "网关服务", "service_name": "jeecg-boot-gateway", "port": 9999,
                 "start_cmd": "docker start jeecg-boot-gateway",
                 "stop_cmd": "docker stop jeecg-boot-gateway"},
                {"name": "注册中心", "service_name": "jeecg-boot-nacos", "port": 8848,
                 "start_cmd": "docker start jeecg-boot-nacos",
                 "stop_cmd": "docker stop jeecg-boot-nacos"},
                {"name": "缓存数据库", "service_name": "jeecg-boot-redis", "port": 6379,
                 "start_cmd": "docker start jeecg-boot-redis",
                 "stop_cmd": "docker stop jeecg-boot-redis"}
            ]
        },
        {
            "ip": "192.168.101.19",
            "name": "应用服务器",
            "platform": "训练平台",
            "services": [
                {"name": "文件服务", "service_name": "ai-modules-file-1.0.0.jar", "port": 9300,
                 "start_cmd": "nohup java -jar ai-modules-file-1.0.0.jar >logs/ai-modules-file.log &",
                 "stop_cmd": "pkill -f ai-modules-file-1.0.0.jar"},
                {"name": "样本服务", "service_name": "ai-sample-1.0.0.jar", "port": 9901,
                 "start_cmd": "nohup java -jar ai-sample-1.0.0.jar >logs/ai-sample.log &",
                 "stop_cmd": "pkill -f ai-sample-1.0.0.jar"},
                {"name": "网关服务", "service_name": "ai-gateway-1.0.0.jar", "port": 8080,
                 "start_cmd": "nohup java -jar ai-gateway-1.0.0.jar >logs/ai-gateway.log &",
                 "stop_cmd": "pkill -f ai-gateway-1.0.0.jar"},
                {"name": "系统服务", "service_name": "ai-modules-system-1.0.0.jar", "port": 9201,
                 "start_cmd": "nohup java -jar ai-modules-system-1.0.0.jar >logs/ai-modules-system.log &",
                 "stop_cmd": "pkill -f ai-modules-system-1.0.0.jar"},
                {"name": "算法服务", "service_name": "ai-algorithm-1.0.0.jar", "port": 9902,
                 "start_cmd": "nohup java -jar ai-algorithm-1.0.0.jar >logs/ai-algorithm.log &",
                 "stop_cmd": "pkill -f ai-algorithm-1.0.0.jar"},
                {"name": "统计服务", "service_name": "ai-analysis-1.0.0.jar", "port": 9912,
                 "start_cmd": "nohup java -jar ai-analysis-1.0.0.jar >logs/ai-analysis.log &",
                 "stop_cmd": "pkill -f ai-analysis-1.0.0.jar"},
                {"name": "权限服务", "service_name": "ai-auth-1.0.0.jar", "port": 9200,
                 "start_cmd": "nohup java -jar ai-auth-1.0.0.jar >logs/ai-auth.log &",
                 "stop_cmd": "pkill -f ai-auth-1.0.0.jar"}
            ]
        },
        {
            "ip": "192.168.101.19",
            "name": "中间件服务器",
            "platform": "训练平台",
            "services": [
                {"name": "注册中心", "service_name": "nacos", "port": 8848,
                 "start_cmd": "/opt/nacos/bin/startup.sh -m standalone",
                 "stop_cmd": "/opt/nacos/bin/startup.sh -m shutdown.sh"},
                {"name": "缓存数据库", "service_name": "redis", "port": 6379,
                 "start_cmd": "docker start redis",
                 "stop_cmd": "docker stop redis"}
            ]
        },
        {
            "ip": "192.168.101.101",
            "name": "中间件服务器",
            "platform": "社区平台",
            "services": [
                {"name": "注册中心", "service_name": "nacos", "port": 8848,
                 "start_cmd": "/opt/nacos/bin/startup.sh -m standalone",
                 "stop_cmd": "/opt/nacos/bin/startup.sh -m shutdown.sh"},
                {"name": "缓存数据库", "service_name": "redis", "port": 6379,
                 "start_cmd": "docker start redis",
                 "stop_cmd": "docker stop redis"}
            ]
        },
        {
            "ip": "192.168.101.101",
            "name": "中间件服务器",
            "platform": "城管平台",
            "services": [
                {"name": "注册中心", "service_name": "nacos", "port": 8848,
                 "start_cmd": "/opt/nacos/bin/startup.sh -m standalone",
                 "stop_cmd": "/opt/nacos/bin/startup.sh -m shutdown.sh"},
                {"name": "缓存数据库", "service_name": "redis", "port": 6379,
                 "start_cmd": "docker start redis",
                 "stop_cmd": "docker stop redis"}
            ]
        },
        {
            "ip": "192.168.101.42",
            "name": "应用服务器",
            "platform": "道路病害平台",
            "services": [
                {"name": "系统服务", "service_name": "jeecg-system-start-3.6.3.jar", "port": 8084,
                 "start_cmd": "nohup java -jar jeecg-system-start-3.6.3.jar >logs/jeecg-system-start.log &",
                 "stop_cmd": "pkill -f jeecg-system-start-3.6.3.jar"},
                {"name": "系统服务", "service_name": "dc3-center-data.jar", "port": 8500,
                 "start_cmd": "nohup java -jar dc3-center-data.jar >logs/dc3-center-data.log &",
                 "stop_cmd": "pkill -f dc3-center-data.jar"},
                {"name": "系统服务", "service_name": "dc3-center-auth.jar", "port": 8300,
                 "start_cmd": "nohup java -jar dc3-center-auth.jar >logs/dc3-center-auth.log &",
                 "stop_cmd": "pkill -f dc3-center-auth.jar"},
                {"name": "系统服务", "service_name": "dc3-center-manager.jar", "port": 8400,
                 "start_cmd": "nohup java -jar dc3-center-manager.jar >logs/dc3-center-manager.log &",
                 "stop_cmd": "pkill -f dc3-center-manager.jar"},
                {"name": "系统服务", "service_name": "dc3-gateway.jar", "port": 8000,
                 "start_cmd": "nohup java -jar dc3-gateway.jar >logs/dc3-gateway.log &",
                 "stop_cmd": "pkill -f dc3-gateway.jar"},
                {"name": "mq驱动服务", "service_name": "dc3-driver-mqtt.jar", "port": 1883,
                 "start_cmd": "nohup java -jar dc3-driver-mqtt.jar >logs/dc3-driver-mqtt.log &",
                 "stop_cmd": "pkill -f dc3-driver-mqtt.jar"}
            ]
        },
        {
            "ip": "192.168.101.43",
            "name": "文件服务器",
            "platform": "道路病害平台",
            "services": [
                {"name": "文件服务器前端", "service_name": "main.go", "port": 8088,
                 "start_cmd": "nohup ./main &",
                 "stop_cmd": "pkill -f main.go"},
                {"name": "文件服务器后端", "service_name": "fileserver", "port": 8080,
                 "start_cmd": "nohup ./fileserver &",
                 "stop_cmd": "pkill -f fileserver"}
            ]
        }
    ]


def insert_monitoring_data(results, batch_id, hostname, current_os, local_ips, insert_time):
    try:
        print(f"    💾 准备将服务监控数据写入数据库...")
        conn = get_connection()
        cursor = conn.cursor()

        insert_sql = """
                     INSERT INTO plat_service_monitoring (id, batch_id, platform, server_name, server_ip, service_name, \
                                                          service_id, port, status, process_status, response_time, \
                                                          start_cmd, stop_cmd, insert_time, local_ip, hostname, os_type) \
                     VALUES (%s, %s, %s, %s, %s, %s, \
                             %s, %s, %s, %s, %s, \
                             %s, %s, %s, %s, %s, %s) \
                     """

        inserted_count = 0
        for result in results:
            record_id = generate_record_id()
            time.sleep(0.001)

            values = (
                record_id,
                batch_id,
                result.get('platform', ''),
                result.get('server', ''),
                result.get('ip', ''),
                result.get('name', ''),
                result.get('id', ''),
                result.get('port', 0),
                result.get('status', '异常'),
                result.get('process', '未运行'),
                result.get('response', ''),
                result.get('start_cmd', ''),
                result.get('stop_cmd', ''),
                insert_time,
                ','.join(local_ips) if local_ips else '',
                hostname,
                current_os
            )

            cursor.execute(insert_sql, values)
            inserted_count += 1
            logger.debug(f"📝 插入服务监控记录 ID: {record_id}")

        conn.commit()
        print(f"    ✅ 服务监控数据存储完成，成功插入 {inserted_count} 条记录")
        logger.info(f"📊 成功插入 {inserted_count} 条监控数据到数据库")
        return True

    except Exception as e:
        print(f"    ❌ 数据存储失败: {e}")
        logger.error(f"🚨 插入数据库时发生错误: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def service_monitoring_check(params=None):
    try:
        print("🚀 启动服务状态监控检查系统...")
        logger.info("📊 开始执行扩展的服务监控检查...")

        current_os = sys_platform.system()
        print(f"🖥️ 检测到运行环境: {current_os}")
        logger.info(f"💻 当前操作系统: {current_os}")

        hostname = ""
        try:
            hostname = socket.gethostname()
            print(f"🏷️ 监控主机名: {hostname}")
            logger.info(f"🏠 主机名: {hostname}")
        except Exception as e:
            logger.error(f"🚨 获取主机名时发生错误: {e}")

        insert_time = datetime.now()
        print(f"⏰ 监控时间戳: {insert_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"📅 监控时间戳: {insert_time}")

        batch_id = generate_batch_id()
        print(f"📋 生成监控批次ID: {batch_id}")
        logger.info(f"🔖 批次ID: {batch_id}")

        local_ips = []
        try:
            local_ips = socket.gethostbyname_ex(hostname)[2]
            local_ips.append('127.0.0.1')
            print(f"🌐 检测到本地IP地址: {', '.join(local_ips)}")
            logger.info(f"🔗 本地IP列表: {', '.join(local_ips)}")
        except Exception as e:
            logger.error(f"🚨 获取本地IP时发生错误: {e}")

        all_results = []

        servers = get_server_definitions()
        total_servers = len(servers)
        print(f"📊 开始监控 {total_servers} 个服务器节点...")

        for i, server in enumerate(servers, 1):
            server_ip = server["ip"]
            is_local_server = server_ip in local_ips

            print(f"\n🔍 [{i}/{total_servers}] 监控服务器: {server['name']} ({server_ip})")
            print(f"    🏷️ 平台: {server['platform'] if server['platform'] else '通用平台'}")
            print(f"    📍 位置: {'本地服务器' if is_local_server else '远程服务器'}")

            logger.info(f"🔍 检查服务器: {server['name']} ({server_ip})")
            logger.info(f"🏷️ 平台: {server['platform'] if server['platform'] else '未指定'}")
            logger.info(f"📍 是否本地服务器: {'是' if is_local_server else '否'}")

            service_count = len(server["services"])
            print(f"    📋 服务数量: {service_count} 个服务待检测")

            for j, service in enumerate(server["services"], 1):
                service_name = service["name"]
                service_id = service["service_name"]
                port = service["port"]
                start_cmd = service.get("start_cmd", "")
                stop_cmd = service.get("stop_cmd", "")

                print(f"    🔧 [{j}/{service_count}] 检测服务: {service_name} (端口: {port})")
                logger.info(f"🔧 测试 {service_name} (端口: {port})...")

                port_connected, response_time = check_port(server_ip, port)

                is_docker = "docker" in start_cmd.lower()

                process_status = False
                if is_local_server:
                    if current_os == "Linux":
                        process_status = is_process_running_linux(service_id, is_docker)
                    elif current_os == "Windows":
                        if is_docker:
                            try:
                                docker_cmd = f"docker ps | findstr {service_id}"
                                output = subprocess.check_output(docker_cmd, shell=True).decode('utf-8').strip()
                                process_status = len(output) > 0
                            except Exception as e:
                                logger.error(f"🚨 检查Docker容器出错: {e}")
                                process_status = port_connected
                        else:
                            if ".jar" in service_id:
                                process_status = port_connected
                            else:
                                process_status = is_process_running_windows(service_id)
                else:
                    process_status = port_connected

                status = "正常" if port_connected else "异常"
                process_info = "运行中" if process_status else "未运行"
                response_info = f"{response_time * 1000:.2f}ms" if port_connected else "超时"

                status_emoji = "✅" if port_connected else "❌"
                process_emoji = "🟢" if process_status else "🔴"

                print(f"        {status_emoji} 端口状态: {status}")
                print(f"        {process_emoji} 进程状态: {process_info}")
                print(f"        ⏱️ 响应时间: {response_info}")

                all_results.append({
                    "server": server["name"],
                    "platform": server["platform"],
                    "ip": server_ip,
                    "name": service_name,
                    "id": service_id,
                    "port": port,
                    "status": status,
                    "process": process_info,
                    "response": response_info,
                    "start_cmd": start_cmd,
                    "stop_cmd": stop_cmd
                })

        print(f"\n💾 准备将监控结果持久化存储...")
        db_success = insert_monitoring_data(all_results, batch_id, hostname, current_os, local_ips, insert_time)

        total_services = len(all_results)
        running_ports = sum(1 for r in all_results if r['status'] == "正常")
        running_processes = sum(1 for r in all_results if r['process'] == "运行中")

        print(f"\n📊 服务监控统计结果:")
        print(f"    📋 总服务数: {total_services}")
        print(f"    ✅ 正常端口: {running_ports}")
        print(f"    🟢 运行进程: {running_processes}")
        print(f"    📈 端口成功率: {(running_ports / total_services * 100):.1f}%")
        print(f"    🔄 进程成功率: {(running_processes / total_services * 100):.1f}%")

        result = {
            "success": True,
            "db_insert_success": db_success,
            "batch_id": batch_id,
            "timestamp": insert_time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_services": total_services,
            "running_ports": running_ports,
            "running_processes": running_processes,
            "hostname": hostname,
            "os_type": current_os,
            "local_ips": local_ips,
            "results": all_results
        }

        print(
            f"✅ 服务监控检查完成。发现 {total_services} 个服务，{running_ports} 个运行端口，{running_processes} 个运行进程。")
        logger.info(
            f"📊 扩展服务监控检查完成。发现 {total_services} 个服务，{running_ports} 个运行端口，{running_processes} 个运行进程。")

        if db_success:
            print(f"💾 监控数据已成功写入数据库，批次ID: {batch_id}")
            logger.info(f"💾 监控数据已成功写入数据库，批次ID: {batch_id}")
        else:
            print(f"⚠️ 监控数据写入数据库失败")
            logger.warning("⚠️ 监控数据写入数据库失败")

        return result

    except Exception as e:
        print(f"❌ 服务监控检查系统执行异常: {e}")
        logger.error(f"🚨 扩展服务监控检查时发生错误: {e}")
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    result = service_monitoring_check()
    print(f"测试结果: {result}")
