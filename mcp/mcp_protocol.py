#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import sys
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

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
        self.tools = {}
        self.register_default_tools()

    def register_default_tools(self):
        self.tools = {
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
                        "ip_list": {"type": "array", "items": {"type": "string"}, "description": "指定需要巡检的服务器IP列表"}
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
                        "ip_list": {"type": "array", "items": {"type": "string"}, "description": "指定需要巡检的服务器IP列表"}
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
                        "disk_threshold": {"type": "integer", "description": "硬盘使用率阈值", "default": 80}
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
                        "error_keywords": {"type": "array", "items": {"type": "string"}, "description": "自定义错误关键词"},
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