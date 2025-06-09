#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import time
from datetime import datetime
import requests


def extract_memory_upgrade_info_from_inspection(memory_inspection_path):
    """从内存巡检JSON文件中提取内存升级建议信息"""

    with open(memory_inspection_path, 'r', encoding='utf-8') as f:
        inspection_data = json.load(f)

    # 获取巡检结果
    results = inspection_data.get("results", {})

    memory_upgrade_records = []

    for server_ip, server_data in results.items():
        if server_data.get("status") != "巡检成功":
            continue

        # 提取内存使用信息
        memory_usage = server_data.get("memory_usage", {})
        hardware_info = server_data.get("hardware_info", {})
        motherboard_info = server_data.get("motherboard_info", {})
        top_processes = server_data.get("top_processes", [])
        analysis = server_data.get("analysis", {})

        # 计算升级理由
        upgrade_reasons = []
        usage_percent = memory_usage.get("usage_percent", 0)

        if usage_percent > 70:
            upgrade_reasons.append(f"内存使用率{usage_percent}%，远超安全阈值70%")

        current_memory_gb = hardware_info.get("total_installed_memory_gb", 0)
        max_memory_str = motherboard_info.get("max_total_memory", "32GB")
        max_memory_gb = int(max_memory_str.replace("GB", "").replace(" (估算)", ""))

        if current_memory_gb < max_memory_gb:
            upgrade_reasons.append(f"主板支持最大{max_memory_gb}GB，当前仅安装{current_memory_gb}GB")

        # 检查内存条配置
        memory_modules = hardware_info.get("memory_modules", [])
        if len(memory_modules) > 1:
            sizes = [int(module.get("size", "0 GB").replace(" GB", "")) for module in memory_modules]
            if len(set(sizes)) > 1:
                upgrade_reasons.append("当前使用不同容量内存条，影响性能和扩展性")

        # 查找高内存占用进程
        high_memory_processes = []
        for process in top_processes:
            mem_percent = float(process.get("memory_percent", 0))
            if mem_percent > 10:  # 占用超过10%内存的进程
                high_memory_processes.append({
                    "command": process.get("command", ""),
                    "pid": process.get("pid", ""),
                    "user": process.get("user", ""),
                    "memory_percent": mem_percent,
                    "memory_usage_kb": int(process.get("memory_usage", 0))
                })

        # 计算推荐升级方案
        recommended_capacity = min(max_memory_gb, 32)  # 推荐升级到最大支持或32GB
        slots = hardware_info.get("total_slots", 2)
        single_capacity = recommended_capacity // slots

        # 推荐内存型号（基于现有DDR4类型）
        supported_types = motherboard_info.get("supported_memory_types", [])
        highest_speed = "DDR4-2666"
        if "DDR4-2666" in supported_types:
            highest_speed = "DDR4-2666"
        elif "DDR4-2400" in supported_types:
            highest_speed = "DDR4-2400"
        else:
            highest_speed = "DDR4-2133"

        # 确定优先级
        priority = "中等"
        if usage_percent > 90:
            priority = "紧急"
        elif usage_percent > 80:
            priority = "高"
        elif usage_percent > 70:
            priority = "中等"
        else:
            priority = "低"

        # 构建详细的JSON数据
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

        memory_upgrade_records.append(memory_upgrade_data)

    return memory_upgrade_records


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
请分析以下内存巡检数据，为每个服务器生成详细的内存升级建议JSON格式。

内存巡检数据：
{json.dumps(inspection_data, ensure_ascii=False, indent=2)}

请为每个服务器生成包含以下信息的JSON：
1. 基本信息：时间戳、服务器IP、申请和解决状态
2. 当前内存状态：容量、使用率、内存条详情、插槽信息
3. 主板信息：制造商、型号、支持的最大内存、插槽数量
4. 系统性能：高内存占用进程、系统运行时间、连接状态
5. 推荐升级方案：内存型号、规格、数量、优先级（不包含价格信息）
6. 价格信息：包含suggest_price（空）、currency（CNY）、suggest_user（空）、suggest_time（空）
7. 升级理由：具体的升级必要性分析
8. 影响分析：预期性能提升、内存压力缓解程度
9. 升级时间规划：采购、安装、测试时间

注意：价格相关字段请留空，用于后续手动填写。

请返回详细且结构化的JSON数据。
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
        "max_tokens": 3000
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()

        result = response.json()
        if "choices" in result and len(result["choices"]) > 0:
            content = result["choices"][0]["message"]["content"]

            # 尝试从回复中提取JSON
            json_start = content.find('[')
            json_end = content.rfind(']') + 1

            if json_start == -1:
                json_start = content.find('{')
                json_end = content.rfind('}') + 1

            if json_start != -1 and json_end > json_start:
                json_str = content[json_start:json_end]
                result_data = json.loads(json_str)

                # 确保价格字段为新格式
                if isinstance(result_data, list):
                    for item in result_data:
                        update_pricing_fields(item)
                else:
                    update_pricing_fields(result_data)
                    result_data = [result_data]

                return result_data

        return None

    except Exception as e:
        print(f"API调用失败: {str(e)}")
        return None


def update_pricing_fields(data):
    """更新价格字段为新格式"""
    # 设置新的价格字段格式
    data["pricing_info"] = {
        "suggest_price": "",
        "currency": "CNY",
        "suggest_user": "",
        "suggest_time": ""
    }

    # 从推荐升级方案中移除价格相关字段
    if "recommended_upgrade" in data:
        price_related_keys = ["estimated_cost_range", "cost", "price", "estimated_unit_price", "estimated_total_cost"]
        for key in price_related_keys:
            if key in data["recommended_upgrade"]:
                del data["recommended_upgrade"][key]


def generate_memory_id(server_ip, current_time, existing_data):
    """生成MEM开头的唯一编号"""
    ip_parts = server_ip.split('.')
    ip_suffix = ip_parts[-1] if len(ip_parts) == 4 else "000"

    current_date = datetime.fromtimestamp(current_time).strftime("%Y%m%d")
    same_day_count = 0
    for record in existing_data:
        record_date = record.get("inspection_date", "")
        record_ip = record.get("server_ip", "")
        if record_date == current_date and record_ip == server_ip:
            same_day_count += 1

    sequence = same_day_count + 1
    memory_id = f"MEM{ip_suffix.zfill(3)}{current_date}{sequence:03d}"

    existing_ids = [record.get("memory_id", "") for record in existing_data]
    counter = 1
    original_id = memory_id
    while memory_id in existing_ids:
        memory_id = f"{original_id}_{counter:02d}"
        counter += 1

    return memory_id


def generate_record_id(existing_data, server_ip, current_date):
    """生成记录ID：日期+编号格式"""
    same_day_count = 0
    for record in existing_data:
        if (record.get("server_ip") == server_ip and
                record.get("record_id", "").startswith(current_date)):
            same_day_count += 1

    record_number = same_day_count + 1
    record_id = f"{current_date}-{record_number:03d}"

    return record_id


def load_existing_json(json_file_path):
    """加载现有的JSON文件"""
    if os.path.exists(json_file_path):
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []
    return []


def save_json_incremental(json_file_path, new_records):
    """增量保存JSON数据"""
    existing_data = load_existing_json(json_file_path)
    current_date = datetime.now().strftime("%Y%m%d")

    for new_data in new_records:
        # 确保价格字段为新格式
        update_pricing_fields(new_data)

        server_ip = new_data.get("server_ip")
        current_time = new_data.get("time", time.time())

        # 生成唯一标识
        memory_id = generate_memory_id(server_ip, current_time, existing_data)
        new_data["memory_id"] = memory_id

        record_id = generate_record_id(existing_data, server_ip, current_date)
        new_data["record_id"] = record_id
        new_data["inspection_date"] = current_date

        # 检查是否存在相同日期和服务器IP的记录
        existing_record_index = None
        for i, record in enumerate(existing_data):
            if (record.get("server_ip") == server_ip and
                    record.get("inspection_date") == current_date):
                existing_record_index = i
                break

        if existing_record_index is not None:
            # 更新现有记录，保留状态和价格信息
            old_record = existing_data[existing_record_index]
            new_data["applied"] = old_record.get("applied", 0)
            new_data["appliedtime"] = old_record.get("appliedtime")
            new_data["solved"] = old_record.get("solved", 0)
            new_data["solvedtime"] = old_record.get("solvedtime")
            new_data["record_id"] = old_record.get("record_id")

            # 保留原有的价格信息（如果有的话）
            if "pricing_info" in old_record:
                old_pricing = old_record["pricing_info"]
                # 保留非空的价格信息
                if old_pricing.get("suggest_price") and old_pricing.get("suggest_price") != "":
                    new_data["pricing_info"]["suggest_price"] = old_pricing["suggest_price"]
                if old_pricing.get("suggest_user") and old_pricing.get("suggest_user") != "":
                    new_data["pricing_info"]["suggest_user"] = old_pricing["suggest_user"]
                if old_pricing.get("suggest_time") and old_pricing.get("suggest_time") != "":
                    new_data["pricing_info"]["suggest_time"] = old_pricing["suggest_time"]
                if old_pricing.get("currency") and old_pricing.get("currency") != "":
                    new_data["pricing_info"]["currency"] = old_pricing["currency"]

            existing_data[existing_record_index] = new_data
            print(f"更新现有记录: {new_data['record_id']} (内存编号: {new_data['memory_id']})")
        else:
            # 添加新记录
            existing_data.append(new_data)
            print(f"新增记录: {record_id} (内存编号: {memory_id})")

    # 按记录ID倒序排列
    existing_data.sort(key=lambda x: x.get("record_id", ""), reverse=True)

    # 写入JSON文件
    with open(json_file_path, 'w', encoding='utf-8') as f:
        json.dump(existing_data, f, ensure_ascii=False, indent=2)


def display_record_summary(json_file_path):
    """显示记录摘要信息"""
    existing_data = load_existing_json(json_file_path)

    if not existing_data:
        print("暂无历史记录")
        return

    print("\n=== 内存升级记录摘要 ===")
    print(f"总记录数: {len(existing_data)}")

    ip_stats = {}
    for record in existing_data:
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
                "price_suggest_user": ""
            }

        ip_stats[server_ip]["total"] += 1
        if record.get("applied", 0) == 1:
            ip_stats[server_ip]["applied"] += 1
        if record.get("solved", 0) == 1:
            ip_stats[server_ip]["solved"] += 1

        # 检查价格是否已填写
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
        print(f"  价格已填写: {'是' if stats['price_filled'] else '否'}")
        if stats['price_filled']:
            print(f"  价格建议人: {stats['price_suggest_user']}")
        print(f"  最新记录: {stats['latest_record']}")
        print(f"  最新内存编号: {stats['latest_memory_id']}")
        print(f"  升级优先级: {stats['latest_priority']}")


def update_price_suggestion(json_file_path, memory_id, suggest_price, suggest_user):
    """更新记录的价格建议"""
    existing_data = load_existing_json(json_file_path)

    updated = False
    for record in existing_data:
        if record.get("memory_id") == memory_id:
            record["pricing_info"]["suggest_price"] = suggest_price
            record["pricing_info"]["suggest_user"] = suggest_user
            record["pricing_info"]["suggest_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            updated = True
            break

    if updated:
        # 写入JSON文件
        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, ensure_ascii=False, indent=2)
        print(f"价格建议已更新: {memory_id} - {suggest_price} CNY (建议人: {suggest_user})")
        return True
    else:
        print(f"未找到内存编号: {memory_id}")
        return False


def main():
    """主函数"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    memory_inspection_path = os.path.join(script_dir, "data", "memory_inspection.json")
    memory_update_json_path = os.path.join(script_dir, "data", "memory_update.json")

    # 检查内存巡检文件是否存在
    if not os.path.exists(memory_inspection_path):
        print(f"错误：内存巡检文件不存在: {memory_inspection_path}")
        return

    try:
        # 读取内存巡检数据
        with open(memory_inspection_path, 'r', encoding='utf-8') as f:
            inspection_data = json.load(f)

        print("正在分析内存巡检数据...")
        print(f"巡检时间: {inspection_data.get('generation_time', '未知')}")
        print(f"巡检服务器数量: {inspection_data.get('inspected_count', 0)}")
        print(f"成功巡检: {inspection_data.get('success_count', 0)}")

        # 先尝试调用大模型API分析
        print("\n正在调用千问大模型分析内存升级建议...")
        api_result = call_qwen_api(inspection_data)

        if api_result is not None:
            memory_records = api_result
            print("使用大模型API分析结果")
        else:
            print("大模型API调用失败，使用本地分析方法...")
            # 回退到本地分析方法
            memory_records = extract_memory_upgrade_info_from_inspection(memory_inspection_path)

        if not memory_records:
            print("未找到需要升级的内存记录")
            return

        # 确保data目录存在
        data_dir = os.path.join(script_dir, "data")
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)

        # 增量保存到JSON文件
        save_json_incremental(memory_update_json_path, memory_records)

        print(f"\n内存升级建议已成功保存到: {memory_update_json_path}")
        print(f"生成记录数量: {len(memory_records)}")

        # 显示每个记录的基本信息
        for record in memory_records:
            pricing_status = "待填写"
            if record.get("pricing_info", {}).get("suggest_price"):
                pricing_status = f"{record['pricing_info']['suggest_price']} CNY"

            print(f"\n服务器: {record.get('server_ip', '未知')}")
            print(f"  内存编号: {record.get('memory_id', '未知')}")
            print(f"  记录ID: {record.get('record_id', '未知')}")
            print(f"  当前内存使用率: {record.get('current_memory_status', {}).get('usage_percentage', 0)}%")
            print(f"  升级优先级: {record.get('recommended_upgrade', {}).get('priority', '未知')}")
            print(f"  建议价格: {pricing_status}")

        # 显示记录摘要
        display_record_summary(memory_update_json_path)

        # 打印第一个记录的详细内容作为示例
        if memory_records:
            print(f"\n=== 示例记录详情 ===")
            print(json.dumps(memory_records[0], ensure_ascii=False, indent=2))

        # 提供价格更新功能提示
        print(f"\n=== 价格更新功能 ===")
        print("如需更新价格建议，可以调用 update_price_suggestion() 函数")
        print("例如：update_price_suggestion(json_file_path, 'MEM15220250605001', '3200', '张三')")

    except Exception as e:
        print(f"处理过程中发生错误: {str(e)}")


if __name__ == "__main__":
    main()

