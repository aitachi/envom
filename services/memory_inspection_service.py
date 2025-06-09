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


class MemoryInspector:
    def __init__(self):
        self.ssh_configs = SSH_CONFIGS
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.input_file = os.path.join(current_dir, 'data', 'system.json')
        self.output_file = os.path.join(current_dir, 'data', 'memory_inspection.json')

        # 主板型号与内存支持的详细映射表
        self.motherboard_specs = {
            # Intel 芯片组 - 消费级
            'H310': {
                'max_total_memory': 32,
                'max_memory_per_slot': 16,
                'typical_slots': 2,
                'memory_types': ['DDR4-2666', 'DDR4-2400', 'DDR4-2133']
            },
            'B360': {
                'max_total_memory': 128,
                'max_memory_per_slot': 32,
                'typical_slots': 4,
                'memory_types': ['DDR4-2666', 'DDR4-2400', 'DDR4-2133']
            },
            'H370': {
                'max_total_memory': 128,
                'max_memory_per_slot': 32,
                'typical_slots': 4,
                'memory_types': ['DDR4-2666', 'DDR4-2400', 'DDR4-2133']
            },
            'Z370': {
                'max_total_memory': 128,
                'max_memory_per_slot': 32,
                'typical_slots': 4,
                'memory_types': ['DDR4-4266', 'DDR4-4000', 'DDR4-3600', 'DDR4-2666']
            },
            'Z390': {
                'max_total_memory': 128,
                'max_memory_per_slot': 32,
                'typical_slots': 4,
                'memory_types': ['DDR4-4266', 'DDR4-4000', 'DDR4-3600', 'DDR4-2666']
            },
            'B460': {
                'max_total_memory': 128,
                'max_memory_per_slot': 32,
                'typical_slots': 4,
                'memory_types': ['DDR4-2933', 'DDR4-2666', 'DDR4-2400']
            },
            'H470': {
                'max_total_memory': 128,
                'max_memory_per_slot': 32,
                'typical_slots': 4,
                'memory_types': ['DDR4-2933', 'DDR4-2666', 'DDR4-2400']
            },
            'Z490': {
                'max_total_memory': 128,
                'max_memory_per_slot': 32,
                'typical_slots': 4,
                'memory_types': ['DDR4-4800', 'DDR4-4266', 'DDR4-3600', 'DDR4-2933']
            },
            'B560': {
                'max_total_memory': 128,
                'max_memory_per_slot': 32,
                'typical_slots': 4,
                'memory_types': ['DDR4-3200', 'DDR4-2933', 'DDR4-2666']
            },
            'H570': {
                'max_total_memory': 128,
                'max_memory_per_slot': 32,
                'typical_slots': 4,
                'memory_types': ['DDR4-3200', 'DDR4-2933', 'DDR4-2666']
            },
            'Z590': {
                'max_total_memory': 128,
                'max_memory_per_slot': 32,
                'typical_slots': 4,
                'memory_types': ['DDR4-5000', 'DDR4-4800', 'DDR4-3600', 'DDR4-3200']
            },
            'B660': {
                'max_total_memory': 128,
                'max_memory_per_slot': 32,
                'typical_slots': 4,
                'memory_types': ['DDR5-4800', 'DDR4-3200', 'DDR4-2933']
            },
            'H670': {
                'max_total_memory': 128,
                'max_memory_per_slot': 32,
                'typical_slots': 4,
                'memory_types': ['DDR5-4800', 'DDR4-3200', 'DDR4-2933']
            },
            'Z690': {
                'max_total_memory': 128,
                'max_memory_per_slot': 32,
                'typical_slots': 4,
                'memory_types': ['DDR5-6400', 'DDR5-5600', 'DDR5-4800', 'DDR4-3200']
            },
            'B760': {
                'max_total_memory': 192,
                'max_memory_per_slot': 48,
                'typical_slots': 4,
                'memory_types': ['DDR5-5600', 'DDR5-4800', 'DDR4-3200']
            },
            'H770': {
                'max_total_memory': 192,
                'max_memory_per_slot': 48,
                'typical_slots': 4,
                'memory_types': ['DDR5-5600', 'DDR5-4800', 'DDR4-3200']
            },
            'Z790': {
                'max_total_memory': 192,
                'max_memory_per_slot': 48,
                'typical_slots': 4,
                'memory_types': ['DDR5-7200', 'DDR5-6400', 'DDR5-5600', 'DDR4-3200']
            },

            # AMD 芯片组
            'A320': {
                'max_total_memory': 128,
                'max_memory_per_slot': 32,
                'typical_slots': 4,
                'memory_types': ['DDR4-2667', 'DDR4-2400', 'DDR4-2133']
            },
            'B350': {
                'max_total_memory': 128,
                'max_memory_per_slot': 32,
                'typical_slots': 4,
                'memory_types': ['DDR4-3200', 'DDR4-2933', 'DDR4-2667']
            },
            'X370': {
                'max_total_memory': 128,
                'max_memory_per_slot': 32,
                'typical_slots': 4,
                'memory_types': ['DDR4-3600', 'DDR4-3200', 'DDR4-2933']
            },
            'B450': {
                'max_total_memory': 128,
                'max_memory_per_slot': 32,
                'typical_slots': 4,
                'memory_types': ['DDR4-3200', 'DDR4-2933', 'DDR4-2667']
            },
            'X470': {
                'max_total_memory': 128,
                'max_memory_per_slot': 32,
                'typical_slots': 4,
                'memory_types': ['DDR4-3600', 'DDR4-3200', 'DDR4-2933']
            },
            'A520': {
                'max_total_memory': 128,
                'max_memory_per_slot': 32,
                'typical_slots': 4,
                'memory_types': ['DDR4-3200', 'DDR4-2933', 'DDR4-2667']
            },
            'B550': {
                'max_total_memory': 128,
                'max_memory_per_slot': 32,
                'typical_slots': 4,
                'memory_types': ['DDR4-4000', 'DDR4-3600', 'DDR4-3200']
            },
            'X570': {
                'max_total_memory': 128,
                'max_memory_per_slot': 32,
                'typical_slots': 4,
                'memory_types': ['DDR4-4000', 'DDR4-3600', 'DDR4-3200']
            },
            'B650': {
                'max_total_memory': 256,
                'max_memory_per_slot': 64,
                'typical_slots': 4,
                'memory_types': ['DDR5-5200', 'DDR5-4800', 'DDR5-4000']
            },
            'X670': {
                'max_total_memory': 256,
                'max_memory_per_slot': 64,
                'typical_slots': 4,
                'memory_types': ['DDR5-6000', 'DDR5-5200', 'DDR5-4800']
            },

            # 服务器芯片组
            'C621': {
                'max_total_memory': 2048,
                'max_memory_per_slot': 256,
                'typical_slots': 8,
                'memory_types': ['DDR4-3200', 'DDR4-2933', 'DDR4-2666', 'DDR4-2400']
            },
            'C622': {
                'max_total_memory': 2048,
                'max_memory_per_slot': 256,
                'typical_slots': 8,
                'memory_types': ['DDR4-3200', 'DDR4-2933', 'DDR4-2666', 'DDR4-2400']
            },
            'C624': {
                'max_total_memory': 2048,
                'max_memory_per_slot': 256,
                'typical_slots': 12,
                'memory_types': ['DDR4-3200', 'DDR4-2933', 'DDR4-2666', 'DDR4-2400']
            },
            'C627': {
                'max_total_memory': 2048,
                'max_memory_per_slot': 256,
                'typical_slots': 12,
                'memory_types': ['DDR4-3200', 'DDR4-2933', 'DDR4-2666', 'DDR4-2400']
            },
            'C629': {
                'max_total_memory': 2048,
                'max_memory_per_slot': 256,
                'typical_slots': 12,
                'memory_types': ['DDR4-3200', 'DDR4-2933', 'DDR4-2666', 'DDR4-2400']
            },
        }

    def load_abnormal_ips(self):
        try:
            if not os.path.exists(self.input_file):
                logger.error(f"系统巡检文件不存在: {self.input_file}")
                return []

            with open(self.input_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('abnormal_memory_ips', [])
        except Exception as e:
            logger.error(f"读取系统巡检文件失败: {e}")
            logger.error(f"尝试读取的文件路径: {self.input_file}")
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

    def parse_memory_usage(self, free_output):
        try:
            lines = free_output.strip().split('\n')
            for line in lines:
                if '内存：' in line or 'Mem:' in line:
                    parts = line.split()
                    if len(parts) >= 7:
                        total_gb = parts[1]
                        used_gb = parts[2]
                        available_gb = parts[6] if len(parts) > 6 else parts[3]

                        # 转换为KB进行计算
                        if 'Gi' in total_gb:
                            total_kb = float(total_gb.replace('Gi', '')) * 1024 * 1024
                            used_kb = float(used_gb.replace('Gi', '')) * 1024 * 1024
                        elif 'Mi' in total_gb:
                            total_kb = float(total_gb.replace('Mi', '')) * 1024
                            used_kb = float(used_gb.replace('Mi', '')) * 1024
                        else:
                            # 假设是KB
                            total_kb = float(total_gb)
                            used_kb = float(used_gb)

                        usage_percent = round((used_kb / total_kb) * 100, 2) if total_kb > 0 else 0

                        return {
                            'total_memory': total_gb,
                            'used_memory': used_gb,
                            'available_memory': available_gb,
                            'usage_percent': usage_percent,
                            'total_memory_gb': round(total_kb / (1024 * 1024), 2)
                        }
        except Exception as e:
            logger.error(f"解析内存使用率失败: {e}")
            return {'error': '解析内存使用率失败'}
        return {}

    def get_chipset_specs(self, chipset):
        """获取芯片组的详细规格"""
        if chipset in self.motherboard_specs:
            return self.motherboard_specs[chipset]

        # 如果精确匹配失败，尝试模糊匹配
        for key in self.motherboard_specs.keys():
            if key in chipset or chipset in key:
                return self.motherboard_specs[key]

        # 默认规格
        return {
            'max_total_memory': 128,
            'max_memory_per_slot': 32,
            'typical_slots': 4,
            'memory_types': ['DDR4-3200', 'DDR4-2933', 'DDR4-2666']
        }

    def parse_motherboard_info(self, dmidecode_output):
        """解析主板信息和内存规格"""
        motherboard_info = {
            'manufacturer': '未知',
            'product_name': '未知',
            'version': '未知',
            'chipset': '未知',
            'max_total_memory': '未知',
            'max_memory_per_slot': '未知',
            'supported_memory_types': [],
            'recommended_slots': '未知'
        }

        try:
            lines = dmidecode_output.strip().split('\n')
            current_section = None

            for line in lines:
                line = line.strip()

                # 检测主板信息段落
                if 'Base Board Information' in line or 'System Information' in line:
                    current_section = 'motherboard'
                elif 'Handle' in line and 'DMI type' in line:
                    current_section = None

                if current_section == 'motherboard':
                    if 'Manufacturer:' in line:
                        motherboard_info['manufacturer'] = line.split(':', 1)[1].strip()
                    elif 'Product Name:' in line:
                        motherboard_info['product_name'] = line.split(':', 1)[1].strip()
                    elif 'Version:' in line:
                        motherboard_info['version'] = line.split(':', 1)[1].strip()

            # 尝试从产品名称中提取芯片组信息
            product_name = motherboard_info['product_name'].upper()
            detected_chipset = None

            # 按优先级匹配芯片组
            chipset_list = list(self.motherboard_specs.keys())
            # 先匹配较新的芯片组
            chipset_list.sort(key=lambda x: x, reverse=True)

            for chipset in chipset_list:
                if chipset in product_name:
                    detected_chipset = chipset
                    break

            # 如果产品名称匹配失败，尝试通过制造商推断
            if not detected_chipset:
                manufacturer = motherboard_info['manufacturer'].upper()
                # 根据制造商和产品名称的模式进行推断
                for chipset in chipset_list:
                    if chipset in product_name or any(
                            pattern in product_name for pattern in [chipset[:3], chipset[-3:]]):
                        detected_chipset = chipset
                        break

            # 应用检测到的芯片组规格
            if detected_chipset:
                motherboard_info['chipset'] = detected_chipset
                specs = self.get_chipset_specs(detected_chipset)
                motherboard_info['max_total_memory'] = f"{specs['max_total_memory']}GB"
                motherboard_info['max_memory_per_slot'] = f"{specs['max_memory_per_slot']}GB"
                motherboard_info['supported_memory_types'] = specs['memory_types']
                motherboard_info['recommended_slots'] = specs['typical_slots']
            else:
                # 使用默认值
                default_specs = self.get_chipset_specs('')
                motherboard_info['max_total_memory'] = f"{default_specs['max_total_memory']}GB (估算)"
                motherboard_info['max_memory_per_slot'] = f"{default_specs['max_memory_per_slot']}GB (估算)"
                motherboard_info['supported_memory_types'] = default_specs['memory_types']
                motherboard_info['recommended_slots'] = default_specs['typical_slots']

        except Exception as e:
            logger.error(f"解析主板信息失败: {e}")
            motherboard_info['error'] = f"解析主板信息失败: {str(e)}"

        return motherboard_info

    def parse_memory_hardware(self, dmidecode_output):
        memory_slots = []
        current_slot = {}
        total_installed_memory = 0
        actual_slots = 0
        max_slot_capacity = 0

        try:
            lines = dmidecode_output.strip().split('\n')
            in_memory_device = False

            for line in lines:
                line = line.strip()

                if 'Memory Device' in line:
                    # 保存上一个插槽信息
                    if current_slot and current_slot.get('size', '') != 'No Module Installed':
                        memory_slots.append(current_slot.copy())
                    current_slot = {}
                    in_memory_device = True
                    actual_slots += 1
                elif 'Handle' in line and 'DMI type' in line and 'Memory Device' not in line:
                    in_memory_device = False

                if in_memory_device:
                    if 'Size:' in line:
                        size_str = line.split(':')[1].strip()
                        current_slot['size'] = size_str

                        if 'No Module Installed' not in size_str and size_str != 'Unknown':
                            # 计算总安装内存（转换为GB）
                            if 'GB' in size_str:
                                try:
                                    size_gb = float(re.findall(r'(\d+)', size_str)[0])
                                    total_installed_memory += size_gb
                                    max_slot_capacity = max(max_slot_capacity, size_gb)
                                except:
                                    pass

                    elif 'Speed:' in line and 'Unknown' not in line:
                        current_slot['speed'] = line.split(':')[1].strip()
                    elif 'Manufacturer:' in line:
                        current_slot['manufacturer'] = line.split(':')[1].strip()
                    elif 'Part Number:' in line:
                        current_slot['part_number'] = line.split(':')[1].strip()
                    elif 'Type:' in line:
                        current_slot['type'] = line.split(':')[1].strip()
                    elif 'Maximum Voltage:' in line:
                        current_slot['voltage'] = line.split(':')[1].strip()

            # 处理最后一个插槽
            if current_slot and current_slot.get('size', '') != 'No Module Installed':
                memory_slots.append(current_slot.copy())

            installed_count = len(memory_slots)
            empty_slots = actual_slots - installed_count

            return {
                'total_slots': actual_slots,
                'installed_slots': installed_count,
                'empty_slots': empty_slots,
                'total_installed_memory_gb': total_installed_memory,
                'max_installed_slot_capacity_gb': max_slot_capacity,
                'memory_modules': memory_slots
            }
        except Exception as e:
            logger.error(f"解析内存硬件信息失败: {e}")
            return {'error': '解析内存硬件信息失败'}

    def parse_top_processes(self, ps_output):
        processes = []
        try:
            lines = ps_output.strip().split('\n')[1:]
            for line in lines:
                parts = line.split()
                if len(parts) >= 11:
                    process = {
                        'user': parts[0],
                        'pid': parts[1],
                        'cpu_percent': parts[2],
                        'memory_percent': parts[3],
                        'memory_usage': parts[5],
                        'command': ' '.join(parts[10:])[:50]
                    }
                    processes.append(process)
        except Exception as e:
            logger.error(f"解析进程信息失败: {e}")
            return {'error': '解析进程信息失败'}
        return processes

    def generate_memory_recommendations(self, memory_info):
        """生成详细的内存推荐建议"""
        recommendations = []

        try:
            motherboard_info = memory_info.get('motherboard_info', {})
            hardware_info = memory_info.get('hardware_info', {})
            memory_usage = memory_info.get('memory_usage', {})

            # 获取主板规格
            max_total_str = motherboard_info.get('max_total_memory', '128GB')
            max_slot_str = motherboard_info.get('max_memory_per_slot', '32GB')
            total_slots = hardware_info.get('total_slots', 4)
            empty_slots = hardware_info.get('empty_slots', 0)
            current_memory = hardware_info.get('total_installed_memory_gb', 0)

            # 解析数值
            max_total_gb = float(re.findall(r'(\d+)', max_total_str)[0]) if re.findall(r'(\d+)', max_total_str) else 128
            max_slot_gb = float(re.findall(r'(\d+)', max_slot_str)[0]) if re.findall(r'(\d+)', max_slot_str) else 32

            # 内存使用率分析
            usage_percent = memory_usage.get('usage_percent', 0)
            if usage_percent > 85:
                recommendations.append(f"内存使用率高达{usage_percent}%，建议立即升级内存")
            elif usage_percent > 75:
                recommendations.append(f"内存使用率{usage_percent}%，建议考虑增加内存")

            # 扩展建议
            if empty_slots > 0:
                if current_memory > 0:
                    # 计算可添加的内存
                    remaining_capacity = max_total_gb - current_memory
                    max_additional_per_slot = min(max_slot_gb, remaining_capacity / empty_slots)

                    recommendations.append(
                        f"有{empty_slots}个空闲插槽，每个插槽最大支持{max_slot_gb}GB内存条"
                    )
                    recommendations.append(
                        f"建议配置: 可增加{empty_slots}条{int(max_additional_per_slot)}GB内存条"
                    )

                    # 推荐具体配置
                    if empty_slots >= 2 and max_additional_per_slot >= 16:
                        recommendations.append(
                            f"推荐配置: {empty_slots}x{int(max_additional_per_slot)}GB = {int(empty_slots * max_additional_per_slot)}GB额外内存"
                        )
                else:
                    recommendations.append(f"所有{total_slots}个插槽均可使用，每插槽最大{max_slot_gb}GB")
            else:
                # 没有空插槽的情况
                current_max_slot = hardware_info.get('max_installed_slot_capacity_gb', 0)
                if current_max_slot < max_slot_gb:
                    upgrade_potential = (max_slot_gb - current_max_slot) * total_slots
                    recommendations.append(
                        f"可通过替换现有内存条升级: 当前最大单条{current_max_slot}GB，可升级至{max_slot_gb}GB"
                    )
                    recommendations.append(
                        f"最大可升级至: {total_slots}x{max_slot_gb}GB = {int(total_slots * max_slot_gb)}GB"
                    )
                else:
                    recommendations.append("内存配置已达主板最大支持容量")

            # 内存类型建议
            supported_types = motherboard_info.get('supported_memory_types', [])
            if supported_types:
                recommendations.append(f"支持内存类型: {', '.join(supported_types[:3])}")
                if 'DDR5' in supported_types[0]:
                    recommendations.append("建议优先选择DDR5内存以获得更好性能")
                elif 'DDR4' in supported_types[0]:
                    recommendations.append("建议选择DDR4-3200或更高频率内存")

        except Exception as e:
            logger.error(f"生成内存建议失败: {e}")
            recommendations.append("内存建议生成失败")

        return recommendations

    def analyze_memory_status(self, memory_info):
        analysis = {
            'status': '正常',
            'warnings': [],
            'recommendations': []
        }

        try:
            # 分析内存使用率
            if 'memory_usage' in memory_info and isinstance(memory_info['memory_usage'], dict):
                usage_percent = memory_info['memory_usage'].get('usage_percent')
                if isinstance(usage_percent, (int, float)):
                    if usage_percent > 90:
                        analysis['status'] = '严重'
                        analysis['warnings'].append(f'内存使用率过高: {usage_percent}%')
                    elif usage_percent > 80:
                        analysis['status'] = '警告'
                        analysis['warnings'].append(f'内存使用率较高: {usage_percent}%')

            # 分析占用内存较高的进程
            if 'top_processes' in memory_info and isinstance(memory_info['top_processes'], list):
                for process in memory_info['top_processes'][:3]:
                    if isinstance(process, dict) and 'memory_percent' in process:
                        try:
                            mem_pct = float(process['memory_percent'])
                            if mem_pct > 20:
                                analysis['warnings'].append(
                                    f"进程 {process.get('command', 'Unknown')} 占用内存过高: {mem_pct}%")
                        except:
                            pass

            # 生成详细推荐建议
            analysis['recommendations'] = self.generate_memory_recommendations(memory_info)

        except Exception as e:
            analysis['error'] = f'分析失败: {str(e)}'
            logger.error(f"内存状态分析失败: {e}")

        return analysis

    def inspect_memory_details(self, ip_list=None):
        print("内存巡检服务启动")
        logger.info("内存巡检服务启动")
        logger.info(f"输入文件路径: {self.input_file}")

        if not ip_list:
            print("从system.json文件读取异常内存IP")
            ip_list = self.load_abnormal_ips()

        if not ip_list:
            print("没有需要巡检的IP地址")
            logger.warning("没有需要巡检的IP地址")
            return {}

        print(f"发现需要巡检的内存异常IP: {ip_list}")
        results = {}

        for ip in ip_list:
            print(f"开始巡检服务器: {ip}")
            logger.info(f"开始内存详细巡检服务器: {ip}")

            result = {
                'ip': ip,
                'status': '巡检失败',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'ssh_connection': {},
                'memory_usage': {},
                'hardware_info': {},
                'motherboard_info': {},
                'top_processes': [],
                'system_info': {},
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
                print(f"正在获取 {ip} 的内存信息...")

                # 获取内存使用情况
                memory_cmd = "free -h"
                output, error = self.execute_command(ssh, memory_cmd)
                if output:
                    result['memory_usage'] = self.parse_memory_usage(output)
                    result['memory_usage']['raw_output'] = output.strip()

                # 获取内存硬件信息
                dmidecode_cmd = "dmidecode -t memory"
                output, error = self.execute_command(ssh, dmidecode_cmd)
                if output:
                    result['hardware_info'] = self.parse_memory_hardware(output)

                # 获取主板信息
                motherboard_cmd = "dmidecode -t baseboard && dmidecode -t system"
                output, error = self.execute_command(ssh, motherboard_cmd)
                if output:
                    result['motherboard_info'] = self.parse_motherboard_info(output)

                # 获取占用内存最高的进程
                processes_cmd = "ps aux --sort=-%mem | head -10"
                output, error = self.execute_command(ssh, processes_cmd)
                if output:
                    result['top_processes'] = self.parse_top_processes(output)

                # 获取系统内存详细信息
                meminfo_cmd = "cat /proc/meminfo | head -10"
                output, error = self.execute_command(ssh, meminfo_cmd)
                if output:
                    result['system_info']['meminfo'] = output.strip()

                # 获取系统运行时间
                uptime_cmd = "uptime"
                output, error = self.execute_command(ssh, uptime_cmd)
                if output:
                    result['system_info']['uptime'] = output.strip()

                # 进行综合分析
                result['analysis'] = self.analyze_memory_status(result)
                result['status'] = '巡检成功'

                print(f"服务器 {ip} 内存巡检完成")
                logger.info(f"服务器 {ip} 内存巡检完成")

            except Exception as e:
                result['error'] = str(e)
                print(f"服务器 {ip} 内存巡检失败: {e}")
                logger.error(f"服务器 {ip} 内存巡检失败: {e}")
            finally:
                ssh.close()

            results[ip] = result

        print("内存巡检服务执行完毕")
        logger.info("内存巡检服务执行完毕")
        return results

    def save_to_file(self, data):
        try:
            os.makedirs(os.path.dirname(self.output_file), exist_ok=True)
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"内存巡检结果已保存到: {self.output_file}")
            logger.info(f"内存巡检结果已保存到: {self.output_file}")
            return True
        except Exception as e:
            print(f"保存结果文件失败: {e}")
            logger.error(f"保存结果文件失败: {e}")
            return False


def memory_inspection(params=None):
    try:
        print("开始执行内存巡检")
        logger.info("开始执行内存巡检")

        ip_list = params.get('ip_list') if params else None
        inspector = MemoryInspector()

        results = inspector.inspect_memory_details(ip_list)

        if not results:
            return {"success": False, "error": "未找到需要巡检的IP列表"}

        report_data = {
            'generation_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'inspected_count': len(results),
            'success_count': sum(1 for r in results.values() if r.get('status') == '巡检成功'),
            'failed_count': sum(1 for r in results.values() if r.get('status') == '巡检失败'),
            'no_permission_count': sum(
                1 for r in results.values() if r.get('ssh_connection', {}).get('status') == '无权限'),
            'results': results
        }

        if inspector.save_to_file(report_data):
            successful_count = report_data['success_count']
            no_permission_count = report_data['no_permission_count']
            print(f"内存巡检完成，共处理{len(results)}台服务器，成功{successful_count}台，无权限{no_permission_count}台")
            return {
                "success": True,
                "message": f"内存巡检完成，共处理{len(results)}台服务器",
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "output_file": inspector.output_file,
                "successful_count": successful_count,
                "failed_count": len(results) - successful_count,
                "no_permission_count": no_permission_count
            }
        else:
            return {"success": False, "error": "保存内存巡检结果失败"}

    except Exception as e:
        print(f"内存巡检服务异常: {e}")
        logger.error(f"内存巡检服务异常: {e}")
        return {"success": False, "error": f"内存巡检服务异常: {str(e)}"}


if __name__ == "__main__":
    result = memory_inspection()
    print(json.dumps(result, ensure_ascii=False, indent=2))