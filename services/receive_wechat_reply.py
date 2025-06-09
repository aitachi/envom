#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import time
from datetime import datetime
from aiohttp import web
import aiohttp
import asyncio
import threading

project_root = os.path.dirname(os.path.abspath(__file__))
CHAT_JSON_PATH = os.path.join(project_root, "chat.json")

def ensure_chat_file_exists():
    try:
        if not os.path.exists(CHAT_JSON_PATH):
            os.makedirs(os.path.dirname(CHAT_JSON_PATH), exist_ok=True)
            with open(CHAT_JSON_PATH, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=2)
            print(f"已创建聊天记录文件: {CHAT_JSON_PATH}")
        return True
    except Exception as e:
        print(f"创建聊天记录文件失败: {str(e)}")
        return False

def save_chat_message(from_user, content, message_type="text"):
    try:
        ensure_chat_file_exists()
        
        chat_data = []
        if os.path.exists(CHAT_JSON_PATH):
            with open(CHAT_JSON_PATH, 'r', encoding='utf-8') as f:
                content_file = f.read().strip()
                if content_file:
                    chat_data = json.loads(content_file)

        new_message = {
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "from_user": from_user,
            "content": content,
            "message_type": message_type,
            "raw_data": {
                "from_user": from_user,
                "content": content,
                "message_type": message_type
            }
        }

        chat_data.append(new_message)

        with open(CHAT_JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(chat_data, f, ensure_ascii=False, indent=2)

        print(f"保存聊天消息: {from_user} - {content}")
        return True

    except Exception as e:
        print(f"保存聊天消息失败: {str(e)}")
        return False

async def handle_webhook(request):
    try:
        data = await request.json()
        
        from_user = data.get('FromUserName', '')
        content = data.get('Content', '')
        msg_type = data.get('MsgType', 'text')
        
        print(f"收到企业微信消息: {from_user} - {content}")
        
        save_chat_message(from_user, content, msg_type)
        
        return web.json_response({"status": "success"})
    except Exception as e:
        print(f"处理企业微信消息失败: {e}")
        return web.json_response({"status": "error", "message": str(e)})

async def start_webhook_server():
    app = web.Application()
    app.router.add_post('/webhook', handle_webhook)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8004)
    await site.start()
    print("企业微信接收服务启动，监听端口 8004")
    
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("停止企业微信接收服务")

def simulate_admin_reply(reply_content):
    from_user = "llm-aitachi"
    save_chat_message(from_user, reply_content, "text")
    print(f"模拟管理员回复: {reply_content}")

if __name__ == "__main__":
    print("企业微信接收服务启动中...")
    
    if len(os.sys.argv) > 1 and os.sys.argv[1] == "simulate":
        reply = os.sys.argv[2] if len(os.sys.argv) > 2 else "同意"
        simulate_admin_reply(reply)
    else:
        try:
            asyncio.run(start_webhook_server())
        except Exception as e:
            print(f"启动失败: {e}")
