#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import json
import sys
import os
from typing import Dict, Any

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.logger import setup_logger
from mcp.mcp_protocol import MCPProtocol

from services.system_inspection_service import system_inspection
from services.memory_inspection_service import memory_inspection
from services.disk_inspection_service import disk_inspection
from services.hardware_summary_service import hardware_summary
from services.full_inspection import full_inspection
from services.apply_purchases import apply_purchases

from services.base.log_analysis_service import log_file_analysis
from services.base.daily_report_service import daily_monitoring_report
from services.base.weekly_report_service import weekly_monitoring_report
from services.base.server_monitoring_service import service_monitoring_check
from services.base.platform_monitoring_service import platform_performance_monitoring

from services.wechat.solved_notice import memory_resolved_notification
from services.wechat.apply_notice import memory_apply_notification

logger = setup_logger(__name__)

class MCPServer:
    def __init__(self):
        self.protocol = MCPProtocol()
        self.handlers = {
            "service_001_system_inspection": system_inspection,
            "service_002_memory_inspection": memory_inspection,
            "service_003_disk_inspection": disk_inspection,
            "service_004_hardware_summary": hardware_summary,
            "service_005_full_inspection": full_inspection,
            "service_006_log_analysis": log_file_analysis,
            "service_007_daily_report": daily_monitoring_report,
            "service_008_weekly_report": weekly_monitoring_report,
            "service_009_service_monitoring": service_monitoring_check,
            "service_010_platform_monitoring": platform_performance_monitoring,
            "service_011_apply_purchases": apply_purchases,
            "service_013_memory_apply_notice": memory_apply_notification,
            "service_015_memory_resolved_notice": memory_resolved_notification
        }
        logger.info("MCP服务器初始化完成，已注册13个服务")

    async def handle_request(self, request_data: str) -> str:
        try:
            request = self.protocol.parse_request(request_data)
            logger.info(f"处理请求: {request.method}")

            if request.method == "list_tools":
                tools = self.protocol.list_tools()
                return self.protocol.create_response(True, tools, None, request.id)

            if request.method == "call_tool":
                tool_name = request.params.get("name") if request.params else None
                tool_params = request.params.get("arguments") if request.params else {}

                if tool_name not in self.handlers:
                    return self.protocol.create_response(False, None, f"未知的工具: {tool_name}", request.id)

                handler = self.handlers[tool_name]
                logger.info(f"执行工具: {tool_name}")

                try:
                    if tool_name == "service_005_full_inspection":
                        if asyncio.iscoroutinefunction(handler):
                            result = await handler(tool_params, self)
                        else:
                            result = handler(tool_params, self)
                    else:
                        if asyncio.iscoroutinefunction(handler):
                            result = await handler(tool_params)
                        else:
                            result = handler(tool_params)

                    return self.protocol.create_response(True, result, None, request.id)
                except Exception as e:
                    logger.error(f"执行工具 {tool_name} 时发生错误: {e}")
                    return self.protocol.create_response(False, None, f"执行工具失败: {str(e)}", request.id)

            return self.protocol.create_response(False, None, f"未知的方法: {request.method}", request.id)

        except Exception as e:
            logger.error(f"处理请求失败: {e}")
            return self.protocol.create_response(False, None, str(e), None)

    async def start_server(self, host="localhost", port=8003):
        async def handle_client(reader, writer):
            client_address = writer.get_extra_info('peername')
            logger.info(f"新客户端连接: {client_address}")

            try:
                while True:
                    data = await reader.read(1024 * 1024)
                    if not data:
                        break

                    request_data = data.decode('utf-8')
                    logger.info(f"收到请求: {request_data[:200]}...")

                    response = await self.handle_request(request_data)

                    writer.write(response.encode('utf-8'))
                    await writer.drain()

            except Exception as e:
                logger.error(f"客户端处理错误: {e}")
            finally:
                logger.info(f"客户端断开连接: {client_address}")
                writer.close()
                await writer.wait_closed()

        server = await asyncio.start_server(handle_client, host, port)
        logger.info(f"MCP服务器启动成功，监听 {host}:{port}")
        print(f"🚀 MCP服务器已启动，监听地址: {host}:{port}")
        print("📋 可用服务:")
        for tool_name, tool_info in self.protocol.tools.items():
            print(f"   - {tool_name}: {tool_info['description']}")
        print("\n等待客户端连接...")

        async with server:
            await server.serve_forever()

async def main():
    try:
        print("=" * 60)
        print("🚀 MCP硬件巡检与监控服务器启动")
        print("=" * 60)
        print(f"📁 项目根目录: {project_root}")
        print("🔄 正在初始化服务器...")
        print()

        server = MCPServer()
        await server.start_server("0.0.0.0", 8003)

    except KeyboardInterrupt:
        logger.info("服务器被用户中断")
        print("\n🛑 服务器已停止")
    except Exception as e:
        logger.error(f"服务器启动失败: {e}")
        print(f"❌ 服务器启动失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())