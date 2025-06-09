#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

current_file = Path(__file__).resolve()
project_root = current_file.parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from services.wechat.send_chat import wechat_notification_service
except ImportError:
    try:
        sys.path.append(str(project_root))
        from services.wechat.send_chat import wechat_notification_service
    except ImportError:
        print("错误: 无法导入 send_chat 模块，请检查文件路径")
        sys.exit(1)


class MemoryPriceInquiry:
    def __init__(self):
        self.memory_data_path = project_root / "services" / "data" / "memory_update.json"
        self.target_users = ['heiha', 'llm-aitachi']
        self.debug = True
        self.retry_count = 3
        self.retry_delay = 2

    def debug_print(self, message):
        if self.debug:
            print(f"[DEBUG] {message}")

    def load_memory_data(self):
        try:
            if not self.memory_data_path.exists():
                print(f"错误: 内存数据文件不存在 - {self.memory_data_path}")
                return None

            with open(self.memory_data_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
                print(f"成功加载内存数据文件: {self.memory_data_path}")

                if data and len(data) > 0:
                    self.debug_print(f"数据记录数量: {len(data)}")
                    self.debug_print(f"第一条记录的主要字段: {list(data[0].keys())}")

                return data
        except Exception as e:
            print(f"加载内存数据文件失败: {str(e)}")
            return None

    def save_memory_data(self, data):
        try:
            with open(self.memory_data_path, 'w', encoding='utf-8') as file:
                json.dump(data, file, ensure_ascii=False, indent=2)
                print(f"成功保存内存数据文件: {self.memory_data_path}")
                return True
        except Exception as e:
            print(f"保存内存数据文件失败: {str(e)}")
            return False

    def calculate_available_memory(self, capacity, usage_percent):
        try:
            if not capacity or usage_percent is None:
                return 'Unknown'

            if 'GiB' in capacity:
                total_gb = float(capacity.replace('GiB', ''))
                used_gb = total_gb * (usage_percent / 100)
                available_gb = total_gb - used_gb
                return f"{available_gb:.1f}GiB"
            elif 'GB' in capacity:
                total_gb = float(capacity.replace('GB', ''))
                used_gb = total_gb * (usage_percent / 100)
                available_gb = total_gb - used_gb
                return f"{available_gb:.1f}GB"
            else:
                return 'Unknown'
        except Exception as e:
            self.debug_print(f"计算可用内存失败: {str(e)}")
            return 'Unknown'

    def determine_memory_status(self, usage_percent):
        try:
            if usage_percent >= 90:
                return "严重"
            elif usage_percent >= 80:
                return "警告"
            elif usage_percent >= 70:
                return "注意"
            elif usage_percent >= 50:
                return "正常"
            else:
                return "良好"
        except:
            return "Unknown"

    def extract_memory_type_and_frequency(self, upgrade_model):
        """从upgrade_recommendation.model中提取内存类型和频率"""
        memory_type = 'Unknown'
        frequency = 'Unknown'

        if not upgrade_model or upgrade_model == 'Unknown':
            return memory_type, frequency

        # 提取内存类型
        if 'DDR5' in upgrade_model:
            memory_type = 'DDR5'
        elif 'DDR4' in upgrade_model:
            memory_type = 'DDR4'
        elif 'DDR3' in upgrade_model:
            memory_type = 'DDR3'

        # 提取频率信息
        import re
        freq_match = re.search(r'(\d{4})', upgrade_model)
        if freq_match:
            frequency = f"{freq_match.group(1)} MHz"

        return memory_type, frequency

    def extract_memory_info(self, record):
        record_id = record.get('record_id', 'Unknown')
        memory_id = record.get('memory_id', record_id)  # 兼容性处理
        server_ip = record.get('server_ip', 'Unknown')
        inspection_date = record.get('inspection_date', 'Unknown')

        # 调试：打印整个记录结构
        self.debug_print(f"原始记录数据: {json.dumps(record, indent=2, ensure_ascii=False)}")

        # 从 current_memory 获取信息
        current_memory = record.get('current_memory', {})
        capacity = current_memory.get('capacity', 'Unknown')
        usage_percent = current_memory.get('usage_percent', 0)
        modules = current_memory.get('modules', [])
        slots = current_memory.get('slots', {})

        # 从 motherboard 获取信息
        motherboard = record.get('motherboard', {})
        motherboard_manufacturer = motherboard.get('manufacturer', 'Unknown')
        motherboard_model = motherboard.get('model', 'Unknown')
        max_memory = motherboard.get('max_memory', 'Unknown')
        motherboard_slots = motherboard.get('slots', 0)

        # 从 upgrade_recommendation 获取信息 - 增加调试
        upgrade_recommendation = record.get('upgrade_recommendation', {})
        self.debug_print(f"upgrade_recommendation 原始数据: {upgrade_recommendation}")
        self.debug_print(f"upgrade_recommendation 类型: {type(upgrade_recommendation)}")

        if isinstance(upgrade_recommendation, dict):
            upgrade_model = upgrade_recommendation.get('model', 'Unknown')  # DDR4-3200
            upgrade_specs = upgrade_recommendation.get('specifications', 'Unknown')  # 16GB
            upgrade_quantity = upgrade_recommendation.get('quantity', 0)  # 2
            upgrade_priority = upgrade_recommendation.get('priority', 'Unknown')  # 高

            self.debug_print(f"提取的upgrade_recommendation字段:")
            self.debug_print(f"  model: {upgrade_model}")
            self.debug_print(f"  specifications: {upgrade_specs}")
            self.debug_print(f"  quantity: {upgrade_quantity}")
            self.debug_print(f"  priority: {upgrade_priority}")
        else:
            self.debug_print(f"upgrade_recommendation 不是字典类型，而是: {type(upgrade_recommendation)}")
            upgrade_model = 'Unknown'
            upgrade_specs = 'Unknown'
            upgrade_quantity = 0
            upgrade_priority = 'Unknown'

        # 从 system_performance 获取信息
        system_performance = record.get('system_performance', {})
        high_memory_processes = system_performance.get('high_memory_processes', [])
        uptime = system_performance.get('uptime', 'Unknown')
        connection_status = system_performance.get('connection_status', 'Unknown')

        # 修正高内存进程中的用户信息
        if high_memory_processes and isinstance(high_memory_processes, list):
            for process in high_memory_processes:
                if isinstance(process, dict) and process.get('user') is None:
                    process['user'] = 'Unknown'

        # 从 upgrade_justification 获取信息
        upgrade_justification = record.get('upgrade_justification', '')

        # 从 impact_analysis 获取信息 - 兼容字符串和字典格式
        impact_analysis = record.get('impact_analysis', {})
        if isinstance(impact_analysis, dict):
            performance_improvement = impact_analysis.get('performance_improvement', '')
            memory_relief = impact_analysis.get('memory_relief', '')
        else:
            # 如果是字符串，直接使用
            performance_improvement = str(impact_analysis) if impact_analysis else ''
            memory_relief = ''

        # 从 upgrade_timeline 获取信息
        upgrade_timeline = record.get('upgrade_timeline', {})
        if isinstance(upgrade_timeline, dict):
            procurement_time = upgrade_timeline.get('procurement', 'Unknown')
            installation_time = upgrade_timeline.get('installation', 'Unknown')
            testing_time = upgrade_timeline.get('testing', 'Unknown')
        else:
            procurement_time = installation_time = testing_time = 'Unknown'

        # 计算可用内存
        available_memory = self.calculate_available_memory(capacity, usage_percent)

        # 确定使用状态
        usage_status = self.determine_memory_status(usage_percent)

        # 从推荐型号提取内存类型和频率
        memory_type, frequency = self.extract_memory_type_and_frequency(upgrade_model)

        # 升级后总容量使用主板最大内存容量
        total_capacity_after = max_memory

        # 确定升级方式
        total_slots = slots.get('total', motherboard_slots) if isinstance(slots, dict) else motherboard_slots
        installed_slots = slots.get('installed', len(modules)) if isinstance(slots, dict) else len(modules)
        empty_slots = slots.get('empty', total_slots - installed_slots) if isinstance(slots, dict) else (
                    total_slots - installed_slots)

        if empty_slots > 0 and upgrade_quantity <= empty_slots:
            upgrade_method = "添加内存条"
        else:
            upgrade_method = "替换现有内存条"

        # 获取系统警告
        warnings = []
        if high_memory_processes and isinstance(high_memory_processes, list):
            for process in high_memory_processes:
                if isinstance(process, dict):
                    command = process.get('command', 'Unknown')
                    memory_percent = process.get('memory_percent', 0)
                    warnings.append(f"高内存进程: {command} (占用{memory_percent}%)")

        self.debug_print(f"最终提取的内存信息:")
        self.debug_print(f"  记录ID: {record_id}")
        self.debug_print(f"  内存ID: {memory_id}")
        self.debug_print(f"  推荐型号: {upgrade_model}")
        self.debug_print(f"  内存类型: {memory_type}")
        self.debug_print(f"  频率: {frequency}")
        self.debug_print(f"  规格容量: {upgrade_specs}")
        self.debug_print(f"  优先级: {upgrade_priority}")
        self.debug_print(f"  购买数量: {upgrade_quantity}")
        self.debug_print(f"  升级后总容量: {total_capacity_after}")

        return {
            'record_id': record_id,
            'memory_id': memory_id,
            'server_ip': server_ip,
            'inspection_date': inspection_date,
            'capacity': capacity,
            'usage_percent': usage_percent,
            'available_memory': available_memory,
            'usage_status': usage_status,
            'modules': modules,
            'slots': slots,
            'motherboard_manufacturer': motherboard_manufacturer,
            'motherboard_model': motherboard_model,
            'max_memory': max_memory,
            'motherboard_slots': motherboard_slots,
            'upgrade_model': upgrade_model,  # DDR4-3200
            'memory_type': memory_type,  # DDR4
            'frequency': frequency,  # 3200 MHz
            'upgrade_specs': upgrade_specs,  # 16GB
            'upgrade_quantity': upgrade_quantity,  # 2
            'total_capacity_after': total_capacity_after,  # 32GB (来自motherboard.max_memory)
            'upgrade_priority': upgrade_priority,  # 高
            'upgrade_method': upgrade_method,
            'high_memory_processes': high_memory_processes,
            'uptime': uptime,
            'connection_status': connection_status,
            'upgrade_justification': upgrade_justification,
            'performance_improvement': performance_improvement,
            'memory_relief': memory_relief,
            'procurement_time': procurement_time,
            'installation_time': installation_time,
            'testing_time': testing_time,
            'warnings': warnings
        }

    def check_empty_price_records(self, data):
        empty_price_records = []

        if not isinstance(data, list):
            print("错误: 数据格式不正确，应为列表格式")
            return empty_price_records

        for record in data:
            pricing_request = record.get('pricing_request', 0)

            if pricing_request == 1:
                record_id = record.get('record_id', record.get('memory_id', 'Unknown ID'))
                print(f"跳过记录 {record_id}: 价格询问已发送 (pricing_request=1)")
                continue

            pricing_info = record.get('pricing_info', {})
            suggest_price = pricing_info.get('suggest_price', '') if isinstance(pricing_info, dict) else ''

            if (not suggest_price or suggest_price.strip() == "") and pricing_request == 0:
                empty_price_records.append(record)
                record_id = record.get('record_id', record.get('memory_id', 'Unknown ID'))
                print(f"发现需要询问价格的记录: {record_id} (pricing_request=0, 价格为空)")

        return empty_price_records

    def update_pricing_request_status(self, data, record_id):
        try:
            for record in data:
                if record.get('record_id') == record_id or record.get('memory_id') == record_id:
                    record['pricing_request'] = 1
                    print(f"✓ 已更新记录 {record_id} 的 pricing_request 状态为 1")
                    return True

            print(f"✗ 未找到 record_id 或 memory_id 为 {record_id} 的记录")
            return False
        except Exception as e:
            print(f"更新 pricing_request 状态失败: {str(e)}")
            return False

    def format_inquiry_message(self, record):
        info = self.extract_memory_info(record)

        self.debug_print(f"格式化消息，使用信息字段对齐:")
        self.debug_print(f"  推荐型号: {info['upgrade_model']} (来自upgrade_recommendation.model)")
        self.debug_print(f"  内存类型: {info['memory_type']} (从upgrade_recommendation.model提取)")
        self.debug_print(f"  频率: {info['frequency']} (从upgrade_recommendation.model提取)")
        self.debug_print(f"  规格容量: {info['upgrade_specs']} (来自upgrade_recommendation.specifications)")
        self.debug_print(f"  优先级: {info['upgrade_priority']} (来自upgrade_recommendation.priority)")
        self.debug_print(f"  购买数量: {info['upgrade_quantity']} (来自upgrade_recommendation.quantity)")
        self.debug_print(f"  升级后总容量: {info['total_capacity_after']} (来自motherboard.max_memory)")

        current_modules_info = ""
        if info['modules'] and isinstance(info['modules'], list):
            for i, module in enumerate(info['modules'], 1):
                if isinstance(module, dict):
                    size = module.get('size', 'Unknown')
                    mtype = module.get('type', 'Unknown')
                    speed = module.get('speed', 'Unknown')
                    manufacturer = module.get('manufacturer', 'Unknown')
                    part_number = module.get('part_number', 'Unknown')
                    current_modules_info += f"\n  模块{i}: {size} {mtype} {speed} ({manufacturer} - {part_number})"

        # 插槽信息
        slots_info = ""
        if isinstance(info['slots'], dict):
            total_slots = info['slots'].get('total', info['motherboard_slots'])
            installed_slots = info['slots'].get('installed', len(info['modules']) if info['modules'] else 0)
            empty_slots = info['slots'].get('empty', total_slots - installed_slots)
            slots_info = f"\n• 插槽状态: 总计{total_slots}个，已使用{installed_slots}个，空闲{empty_slots}个"

        # 高内存进程信息
        process_info = ""
        if info['high_memory_processes'] and isinstance(info['high_memory_processes'], list):
            process_info = "\n📊 高内存进程:"
            for process in info['high_memory_processes']:
                if isinstance(process, dict):
                    command = process.get('command', 'Unknown')
                    memory_percent = process.get('memory_percent', 0)
                    user = process.get('user', 'Unknown')
                    process_info += f"\n• {command} (用户:{user}, 占用:{memory_percent}%)"

        warnings_text = ""
        if info['warnings']:
            warnings_text = "\n⚠️ 系统警告:\n"
            for warning in info['warnings']:
                warnings_text += f"• {warning}\n"

        # 升级理由和影响分析
        justification_text = ""
        if info['upgrade_justification']:
            justification_text = f"\n🔍 升级理由:\n{info['upgrade_justification']}"

        impact_text = ""
        if info['performance_improvement'] or info['memory_relief']:
            impact_text = "\n📈 预期效果:"
            if info['performance_improvement']:
                impact_text += f"\n• 性能提升: {info['performance_improvement']}"
            if info['memory_relief']:
                impact_text += f"\n• 内存缓解: {info['memory_relief']}"

        # 升级时间线
        timeline_text = ""
        if info['procurement_time'] != 'Unknown' or info['installation_time'] != 'Unknown' or info[
            'testing_time'] != 'Unknown':
            timeline_text = "\n⏰ 升级时间线:"
            if info['procurement_time'] != 'Unknown':
                timeline_text += f"\n• 采购时间: {info['procurement_time']}"
            if info['installation_time'] != 'Unknown':
                timeline_text += f"\n• 安装时间: {info['installation_time']}"
            if info['testing_time'] != 'Unknown':
                timeline_text += f"\n• 测试时间: {info['testing_time']}"

        message = f"""内存升级价格询问

📋 基本信息:
• 记录ID: {info['record_id']}
• 内存ID: {info['memory_id']}
• 服务器IP: {info['server_ip']}
• 检查日期: {info['inspection_date']}
• 主板厂商: {info['motherboard_manufacturer']}
• 主板型号: {info['motherboard_model']}
• 主板最大支持: {info['max_memory']}
• 系统运行时间: {info['uptime']}
• 连接状态: {info['connection_status']}{slots_info}

📊 当前状态:
• 当前容量: {info['capacity']}
• 使用率: {info['usage_percent']}%
• 可用内存: {info['available_memory']}
• 状态: {info['usage_status']}
• 优先级: {info['upgrade_priority']}{current_modules_info}
{process_info}
{warnings_text}
🔧 升级方案:
• 推荐型号: {info['upgrade_model']}
• 内存类型: {info['memory_type']}
• 频率: {info['frequency']}
• 规格容量: {info['upgrade_specs']}
• 购买数量: {info['upgrade_quantity']}条
• 升级后总容量: {info['total_capacity_after']}
• 升级方式: {info['upgrade_method']}{justification_text}{impact_text}{timeline_text}

💰 请提供以上内存的采购价格信息，谢谢！

时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""

        return message

    def send_price_inquiry_with_retry(self, user, message, record_id):
        for attempt in range(self.retry_count):
            try:
                print(f"\n正在向用户 {user} 发送价格询问消息... (尝试 {attempt + 1}/{self.retry_count})")
                print(f"记录ID: {record_id}")

                params = {
                    'to_user': user,
                    'content': message
                }

                result = wechat_notification_service(params)

                if result.get('success'):
                    print(f"✓ 成功向 {user} 发送价格询问消息")
                    return result
                else:
                    print(f"✗ 向 {user} 发送消息失败: {result.get('message')}")
                    if attempt < self.retry_count - 1:
                        print(f"等待 {self.retry_delay} 秒后重试...")
                        time.sleep(self.retry_delay)

            except Exception as e:
                print(f"✗ 发送消息时发生异常: {str(e)}")
                if attempt < self.retry_count - 1:
                    print(f"等待 {self.retry_delay} 秒后重试...")
                    time.sleep(self.retry_delay)
                else:
                    print(f"✗ 向 {user} 发送消息最终失败，已重试 {self.retry_count} 次")

        return {'success': False, 'message': f'重试 {self.retry_count} 次后仍然失败'}

    def send_price_inquiry(self, record):
        message = self.format_inquiry_message(record)
        record_id = record.get('record_id', record.get('memory_id', 'Unknown'))

        results = []

        for user in self.target_users:
            if len(results) > 0:
                print(f"等待 {self.retry_delay} 秒后发送下一条消息...")
                time.sleep(self.retry_delay)

            result = self.send_price_inquiry_with_retry(user, message, record_id)
            results.append({
                'user': user,
                'record_id': record_id,
                'result': result
            })

        return results

    def process_price_inquiries(self):
        print("=" * 60)
        print("内存升级价格询问服务启动")
        print(f"检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"运行平台: {os.name} ({sys.platform})")
        print("=" * 60)

        data = self.load_memory_data()
        if not data:
            return False

        empty_price_records = self.check_empty_price_records(data)

        if not empty_price_records:
            print("✓ 所有内存升级记录都已有价格信息或已发送询问，无需发送询问消息")
            return True

        print(f"发现 {len(empty_price_records)} 条需要询问价格的记录")

        all_results = []
        updated_records = []

        for i, record in enumerate(empty_price_records, 1):
            record_id = record.get('record_id', record.get('memory_id', f'Unknown_{i}'))
            print(f"\n处理第 {i}/{len(empty_price_records)} 条记录...")

            results = self.send_price_inquiry(record)
            all_results.extend(results)

            success_results = [r for r in results if r['result'].get('success')]

            if success_results:
                if self.update_pricing_request_status(data, record_id):
                    updated_records.append(record_id)

        if updated_records:
            print(f"\n正在保存数据文件，已更新 {len(updated_records)} 条记录的状态...")
            if self.save_memory_data(data):
                print(f"✓ 成功更新以下记录的 pricing_request 状态: {', '.join(updated_records)}")
            else:
                print("✗ 保存数据文件失败，状态更新可能丢失")

        success_count = sum(1 for result in all_results if result['result'].get('success'))
        total_count = len(all_results)

        print("\n" + "=" * 60)
        print("价格询问任务完成")
        print(f"总发送: {total_count} 条消息")
        print(f"成功: {success_count} 条")
        print(f"失败: {total_count - success_count} 条")
        print(f"状态更新: {len(updated_records)} 条记录")
        print("=" * 60)

        return success_count > 0


def main():
    try:
        inquiry_service = MemoryPriceInquiry()
        success = inquiry_service.process_price_inquiries()

        if success:
            print("\n✓ 价格询问任务执行完成")
            sys.exit(0)
        else:
            print("\n✗ 价格询问任务执行失败")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\n用户中断操作")
        sys.exit(1)
    except Exception as e:
        print(f"\n程序执行异常: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()