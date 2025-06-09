#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import json
import os
import requests
import sys
from datetime import datetime

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from utils.logger import setup_logger

logger = setup_logger(__name__)

LLM_CONFIG = {
    'base_url': 'http://192.168.101.214:6007',
    'chat_endpoint': '/v1/chat/completions',
    'model_name': 'Qwen3-32B-AWQ'
}

class FullInspectionRunner:
    def __init__(self, mcp_server=None):
        self.mcp_server = mcp_server
        self.system_file = os.path.join(project_root, 'services', 'data', 'system.json')
        self.llm_config = LLM_CONFIG

    def load_system_data(self):
        try:
            with open(self.system_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"读取系统文件失败: {e}")
            return None

    def call_llm(self, prompt, temperature=0.3, max_tokens=800):
        try:
            url = f"{self.llm_config['base_url']}{self.llm_config['chat_endpoint']}"
            payload = {
                "model": self.llm_config['model_name'],
                "messages": [
                    {"role": "system",
                     "content": "你是一个智能运维调度专家，负责控制硬件巡检流程。你需要根据当前状态决定下一步应该执行哪个MCP服务。"},
                    {"role": "user", "content": prompt}
                ],
                "temperature": temperature,
                "max_tokens": max_tokens
            }

            headers = {"Content-Type": "application/json"}
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()

            result = response.json()
            return result["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"LLM调用失败: {e}")
            return None

    def parse_llm_decision(self, llm_response):
        try:
            import re
            json_match = re.search(r'\{.*\}', llm_response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        return None

    async def call_mcp_tool(self, tool_name, params=None):
        if params is None:
            params = {}

        request_data = json.dumps({
            "method": "call_tool",
            "params": {
                "name": tool_name,
                "arguments": params
            },
            "id": f"full_inspection_{tool_name}"
        })

        response_str = await self.mcp_server.handle_request(request_data)
        response = json.loads(response_str)
        return response

    async def get_next_step_from_llm(self, current_step, execution_results, available_services):
        executed_services = [step['service'] for step in execution_results.get('steps', [])]

        prompt = f"""
当前硬件巡检流程状态：
- 当前步骤: {current_step}
- 已执行的服务: {executed_services}
- 已执行结果: {json.dumps(execution_results, ensure_ascii=False, indent=2)}

可用的MCP服务：
{json.dumps(available_services, ensure_ascii=False, indent=2)}

请分析当前状态并决定下一步应该执行哪个服务。返回JSON格式：
{{
    "next_service": "服务名称或null",
    "reason": "选择原因",
    "params": {{"参数": "值"}},
    "should_continue": true/false,
    "message": "给用户的消息"
}}

决策规则：
1. 如果是第一步(current_step=0)，执行service_001_system_inspection进行系统巡检
2. 系统巡检完成后，根据异常IP列表执行内存巡检service_002_memory_inspection
3. 内存巡检完成后，执行硬盘巡检service_003_disk_inspection
4. 内存和硬盘巡检都完成后，执行service_004_hardware_summary生成AI报告
5. AI报告生成完成后，执行service_011_apply_purchases进行内存升级建议(不等待回复)
6. 内存升级建议完成后，返回should_continue: false结束流程
7. 如果前一步失败，分析是否可以继续下一步

重要：只有当所有5个核心服务都执行完成后才能设置should_continue: false
"""

        response = self.call_llm(prompt)
        if response:
            decision = self.parse_llm_decision(response)
            if decision:
                return decision

        executed_services = [step['service'] for step in execution_results.get('steps', [])]

        if current_step == 0:
            return {
                "next_service": "service_001_system_inspection",
                "reason": "开始执行系统巡检",
                "params": {},
                "should_continue": True,
                "message": "执行系统巡检以获取异常服务器列表"
            }
        elif "service_001_system_inspection" in executed_services and "service_002_memory_inspection" not in executed_services:
            return {
                "next_service": "service_002_memory_inspection",
                "reason": "系统巡检完成，开始内存巡检",
                "params": {},
                "should_continue": True,
                "message": "执行内存详细巡检"
            }
        elif "service_002_memory_inspection" in executed_services and "service_003_disk_inspection" not in executed_services:
            return {
                "next_service": "service_003_disk_inspection",
                "reason": "内存巡检完成，开始硬盘巡检",
                "params": {},
                "should_continue": True,
                "message": "执行硬盘详细巡检"
            }
        elif ("service_002_memory_inspection" in executed_services and
              "service_003_disk_inspection" in executed_services and
              "service_004_hardware_summary" not in executed_services):
            return {
                "next_service": "service_004_hardware_summary",
                "reason": "内存和硬盘巡检完成，生成AI分析报告",
                "params": {},
                "should_continue": True,
                "message": "生成硬件巡检AI分析报告"
            }
        elif ("service_004_hardware_summary" in executed_services and
              "service_011_apply_purchases" not in executed_services):
            return {
                "next_service": "service_011_apply_purchases",
                "reason": "AI分析报告完成，开始内存升级建议",
                "params": {"wait_for_approval": False},
                "should_continue": True,
                "message": "生成内存升级建议"
            }
        else:
            return {
                "next_service": None,
                "reason": "所有巡检步骤已完成",
                "params": {},
                "should_continue": False,
                "message": "硬件巡检流程执行完成"
            }

    async def run_full_inspection(self, params=None):
        logger.info("【服务005】开始执行完整巡检流程 - 通过大模型智能调度")
        print("=== 硬件巡检智能助手 - AI驱动的完整巡检流程 ===")

        hours = params.get('hours', 6) if params else 6
        memory_threshold = params.get('memory_threshold', 70) if params else 70
        disk_threshold = params.get('disk_threshold', 80) if params else 80
        wait_for_approval = params.get('wait_for_approval', False) if params else False

        execution_results = {
            'start_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'parameters': {
                'hours': hours,
                'memory_threshold': memory_threshold,
                'disk_threshold': disk_threshold,
                'wait_for_approval': wait_for_approval
            },
            'steps': [],
            'status': 'running',
            'end_time': None,
            'ai_decisions': []
        }

        available_services = [
            {
                "name": "service_001_system_inspection",
                "description": "系统巡检 - 查询数据库获取异常服务器列表",
                "step_order": 1
            },
            {
                "name": "service_002_memory_inspection",
                "description": "内存巡检 - SSH连接详细检查内存",
                "step_order": 2
            },
            {
                "name": "service_003_disk_inspection",
                "description": "硬盘巡检 - SSH连接详细检查硬盘",
                "step_order": 3
            },
            {
                "name": "service_004_hardware_summary",
                "description": "AI分析报告 - 生成智能分析报告",
                "step_order": 4
            },
            {
                "name": "service_011_apply_purchases",
                "description": "内存升级建议 - 生成内存升级建议",
                "step_order": 5
            }
        ]

        current_step = 0
        max_steps = 15

        try:
            while current_step < max_steps:
                print(f"\n🤖 AI正在分析当前状态并决定下一步操作...")

                decision = await self.get_next_step_from_llm(
                    current_step,
                    execution_results,
                    available_services
                )

                execution_results['ai_decisions'].append({
                    'step': current_step + 1,
                    'decision': decision,
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })

                print(f"📋 AI决策: {decision.get('message', '未知决策')}")
                logger.info(f"AI决策: {decision}")

                next_service = decision.get('next_service')
                if not next_service:
                    print("🎯 AI判断流程应该结束")
                    break

                print(f"⚙️  执行服务: {next_service}")
                print(f"📝 执行原因: {decision.get('reason', '未知原因')}")

                service_params = decision.get('params', {})

                if next_service == "service_001_system_inspection":
                    service_params.update({
                        "hours": hours,
                        "memory_threshold": memory_threshold,
                        "disk_threshold": disk_threshold
                    })

                elif next_service in ["service_002_memory_inspection", "service_003_disk_inspection"]:
                    system_data = self.load_system_data()
                    if system_data:
                        if next_service == "service_002_memory_inspection":
                            ip_list = system_data.get('abnormal_memory_ips', [])
                        else:
                            ip_list = system_data.get('abnormal_disk_ips', [])

                        if ip_list:
                            service_params['ip_list'] = ip_list
                        else:
                            print(f"📋 跳过 {next_service} - 未发现需要巡检的IP")

                elif next_service == "service_011_apply_purchases":
                    service_params['wait_for_approval'] = wait_for_approval

                print(f"🔄 正在执行 {next_service}...")
                result = await self.call_mcp_tool(next_service, service_params)

                step_result = {
                    'step': current_step + 1,
                    'service': next_service,
                    'status': 'success' if result.get('success') else 'failed',
                    'message': result.get('data', {}).get('message', '') if result.get('success') else result.get(
                        'error', ''),
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'ai_reason': decision.get('reason', ''),
                    'params': service_params,
                    'result_data': result.get('data', {}) if result.get('success') else None
                }

                if result.get('success'):
                    print(f"✅ {next_service} 执行成功")
                    data = result.get('data', {})
                    if 'successful_count' in data:
                        print(
                            f"   成功: {data.get('successful_count', 0)}台, 无权限: {data.get('no_permission_count', 0)}台")

                    if 'output_file' in data:
                        print(f"   输出文件: {data['output_file']}")

                    if 'records_count' in data:
                        print(f"   生成记录: {data.get('records_count', 0)}条")

                else:
                    step_result['error'] = result.get('error')
                    print(f"❌ {next_service} 执行失败: {result.get('error')}")

                execution_results['steps'].append(step_result)
                current_step += 1

                if next_service == "service_001_system_inspection" and result.get('success'):
                    system_data = self.load_system_data()
                    if system_data:
                        abnormal_memory_ips = system_data.get('abnormal_memory_ips', [])
                        abnormal_disk_ips = system_data.get('abnormal_disk_ips', [])
                        print(f"   发现异常内存服务器: {len(abnormal_memory_ips)}台 {abnormal_memory_ips}")
                        print(f"   发现异常硬盘服务器: {len(abnormal_disk_ips)}台 {abnormal_disk_ips}")

                if not decision.get('should_continue', False):
                    print("🎯 AI判断当前步骤完成后流程结束")
                    break

                await asyncio.sleep(1)

            execution_results['status'] = 'completed'
            execution_results['end_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            print("\n=== AI驱动的完整巡检流程执行完成 ===")
            print("📁 生成的结果文件:")
            print(f"   - {self.system_file} (系统巡检结果)")
            print("   - services/data/memory_inspection.json (内存巡检结果)")
            print("   - services/data/disk_inspection.json (硬盘巡检结果)")
            print("   - services/data/hardware_summary.txt (AI分析报告)")
            print("   - services/data/memory_update.json (内存升级建议)")
            print(f"🤖 AI共做出 {len(execution_results['ai_decisions'])} 次决策")
            print(f"📊 成功执行 {len([s for s in execution_results['steps'] if s['status'] == 'success'])} 个服务")

            logger.info("【服务005】AI驱动的完整巡检流程执行完成")

            return execution_results

        except Exception as e:
            execution_results['status'] = 'failed'
            execution_results['error'] = str(e)
            execution_results['end_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            logger.error(f"【服务005】完整巡检流程执行失败: {e}")
            print(f"❌ 完整巡检流程执行失败: {e}")
            return execution_results

async def full_inspection(params=None, mcp_server=None):
    try:
        print("【服务005】AI驱动的硬件巡检完整流程启动")
        logger.info("【服务005】开始执行AI驱动的硬件巡检完整流程")

        if not mcp_server:
            return {"success": False, "error": "缺少MCP服务器实例"}

        runner = FullInspectionRunner(mcp_server)
        results = await runner.run_full_inspection(params)

        if results['status'] == 'completed':
            return {
                "success": True,
                "message": "AI驱动的完整巡检流程执行完成",
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "execution_results": results
            }
        else:
            return {
                "success": False,
                "error": f"完整巡检流程执行失败: {results.get('error', '未知错误')}",
                "execution_results": results
            }

    except Exception as e:
        error_msg = f"【服务005】完整巡检流程异常: {str(e)}"
        print(error_msg)
        logger.error(error_msg)
        return {"success": False, "error": error_msg}

async def main():
    print("独立运行模式 - 需要MCP服务器实例")
    print("请通过MCP服务器调用此服务")

if __name__ == "__main__":
    asyncio.run(main())