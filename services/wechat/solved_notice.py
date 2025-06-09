#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import requests
import time
import pymysql
from datetime import datetime

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)


def load_memory_update_data():
    memory_file = os.path.join(project_root, 'services', 'data', 'memory_update.json')
    print(f"[DEBUG] 尝试加载内存数据文件: {memory_file}")
    try:
        with open(memory_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"[DEBUG] 成功加载内存数据，记录数: {len(data) if isinstance(data, list) else 1}")
            return data
    except FileNotFoundError:
        print(f"[ERROR] 未找到 {memory_file} 文件")
        return None
    except json.JSONDecodeError as e:
        print(f"[ERROR] JSON文件格式错误: {e}")
        return None
    except Exception as e:
        print(f"[ERROR] 读取文件时发生错误: {str(e)}")
        return None


def save_memory_update_data(data):
    memory_file = os.path.join(project_root, 'services', 'data', 'memory_update.json')
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(memory_file), exist_ok=True)

        # 保存数据
        with open(memory_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"[DEBUG] 内存数据已保存到: {memory_file}")

        # 验证保存结果
        try:
            with open(memory_file, 'r', encoding='utf-8') as f:
                saved_data = json.load(f)
                print(f"[DEBUG] 保存验证成功，记录数: {len(saved_data) if isinstance(saved_data, list) else 1}")
                return True
        except Exception as e:
            print(f"[ERROR] 保存验证失败: {str(e)}")
            return False

    except Exception as e:
        print(f"[ERROR] 保存文件时发生错误: {str(e)}")
        return False


def check_memory_status(ip):
    print(f"[DEBUG] 查询IP {ip} 的内存状态...")
    connection = None
    try:
        connection = pymysql.connect(
            host='192.168.101.62',
            user='root',
            password='123456',
            database='envom',
            charset='utf8mb4',
            connect_timeout=10
        )

        cursor = connection.cursor()
        query = "SELECT memory_status FROM howso_server_performance_metrics WHERE ip = %s ORDER BY insert_time DESC LIMIT 1"
        cursor.execute(query, (ip,))
        result = cursor.fetchone()
        cursor.close()

        if result:
            status = result[0]
            print(f"[DEBUG] IP {ip} 数据库查询结果: {status}")
            return status
        else:
            print(f"[DEBUG] IP {ip} 在数据库中未找到记录")
            return None
    except Exception as e:
        print(f"[ERROR] 查询内存状态时发生异常: {str(e)}")
        return None
    finally:
        if connection:
            connection.close()


def send_wechat_work_message(corp_id, corp_secret, agent_id, to_users, content):
    """发送企业微信消息到多个用户"""
    try:
        # 将用户列表转换为微信API要求的格式
        if isinstance(to_users, list):
            to_user_str = "|".join(to_users)
        else:
            to_user_str = to_users

        print(f"[DEBUG] 准备发送企业微信消息给用户: {to_user_str}")
        print(f"[DEBUG] 消息内容长度: {len(content)} 字符")

        token_url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={corp_id}&corpsecret={corp_secret}"
        response = requests.get(token_url, timeout=10)
        token_result = response.json()

        access_token = token_result.get('access_token')
        if not access_token:
            print(f"[ERROR] 获取access_token失败: {token_result}")
            return False

        print(f"[DEBUG] 获取access_token成功")

        send_url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"

        data = {
            "touser": to_user_str,
            "msgtype": "text",
            "agentid": int(agent_id),
            "text": {
                "content": content
            },
            "safe": 0
        }

        response = requests.post(send_url, data=json.dumps(data), timeout=10)
        result = response.json()

        if result.get('errcode') == 0:
            print(f"[DEBUG] 企业微信消息发送成功")
            return True
        else:
            print(f"[ERROR] 企业微信消息发送失败: {result}")
            return False
    except Exception as e:
        print(f"[ERROR] 发送消息时发生异常: {str(e)}")
        return False


def add_chat_record(to_users, content, corp_id, agent_id):
    """为每个用户添加聊天记录"""
    try:
        current_time = datetime.now()
        timestamp_unix = int(current_time.timestamp())
        timestamp_formatted = current_time.strftime("%Y-%m-%d %H:%M:%S")

        chat_file = os.path.join(project_root, 'chat.json')
        try:
            if os.path.exists(chat_file):
                with open(chat_file, 'r', encoding='utf-8') as f:
                    chat_history = json.load(f)
            else:
                chat_history = []
        except:
            chat_history = []

        # 为每个用户创建聊天记录
        for to_user in to_users:
            msg_id = str(timestamp_unix * 1000 + int(current_time.microsecond / 1000))
            
            chat_record = {
                "to_user": to_user,
                "from_user": "system",
                "create_time": str(timestamp_unix),
                "create_time_formatted": timestamp_formatted,
                "msg_type": "text",
                "content": content,
                "msg_id": msg_id,
                "agent_id": agent_id,
                "timestamp": timestamp_formatted,
                "timestamp_unix": timestamp_unix
            }
            
            chat_history.append(chat_record)

        with open(chat_file, 'w', encoding='utf-8') as f:
            json.dump(chat_history, f, ensure_ascii=False, indent=2)

        print(f"[DEBUG] 聊天记录已保存，为 {len(to_users)} 个用户创建记录")
        return True
    except Exception as e:
        print(f"[ERROR] 添加聊天记录时发生异常: {str(e)}")
        return False


def generate_detailed_message(item):
    """生成详细的恢复通知消息"""
    try:
        mem_id = item.get('memory_id', 'Unknown')
        ip = item.get('server_ip', item.get('ip', 'Unknown'))

        # 获取内存详细信息
        current_memory = item.get('current_memory_status', {})
        pricing_info = item.get('pricing_info', {})
        recommended_upgrade = item.get('recommended_upgrade', {})

        # 基础信息
        total_capacity = current_memory.get('total_capacity_display', '未知')
        used_memory = current_memory.get('used_memory', '未知')
        usage_percentage = current_memory.get('usage_percentage', 0)

        # 升级建议信息
        suggest_price = pricing_info.get('suggest_price', '未知')
        memory_model = recommended_upgrade.get('memory_model', '未知')
        total_after_upgrade = recommended_upgrade.get('total_capacity_after_upgrade_gb', '未知')

        # 构建详细消息
        message = f"""🎉 {mem_id}(IP:{ip})内存异常已恢复正常

📊 历史异常情况：
• 总内存容量：{total_capacity}
• 已用内存：{used_memory}
• 使用率：{usage_percentage}%

💰 升级建议信息：
• 推荐内存：{memory_model}
• 升级后容量：{total_after_upgrade}GB
• 预估价格：¥{suggest_price}

✅ 当前状态：内存使用率已恢复正常范围，系统运行稳定"""

        return message

    except Exception as e:
        print(f"[ERROR] 生成详细消息时发生异常: {str(e)}")
        # 如果生成详细消息失败，返回简单消息
        mem_id = item.get('memory_id', 'Unknown')
        ip = item.get('server_ip', item.get('ip', 'Unknown'))
        return f"{mem_id}(IP:{ip})内存异常已恢复正常"


def update_solved_status(memory_data, resolved_items):
    """更新解决状态"""
    data_updated = False
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print(f"[DEBUG] 开始更新解决状态，待更新项目数: {len(resolved_items)}")

    if isinstance(memory_data, list):
        for i, item in enumerate(memory_data):
            if not isinstance(item, dict):
                continue

            mem_id = item.get('memory_id', f'MEM_{i}')

            # 检查是否是需要更新的项目
            for resolved_item in resolved_items:
                if resolved_item.get('memory_id') == mem_id:
                    print(f"[DEBUG] 更新记录 {i}: {mem_id} - solved: 0 -> 1")
                    memory_data[i]['solved'] = 1
                    memory_data[i]['solvedtime'] = current_time
                    data_updated = True
                    break

    elif isinstance(memory_data, dict):
        for key, item in memory_data.items():
            if not isinstance(item, dict):
                continue

            mem_id = item.get('memory_id', key)

            # 检查是否是需要更新的项目
            for resolved_item in resolved_items:
                if resolved_item.get('memory_id') == mem_id:
                    print(f"[DEBUG] 更新记录 {key}: {mem_id} - solved: 0 -> 1")
                    memory_data[key]['solved'] = 1
                    memory_data[key]['solvedtime'] = current_time
                    data_updated = True
                    break

    print(f"[DEBUG] 解决状态更新完成，数据是否更新: {data_updated}")
    return data_updated


def process_memory_data(memory_data):
    """处理内存数据"""
    resolved_items = []

    print(f"[DEBUG] 开始处理内存数据，数据类型: {type(memory_data)}")

    if isinstance(memory_data, list):
        print(f"[DEBUG] 处理列表格式数据，共 {len(memory_data)} 条记录")
        for i, item in enumerate(memory_data):
            if not isinstance(item, dict):
                print(f"[DEBUG] 跳过非字典项 {i}: {type(item)}")
                continue

            solved = item.get('solved', 0)
            mem_id = item.get('memory_id', item.get('mem_id', f'MEM_{i}'))
            ip = item.get('server_ip', item.get('ip', '192.168.10.152'))

            print(f"[DEBUG] 记录 {i}: memory_id={mem_id}, ip={ip}, solved={solved}")

            # 如果已经解决，跳过
            if solved == 1:
                print(f"[DEBUG] 记录 {i} 已解决(solved=1)，跳过处理")
                continue

            # 如果未解决，检查当前状态
            if solved == 0:
                print(f"[DEBUG] 记录 {i} 未解决(solved=0)，检查当前状态...")
                memory_status = check_memory_status(ip)

                print(f"[DEBUG] 记录 {i} 数据库状态查询结果: {memory_status}")

                if memory_status == '正常':
                    print(f"[DEBUG] ✓ 记录 {i} 状态已恢复正常，加入解决列表")
                    resolved_items.append(item)
                elif memory_status == '异常':
                    print(f"[DEBUG] ✗ 记录 {i} 状态仍然异常，保持solved=0")
                else:
                    print(f"[DEBUG] ? 记录 {i} 状态未知({memory_status})，保持solved=0")

    elif isinstance(memory_data, dict):
        print(f"[DEBUG] 处理字典格式数据，共 {len(memory_data)} 个键")
        for key, item in memory_data.items():
            if not isinstance(item, dict):
                print(f"[DEBUG] 跳过非字典项 {key}: {type(item)}")
                continue

            solved = item.get('solved', 0)
            mem_id = item.get('memory_id', item.get('mem_id', key))
            ip = item.get('server_ip', item.get('ip', '192.168.10.152'))

            print(f"[DEBUG] 记录 {key}: memory_id={mem_id}, ip={ip}, solved={solved}")

            # 如果已经解决，跳过
            if solved == 1:
                print(f"[DEBUG] 记录 {key} 已解决(solved=1)，跳过处理")
                continue

            # 如果未解决，检查当前状态
            if solved == 0:
                print(f"[DEBUG] 记录 {key} 未解决(solved=0)，检查当前状态...")
                memory_status = check_memory_status(ip)

                print(f"[DEBUG] 记录 {key} 数据库状态查询结果: {memory_status}")

                if memory_status == '正常':
                    print(f"[DEBUG] ✓ 记录 {key} 状态已恢复正常，加入解决列表")
                    resolved_items.append(item)
                elif memory_status == '异常':
                    print(f"[DEBUG] ✗ 记录 {key} 状态仍然异常，保持solved=0")
                else:
                    print(f"[DEBUG] ? 记录 {key} 状态未知({memory_status})，保持solved=0")
    else:
        print(f"[ERROR] 不支持的数据格式: {type(memory_data)}")

    print(f"[DEBUG] 处理完成，发现 {len(resolved_items)} 个已恢复的问题")
    return resolved_items


def memory_resolved_notification(params=None):
    try:
        print(f"[DEBUG] 开始执行内存问题解决通知服务")
        print(f"[DEBUG] 项目根路径: {project_root}")

        CORP_ID = "123321"
        CORP_SECRET = "123321"
        AGENT_ID = "123321"
        TO_USERS = ["llm-aitachi", "chi"]  # 修改为用户列表

        # 加载内存数据
        memory_data = load_memory_update_data()
        if memory_data is None:
            return {
                "success": False,
                "message": "无法加载内存数据文件",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

        # 打印当前数据状态用于调试
        print(f"[DEBUG] 当前数据状态:")
        if isinstance(memory_data, list):
            for i, item in enumerate(memory_data):
                if isinstance(item, dict):
                    solved = item.get('solved', 0)
                    mem_id = item.get('memory_id', f'MEM_{i}')
                    ip = item.get('server_ip', 'Unknown')
                    print(f"[DEBUG]   记录 {i}: {mem_id} (IP:{ip}) - solved={solved}")

        # 处理内存数据
        resolved_items = process_memory_data(memory_data)

        # 如果有已解决的项目，发送通知并更新状态
        if resolved_items:
            print(f"[DEBUG] 发现 {len(resolved_items)} 个已解决的问题，准备发送通知")

            if len(resolved_items) == 1:
                # 单个问题，生成详细消息
                message = generate_detailed_message(resolved_items[0])
            else:
                # 多个问题，生成汇总消息
                mem_summaries = []
                for item in resolved_items:
                    mem_id = item.get('memory_id', 'Unknown')
                    ip = item.get('server_ip', item.get('ip', 'Unknown'))
                    mem_summaries.append(f"{mem_id}(IP:{ip})")

                message = f"""🎉 批量内存问题恢复通知

✅ 以下内存问题已恢复正常：
{chr(10).join(['• ' + summary for summary in mem_summaries])}

📊 共计 {len(resolved_items)} 个服务器内存状态已恢复正常，系统运行稳定。"""

            print(f"[DEBUG] 准备发送的消息:\n{message}")

            # 发送企业微信消息到多个用户
            success = send_wechat_work_message(CORP_ID, CORP_SECRET, AGENT_ID, TO_USERS, message)

            if success:
                # 为每个用户添加聊天记录
                add_chat_record(TO_USERS, message, CORP_ID, AGENT_ID)

                # 更新解决状态
                print(f"[DEBUG] 更新 {len(resolved_items)} 个已解决项目的状态")
                data_updated = update_solved_status(memory_data, resolved_items)

                if data_updated:
                    print(f"[DEBUG] 解决状态已更新，保存到文件")
                    save_success = save_memory_update_data(memory_data)
                    if save_success:
                        print(f"[DEBUG] 数据保存成功")
                    else:
                        print(f"[ERROR] 数据保存失败")

                return {
                    "success": True,
                    "message": f"检测到 {len(resolved_items)} 个已解决的内存问题，通知已发送给 {len(TO_USERS)} 个用户",
                    "resolved_count": len(resolved_items),
                    "notification_content": message,
                    "data_updated": data_updated,
                    "recipients": TO_USERS,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
            else:
                return {
                    "success": False,
                    "message": "通知发送失败",
                    "resolved_count": len(resolved_items),
                    "data_updated": False,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
        else:
            print(f"[DEBUG] 没有发现已解决的内存问题")
            return {
                "success": True,
                "message": "没有需要通知的已解决内存问题",
                "resolved_count": 0,
                "data_updated": False,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

    except Exception as e:
        print(f"[ERROR] 服务执行异常: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "message": f"服务执行异常: {str(e)}",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }


if __name__ == "__main__":
    print("=" * 60)
    print("🚀 内存问题解决通知服务")
    print("=" * 60)
    result = memory_resolved_notification()
    print("=" * 60)
    print("📊 执行结果:")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("=" * 60)
