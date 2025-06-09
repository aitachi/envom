#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import paramiko
import os
import re
import sys
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logger import setup_logger

logger = setup_logger(__name__)

SSH_CONFIGS = {
    '192.168.10.152': {'username': 'root', 'password': 'howso@123'},
    '192.168.101.222': {'username': 'root', 'password': 'zxx@123howso?'},
    '192.168.121.23': {'username': 'root', 'password': 'abc,.123'},
    '192.168.121.26': {'username': 'root', 'password': 'howso@123'}
}


class DiskInspector:
    def __init__(self):
        self.ssh_configs = SSH_CONFIGS
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.input_file = os.path.join(current_dir, 'data', 'system.json')
        self.output_file = os.path.join(current_dir, 'data', 'disk_inspection.json')

        # 打印路径信息用于调试
        print(f"当前脚本目录: {current_dir}")
        print(f"输入文件路径: {self.input_file}")
        print(f"输出文件路径: {self.output_file}")
        print(f"输入文件是否存在: {os.path.exists(self.input_file)}")

    def load_abnormal_ips(self):
        try:
            print(f"尝试读取文件: {self.input_file}")
            if not os.path.exists(self.input_file):
                error_msg = f"系统巡检文件不存在: {self.input_file}"
                logger.warning(error_msg)
                print(error_msg)

                # 检查父目录是否存在
                parent_dir = os.path.dirname(self.input_file)
                print(f"父目录 {parent_dir} 是否存在: {os.path.exists(parent_dir)}")
                if os.path.exists(parent_dir):
                    files_in_dir = os.listdir(parent_dir)
                    print(f"父目录中的文件: {files_in_dir}")

                return []

            with open(self.input_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                abnormal_disk_ips = data.get('abnormal_disk_ips', [])
                print(f"从system.json读取到的异常硬盘IP: {abnormal_disk_ips}")
                return abnormal_disk_ips
        except Exception as e:
            error_msg = f"读取系统巡检文件失败: {e}"
            logger.error(error_msg)
            print(error_msg)
            return []

    def check_ssh_config(self, ip):
        if ip not in self.ssh_configs:
            return False, "缺少root权限 无法巡检该IP"
        return True, None

    def connect_ssh(self, ip, timeout=15):
        try:
            has_config, error_msg = self.check_ssh_config(ip)
            if not has_config:
                return None, error_msg

            config = self.ssh_configs[ip]
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(ip, username=config['username'], password=config['password'], timeout=timeout)
            return ssh, None
        except paramiko.AuthenticationException:
            return None, "缺少root权限 无法巡检该IP"
        except paramiko.SSHException as e:
            return None, "缺少root权限 无法巡检该IP"
        except Exception as e:
            return None, "缺少root权限 无法巡检该IP"

    def execute_command(self, ssh, command, timeout=30):
        try:
            stdin, stdout, stderr = ssh.exec_command(command, timeout=timeout)
            output = stdout.read().decode('utf-8')
            error = stderr.read().decode('utf-8')
            return output, error
        except Exception as e:
            return None, str(e)

    def parse_disk_usage(self, df_output):
        partitions = []
        try:
            lines = df_output.strip().split('\n')[1:]
            for line in lines:
                parts = line.split()
                if len(parts) >= 6 and parts[0].startswith('/dev/'):
                    partition = {
                        'filesystem': parts[0],
                        'size': parts[1],
                        'used': parts[2],
                        'available': parts[3],
                        'usage_percent': parts[4],
                        'mount_point': parts[5]
                    }
                    partitions.append(partition)
        except:
            return {'error': '解析磁盘使用率失败'}
        return partitions

    def parse_disk_hardware(self, lsblk_output):
        disks = []
        try:
            lines = lsblk_output.strip().split('\n')[1:]
            for line in lines:
                parts = line.split()
                if len(parts) >= 3:
                    disk = {
                        'name': parts[0],
                        'size': parts[1],
                        'type': parts[2],
                        'mount_point': parts[3] if len(parts) > 3 else ''
                    }
                    disks.append(disk)
        except:
            return {'error': '解析磁盘硬件信息失败'}
        return disks

    def parse_disk_smart(self, smart_output):
        smart_info = {}
        try:
            lines = smart_output.strip().split('\n')
            for line in lines:
                if 'Model Family:' in line:
                    smart_info['model_family'] = line.split(':')[1].strip()
                elif 'Device Model:' in line:
                    smart_info['device_model'] = line.split(':')[1].strip()
                elif 'Serial Number:' in line:
                    smart_info['serial_number'] = line.split(':')[1].strip()
                elif 'User Capacity:' in line:
                    smart_info['capacity'] = line.split(':')[1].strip()
                elif 'Rotation Rate:' in line:
                    smart_info['rotation_rate'] = line.split(':')[1].strip()
                elif 'SMART overall-health' in line:
                    smart_info['health_status'] = line.split(':')[1].strip()
        except:
            smart_info['error'] = '解析SMART信息失败'
        return smart_info

    def analyze_disk_status(self, disk_info):
        analysis = {
            'status': '正常',
            'warnings': [],
            'recommendations': [],
            'high_usage_partitions': []
        }

        try:
            if 'disk_usage' in disk_info and isinstance(disk_info['disk_usage'], list):
                for partition in disk_info['disk_usage']:
                    if isinstance(partition, dict) and 'usage_percent' in partition:
                        usage_str = partition['usage_percent'].replace('%', '')
                        try:
                            usage = float(usage_str)
                            if usage > 90:
                                analysis['status'] = '严重'
                                analysis['warnings'].append(f"分区 {partition['mount_point']} 使用率过高: {usage}%")
                                analysis['high_usage_partitions'].append(partition)
                                analysis['recommendations'].append(f"立即清理 {partition['mount_point']} 分区")
                            elif usage > 80:
                                analysis['status'] = '警告'
                                analysis['warnings'].append(f"分区 {partition['mount_point']} 使用率较高: {usage}%")
                                analysis['high_usage_partitions'].append(partition)
                                analysis['recommendations'].append(f"监控 {partition['mount_point']} 分区使用情况")
                        except:
                            pass

            if 'smart_info' in disk_info and isinstance(disk_info['smart_info'], dict):
                health = disk_info['smart_info'].get('health_status', '')
                if 'PASSED' not in health and health != '':
                    analysis['warnings'].append(f"硬盘健康状态异常: {health}")
                    analysis['recommendations'].append("检查硬盘健康状态，考虑备份数据")

        except Exception as e:
            analysis['error'] = f'分析失败: {str(e)}'

        return analysis

    def create_test_data(self):
        """创建测试数据文件，如果system.json不存在"""
        try:
            # 确保data目录存在
            data_dir = os.path.dirname(self.input_file)
            os.makedirs(data_dir, exist_ok=True)

            # 创建测试的system.json文件
            test_data = {
                'generation_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'query_parameters': {
                    'hours': 6,
                    'memory_threshold': 70,
                    'disk_threshold': 80
                },
                'abnormal_memory_ips': ['192.168.10.152', '192.168.121.23'],
                'abnormal_disk_ips': ['192.168.121.23', '192.168.121.26'],
                'server_monitoring': {
                    'abnormal_memory_ips': ['192.168.10.152', '192.168.121.23'],
                    'abnormal_disk_ips': ['192.168.121.23', '192.168.121.26'],
                    'memory_details': [],
                    'disk_details': []
                },
                'environment_monitoring': {
                    'abnormal_environment_details': []
                }
            }

            with open(self.input_file, 'w', encoding='utf-8') as f:
                json.dump(test_data, f, ensure_ascii=False, indent=2)

            print(f"创建测试数据文件: {self.input_file}")
            logger.info(f"创建测试数据文件: {self.input_file}")
            return True
        except Exception as e:
            print(f"创建测试数据文件失败: {e}")
            logger.error(f"创建测试数据文件失败: {e}")
            return False

    def inspect_disk_details(self, ip_list=None):
        print("硬盘巡检服务启动")
        logger.info("硬盘巡检服务启动")

        if not ip_list:
            print("从system.json文件读取异常硬盘IP")
            ip_list = self.load_abnormal_ips()

            # 如果没有读取到IP且文件不存在，尝试创建测试数据
            if not ip_list and not os.path.exists(self.input_file):
                print("system.json文件不存在，创建测试数据...")
                if self.create_test_data():
                    ip_list = self.load_abnormal_ips()

        if not ip_list:
            print("没有找到需要巡检的硬盘异常IP")
            logger.warning("没有找到需要巡检的硬盘异常IP")

            # 提供手动测试选项
            print("是否要手动指定IP进行测试？可用的IP配置有:")
            for ip in self.ssh_configs.keys():
                print(f"  - {ip}")

            # 使用配置中的第一个IP作为测试
            test_ip = list(self.ssh_configs.keys())[0]
            print(f"使用 {test_ip} 进行测试巡检...")
            ip_list = [test_ip]

        print(f"发现需要巡检的硬盘异常IP: {ip_list}")
        results = {}

        for ip in ip_list:
            print(f"开始巡检服务器: {ip}")
            logger.info(f"开始硬盘详细巡检服务器: {ip}")

            result = {
                'ip': ip,
                'status': '巡检失败',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'ssh_connection': {},
                'disk_usage': [],
                'hardware_info': [],
                'smart_info': {},
                'large_files': [],
                'analysis': {},
                'error': None
            }

            has_config, config_error = self.check_ssh_config(ip)
            if not has_config:
                result['ssh_connection'] = {
                    'status': '无权限',
                    'error': config_error,
                    'user': 'root'
                }
                result['error'] = config_error
                print(f"服务器 {ip}: {config_error}")
                results[ip] = result
                continue

            ssh, error = self.connect_ssh(ip)
            if ssh is None:
                result['ssh_connection'] = {
                    'status': '无权限',
                    'error': error,
                    'user': self.ssh_configs.get(ip, {}).get('username', 'root')
                }
                result['error'] = error
                print(f"服务器 {ip}: {error}")
                results[ip] = result
                continue

            result['ssh_connection'] = {
                'status': '连接成功',
                'user': self.ssh_configs[ip]['username']
            }

            try:
                print(f"正在获取 {ip} 的硬盘信息...")

                # 获取磁盘使用率
                df_cmd = "df -h"
                output, error = self.execute_command(ssh, df_cmd)
                if output:
                    result['disk_usage'] = self.parse_disk_usage(output)
                    print(f"  ✓ 获取磁盘使用率成功")

                # 获取硬件信息
                lsblk_cmd = "lsblk -o NAME,SIZE,TYPE,MOUNTPOINT"
                output, error = self.execute_command(ssh, lsblk_cmd)
                if output:
                    result['hardware_info'] = self.parse_disk_hardware(output)
                    print(f"  ✓ 获取硬盘硬件信息成功")

                # 获取SMART信息
                smart_cmd = "smartctl -a /dev/sda 2>/dev/null || smartctl -a /dev/vda 2>/dev/null || echo 'smartctl not available'"
                output, error = self.execute_command(ssh, smart_cmd)
                if output and 'not available' not in output:
                    result['smart_info'] = self.parse_disk_smart(output)
                    print(f"  ✓ 获取SMART信息成功")
                else:
                    print(f"  ⚠ SMART信息不可用")

                # 查找大文件
                large_files_cmd = "find / -type f -size +100M 2>/dev/null | head -10"
                output, error = self.execute_command(ssh, large_files_cmd)
                if output:
                    result['large_files'] = [f for f in output.strip().split('\n') if f.strip()][:10]
                    print(f"  ✓ 找到 {len(result['large_files'])} 个大文件")

                # 获取目录大小
                du_cmd = "du -sh /var/log /tmp /var/cache 2>/dev/null || echo 'du failed'"
                output, error = self.execute_command(ssh, du_cmd)
                if output and 'failed' not in output:
                    result['directory_sizes'] = output.strip()
                    print(f"  ✓ 获取目录大小信息成功")

                # 分析磁盘状态
                result['analysis'] = self.analyze_disk_status(result)
                result['status'] = '巡检成功'

                print(f"服务器 {ip} 硬盘巡检完成")
                logger.info(f"服务器 {ip} 硬盘巡检完成")

            except Exception as e:
                result['error'] = str(e)
                print(f"服务器 {ip} 硬盘巡检失败: {e}")
                logger.error(f"服务器 {ip} 硬盘巡检失败: {e}")
            finally:
                ssh.close()

            results[ip] = result

        print("硬盘巡检服务执行完毕")
        logger.info("硬盘巡检服务执行完毕")
        return results

    def save_to_file(self, data):
        try:
            os.makedirs(os.path.dirname(self.output_file), exist_ok=True)
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"硬盘巡检结果已保存到: {self.output_file}")
            logger.info(f"硬盘巡检结果已保存到: {self.output_file}")
            return True
        except Exception as e:
            print(f"保存结果文件失败: {e}")
            logger.error(f"保存结果文件失败: {e}")
            return False


def disk_inspection(params=None):
    try:
        print("开始执行硬盘巡检")
        logger.info("开始执行硬盘巡检")

        ip_list = params.get('ip_list') if params else None
        inspector = DiskInspector()

        results = inspector.inspect_disk_details(ip_list)

        if not results:
            return {
                "success": False,
                "message": "硬盘巡检跳过，没有需要巡检的服务器IP",
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "output_file": inspector.output_file,
                "successful_count": 0,
                "failed_count": 0,
                "no_permission_count": 0
            }

        report_data = {
            'generation_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'inspected_count': len(results),
            'success_count': sum(1 for r in results.values() if r.get('status') == '巡检成功'),
            'failed_count': sum(1 for r in results.values() if r.get('status') == '巡检失败'),
            'no_permission_count': sum(
                1 for r in results.values() if r.get('ssh_connection', {}).get('status') == '无权限'),
            'results': results
        }

        inspector.save_to_file(report_data)
        successful_count = report_data['success_count']
        no_permission_count = report_data['no_permission_count']
        print(f"硬盘巡检完成，共处理{len(results)}台服务器，成功{successful_count}台，无权限{no_permission_count}台")

        return {
            "success": True,
            "message": f"硬盘巡检完成，共处理{len(results)}台服务器，成功{successful_count}台",
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "output_file": inspector.output_file,
            "successful_count": successful_count,
            "failed_count": len(results) - successful_count,
            "no_permission_count": no_permission_count
        }

    except Exception as e:
        print(f"硬盘巡检服务异常: {e}")
        logger.error(f"硬盘巡检服务异常: {e}")
        return {
            "success": False,
            "message": f"硬盘巡检服务异常: {str(e)}",
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "error": str(e)
        }


if __name__ == "__main__":
    result = disk_inspection()
    print(json.dumps(result, ensure_ascii=False, indent=2))