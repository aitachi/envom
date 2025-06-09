#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import json
import os
import sys
import subprocess
import time
import logging
import glob
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import threading
import queue
import signal

import io

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

try:
    from utils.logger import setup_logger
    from chat_agent import ChatAgent
except ImportError as e:
    print(f"导入模块失败: {e}")

app = FastAPI(title="智能运维监控系统")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatLogHandler(logging.Handler):
    def __init__(self, state):
        super().__init__()
        self.state = state

    def emit(self, record):
        try:
            log_message = self.format(record)
            self.state.add_chat_log('log', f"[{record.name}] {log_message}")
            if self.state.websocket_connections:
                asyncio.create_task(self.state.broadcast_message('chat_message', {
                    'type': 'log',
                    'content': f"[{record.name}] {log_message}",
                    'timestamp': datetime.now().strftime("%H:%M:%S")
                }))
        except Exception:
            pass


class SystemState:
    def __init__(self):
        self.services = {
            'mcp': {'running': False, 'process': None, 'port': 8000},
            'scheduler': {'running': False, 'process': None},
            'chat': {'running': False, 'agent': None}
        }
        self.websocket_connections = []
        self.log_queues = {
            'mcp': queue.Queue(),
            'scheduler': queue.Queue(),
            'chat': queue.Queue()
        }
        self.chat_agent = None
        self.chat_logs = []
        self.setup_global_logging()

    def setup_global_logging(self):
        chat_handler = ChatLogHandler(self)
        chat_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(levelname)s - %(message)s')
        chat_handler.setFormatter(formatter)
        root_logger = logging.getLogger()
        root_logger.addHandler(chat_handler)
        for logger_name in ['__main__', 'chat_agent', 'run_server', 'chat_scheduler']:
            logger = logging.getLogger(logger_name)
            logger.addHandler(chat_handler)

    async def broadcast_message(self, message_type: str, data: Any):
        if self.websocket_connections:
            message = json.dumps({
                'type': message_type,
                'data': data,
                'timestamp': datetime.now().isoformat()
            })
            active_connections = []
            for websocket in self.websocket_connections:
                try:
                    await websocket.send_text(message)
                    active_connections.append(websocket)
                except:
                    pass
            self.websocket_connections = active_connections

    def add_chat_log(self, message_type: str, content: str):
        log_entry = {
            'type': message_type,
            'content': content,
            'timestamp': datetime.now().strftime("%H:%M:%S")
        }
        self.chat_logs.append(log_entry)
        if len(self.chat_logs) > 200:
            self.chat_logs = self.chat_logs[-150:]


state = SystemState()
logger = setup_logger(__name__)

static_dir = os.path.join(project_root, "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)

SCHEDULED_TASKS = {
    '005': {'times': ['10:15', '15:15'], 'name': '完整巡检流程'},
    '007': {'times': ['10:10', '15:10'], 'name': '日报生成'},
    '008': {'times': ['monday-08:00'], 'name': '周报生成'},
    '009': {'times': ['09:55', '14:55'], 'name': '服务监控检查'},
    '010': {'times': ['09:58', '14:58'], 'name': '平台性能监控'}
}


def calculate_next_execution(time_str: str) -> datetime:
    now = datetime.now()

    if time_str.startswith('monday-'):
        time_part = time_str.split('-')[1]
        hour, minute = map(int, time_part.split(':'))
        days_ahead = 0 - now.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        next_monday = now + timedelta(days=days_ahead)
        next_time = next_monday.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if now.weekday() == 0:
            today_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if today_time > now:
                next_time = today_time
        return next_time
    else:
        hour, minute = map(int, time_str.split(':'))
        next_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if next_time <= now:
            next_time = next_time + timedelta(days=1)
        return next_time


@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    html_file = os.path.join(static_dir, "dashboard.html")

    if os.path.exists(html_file):
        try:
            with open(html_file, 'r', encoding='utf-8') as f:
                html_content = f.read()
            return HTMLResponse(content=html_content, status_code=200)
        except Exception as e:
            logger.error(f"读取HTML文件失败: {e}")
            return HTMLResponse(content=create_error_page(), status_code=500)
    else:
        logger.warning(f"前端页面文件不存在: {html_file}")
        return HTMLResponse(content=create_setup_page(), status_code=404)


def create_error_page():
    return """
    <!DOCTYPE html>
    <html>
    <head><title>错误 - 智能运维监控系统</title></head>
    <body>
        <h1>❌ 页面加载错误</h1>
        <p>无法读取dashboard.html文件，请检查文件是否存在且可读。</p>
        <button onclick="location.reload()">🔄 重新加载</button>
    </body>
    </html>
    """


def create_setup_page():
    return f"""
    <!DOCTYPE html>
    <html>
    <head><title>设置向导 - 智能运维监控系统</title></head>
    <body>
        <h1>🚀 智能运维监控系统设置向导</h1>
        <p>❌ 未找到前端页面文件: {os.path.join(static_dir, "dashboard.html")}</p>
        <p>请将dashboard.html文件复制到static目录中。</p>
        <button onclick="location.reload()">🔄 重新检查</button>
    </body>
    </html>
    """


@app.get("/api/countdown")
async def get_countdown():
    now = datetime.now()
    countdowns = {}

    for service_id, config in SCHEDULED_TASKS.items():
        min_seconds = float('inf')
        for time_str in config['times']:
            next_time = calculate_next_execution(time_str)
            seconds = int((next_time - now).total_seconds())
            if seconds < min_seconds:
                min_seconds = seconds

        countdowns[service_id] = {
            'seconds': max(0, min_seconds),
            'name': config['name']
        }

    return countdowns


@app.get("/api/chat/logs")
async def get_chat_logs():
    return {'logs': state.chat_logs}


@app.get("/api/ai-report")
async def get_ai_report():
    try:
        report_file = os.path.join(project_root, "services", "data", "hardware_summary.txt")

        if os.path.exists(report_file):
            with open(report_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()

            if content:
                mtime = os.path.getmtime(report_file)
                timestamp = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")

                return {
                    'success': True,
                    'content': content,
                    'timestamp': timestamp
                }
            else:
                return {
                    'success': True,
                    'content': None,
                    'timestamp': None
                }
        else:
            return {
                'success': True,
                'content': None,
                'timestamp': None
            }

    except Exception as e:
        logger.error(f"读取AI报告失败: {e}")
        return {
            'success': False,
            'error': str(e)
        }


@app.get("/api/file/{filename}")
async def get_file(filename: str):
    try:
        file_paths = [
            os.path.join(project_root, "services", "data", filename),
            os.path.join(project_root, "data", filename),
            os.path.join(project_root, filename)
        ]

        for file_path in file_paths:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                return PlainTextResponse(content=content)

        return PlainTextResponse(content="", status_code=200)
    except Exception as e:
        logger.error(f"读取文件 {filename} 失败: {e}")
        return PlainTextResponse(content="", status_code=200)


@app.get("/api/service/logs/{filename}")
async def get_service_logs(filename: str, since: int = 0):
    try:
        return {'logs': []}
    except Exception as e:
        logger.error(f"获取服务日志失败: {e}")
        return {'logs': []}


@app.post("/api/chat")
async def chat_endpoint(request: dict):
    try:
        user_input = request.get('message', '')
        if not user_input:
            return {'success': False, 'error': '消息不能为空'}

        logger.info(f"收到用户输入: {user_input}")

        state.add_chat_log('user', user_input)

        await state.broadcast_message('chat_message', {
            'type': 'user',
            'content': user_input,
            'timestamp': datetime.now().strftime("%H:%M:%S")
        })

        if not state.chat_agent:
            logger.info("初始化Chat代理")
            state.chat_agent = ChatAgent()

        logger.info("开始处理用户请求")
        response = await state.chat_agent.process_user_input(user_input)
        logger.info("用户请求处理完成")

        state.add_chat_log('assistant', response)

        await state.broadcast_message('chat_message', {
            'type': 'assistant',
            'content': response,
            'timestamp': datetime.now().strftime("%H:%M:%S")
        })

        return {
            'success': True,
            'response': response
        }

    except Exception as e:
        error_msg = f"Chat处理失败: {str(e)}"
        logger.error(error_msg)

        state.add_chat_log('error', error_msg)

        await state.broadcast_message('chat_message', {
            'type': 'error',
            'content': error_msg,
            'timestamp': datetime.now().strftime("%H:%M:%S")
        })

        return {'success': False, 'error': str(e)}


@app.post("/api/service/{service_name}/toggle")
async def toggle_service(service_name: str):
    try:
        if service_name not in state.services:
            return {'success': False, 'error': f'未知服务: {service_name}'}

        service = state.services[service_name]

        if service['running']:
            logger.info(f"正在停止服务: {service_name}")
            await stop_service(service_name)
            return {'success': True, 'status': 'stopped'}
        else:
            logger.info(f"正在启动服务: {service_name}")
            await start_service(service_name)
            return {'success': True, 'status': 'started'}

    except Exception as e:
        logger.error(f"服务切换失败: {e}")
        return {'success': False, 'error': str(e)}


@app.get("/api/service/status")
async def get_service_status():
    return {
        service_name: {'running': service['running']}
        for service_name, service in state.services.items()
    }


async def start_service(service_name: str):
    service = state.services[service_name]

    if service['running']:
        return

    try:
        if service_name == 'mcp':
            logger.info("启动MCP服务器进程")
            process = subprocess.Popen([
                sys.executable, 'run_server.py'
            ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                universal_newlines=True, cwd=project_root)

            service['process'] = process
            service['running'] = True

            threading.Thread(target=monitor_process_output,
                             args=(process, 'mcp'), daemon=True).start()

        elif service_name == 'scheduler':
            logger.info("启动调度器进程")
            process = subprocess.Popen([
                sys.executable, 'chat_scheduler.py'
            ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                universal_newlines=True, cwd=project_root)

            service['process'] = process
            service['running'] = True

            threading.Thread(target=monitor_process_output,
                             args=(process, 'scheduler'), daemon=True).start()

        elif service_name == 'chat':
            logger.info("初始化Chat代理服务")
            state.chat_agent = ChatAgent()
            service['running'] = True

        logger.info(f"服务 {service_name} 启动成功")
        await state.broadcast_message('service_status', {
            'service': service_name,
            'status': 'started'
        })

    except Exception as e:
        logger.error(f"启动服务 {service_name} 失败: {e}")
        service['running'] = False
        raise


async def stop_service(service_name: str):
    service = state.services[service_name]

    if not service['running']:
        return

    try:
        if service_name in ['mcp', 'scheduler'] and service['process']:
            logger.info(f"终止进程: {service_name}")
            service['process'].terminate()
            try:
                service['process'].wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning(f"强制杀死进程: {service_name}")
                service['process'].kill()
            service['process'] = None
        elif service_name == 'chat':
            logger.info("停止Chat代理服务")
            state.chat_agent = None

        service['running'] = False
        logger.info(f"服务 {service_name} 停止成功")

        await state.broadcast_message('service_status', {
            'service': service_name,
            'status': 'stopped'
        })

    except Exception as e:
        logger.error(f"停止服务 {service_name} 失败: {e}")
        raise


def monitor_process_output(process, service_name):
    try:
        logger.info(f"开始监控进程输出: {service_name}")
        for line in iter(process.stdout.readline, ''):
            if line:
                state.log_queues[service_name].put(line.strip())
                state.add_chat_log('log', f"[{service_name}] {line.strip()}")

    except Exception as e:
        logger.error(f"监控 {service_name} 输出失败: {e}")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    state.websocket_connections.append(websocket)
    logger.info("新的WebSocket连接已建立")

    try:
        async def send_logs():
            while True:
                try:
                    for service_name, log_queue in state.log_queues.items():
                        try:
                            while not log_queue.empty():
                                log_message = log_queue.get_nowait()
                                await websocket.send_text(json.dumps({
                                    'type': 'log',
                                    'service': service_name,
                                    'message': log_message,
                                    'timestamp': datetime.now().isoformat()
                                }))
                        except queue.Empty:
                            pass

                    await asyncio.sleep(0.1)
                except WebSocketDisconnect:
                    break
                except Exception as e:
                    logger.error(f"发送日志失败: {e}")
                    break

        log_task = asyncio.create_task(send_logs())

        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)

                if message.get('type') == 'ping':
                    await websocket.send_text(json.dumps({'type': 'pong'}))

            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"WebSocket消息处理错误: {e}")
                break

    except WebSocketDisconnect:
        pass
    finally:
        if websocket in state.websocket_connections:
            state.websocket_connections.remove(websocket)
        logger.info("WebSocket连接已断开")


def cleanup():
    logger.info("开始清理所有服务")
    for service_name, service in state.services.items():
        if service['running'] and service.get('process'):
            try:
                service['process'].terminate()
                service['process'].wait(timeout=5)
                logger.info(f"服务 {service_name} 已清理")
            except:
                pass


def signal_handler(signum, frame):
    logger.info("收到停止信号，正在清理资源")
    cleanup()
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

if __name__ == "__main__":
    print("[启动] 智能运维监控系统Web服务器")
    print("=" * 50)
    print(f"[目录] 项目根目录: {project_root}")
    print(f"[静态] 静态文件目录: {static_dir}")
    print(f"[访问] 主页地址: http://localhost:8080")
    print(f"[MCP] MCP服务器端口: localhost:8000")
    print("[提示] 按 Ctrl+C 停止服务器")
    print("=" * 50)

    dashboard_file = os.path.join(static_dir, "dashboard.html")
    if os.path.exists(dashboard_file):
        print(f"[文件] 前端页面文件已找到: {dashboard_file}")
        logger.info(f"前端页面文件已找到: {dashboard_file}")
    else:
        print(f"[错误] 前端页面文件缺失: {dashboard_file}")
        logger.error(f"前端页面文件缺失: {dashboard_file}")

    try:
        logger.info("启动Web服务器")
        uvicorn.run(app, host="127.0.0.1", port=8080, log_level="info")
    except KeyboardInterrupt:
        print("\n[停止] 服务器已停止")
        logger.info("服务器已停止")
    finally:
        cleanup()