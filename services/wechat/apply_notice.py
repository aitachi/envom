#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import requests
import time
import pymysql
from datetime import datetime

# 修正：获取当前脚本所在目录，然后正确计算项目根路径
current_script_dir = os.path.dirname(os.path.abspath(__file__))
# 从 /home/ubuntu/env_mcp/services/wechat 回到 /home/ubuntu/env_mcp
project_root = os.path.dirname(os.path.dirname(current_script_dir))
sys.path.insert(0, project_root)


def load_memory_update_data():
    # 修正：添加正确的路径
    possible_paths = [
        os.path.join(project_root, 'services', 'data', 'memory_update.json'),  # /home/ubuntu/env_mcp/services/data/memory_update.json
        os.path.join(os.path.dirname(current_script_dir), 'data', 'memory_update.json'),  # /home/ubuntu/env_mcp/services/data/memory_update.json
        os.path.join(current_script_dir, 'data', 'memory_update.json'),  # services/wechat/data/memory_update.json
        os.path.join(current_script_dir, 'memory_update.json'),  # services/wechat/memory_update.json
        os.path.join(os.path.dirname(current_script_dir), 'memory_update.json'),  # services/memory_update.json
        os.path.join(project_root, 'memory_update.json'),  # 项目根目录/memory_update.json
        'memory_update.json'  # 当前工作目录
    ]
    
    memory_file = None
    for path in possible_paths:
        print(f"[DEBUG] 尝试路径: {path}")
        if os.path.exists(path):
            memory_file = path
            print(f"[DEBUG] 找到文件: {memory_file}")
            break
    
    if memory_file is None:
        print(f"[ERROR] 在以下路径都未找到 memory_update.json 文件:")
        for path in possible_paths:
            print(f"[ERROR]   - {path}")
        
        # 检查 data 目录内容
        data_dir = os.path.join(os.path.dirname(current_script_dir), 'data')
        print(f"[DEBUG] 检查 data 目录: {data_dir}")
        try:
            if os.path.exists(data_dir):
                print(f"[DEBUG] data 目录内容:")
                for item in os.listdir(data_dir):
                    print(f"[DEBUG]   - {item}")
            else:
                print(f"[DEBUG] data 目录不存在")
        except Exception as e:
            print(f"[DEBUG] 无法访问 data 目录: {e}")
            
        return None
    
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
    # 使用找到的文件路径，或者默认保存路径
    memory_file = os.path.join(os.path.dirname(current_script_dir), 'data', 'memory_update.json')
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


def generate_purchase_application(item):
    try:
        memory_id = item.get('memory_id', 'Unknown')
        server_ip = item.get('server_ip', 'Unknown')
        
        # 修正：从 pricing_info 中获取数据，如果为空则使用默认值
        pricing_info = item.get('pricing_info', {})
        suggest_user = pricing_info.get('suggest_user') or 'llm-aitachi'  # 默认申请人
        suggest_time = pricing_info.get('suggest_time') or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        suggest_price = pricing_info.get('suggest_price') or '待询价'
        
        # 修正：使用实际存在的字段
        upgrade_justification = item.get('upgrade_justification', '未提供升级理由')
        impact_analysis = item.get('impact_analysis', '未提供影响分析')
        
        # 从升级推荐中获取详细信息
        upgrade_recommendation = item.get('upgrade_recommendation', {})
        upgrade_model = upgrade_recommendation.get('model', '未指定')
        upgrade_specs = upgrade_recommendation.get('specifications', '未指定')
        upgrade_quantity = upgrade_recommendation.get('quantity', 0)
        upgrade_priority = upgrade_recommendation.get('priority', '中')
        
        # 从当前内存信息中获取详情
        current_memory = item.get('current_memory', {})
        current_capacity = current_memory.get('capacity', '未知')
        usage_percent = current_memory.get('usage_percent', 0)
        
        # 从主板信息中获取详情
        motherboard = item.get('motherboard', {})
        mb_model = motherboard.get('model', '未知')
        max_memory = motherboard.get('max_memory', '未知')
        
        # 从升级时间线获取信息
        upgrade_timeline = item.get('upgrade_timeline', {})
        procurement_time = upgrade_timeline.get('procurement', '未指定')
        installation_time = upgrade_timeline.get('installation', '未指定')
        
        user_display = {
            'llm-aitachi': '刘浏/llm-aitachi',
            'heiha': '王传庭/heiha',
            'chuqi': '初七/chuqi'
        }.get(suggest_user, suggest_user)

        print(f"[DEBUG] 开始为申请编号 {memory_id} 生成采购申请...")

        # 生成完整的申请内容
        application_content = f"""📋 内存升级采购申请

🔢 申请编号：{memory_id}
🖥️ 服务器IP：{server_ip}
👤 申请人：{user_display}
📅 申请时间：{suggest_time}
💰 预估价格：¥{suggest_price}

📊 当前内存状态：
• 容量：{current_capacity}
• 使用率：{usage_percent}%
• 主板型号：{mb_model}
• 最大支持：{max_memory}

📈 升级理由：
• {upgrade_justification}

🔧 升级方案：
• 推荐型号：{upgrade_model}
• 规格容量：{upgrade_specs}
• 购买数量：{upgrade_quantity}个
• 优先级：{upgrade_priority}

💡 影响分析：
• {impact_analysis}

⏱️ 预计时间：
• 采购周期：{procurement_time}
• 安装时间：{installation_time}

⏰ 申请提交时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""

        print(f"[DEBUG] 申请编号 {memory_id} 的采购申请生成完成")
        return application_content
    except Exception as e:
        print(f"[ERROR] 生成采购申请时发生异常: {str(e)}")
        return f"生成采购申请失败: {str(e)}"


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

        # 获取access_token
        token_url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={corp_id}&corpsecret={corp_secret}"
        response = requests.get(token_url, timeout=10)
        response.raise_for_status()
        token_result = response.json()

        access_token = token_result.get('access_token')
        if not access_token:
            error_msg = token_result.get('errmsg', '未知错误')
            error_code = token_result.get('errcode', '未知错误码')
            print(f"[ERROR] 获取access_token失败: 错误码{error_code}, 错误信息: {error_msg}")
            return False

        print(f"[DEBUG] 获取access_token成功")

        # 发送消息
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

        headers = {
            "Content-Type": "application/json; charset=utf-8"
        }

        response = requests.post(send_url, data=json.dumps(data), headers=headers, timeout=10)
        response.raise_for_status()
        result = response.json()

        print(f"[DEBUG] API响应: {result}")

        if result.get('errcode') == 0:
            print(f"[DEBUG] 企业微信消息发送成功")
            return True
        else:
            error_msg = result.get('errmsg', '未知错误')
            error_code = result.get('errcode', '未知错误码')
            invalid_user = result.get('invaliduser', '')
            print(f"[ERROR] 企业微信消息发送失败: 错误码{error_code}, 错误信息: {error_msg}")
            if invalid_user:
                print(f"[ERROR] 无效用户: {invalid_user}")
            return False
    except requests.exceptions.Timeout:
        print(f"[ERROR] 发送消息超时")
        return False
    except requests.exceptions.ConnectionError:
        print(f"[ERROR] 网络连接失败")
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


def update_applied_status(memory_data, need_apply_items):
    """更新申请状态"""
    data_updated = False
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print(f"[DEBUG] 开始更新申请状态，待更新项目数: {len(need_apply_items)}")

    if isinstance(memory_data, list):
        for i, item in enumerate(memory_data):
            if not isinstance(item, dict):
                continue

            mem_id = item.get('memory_id', f'MEM_{i}')

            # 检查是否是需要更新的项目
            for need_apply_item in need_apply_items:
                if need_apply_item.get('memory_id') == mem_id:
                    print(f"[DEBUG] 更新记录 {i}: {mem_id} - applied: 0 -> 1")
                    memory_data[i]['applied'] = 1
                    memory_data[i]['appliedtime'] = current_time
                    data_updated = True
                    break

    elif isinstance(memory_data, dict):
        for key, item in memory_data.items():
            if not isinstance(item, dict):
                continue

            mem_id = item.get('memory_id', key)

            # 检查是否是需要更新的项目
            for need_apply_item in need_apply_items:
                if need_apply_item.get('memory_id') == mem_id:
                    print(f"[DEBUG] 更新记录 {key}: {mem_id} - applied: 0 -> 1")
                    memory_data[key]['applied'] = 1
                    memory_data[key]['appliedtime'] = current_time
                    data_updated = True
                    break

    print(f"[DEBUG] 申请状态更新完成，数据是否更新: {data_updated}")
    return data_updated


def process_apply_data(memory_data):
    """处理申请数据"""
    need_apply_items = []

    print(f"[DEBUG] 开始处理申请数据，数据类型: {type(memory_data)}")

    if isinstance(memory_data, list):
        print(f"[DEBUG] 处理列表格式数据，共 {len(memory_data)} 条记录")
        for i, item in enumerate(memory_data):
            if not isinstance(item, dict):
                print(f"[DEBUG] 跳过非字典项 {i}: {type(item)}")
                continue

            solved = item.get('solved', 0)
            applied = item.get('applied', 0)
            mem_id = item.get('memory_id', item.get('mem_id', f'MEM_{i}'))

            print(f"[DEBUG] 记录 {i}: memory_id={mem_id}, solved={solved}, applied={applied}")

            # 检查是否已解决
            if solved == 1:
                print(f"[DEBUG] 记录 {i} 已解决(solved=1)，跳过处理")
                continue

            # 检查是否已申请
            if applied == 1:
                print(f"[DEBUG] 记录 {i} 已申请(applied=1)，跳过处理")
                continue

            # 符合申请条件：未解决且未申请
            if solved == 0 and applied == 0:
                print(f"[DEBUG] 记录 {i} 需要申请(solved=0, applied=0)，加入申请列表")
                need_apply_items.append(item)

    elif isinstance(memory_data, dict):
        print(f"[DEBUG] 处理字典格式数据，共 {len(memory_data)} 个键")
        for key, item in memory_data.items():
            if not isinstance(item, dict):
                print(f"[DEBUG] 跳过非字典项 {key}: {type(item)}")
                continue

            solved = item.get('solved', 0)
            applied = item.get('applied', 0)
            mem_id = item.get('memory_id', item.get('mem_id', key))

            print(f"[DEBUG] 记录 {key}: memory_id={mem_id}, solved={solved}, applied={applied}")

            # 检查是否已解决
            if solved == 1:
                print(f"[DEBUG] 记录 {key} 已解决(solved=1)，跳过处理")
                continue

            # 检查是否已申请
            if applied == 1:
                print(f"[DEBUG] 记录 {key} 已申请(applied=1)，跳过处理")
                continue

            # 符合申请条件：未解决且未申请
            if solved == 0 and applied == 0:
                print(f"[DEBUG] 记录 {key} 需要申请(solved=0, applied=0)，加入申请列表")
                need_apply_items.append(item)
    else:
        print(f"[ERROR] 不支持的数据格式: {type(memory_data)}")

    print(f"[DEBUG] 处理完成，发现 {len(need_apply_items)} 个需要申请的问题")
    return need_apply_items


def memory_apply_notification(params=None):
    try:
        print(f"[DEBUG] 开始执行内存升级申请通知服务")
        print(f"[DEBUG] 当前脚本目录: {current_script_dir}")
        print(f"[DEBUG] 项目根路径: {project_root}")

        CORP_ID = "ww568874482f006b53"
        CORP_SECRET = "zJM1d6Ljk86fiK4WUptdi4gmA7Gj0RkaHDYiFW6wM8g"
        AGENT_ID = "1000008"
        TO_USERS = ["llm-aitachi", "chuqi"]  # 修改为用户列表

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
                    applied = item.get('applied', 0)
                    mem_id = item.get('memory_id', f'MEM_{i}')
                    server_ip = item.get('server_ip', 'Unknown')
                    print(f"[DEBUG]   记录 {i}: {mem_id} - server_ip={server_ip}, solved={solved}, applied={applied}")

        # 处理申请数据
        need_apply_items = process_apply_data(memory_data)

        # 如果有需要申请的项目，发送通知
        if need_apply_items:
            print(f"[DEBUG] 发现 {len(need_apply_items)} 个需要申请的问题，准备发送通知")

            success_count = 0
            fail_count = 0
            successfully_sent_items = []

            for i, item in enumerate(need_apply_items):
                print(f"[DEBUG] 处理第 {i + 1}/{len(need_apply_items)} 个申请项目")

                # 生成申请内容
                application_content = generate_purchase_application(item)

                # 发送企业微信消息到多个用户
                success = send_wechat_work_message(CORP_ID, CORP_SECRET, AGENT_ID, TO_USERS, application_content)

                if success:
                    success_count += 1
                    successfully_sent_items.append(item)
                    # 为每个用户添加聊天记录
                    add_chat_record(TO_USERS, application_content, CORP_ID, AGENT_ID)
                    print(f"[DEBUG] 第 {i + 1} 个申请发送成功，已发送给 {len(TO_USERS)} 个用户")
                else:
                    fail_count += 1
                    print(f"[ERROR] 第 {i + 1} 个申请发送失败")

                # 添加延迟避免频率限制
                if i < len(need_apply_items) - 1:
                    print(f"[DEBUG] 等待 3 秒后处理下一个申请项目...")
                    time.sleep(3)

            # 更新成功发送的项目的申请状态
            if successfully_sent_items:
                print(f"[DEBUG] 更新 {len(successfully_sent_items)} 个成功发送项目的申请状态")
                data_updated = update_applied_status(memory_data, successfully_sent_items)

                if data_updated:
                    print(f"[DEBUG] 申请状态已更新，保存到文件")
                    save_success = save_memory_update_data(memory_data)
                    if save_success:
                        print(f"[DEBUG] 数据保存成功")
                    else:
                        print(f"[ERROR] 数据保存失败")

            message = f"发现 {len(need_apply_items)} 个需要申请的内存升级，成功发送 {success_count} 个，失败 {fail_count} 个"
            return {
                "success": success_count > 0,
                "message": message,
                "apply_count": len(need_apply_items),
                "success_count": success_count,
                "fail_count": fail_count,
                "data_updated": len(successfully_sent_items) > 0,
                "recipients": TO_USERS,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        else:
            print(f"[DEBUG] 没有发现需要申请的内存问题")
            return {
                "success": True,
                "message": "没有需要申请的内存升级",
                "apply_count": 0,
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
    print("🚀 内存升级申请通知服务")
    print("=" * 60)
    result = memory_apply_notification()
    print("=" * 60)
    print("📊 执行结果:")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("=" * 60)
