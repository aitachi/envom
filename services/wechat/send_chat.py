import requests
import json
import os
from datetime import datetime
from pathlib import Path

def get_project_root():
    """获取项目根目录"""
    # 从当前文件位置向上查找，直到找到项目根目录
    current_file = Path(__file__).resolve()
    # 假设当前文件在 services/wechat/ 目录下
    project_root = current_file.parent.parent.parent
    return project_root

def add_chat_record(to_user, from_user, content, corp_id, agent_id, msg_type="text"):
    """添加聊天记录到chat.json文件"""
    try:
        project_root = get_project_root()
        chat_file = project_root / 'chat.json'
        
        current_time = datetime.now()
        timestamp_unix = int(current_time.timestamp())
        timestamp_formatted = current_time.strftime("%Y-%m-%d %H:%M:%S")
        
        # 生成消息ID
        msg_id = str(timestamp_unix * 1000 + int(current_time.microsecond / 1000))
        
        chat_record = {
            "to_user": to_user,
            "from_user": from_user,
            "create_time": str(timestamp_unix),
            "create_time_formatted": timestamp_formatted,
            "msg_type": msg_type,
            "content": content,
            "msg_id": msg_id,
            "agent_id": agent_id,
            "timestamp": timestamp_formatted,
            "timestamp_unix": timestamp_unix
        }
        
        # 读取现有聊天记录
        try:
            if chat_file.exists():
                with open(chat_file, 'r', encoding='utf-8') as f:
                    chat_history = json.load(f)
            else:
                chat_history = []
        except (json.JSONDecodeError, FileNotFoundError):
            chat_history = []
        
        # 添加新记录
        chat_history.append(chat_record)
        
        # 保存到文件
        with open(chat_file, 'w', encoding='utf-8') as f:
            json.dump(chat_history, f, ensure_ascii=False, indent=2)
        
        print(f"[DEBUG] 聊天记录已保存到: {chat_file}")
        return True
    except Exception as e:
        print(f"[ERROR] 添加聊天记录时发生异常: {str(e)}")
        return False

def send_wechat_work_message(corp_id, corp_secret, agent_id, to_user, content):
    try:
        print(f"正在发送企业微信消息...")
        print(f"接收用户: {to_user}")
        print(f"消息内容: {content}")

        token_url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={corp_id}&corpsecret={corp_secret}"
        response = requests.get(token_url, timeout=10)
        token_result = response.json()

        access_token = token_result.get('access_token')

        if not access_token:
            error_msg = token_result.get('errmsg', '未知错误')
            print(f"获取access_token失败: {error_msg}")
            return False

        print(f"获取access_token成功")

        send_url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"

        data = {
            "touser": to_user,
            "msgtype": "text",
            "agentid": int(agent_id),
            "text": {
                "content": content
            },
            "safe": 0
        }

        response = requests.post(send_url, data=json.dumps(data), timeout=10)
        result = response.json()

        print(f"API响应: {result}")

        if result.get('errcode') == 0:
            print("消息发送成功")
            # 发送成功后添加聊天记录
            add_chat_record(to_user, "system", content, corp_id, agent_id)
            return True
        else:
            error_msg = result.get('errmsg', '未知错误')
            print(f"消息发送失败: {error_msg}")
            return False

    except Exception as e:
        print(f"发送消息时发生异常: {str(e)}")
        return False

def send_wechat_work_message_simple(to_user, content):
    CORP_ID = "111222"
    CORP_SECRET = "111222"
    AGENT_ID = "111222"
    return send_wechat_work_message(CORP_ID, CORP_SECRET, AGENT_ID, to_user, content)

def wechat_notification_service(params=None):
    if not params:
        return {
            "success": False,
            "message": "参数不能为空",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    to_user = params.get('to_user')
    content = params.get('content')

    if not to_user:
        return {
            "success": False,
            "message": "参数错误：to_user（接收用户）不能为空",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    if not content:
        return {
            "success": False,
            "message": "参数错误：content（消息内容）不能为空",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    corp_id = params.get('corp_id', "ww568874482f006b53")
    corp_secret = params.get('corp_secret', "zJM1d6Ljk86fiK4WUptdi4gmA7Gj0RkaHDYiFW6wM8g")
    agent_id = params.get('agent_id', "1000008")

    try:
        success = send_wechat_work_message(corp_id, corp_secret, agent_id, to_user, content)

        if success:
            return {
                "success": True,
                "message": f"企业微信消息发送成功",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "details": {
                    "to_user": to_user,
                    "content": content,
                    "corp_id": corp_id,
                    "agent_id": agent_id
                }
            }
        else:
            return {
                "success": False,
                "message": "企业微信消息发送失败",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "details": {
                    "to_user": to_user,
                    "content": content
                }
            }

    except Exception as e:
        return {
            "success": False,
            "message": f"企业微信服务异常：{str(e)}",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "error": str(e)
        }

if __name__ == "__main__":
    CORP_ID = "111222"
    CORP_SECRET = "111222"
    AGENT_ID = "111222"
    TO_USER = "llm-aitachi"
    MESSAGE_CONTENT = "1+1=2"
    send_wechat_work_message(CORP_ID, CORP_SECRET, AGENT_ID, TO_USER, MESSAGE_CONTENT)
