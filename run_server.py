#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import json
import sys
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from datetime import datetime

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

try:
    from config.config import LLM_CONFIG
    from utils.logger import setup_logger
    from utils.database import Database

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

    from services.wechat.send_chat import wechat_notification_service
    from services.wechat.solved_notice import memory_resolved_notification
    from services.wechat.apply_notice import memory_apply_notification
    from services.wechat.price_get import MemoryPriceInquiry

except ImportError as e:
    print(f"导入模块失败: {e}")
    print("请确保所有依赖模块存在")
    import traceback

    traceback.print_exc()
    sys.exit(1)

logger = setup_logger(__name__)


@dataclass
class MCPRequest:
    method: str
    params: Optional[Dict[str, Any]] = None
    id: Optional[str] = None


@dataclass
class MCPResponse:
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    id: Optional[str] = None


class MCPProtocol:
    def __init__(self):
        self.tools = self._register_tools()

    def _register_tools(self):
        return {
            "service_001_system_inspection": {
                "name": "service_001_system_inspection",
                "service_id": "001",
                "description": "【服务001】执行全系统状态巡检，查询数据库获取内存、硬盘使用率异常的服务器IP列表和环境监控数据",
                "keywords": ["系统巡检", "全系统检查", "系统状态", "数据库查询", "异常服务器", "环境监控"],
                "parameters": {
                    "type": "object",
                    "properties": {
                        "hours": {"type": "integer", "description": "查询最近N小时内的数据", "default": 6},
                        "memory_threshold": {"type": "integer", "description": "内存使用率阈值", "default": 70},
                        "disk_threshold": {"type": "integer", "description": "硬盘使用率阈值", "default": 80}
                    }
                }
            },
            "service_002_memory_inspection": {
                "name": "service_002_memory_inspection",
                "service_id": "002",
                "description": "【服务002】对指定IP服务器进行详细内存巡检，通过SSH连接获取内存使用率、硬件信息、进程占用情况",
                "keywords": ["内存巡检", "内存检查", "内存详细检查", "SSH连接", "进程分析", "内存硬件"],
                "parameters": {
                    "type": "object",
                    "properties": {
                        "ip_list": {"type": "array", "items": {"type": "string"},
                                    "description": "指定需要巡检的服务器IP列表"}
                    }
                }
            },
            "service_003_disk_inspection": {
                "name": "service_003_disk_inspection",
                "service_id": "003",
                "description": "【服务003】对指定IP服务器进行详细硬盘巡检，通过SSH连接获取硬盘使用率、硬件信息、大文件分析",
                "keywords": ["硬盘巡检", "磁盘检查", "硬盘详细检查", "存储分析", "大文件检查", "硬盘硬件"],
                "parameters": {
                    "type": "object",
                    "properties": {
                        "ip_list": {"type": "array", "items": {"type": "string"},
                                    "description": "指定需要巡检的服务器IP列表"}
                    }
                }
            },
            "service_004_hardware_summary": {
                "name": "service_004_hardware_summary",
                "service_id": "004",
                "description": "【服务004】生成硬件巡检AI智能分析报告，基于内存和硬盘巡检结果提供采购建议和优化方案",
                "keywords": ["AI分析报告", "硬件分析", "采购建议", "优化方案", "智能报告", "总结分析"],
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            },
            "service_005_full_inspection": {
                "name": "service_005_full_inspection",
                "service_id": "005",
                "description": "【服务005】执行完整巡检流程，按顺序调用系统巡检->内存巡检->硬盘巡检->AI分析报告->内存升级建议的完整自动化流程",
                "keywords": ["完整巡检", "全流程巡检", "自动化巡检", "完整检查", "一键巡检", "端到端巡检"],
                "parameters": {
                    "type": "object",
                    "properties": {
                        "hours": {"type": "integer", "description": "查询最近N小时内的数据", "default": 6},
                        "memory_threshold": {"type": "integer", "description": "内存使用率阈值", "default": 70},
                        "disk_threshold": {"type": "integer", "description": "硬盘使用率阈值", "default": 80},
                        "wait_for_approval": {"type": "boolean", "description": "是否等待审批回复", "default": False}
                    }
                }
            },
            "service_006_log_analysis": {
                "name": "service_006_log_analysis",
                "service_id": "006",
                "description": "【服务006】智能日志文件分析，支持错误检测、模式识别、AI智能分析等功能",
                "keywords": ["日志分析", "日志文件分析", "错误检测", "日志智能分析", "文件分析", "日志诊断"],
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "日志文件路径", "required": True},
                        "line_limit": {"type": "integer", "description": "读取行数限制", "default": 1000},
                        "error_keywords": {"type": "array", "items": {"type": "string"},
                                           "description": "自定义错误关键词"},
                        "context_lines": {"type": "integer", "description": "错误上下文行数", "default": 3},
                        "ai_analysis": {"type": "boolean", "description": "是否启用AI分析", "default": True}
                    }
                }
            },
            "service_007_daily_report": {
                "name": "service_007_daily_report",
                "service_id": "007",
                "description": "【服务007】生成昨日监控数据的智能分析日报，包含系统状态、异常分析、风险预测等",
                "keywords": ["日报生成", "日报分析", "昨日报告", "每日监控报告", "日常报告", "监控日报"],
                "parameters": {
                    "type": "object",
                    "properties": {
                        "debug": {"type": "boolean", "description": "是否启用调试模式", "default": False}
                    }
                }
            },
            "service_008_weekly_report": {
                "name": "service_008_weekly_report",
                "service_id": "008",
                "description": "【服务008】生成上周监控数据的智能分析周报，包含趋势分析、异常统计、运维建议等",
                "keywords": ["周报生成", "周报分析", "上周报告", "每周监控报告", "周期报告", "监控周报"],
                "parameters": {
                    "type": "object",
                    "properties": {
                        "debug": {"type": "boolean", "description": "是否启用调试模式", "default": False}
                    }
                }
            },
            "service_009_service_monitoring": {
                "name": "service_009_service_monitoring",
                "service_id": "009",
                "description": "【服务009】执行服务状态监控检查，检测各平台服务的运行状态、端口连通性、进程状态等",
                "keywords": ["服务监控", "服务状态检查", "端口检查", "进程监控", "服务健康检查", "平台监控"],
                "parameters": {
                    "type": "object",
                    "properties": {
                        "timeout": {"type": "integer", "description": "连接超时时间(秒)", "default": 2}
                    }
                }
            },
            "service_010_platform_monitoring": {
                "name": "service_010_platform_monitoring",
                "service_id": "010",
                "description": "【服务010】执行平台性能监控，获取CPU、内存、磁盘使用率等性能指标并进行异常检测",
                "keywords": ["平台监控", "性能监控", "资源监控", "CPU监控", "内存监控", "磁盘监控"],
                "parameters": {
                    "type": "object",
                    "properties": {
                        "time_range": {"type": "string", "description": "监控时间范围", "default": "1h"}
                    }
                }
            },
            "service_011_apply_purchases": {
                "name": "service_011_apply_purchases",
                "service_id": "011",
                "description": "【服务011】内存升级建议，从内存巡检结果生成详细的内存升级建议和价格预估",
                "keywords": ["内存升级", "升级建议", "内存分析", "硬件建议", "内存申请", "内存更换"],
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            },
            "service_012_wechat_notification": {
                "name": "service_012_wechat_notification",
                "service_id": "012",
                "description": "【服务012】企业微信通知服务，支持发送文本消息到指定用户或群组，用于运维报告推送和异常告警",
                "keywords": ["企业微信", "消息通知", "微信推送", "告警通知", "消息发送", "运维通知"],
                "parameters": {
                    "type": "object",
                    "properties": {
                        "to_user": {"type": "string", "description": "接收消息的用户ID，必填参数", "required": True},
                        "content": {"type": "string", "description": "消息内容，必填参数", "required": True},
                        "corp_id": {"type": "string", "description": "企业ID，可选（使用默认配置）"},
                        "corp_secret": {"type": "string", "description": "应用Secret，可选（使用默认配置）"},
                        "agent_id": {"type": "string", "description": "应用ID，可选（使用默认配置）"}
                    }
                }
            },
            "service_013_memory_apply_notice": {
                "name": "service_013_memory_apply_notice",
                "service_id": "013",
                "description": "【服务013】内存升级申请通知服务，检测需要申请的内存升级并发送采购申请通知",
                "keywords": ["内存申请", "采购申请", "升级申请", "申请通知", "QWEN3分析", "采购流程"],
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            },
            "service_014_memory_price_inquiry": {
                "name": "service_014_memory_price_inquiry",
                "service_id": "014",
                "description": "【服务014】内存价格询问服务，检测价格为空的内存升级记录并发送价格询问",
                "keywords": ["内存价格", "价格询问", "询价", "价格查询", "内存报价", "价格请求"],
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            },
            "service_015_memory_resolved_notice": {
                "name": "service_015_memory_resolved_notice",
                "service_id": "015",
                "description": "【服务015】内存问题解决通知服务，检测已恢复正常的内存问题并发送企业微信通知",
                "keywords": ["内存恢复", "问题解决", "状态通知", "自动检测", "恢复通知", "内存监控"],
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        }

    def parse_request(self, request_data: str) -> MCPRequest:
        try:
            data = json.loads(request_data)
            return MCPRequest(
                method=data.get("method"),
                params=data.get("params"),
                id=data.get("id")
            )
        except Exception as e:
            raise ValueError(f"无效的请求格式: {e}")

    def create_response(self, success: bool, data: Any = None, error: str = None, request_id: str = None) -> str:
        response = MCPResponse(success=success, data=data, error=error, id=request_id)
        return json.dumps({
            "success": response.success,
            "data": response.data,
            "error": response.error,
            "id": response.id
        }, ensure_ascii=False, indent=2)

    def list_tools(self) -> List[Dict[str, Any]]:
        return list(self.tools.values())

    def get_tool(self, name: str) -> Optional[Dict[str, Any]]:
        return self.tools.get(name)


def memory_price_inquiry_service(params=None):
    try:
        inquiry_service = MemoryPriceInquiry()
        success = inquiry_service.process_price_inquiries()

        if success:
            return {
                "success": True,
                "message": "价格询问任务执行完成",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        else:
            return {
                "success": False,
                "message": "价格询问任务执行失败",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
    except Exception as e:
        return {
            "success": False,
            "message": f"价格询问服务异常: {str(e)}",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }


class MCPServer:
    def __init__(self):
        print("🔧 正在初始化MCP运维服务协议栈...")
        self.protocol = MCPProtocol()
        self.handlers = {}
        self._initialize_handlers()
        print(f"✅ MCP运维服务集群初始化完成，已注册 {len(self.handlers)} 个专业运维服务")
        logger.info(f"📊 MCP服务器初始化完成，已注册 {len(self.handlers)} 个服务")

    def _initialize_handlers(self):
        print("🔗 正在建立运维服务处理器映射...")

        service_handlers = {
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
            "service_012_wechat_notification": wechat_notification_service,
            "service_013_memory_apply_notice": memory_apply_notification,
            "service_014_memory_price_inquiry": memory_price_inquiry_service,
            "service_015_memory_resolved_notice": memory_resolved_notification
        }

        for service_name, handler_func in service_handlers.items():
            try:
                if handler_func and callable(handler_func):
                    self.handlers[service_name] = handler_func
                    print(f"    ✅ 运维服务注册成功: {service_name}")
                    logger.info(f"🔧 成功注册服务: {service_name}")
                else:
                    raise ImportError(f"处理函数 {handler_func} 不可用")
            except Exception as e:
                print(f"    ⚠️ 服务 {service_name} 注册失败，使用占位模块")
                logger.warning(f"⚠️ 服务 {service_name} 导入失败: {e}，使用占位函数")
                self.handlers[service_name] = self._create_placeholder_handler(service_name)

    def _create_placeholder_handler(self, service_name):
        def placeholder_handler(params=None, server=None):
            return {
                "success": False,
                "message": f"【{service_name}】服务正在开发中，暂时无法使用",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "status": "placeholder",
                "params": params
            }

        return placeholder_handler

    def _is_valid_json_request(self, request_data: str) -> bool:
        try:
            request_data = request_data.strip()
            if not request_data:
                return False
            if not (request_data.startswith('{') and request_data.endswith('}')):
                return False
            json.loads(request_data)
            return True
        except:
            return False

    async def handle_request(self, request_data: str) -> str:
        try:
            if not request_data.strip():
                logger.warning("🚨 收到空请求")
                return self.protocol.create_response(False, None, "请求数据为空", None)

            if not self._is_valid_json_request(request_data):
                logger.warning(f"🚨 收到非MCP协议请求，忽略: {request_data[:100]}")
                return self.protocol.create_response(False, None, "非MCP协议请求", None)

            request = self.protocol.parse_request(request_data)
            print(f"📡 收到MCP协议请求: {request.method}")
            logger.info(f"📡 处理MCP请求: {request.method}")

            if request.method == "list_tools":
                print(f"📋 响应工具列表查询请求")
                tools = self.protocol.list_tools()
                return self.protocol.create_response(True, tools, None, request.id)

            if request.method == "call_tool":
                tool_name = request.params.get("name") if request.params else None
                tool_params = request.params.get("arguments") if request.params else {}

                print(f"🔧 准备调用运维工具: {tool_name}")

                if tool_name not in self.handlers:
                    print(f"❌ 未知的运维工具: {tool_name}")
                    return self.protocol.create_response(False, None, f"未知的工具: {tool_name}", request.id)

                handler = self.handlers[tool_name]
                print(f"🚀 开始执行运维工具: {tool_name}")
                logger.info(f"🔧 执行工具: {tool_name}")

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

                    print(f"✅ 运维工具 {tool_name} 执行完成")
                    return self.protocol.create_response(True, result, None, request.id)
                except Exception as e:
                    print(f"❌ 运维工具 {tool_name} 执行异常: {e}")
                    logger.error(f"🚨 执行工具 {tool_name} 时发生错误: {e}")
                    import traceback
                    traceback.print_exc()
                    return self.protocol.create_response(False, None, f"执行工具失败: {str(e)}", request.id)

            return self.protocol.create_response(False, None, f"未知的方法: {request.method}", request.id)

        except Exception as e:
            print(f"💥 MCP请求处理异常: {e}")
            logger.error(f"🚨 处理请求失败: {e}")
            import traceback
            traceback.print_exc()
            return self.protocol.create_response(False, None, str(e), None)

    async def start_server(self, host="localhost", port=8004):
        async def handle_client(reader, writer):
            client_address = writer.get_extra_info('peername')
            print(f"🔗 新的MCP客户端连接: {client_address}")
            logger.info(f"📡 新客户端连接: {client_address}")

            try:
                while True:
                    data = await reader.read(1024 * 1024)
                    if not data:
                        break

                    request_data = data.decode('utf-8')

                    if self._is_valid_json_request(request_data):
                        print(f"📨 收到有效MCP协议请求")
                        logger.info(f"📡 收到有效MCP请求: {request_data[:200]}...")
                        response = await self.handle_request(request_data)
                        writer.write(response.encode('utf-8'))
                        await writer.drain()
                    else:
                        print(f"⚠️ 忽略非MCP协议数据")
                        logger.warning(f"⚠️ 忽略非MCP请求: {request_data[:100]}...")
                        error_response = self.protocol.create_response(False, None, "不支持的请求格式", None)
                        writer.write(error_response.encode('utf-8'))
                        await writer.drain()

            except asyncio.CancelledError:
                print(f"🔌 MCP客户端连接被取消: {client_address}")
                logger.info(f"📡 客户端连接被取消: {client_address}")
            except ConnectionResetError:
                print(f"🔌 MCP客户端连接重置: {client_address}")
                logger.info(f"📡 客户端连接重置: {client_address}")
            except Exception as e:
                print(f"💥 MCP客户端处理异常: {e}")
                logger.error(f"🚨 客户端处理错误: {e}")
            finally:
                try:
                    print(f"👋 MCP客户端断开连接: {client_address}")
                    logger.info(f"📡 客户端断开连接: {client_address}")
                    writer.close()
                    await writer.wait_closed()
                except:
                    pass

        server = await asyncio.start_server(handle_client, host, port)
        print(f"🚀 MCP运维服务协议栈启动成功")
        logger.info(f"📊 MCP服务器启动成功，监听 {host}:{port}")

        print(f"🚀 MCP硬件巡检与监控服务器已启动")
        print(f"📡 MCP监听地址: {host}:{port}")
        print(f"📊 已注册服务数量: {len(self.protocol.tools)}")
        print("\n📋 可用服务列表:")

        hardware_services = []
        monitoring_services = []
        notification_services = []

        for tool_name, tool_info in self.protocol.tools.items():
            service_id = tool_info.get('service_id', '000')
            if service_id in ['001', '002', '003', '004', '005', '011']:
                hardware_services.append((tool_name, tool_info['description']))
            elif service_id in ['012', '013', '014', '015']:
                notification_services.append((tool_name, tool_info['description']))
            else:
                monitoring_services.append((tool_name, tool_info['description']))

        print("   🔧 硬件巡检服务 (001-005, 011):")
        for tool_name, description in hardware_services:
            print(f"      - {tool_name}: {description}")

        print("   📈 基础监控服务 (006-010):")
        for tool_name, description in monitoring_services:
            print(f"      - {tool_name}: {description}")

        print("   📱 通知推送服务 (012-015):")
        for tool_name, description in notification_services:
            print(f"      - {tool_name}: {description}")

        print("\n⏳ 等待MCP客户端连接...")

        async with server:
            await server.serve_forever()


async def main():
    try:
        print("=" * 60)
        print("🚀 MCP硬件巡检与监控服务器启动")
        print("=" * 60)
        print(f"📁 项目根目录: {project_root}")
        print(f"🔧 Python版本: {sys.version}")
        print("🔄 正在初始化服务器...")
        print()

        server = MCPServer()
        await server.start_server("0.0.0.0", 8004)

    except KeyboardInterrupt:
        print("\n🛑 检测到键盘中断信号")
        logger.info("🛑 服务器被用户中断")
        print("🛑 MCP服务器已停止")
    except Exception as e:
        print(f"❌ MCP服务器启动失败: {e}")
        logger.error(f"🚨 服务器启动失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())