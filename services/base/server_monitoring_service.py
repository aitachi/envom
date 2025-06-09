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
                {"name": "你猜服务", "service_name": "ai-platform-modules-system-1.0.0.jar", "port": 1111,
                 "start_cmd": "nohup java -jar ai-platform-modules-system-1.0.0.jar >logs/ai-platform-modules-system.log &",
                 "stop_cmd": "pkill -f ai-platform-modules-system-1.0.0.jar"},
            ]
        },
        {
            "ip": "192.168.101.45",
            "name": "应用服务器",
            "platform": "A平台",
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
