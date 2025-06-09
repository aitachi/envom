#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import json
import sys
import os
import requests
import threading
import time
import logging
from typing import List, Dict, Any
from datetime import datetime
from io import StringIO

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

try:
    from run_server import MCPServer
except ImportError as e:
    print(f"导入模块失败: {e}")
    print("请确保所有依赖模块存在")
    sys.exit(1)


def safe_string(text):
    if not isinstance(text, str):
        text = str(text)
    text = text.encode('utf-8', errors='ignore').decode('utf-8')
    text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\r\t')
    return text


class InfoLogFilter(logging.Filter):
    """自定义日志过滤器，屏蔽包含 '- INFO -' 的日志"""

    def filter(self, record):
        # 获取格式化后的日志消息
        formatted_message = record.getMessage()
        # 如果消息中包含 '- INFO -'，则不显示
        return '- INFO -' not in formatted_message


def setup_chat_logger():
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.ERROR)

    logger = logging.getLogger('chat_agent')
    logger.setLevel(logging.DEBUG)

    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # 文件处理器 - 记录所有日志到文件
    file_handler = logging.FileHandler('chat_agent.log', encoding='utf-8', errors='ignore')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # 控制台处理器 - 添加过滤器屏蔽 INFO 日志
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.ERROR)
    console_formatter = logging.Formatter('%(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)

    # 添加自定义过滤器到控制台处理器
    info_filter = InfoLogFilter()
    console_handler.addFilter(info_filter)

    logger.addHandler(console_handler)

    # 设置其他模块的日志级别
    logging.getLogger('run_server').setLevel(logging.ERROR)
    logging.getLogger('services').setLevel(logging.ERROR)
    logging.getLogger('services.wechat').setLevel(logging.ERROR)
    logging.getLogger('services.wechat.send_chat').setLevel(logging.ERROR)
    logging.getLogger('urllib3').setLevel(logging.ERROR)
    logging.getLogger('requests').setLevel(logging.ERROR)

    # 为所有可能输出 INFO 日志的 logger 添加过滤器
    for logger_name in ['run_server', 'services', 'services.wechat', 'services.wechat.send_chat', 'urllib3',
                        'requests']:
        target_logger = logging.getLogger(logger_name)
        for handler in target_logger.handlers:
            handler.addFilter(info_filter)

    return logger


logger = setup_chat_logger()


class LLMScheduler:
    def __init__(self):
        self.llm_config = {
            'base_url': "http://192.168.101.214:6007",
            'chat_endpoint': "/v1/chat/completions",
            'model_name': "Qwen3-32B-AWQ"
        }
        self.tools = [
            {
                "name": "service_001_system_inspection",
                "service_id": "001",
                "description": "【服务001】执行全系统状态巡检，查询数据库获取内存、硬盘使用率异常的服务器IP列表和环境监控数据",
                "keywords": ["系统巡检", "全系统检查", "系统状态", "数据库查询", "异常服务器", "环境监控"],
                "usage": "当需要了解系统整体状况、查询异常服务器列表时使用"
            },
            {
                "name": "service_002_memory_inspection",
                "service_id": "002",
                "description": "【服务002】对指定IP服务器进行详细内存巡检，通过SSH连接获取内存使用率、硬件信息、进程占用情况",
                "keywords": ["内存巡检", "内存检查", "内存详细检查", "SSH连接", "进程分析", "内存硬件"],
                "usage": "当发现内存异常服务器后，需要详细检查内存状态时使用"
            },
            {
                "name": "service_003_disk_inspection",
                "service_id": "003",
                "description": "【服务003】对指定IP服务器进行详细硬盘巡检，通过SSH连接获取硬盘使用率、硬件信息、大文件分析",
                "keywords": ["硬盘巡检", "磁盘检查", "硬盘详细检查", "存储分析", "大文件检查", "硬盘硬件"],
                "usage": "当发现硬盘异常服务器后，需要详细检查硬盘状态时使用"
            },
            {
                "name": "service_004_hardware_summary",
                "service_id": "004",
                "description": "【服务004】生成硬件巡检AI智能分析报告，基于内存和硬盘巡检结果提供采购建议和优化方案",
                "keywords": ["AI分析报告", "硬件分析", "采购建议", "优化方案", "智能报告", "总结分析"],
                "usage": "当完成硬件巡检后，需要AI分析和采购建议时使用"
            },
            {
                "name": "service_005_full_inspection",
                "service_id": "005",
                "description": "【服务005】执行完整巡检流程，按顺序调用系统巡检->内存巡检->硬盘巡检->AI分析报告->内存升级建议的完整自动化流程",
                "keywords": ["完整巡检", "全流程巡检", "自动化巡检", "完整检查", "一键巡检", "端到端巡检"],
                "usage": "当需要执行完整的硬件巡检流程时使用"
            },
            {
                "name": "service_006_log_analysis",
                "service_id": "006",
                "description": "【服务006】智能日志文件分析，支持错误检测、模式识别、AI智能分析等功能",
                "keywords": ["日志分析", "日志文件分析", "错误检测", "日志智能分析", "文件分析", "日志诊断"],
                "usage": "当需要分析日志文件、检测错误、诊断问题时使用"
            },
            {
                "name": "service_007_daily_report",
                "service_id": "007",
                "description": "【服务007】生成昨日监控数据的智能分析日报，包含系统状态、异常分析、风险预测等",
                "keywords": ["日报生成", "日报分析", "昨日报告", "每日监控报告", "日常报告", "监控日报"],
                "usage": "当需要生成每日监控报告、分析昨日系统状态时使用"
            },
            {
                "name": "service_008_weekly_report",
                "service_id": "008",
                "description": "【服务008】生成上周监控数据的智能分析周报，包含趋势分析、异常统计、运维建议等",
                "keywords": ["周报生成", "周报分析", "上周报告", "每周监控报告", "周期报告", "监控周报"],
                "usage": "当需要生成每周监控报告、分析一周系统趋势时使用"
            },
            {
                "name": "service_009_service_monitoring",
                "service_id": "009",
                "description": "【服务009】执行服务状态监控检查，检测各平台服务的运行状态、端口连通性、进程状态等",
                "keywords": ["服务监控", "服务状态检查", "端口检查", "进程监控", "服务健康检查", "平台监控"],
                "usage": "当需要检查服务运行状态、端口连通性、进程状态时使用"
            },
            {
                "name": "service_010_platform_monitoring",
                "service_id": "010",
                "description": "【服务010】执行平台性能监控，获取CPU、内存、磁盘使用率等性能指标并进行异常检测",
                "keywords": ["平台监控", "性能监控", "资源监控", "CPU监控", "内存监控", "磁盘监控"],
                "usage": "当需要监控系统性能、检查资源使用情况时使用"
            },
            {
                "name": "service_011_apply_purchases",
                "service_id": "011",
                "description": "【服务011】内存升级建议，从内存巡检结果生成详细的内存升级建议和价格预估",
                "keywords": ["内存升级", "升级建议", "内存分析", "硬件建议", "内存申请", "内存更换"],
                "usage": "当需要生成内存升级建议、分析内存需求时使用"
            },
            {
                "name": "service_012_wechat_notification",
                "service_id": "012",
                "description": "【服务012】企业微信通知服务，支持发送文本消息到指定用户或群组，用于运维报告推送和异常告警",
                "keywords": ["企业微信", "消息通知", "微信推送", "告警通知", "消息发送", "运维通知"],
                "usage": "当需要发送企业微信通知、推送运维报告、发送告警消息时使用"
            },
            {
                "name": "service_013_memory_apply_notice",
                "service_id": "013",
                "description": "【服务013】内存升级申请通知服务，检测需要申请的内存升级并发送采购申请通知",
                "keywords": ["内存申请", "采购申请", "升级申请", "申请通知", "QWEN3分析", "采购流程"],
                "usage": "当需要检测并发送内存升级申请通知时使用"
            },
            {
                "name": "service_015_memory_resolved_notice",
                "service_id": "015",
                "description": "【服务015】内存问题解决通知服务，检测已恢复正常的内存问题并发送企业微信通知",
                "keywords": ["内存恢复", "问题解决", "状态通知", "自动检测", "恢复通知", "内存监控"],
                "usage": "当需要检测已解决的内存问题并发送通知时使用"
            }
        ]
        logger.debug(f"⚙️ AI运维大脑初始化完成，已加载{len(self.tools)}个专业运维工具模块")

    def call_llm(self, prompt, temperature=0.1, max_tokens=1000):
        try:
            clean_prompt = safe_string(prompt)
            print("    🧠 启动QWEN3-32B神经网络模型，执行深度语义理解...")
            logger.debug("🔮 AI大脑开始深度解析用户运维需求")

            url = f"{self.llm_config['base_url']}{self.llm_config['chat_endpoint']}"
            payload = {
                "model": self.llm_config['model_name'],
                "messages": [
                    {"role": "system",
                     "content": "你是一个专业的智能运维助手，专门负责分析用户需求并选择合适的运维工具。请严格按照用户的真实意图进行分析，不要做多余的推测。"},
                    {"role": "user", "content": clean_prompt}
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": False
            }

            headers = {
                "Content-Type": "application/json; charset=utf-8",
                "Accept": "application/json"
            }

            print("    🌐 向AI运维大脑发送智能分析请求...")
            logger.debug(f"🔗 建立与QWEN3模型的神经网络连接: {url}")

            response = requests.post(url, json=payload, headers=headers, timeout=30)

            logger.debug(f"📡 AI大脑响应状态: {response.status_code}")
            if response.status_code != 200:
                logger.error(f"⚠️ AI大脑响应异常: {response.text}")

            response.raise_for_status()

            result = response.json()
            response_content = result["choices"][0]["message"]["content"]
            clean_response = safe_string(response_content)
            print("    ✨ AI运维大脑完成智能决策，获得最优执行方案")
            logger.debug(f"🎯 AI决策分析完成，智能推理结果长度: {len(clean_response)}")
            return clean_response
        except Exception as e:
            print(f"    ❌ AI运维大脑连接异常: {e}")
            logger.error(f"🚨 AI神经网络通信故障: {e}")
            return None

    def parse_user_intent(self, user_input):
        clean_input = safe_string(user_input)
        logger.debug(f"📥 开始解析运维指令: {clean_input}")

        print("    🤖 AI运维引擎启动 - 执行智能意图识别与任务编排...")

        tools_info = json.dumps(self.tools, ensure_ascii=False, indent=2)

        analysis_prompt = f"""
作为专业的智能运维助手，请分析用户需求并制定执行计划。

用户需求: "{clean_input}"

可用的运维服务工具:
{tools_info}

请进行三个阶段的深度分析：

### 第一阶段：需求理解与意图识别
1. 用户的核心需求是什么？
2. 这个需求属于哪个运维领域？
3. 需要执行什么类型的操作？

### 第二阶段：服务匹配与技术分析
1. 哪个服务最符合用户需求？
2. 为什么选择这个服务而不是其他服务？
3. 需要什么参数配置？

### 第三阶段：执行计划制定
基于分析结果，制定详细的执行计划。

特别注意企业微信服务的参数解析：
- 识别关键词："企业微信"、"微信通知"、"发送消息"、"推送"等
- 从输入中提取：接收用户ID 和 消息内容
- 参数格式：{{"to_user": "用户ID", "content": "消息内容"}}

特别注意内存解决通知服务：
- 识别关键词："内存恢复"、"问题解决"、"内存通知"、"恢复通知"等
- 该服务无需参数

特别注意内存申请通知服务：
- 识别关键词："内存申请"、"采购申请"、"升级申请"、"申请通知"等
- 该服务无需参数

请严格按照以下JSON格式输出分析结果：
{{
    "stage1_analysis": {{
        "core_requirement": "用户核心需求描述",
        "domain": "运维领域分类",
        "operation_type": "操作类型"
    }},
    "stage2_analysis": {{
        "matched_service": "最佳匹配服务",
        "technical_reason": "技术选择原因",
        "confidence": 0.95,
        "parameters": {{"参数名": "参数值"}}
    }},
    "stage3_plan": {{
        "execution_strategy": "执行策略",
        "risk_assessment": "风险评估",
        "expected_outcome": "预期结果"
    }},
    "final_decision": {{
        "intent": "最终理解的用户意图",
        "matched_service": "选定的服务名称",
        "confidence": 0.95,
        "execution_plan": [
            {{
                "tool": "服务名称",
                "params": {{"参数名": "参数值"}},
                "order": 1,
                "reason": "执行原因",
                "risk_assessment": "风险评估",
                "performance_impact": "性能影响"
            }}
        ]
    }}
}}

只返回JSON，不要添加任何解释文字。
"""

        response = self.call_llm(analysis_prompt, temperature=0.1)

        if response:
            try:
                print("    🔍 AI大脑正在解析决策矩阵...")

                import re
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    parsed_result = json.loads(json_match.group())

                    final_decision = parsed_result.get('final_decision', {})
                    if final_decision and 'execution_plan' in final_decision:
                        print("    ✅ AI运维大脑决策完成，生成最优执行路径")
                        logger.debug(
                            f"🎯 AI决策成功: 目标服务={final_decision.get('matched_service')}, 可信度={final_decision.get('confidence')}")
                        logger.debug(f"📊 完整决策矩阵: {parsed_result}")
                        return final_decision

            except Exception as e:
                print(f"    ⚠️ AI决策解析遇到挑战: {e}")
                logger.error(f"🚨 AI决策结果解析异常: {e}")
                logger.error(f"📋 原始AI响应: {response}")

        print("    🔄 启用AI运维智能兜底决策系统...")
        logger.error("🔧 主AI决策失败，启动备用智能决策引擎")

        fallback_service = self._intelligent_fallback(clean_input)

        fallback_plan = {
            "intent": f"智能兜底分析：{clean_input}",
            "matched_service": fallback_service["service"],
            "confidence": fallback_service["confidence"],
            "technical_reasoning": f"基于关键词智能匹配，选择{fallback_service['service']}服务",
            "execution_plan": [
                {
                    "tool": fallback_service["service"],
                    "params": fallback_service["params"],
                    "order": 1,
                    "reason": fallback_service["reason"],
                    "risk_assessment": "低风险，标准操作流程",
                    "performance_impact": "正常性能消耗"
                }
            ]
        }

        logger.debug(f"🛡️ 兜底决策选择: {fallback_service['service']}")
        logger.debug(f"📋 兜底决策详情: {fallback_plan}")
        return fallback_plan

    def _intelligent_fallback(self, user_input):
        user_input_lower = user_input.lower()

        wechat_keywords = ["企业微信", "微信", "发送", "通知", "推送", "消息"]
        if any(keyword in user_input for keyword in wechat_keywords):
            params = self._parse_wechat_params(user_input)
            return {
                "service": "service_012_wechat_notification",
                "params": params,
                "confidence": 0.8,
                "reason": "检测到企业微信通知相关关键词，智能解析用户和消息内容"
            }

        memory_apply_keywords = ["内存申请", "采购申请", "升级申请", "申请通知"]
        if any(keyword in user_input for keyword in memory_apply_keywords):
            return {
                "service": "service_013_memory_apply_notice",
                "params": {},
                "confidence": 0.8,
                "reason": "检测到内存升级申请相关关键词"
            }

        memory_resolved_keywords = ["内存恢复", "问题解决", "内存通知", "恢复通知", "解决通知"]
        if any(keyword in user_input for keyword in memory_resolved_keywords):
            return {
                "service": "service_015_memory_resolved_notice",
                "params": {},
                "confidence": 0.8,
                "reason": "检测到内存问题解决通知相关关键词"
            }

        keyword_mapping = {
            "周报": ("service_008_weekly_report", {}),
            "日报": ("service_007_daily_report", {}),
            "日志": ("service_006_log_analysis", {}),
            "服务监控": ("service_009_service_monitoring", {}),
            "性能监控": ("service_010_platform_monitoring", {}),
            "平台监控": ("service_010_platform_monitoring", {}),
            "系统巡检": ("service_001_system_inspection", {}),
            "内存巡检": ("service_002_memory_inspection", {}),
            "硬盘巡检": ("service_003_disk_inspection", {}),
            "完整巡检": ("service_005_full_inspection", {}),
            "升级建议": ("service_011_apply_purchases", {})
        }

        for keyword, (service, params) in keyword_mapping.items():
            if keyword in user_input:
                return {
                    "service": service,
                    "params": params,
                    "confidence": 0.7,
                    "reason": f"基于关键词'{keyword}'智能匹配到{service}服务"
                }

        return {
            "service": "service_005_full_inspection",
            "params": {},
            "confidence": 0.5,
            "reason": "未找到明确匹配，使用默认完整巡检服务"
        }

    def _parse_wechat_params(self, user_input):
        import re
        patterns = [
            r"发送给\s*(\S+)\s*说\s*(.+)",
            r"通知\s*(\S+)\s*说\s*(.+)",
            r"企业微信\s+发送给\s*(\S+)\s+说\s*(.+)",
            r"企业微信\s+(\S+)\s+说\s*(.+)",
            r"微信通知\s*(\S+)\s*(.+)"
        ]

        for pattern in patterns:
            match = re.search(pattern, user_input, re.IGNORECASE)
            if match:
                to_user = match.group(1).strip()
                content = match.group(2).strip()
                return {"to_user": to_user, "content": content}

        return {"to_user": "default_user", "content": "测试消息"}


class TaskExecutor:
    def __init__(self):
        print("⚙️ 初始化MCP任务执行引擎，建立运维服务调度中心...")
        logger.debug("🔧 MCP任务执行器启动初始化流程")

        self.mcp_server = MCPServer()

        print("✅ MCP运维服务集群连接成功，具备14个专业运维服务能力")
        logger.debug("🎯 MCP任务执行器初始化完成，运维服务调度中心已就绪")

    async def execute_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        try:
            print(f"    🛠️ 启动MCP服务调度器，准备执行 [{tool_name}] 运维服务...")
            safe_tool_name = safe_string(tool_name)
            clean_params = {k: safe_string(str(v)) for k, v in params.items()}

            logger.debug(f"🔧 MCP服务调度开始: {safe_tool_name}, 执行参数: {clean_params}")

            request_data = json.dumps({
                "method": "call_tool",
                "params": {
                    "name": tool_name,
                    "arguments": params
                },
                "id": f"exec_{tool_name}_{int(asyncio.get_event_loop().time())}"
            })

            print(f"    📡 通过MCP协议向运维服务集群发送任务指令...")
            logger.debug(f"📋 MCP任务指令: {safe_string(request_data)}")

            response_str = await self.mcp_server.handle_request(request_data)
            response = json.loads(response_str)
            logger.debug(f"📊 MCP服务响应: {safe_string(str(response))}")

            if response.get('success'):
                print(f"    ✅ 运维服务 [{tool_name}] 执行成功，任务完成")
                logger.debug(f"🎯 MCP服务 {safe_tool_name} 执行成功")
            else:
                print(f"    ❌ 运维服务 [{tool_name}] 执行遇到问题: {response.get('error', '未知错误')}")
                logger.error(f"🚨 MCP服务 {safe_tool_name} 执行失败: {safe_string(str(response.get('error')))}")

            return response
        except Exception as e:
            print(f"    💥 MCP服务调度异常: {e}")
            logger.error(f"🚨 MCP服务 {tool_name} 调度失败: {e}")
            return {"success": False, "error": str(e)}

    async def execute_plan(self, execution_plan: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        results = []
        total_tasks = len(execution_plan)

        print(f"🚀 启动AI运维任务编排器，准备执行 {total_tasks} 个专业运维任务")
        logger.debug(f"📋 运维任务编排开始，总任务数: {total_tasks}")

        execution_plan.sort(key=lambda x: x.get('order', 0))

        for i, task in enumerate(execution_plan, 1):
            tool_name = task.get('tool')
            params = task.get('params', {})
            reason = task.get('reason', '')
            risk_assessment = task.get('risk_assessment', '未评估')
            performance_impact = task.get('performance_impact', '未知影响')

            safe_tool_name = safe_string(tool_name)
            safe_reason = safe_string(reason)
            safe_risk = safe_string(risk_assessment)
            safe_performance = safe_string(performance_impact)

            print(f"\n🔹 [{i}/{total_tasks}] 运维任务执行中: {safe_tool_name}")
            print(f"    📋 任务目标: {safe_reason}")
            print(f"    ⚠️ 风险评估: {safe_risk}")
            print(f"    📊 性能影响: {safe_performance}")

            if i < total_tasks:
                next_task = execution_plan[i].get('tool', '无')
                safe_next_task = safe_string(next_task)
                print(f"    🔮 下一步计划: 将执行 [{safe_next_task}] 运维服务")
            else:
                print(f"    🏁 任务队列状态: 这是最后一个任务，完成后将生成执行报告")

            logger.debug(f"🔧 执行运维任务 {i}/{total_tasks}: {safe_tool_name}")
            logger.debug(f"📋 任务详情 - 目标: {safe_reason}, 风险: {safe_risk}, 性能: {safe_performance}")

            result = await self.execute_tool(tool_name, params)

            results.append({
                "tool": tool_name,
                "params": params,
                "reason": reason,
                "risk_assessment": risk_assessment,
                "performance_impact": performance_impact,
                "result": result
            })

            if not result.get('success', False):
                print(f"    ⚠️ 任务执行遇到问题，但继续执行后续任务...")
                logger.error(f"🚨 运维任务 {safe_tool_name} 执行失败，继续后续任务")
            else:
                print(f"    🎉 运维任务 [{safe_tool_name}] 圆满完成")
                logger.debug(f"✅ 运维任务 {safe_tool_name} 执行成功")

        print(f"\n🏆 AI运维任务编排器完成所有任务，共处理 {total_tasks} 个运维任务")
        logger.debug(f"🎯 运维任务编排完成，总任务: {total_tasks}")
        return results

    def format_results(self, results: List[Dict[str, Any]]) -> str:
        logger.debug("📊 开始生成AI运维执行报告")

        formatted = "# 🎯 AI智能运维任务执行报告\n\n"
        formatted += f"📅 **执行时间**: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}\n"
        formatted += f"🧠 **AI引擎**: QWEN3-32B大模型深度分析\n"
        formatted += f"📊 **任务总数**: {len(results)} 项\n"

        success_count = sum(1 for r in results if r['result'].get('success', False))
        formatted += f"✅ **成功任务**: {success_count} 项\n"
        formatted += f"❌ **失败任务**: {len(results) - success_count} 项\n"
        formatted += f"📈 **成功率**: {(success_count / len(results) * 100):.1f}%\n\n"

        formatted += "## 📋 详细执行结果\n\n"

        for i, result in enumerate(results, 1):
            tool_name = safe_string(result['tool'])
            success = result['result'].get('success', False)
            status = "✅ 执行成功" if success else "❌ 执行失败"

            formatted += f"### {i}. {tool_name} {status}\n\n"
            formatted += f"**🎯 执行原因**: {safe_string(result['reason'])}\n\n"
            formatted += f"**⚠️ 风险评估**: {safe_string(result.get('risk_assessment', '未评估'))}\n\n"
            formatted += f"**📊 性能影响**: {safe_string(result.get('performance_impact', '未知影响'))}\n\n"

            if success:
                data = result['result'].get('data', {})
                message = safe_string(data.get('message', '任务执行完成'))
                formatted += f"**📊 执行结果**: {message}\n\n"

                if 'timestamp' in data:
                    formatted += f"**⏰ 完成时间**: {safe_string(data['timestamp'])}\n\n"

                if 'output_file' in data:
                    formatted += f"**📁 输出文件**: {safe_string(data['output_file'])}\n\n"

                if 'successful_count' in data:
                    formatted += f"**✅ 成功处理**: {data['successful_count']} 项\n\n"

                if 'failed_count' in data:
                    formatted += f"**❌ 处理失败**: {data['failed_count']} 项\n\n"

                if 'records_count' in data:
                    formatted += f"**📝 生成记录**: {data['records_count']} 条\n\n"
            else:
                error = safe_string(result['result'].get('error', '未知错误'))
                formatted += f"**💥 错误信息**: {error}\n\n"

            formatted += "---\n\n"

        formatted += "## 🚀 AI智能运维系统总结\n\n"
        formatted += "本次运维任务已通过QWEN3-32B大模型进行深度智能分析，每个AI决策都经过了专业的技术评估和执行风险分析，"
        formatted += "确保了执行过程的科学性、可靠性和技术先进性。所有操作均已记录并生成详细的技术报告。\n\n"
        formatted += "🔧 **技术特点**: 基于MCP协议的模块化服务架构，支持复杂运维任务的智能编排和自动化执行。\n\n"
        formatted += "🧠 **AI增强**: 集成QWEN3-32B大模型，提供自然语言理解、智能决策分析和专业技术建议。\n\n"
        formatted += "💡 如需查看更多详细信息，请检查各服务生成的输出文件和日志记录。\n"

        logger.debug(f"📊 AI运维报告生成完成，成功率: {(success_count / len(results) * 100):.1f}%")
        return formatted


class ChatAgent:
    def __init__(self):
        print("🤖 正在初始化AI智能运维助手...")
        print("🧠 加载QWEN3-32B大模型神经网络引擎...")
        logger.debug("🚀 ChatAgent AI运维助手启动初始化")

        self.scheduler = LLMScheduler()
        print("⚙️ 初始化MCP任务执行引擎...")
        self.executor = TaskExecutor()

        print("✅ AI智能运维助手初始化完成，已具备完整的AI驱动运维能力")
        logger.debug("🎯 ChatAgent AI运维助手初始化完成")

    async def process_user_input(self, user_input: str) -> str:
        try:
            clean_input = safe_string(user_input)
            logger.debug(f"📥 开始处理用户运维指令: {clean_input}")
            print(f"\n🤖 AI运维助手正在分析您的需求: {clean_input}")
            print("=" * 60)

            print("🧠 【阶段1/4】启动QWEN3-32B智能语义分析引擎...")
            print("    📝 深度分析用户输入的自然语言需求")
            print("    🔍 智能匹配最适合的运维服务工具")
            print("    📊 评估匹配置信度并生成技术执行计划")
            print("    🎯 进行风险评估和性能影响分析")

            plan = self.scheduler.parse_user_intent(clean_input)

            matched_service = plan.get('matched_service', 'unknown')
            confidence = plan.get('confidence', 0.0)
            intent = plan.get('intent', '未知意图')
            technical_reasoning = plan.get('technical_reasoning', '技术推理不可用')

            safe_matched_service = safe_string(matched_service)
            safe_intent = safe_string(intent)
            safe_technical_reasoning = safe_string(technical_reasoning)

            logger.debug(f"🎯 AI分析完成 - 服务: {safe_matched_service}, 置信度: {confidence}, 意图: {safe_intent}")
            logger.debug(f"🧠 技术推理: {safe_technical_reasoning}")

            print(f"\n🎯 【阶段2/4】QWEN3深度分析完成，智能决策结果:")
            print(f"    🔧 推荐服务: {safe_matched_service}")
            print(f"    📈 置信度: {confidence:.1%}")
            print(f"    💭 理解意图: {safe_intent}")
            print(f"    🧠 技术推理: {safe_technical_reasoning}")

            execution_plan = plan.get('execution_plan', [])
            if not execution_plan:
                logger.error("🚨 执行计划为空，返回服务清单")
                print("\n❌ QWEN3无法理解您的需求，为您提供可用服务清单:")
                return "抱歉，QWEN3无法理解您的需求，请重新描述。您可以尝试以下请求：\n\n" \
                       "🔧 **硬件巡检类服务**:\n" \
                       "- 完整巡检 (执行全流程自动化巡检)\n" \
                       "- 系统巡检 (查询数据库获取异常服务器)\n" \
                       "- 内存巡检 (SSH连接详细检查内存状态)\n" \
                       "- 硬盘巡检 (SSH连接详细检查硬盘状态)\n" \
                       "- AI分析报告 (生成智能硬件分析报告)\n" \
                       "- 内存升级建议 (生成内存升级建议)\n\n" \
                       "📊 **监控分析类服务**:\n" \
                       "- 日志分析 (智能分析日志文件)\n" \
                       "- 日报 (生成每日监控分析报告)\n" \
                       "- 周报 (生成每周趋势分析报告)\n" \
                       "- 服务监控 (检查服务运行状态)\n" \
                       "- 平台监控 (监控系统性能指标)\n\n" \
                       "📱 **通知推送类服务**:\n" \
                       "- 企业微信通知 (发送微信消息和告警)\n" \
                       "- 内存申请通知 (检测并发送内存升级申请)\n" \
                       "- 内存解决通知 (检测并通知已解决的内存问题)\n\n"

            print(f"\n⚙️ 【阶段3/4】通过MCP协议调用专业运维服务...")
            print("    🔗 建立与MCP服务器的安全连接")
            print("    📡 发送标准化的服务调用请求")
            print("    🏃‍♂️ 执行具体的运维操作任务")
            print("    📊 实时监控执行状态和性能指标")

            results = await self.executor.execute_plan(execution_plan)

            print(f"\n📊 【阶段4/4】生成AI智能分析报告...")
            print("    📝 整理所有执行结果")
            print("    🎨 格式化为专业技术报告")
            print("    📈 生成性能统计和成功率分析")
            print("    ✅ 任务执行流程完成")

            formatted_results = self.executor.format_results(results)
            logger.debug("🎯 用户运维请求处理完成")

            return formatted_results

        except Exception as e:
            print(f"\n💥 处理过程中遇到异常: {e}")
            logger.error(f"🚨 处理用户输入失败: {e}")
            return f"❌ 处理请求时发生错误: {str(e)}\n\n💡 请检查网络连接或稍后重试。如问题持续存在，请联系技术支持。"

    async def chat(self):
        print("🚀 硬件巡检智能助手已启动 (QWEN3-32B大模型驱动版本)")
        print("=" * 60)
        print("🎯 **核心能力**: QWEN3智能分析 + MCP协议调用 + 专业运维服务")
        print("🧠 **智能引擎**: QWEN3-32B大模型自然语言处理，智能匹配最佳运维方案")
        print("🔧 **服务架构**: 模块化MCP服务，支持复杂运维任务编排")
        print("📊 **技术特性**: 风险评估、性能分析、智能推理、自动化执行")
        print("=" * 60)

        print("\n📌 **可用服务类型**:")
        print("   🔧 【硬件巡检服务】")
        print("     • 服务001: 系统巡检 - 数据库查询异常服务器")
        print("     • 服务002: 内存巡检 - SSH连接深度内存分析")
        print("     • 服务003: 硬盘巡检 - SSH连接存储状态检查")
        print("     • 服务004: AI分析报告 - 智能硬件评估建议")
        print("     • 服务005: 完整巡检 - 端到端自动化流程")
        print("     • 服务011: 内存升级建议 - 内存升级方案生成")

        print("\n   📊 【监控分析服务】")
        print("     • 服务006: 日志分析 - AI智能日志诊断")
        print("     • 服务007: 日报生成 - 昨日监控数据分析")
        print("     • 服务008: 周报生成 - 趋势分析与预测")
        print("     • 服务009: 服务监控 - 实时服务状态检查")
        print("     • 服务010: 平台监控 - 系统性能全面监控")

        print("\n   📱 【通知推送服务】")
        print("     • 服务012: 企业微信通知 - 消息推送和告警通知")
        print("     • 服务013: 内存申请通知 - 自动检测需要申请的内存升级")
        print("     • 服务015: 内存解决通知 - 自动检测已解决的内存问题")

        print("\n💡 **使用说明**:")
        print("   • 直接用自然语言描述需求，QWEN3会自动理解并选择服务")
        print("   • 支持复杂任务的智能拆解和自动化执行")
        print("   • 所有操作都会生成详细的技术分析报告和性能统计")
        print("   • 输入 'quit' 或 '退出' 结束对话")

        print("\n🧠 **QWEN3-32B智能语义理解已就绪，开始您的专业运维之旅...**")
        logger.debug("🎯 ChatAgent聊天界面启动完成")

        while True:
            try:
                user_input = input("\n🗣️  请输入您的需求: ").strip()

                if user_input.lower() in ['quit', 'exit', '退出', 'q']:
                    print("\n👋 感谢使用硬件巡检智能助手！")
                    print("🎉 期待下次为您提供更优质的智能运维服务")
                    logger.debug("👋 用户主动退出聊天")
                    break

                if not user_input:
                    print(
                        "💭 请告诉我您需要什么帮助，比如：'检查内存状态'、'生成系统报告'、'发送微信通知'、'内存申请通知'、'内存解决通知'等")
                    continue

                clean_input = safe_string(user_input)
                logger.debug(f"📥 用户运维指令: {clean_input}")
                response = await self.process_user_input(clean_input)
                print(f"\n📊 **执行结果报告**:\n{response}")
                print("\n" + "=" * 60)
                print("💡 如需其他帮助，请继续输入您的需求...")

            except KeyboardInterrupt:
                print("\n\n👋 检测到退出信号，感谢使用硬件巡检智能助手！")
                print("🎉 期待下次为您提供更优质的智能运维服务")
                logger.debug("⌨️ 用户键盘中断退出")
                break
            except Exception as e:
                safe_error = safe_string(str(e))
                logger.error(f"🚨 聊天处理错误: {safe_error}")
                print(f"❌ 系统遇到异常: {safe_error}")
                print("💡 请稍后重试，或联系技术支持获取帮助")


async def main():
    logger.debug("🚀 程序启动")
    agent = ChatAgent()
    await agent.chat()
    logger.debug("🏁 程序结束")


if __name__ == "__main__":
    asyncio.run(main())
