#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import time
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import schedule
from threading import Thread

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

try:
    from utils.logger import setup_logger
    from chat_agent import ChatAgent
except ImportError as e:
    print(f"导入模块失败: {e}")
    print("请确保所有依赖模块存在")
    sys.exit(1)

logger = setup_logger(__name__)

class PreciseScheduler:
    def __init__(self):
        self.chat_agent = ChatAgent()
        self.is_running = False
        self.task_history = []
        self.next_tasks = []

        self.scheduled_services = {
            "service_005": {
                "name": "完整巡检流程",
                "requests": [
                    "执行完整巡检流程",
                    "进行全流程巡检",
                    "一键巡检",
                    "完整硬件巡检"
                ],
                "times": ["10:15", "15:15"],
                "description": "每天10:15、15:15执行"
            },
            "service_007": {
                "name": "日报生成",
                "requests": [
                    "生成日报",
                    "生成每日监控报告",
                    "昨日系统分析报告",
                    "日常监控日报"
                ],
                "times": ["10:10", "15:10"],
                "description": "每天10:10、15:10执行"
            },
            "service_008": {
                "name": "周报生成",
                "requests": [
                    "生成周报",
                    "生成每周监控报告",
                    "上周系统分析报告",
                    "周期性监控周报"
                ],
                "times": ["monday-08:00"],
                "description": "每周一08:00执行"
            },
            "service_009": {
                "name": "服务监控检查",
                "requests": [
                    "执行服务监控检查",
                    "检查服务运行状态",
                    "服务健康检查",
                    "平台服务监控"
                ],
                "times": ["09:55", "14:55"],
                "description": "每天09:55、14:55执行"
            },
            "service_010": {
                "name": "平台性能监控",
                "requests": [
                    "执行平台性能监控",
                    "监控系统性能",
                    "平台资源监控",
                    "性能指标检查"
                ],
                "times": ["09:58", "14:58"],
                "description": "每天09:58、14:58执行"
            }
        }

        self.manual_services = {
            "service_001": {
                "name": "系统巡检",
                "description": "通过chat手动触发"
            },
            "service_002": {
                "name": "内存巡检",
                "description": "通过chat手动触发"
            },
            "service_003": {
                "name": "硬盘巡检",
                "description": "通过chat手动触发"
            },
            "service_004": {
                "name": "AI分析报告",
                "description": "通过chat手动触发"
            },
            "service_006": {
                "name": "日志文件分析",
                "description": "通过chat手动触发"
            },
            "service_011": {
                "name": "硬件更换审批",
                "description": "通过chat手动触发"
            }
        }

        self.request_counters = {service: 0 for service in self.scheduled_services.keys()}

    def get_service_request(self, service_id: str) -> str:
        if service_id not in self.scheduled_services:
            return f"执行{service_id}"

        requests = self.scheduled_services[service_id]["requests"]
        counter = self.request_counters[service_id]
        request = requests[counter % len(requests)]
        self.request_counters[service_id] += 1

        return request

    def calculate_next_execution_time(self, service_id: str, time_str: str) -> datetime:
        now = datetime.now()

        if time_str.startswith("monday-"):
            time_part = time_str.split("-")[1]
            hour, minute = map(int, time_part.split(":"))

            days_ahead = 0 - now.weekday()
            if days_ahead <= 0:
                days_ahead += 7

            next_monday = now + timedelta(days=days_ahead)
            next_time = next_monday.replace(hour=hour, minute=minute, second=0, microsecond=0)

            if now.weekday() == 0:
                today_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                if today_time > now:
                    next_time = today_time

        else:
            hour, minute = map(int, time_str.split(":"))
            next_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

            if next_time <= now:
                next_time += timedelta(days=1)

        return next_time

    def get_time_until_execution(self, target_time: datetime) -> str:
        now = datetime.now()
        diff = target_time - now

        if diff.total_seconds() <= 0:
            return "即将执行"

        days = diff.days
        hours, remainder = divmod(diff.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        if days > 0:
            return f"{days}天{hours}小时{minutes}分钟"
        elif hours > 0:
            return f"{hours}小时{minutes}分钟{seconds}秒"
        elif minutes > 0:
            return f"{minutes}分钟{seconds}秒"
        else:
            return f"{seconds}秒"

    async def execute_scheduled_task(self, service_id: str, scheduled_time: str):
        try:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            service_name = self.scheduled_services[service_id]["name"]
            user_request = self.get_service_request(service_id)

            print("=" * 100)
            print(f"⏰ 定时任务执行: {service_name} ({service_id})")
            print(f"🕐 当前时间: {current_time}")
            print(f"📅 计划时间: {scheduled_time}")
            print(f"📝 执行请求: {user_request}")
            print("=" * 100)

            logger.info(f"定时执行任务 {service_id} ({service_name}): {user_request}")

            start_time = time.time()

            response = await self.chat_agent.process_user_input(user_request)

            execution_time = time.time() - start_time

            print(f"\n📊 执行结果:")
            print("-" * 80)
            print(response)
            print("-" * 80)
            print(f"⏱️  执行耗时: {execution_time:.2f} 秒")
            print("=" * 100)
            print()

            task_record = {
                "service_id": service_id,
                "service_name": service_name,
                "request": user_request,
                "execution_time": execution_time,
                "timestamp": current_time,
                "scheduled_time": scheduled_time,
                "success": True,
                "type": "scheduled"
            }
            self.task_history.append(task_record)

            logger.info(f"定时任务 {service_id} 执行完成，耗时: {execution_time:.2f}秒")

        except Exception as e:
            error_msg = f"定时任务 {service_id} 执行失败: {str(e)}"
            print(f"❌ {error_msg}")
            logger.error(error_msg)

            task_record = {
                "service_id": service_id,
                "service_name": service_name,
                "request": user_request if 'user_request' in locals() else "未知",
                "execution_time": 0,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "scheduled_time": scheduled_time,
                "success": False,
                "error": str(e),
                "type": "scheduled"
            }
            self.task_history.append(task_record)

            import traceback
            traceback.print_exc()

    def setup_schedule(self):
        print("📅 设置精确定时任务...")

        schedule.every().day.at("10:15").do(
            lambda: asyncio.create_task(self.execute_scheduled_task("service_005", "10:15"))
        )
        schedule.every().day.at("15:15").do(
            lambda: asyncio.create_task(self.execute_scheduled_task("service_005", "15:15"))
        )

        schedule.every().day.at("10:10").do(
            lambda: asyncio.create_task(self.execute_scheduled_task("service_007", "10:10"))
        )
        schedule.every().day.at("15:10").do(
            lambda: asyncio.create_task(self.execute_scheduled_task("service_007", "15:10"))
        )

        schedule.every().monday.at("08:00").do(
            lambda: asyncio.create_task(self.execute_scheduled_task("service_008", "周一08:00"))
        )

        schedule.every().day.at("09:55").do(
            lambda: asyncio.create_task(self.execute_scheduled_task("service_009", "09:55"))
        )
        schedule.every().day.at("14:55").do(
            lambda: asyncio.create_task(self.execute_scheduled_task("service_009", "14:55"))
        )

        schedule.every().day.at("09:58").do(
            lambda: asyncio.create_task(self.execute_scheduled_task("service_010", "09:58"))
        )
        schedule.every().day.at("14:58").do(
            lambda: asyncio.create_task(self.execute_scheduled_task("service_010", "14:58"))
        )

        print("✅ 精确定时任务设置完成!")

    def update_next_tasks(self):
        self.next_tasks = []

        for service_id, config in self.scheduled_services.items():
            service_name = config["name"]

            for time_str in config["times"]:
                next_time = self.calculate_next_execution_time(service_id, time_str)

                self.next_tasks.append({
                    "service_id": service_id,
                    "service_name": service_name,
                    "scheduled_time": time_str,
                    "next_execution": next_time,
                    "countdown": self.get_time_until_execution(next_time)
                })

        self.next_tasks.sort(key=lambda x: x["next_execution"])

    def print_countdown_status(self):
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        print("\n" + "=" * 120)
        print(f"⏰ 任务倒计时状态报告 - {current_time}")
        print("=" * 120)

        self.update_next_tasks()

        print(f"📋 定时任务列表 (共{len(self.next_tasks)}个):")
        print("-" * 120)
        print(f"{'序号':<4} {'服务ID':<12} {'服务名称':<16} {'计划时间':<12} {'下次执行时间':<20} {'倒计时':<20}")
        print("-" * 120)

        for i, task in enumerate(self.next_tasks, 1):
            next_time_str = task["next_execution"].strftime("%m-%d %H:%M:%S")
            countdown = self.get_time_until_execution(task["next_execution"])

            print(f"{i:<4} {task['service_id']:<12} {task['service_name']:<16} "
                  f"{task['scheduled_time']:<12} {next_time_str:<20} {countdown:<20}")

        print("-" * 120)

        print(f"📝 手动触发服务列表 (共{len(self.manual_services)}个):")
        print("-" * 80)
        for service_id, config in self.manual_services.items():
            print(f"  {service_id}: {config['name']} - {config['description']}")
        print("-" * 80)

        if self.task_history:
            total_tasks = len(self.task_history)
            successful_tasks = sum(1 for task in self.task_history if task['success'])
            failed_tasks = total_tasks - successful_tasks

            print(f"📊 任务执行统计:")
            print(f"  总执行次数: {total_tasks}")
            print(f"  成功次数: {successful_tasks}")
            print(f"  失败次数: {failed_tasks}")
            print(f"  成功率: {(successful_tasks / total_tasks * 100):.1f}%")

            recent_tasks = self.task_history[-5:]
            print(f"\n📈 最近执行的任务:")
            for task in recent_tasks:
                status = "✅" if task['success'] else "❌"
                print(f"  {status} {task['timestamp']} - {task['service_name']} ({task['service_id']})")

        print("=" * 120)
        print()

    async def countdown_loop(self):
        while self.is_running:
            try:
                self.print_countdown_status()

                await asyncio.sleep(600)

            except Exception as e:
                logger.error(f"倒计时循环发生错误: {e}")
                print(f"❌ 倒计时循环错误: {e}")
                await asyncio.sleep(60)

    async def schedule_loop(self):
        while self.is_running:
            try:
                schedule.run_pending()

                await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"定时任务循环发生错误: {e}")
                print(f"❌ 定时任务循环错误: {e}")
                await asyncio.sleep(5)

    def print_startup_info(self):
        print("🤖 精确智能运维定时调度器")
        print("=" * 60)
        print("📋 定时执行的服务:")
        for service_id, config in self.scheduled_services.items():
            print(f"  {service_id}: {config['name']} - {config['description']}")

        print("\n📝 手动触发的服务:")
        for service_id, config in self.manual_services.items():
            print(f"  {service_id}: {config['name']} - {config['description']}")

        print(f"\n⏰ 倒计时报告: 每10分钟输出一次")
        print(f"💡 按 Ctrl+C 停止调度器")
        print("=" * 60)

    async def start_scheduler(self):
        self.is_running = True

        self.print_startup_info()
        self.setup_schedule()

        logger.info("精确定时调度器启动")

        try:
            self.print_countdown_status()

            await asyncio.gather(
                self.schedule_loop(),
                self.countdown_loop()
            )

        except KeyboardInterrupt:
            print("\n\n🛑 收到停止信号，正在关闭调度器...")
            await self.stop_scheduler()
        except Exception as e:
            logger.error(f"调度器运行时发生错误: {e}")
            print(f"❌ 调度器运行错误: {e}")
            import traceback
            traceback.print_exc()

    async def stop_scheduler(self):
        self.is_running = False
        final_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        print("🛑 精确定时调度器已停止")
        print(f"⏰ 停止时间: {final_time}")

        if self.task_history:
            total_tasks = len(self.task_history)
            successful_tasks = sum(1 for task in self.task_history if task['success'])
            print(f"📊 总执行统计: {successful_tasks}/{total_tasks} 成功")

        print("👋 感谢使用精确智能运维调度器!")

        logger.info(f"精确定时调度器停止，共执行 {len(self.task_history)} 次任务")

async def main():
    print("🤖 精确智能运维定时调度器启动程序")
    print("=" * 50)

    try:
        scheduler = PreciseScheduler()
        await scheduler.start_scheduler()

    except KeyboardInterrupt:
        print("\n👋 程序被用户中断")
    except Exception as e:
        logger.error(f"程序运行失败: {e}")
        print(f"❌ 程序运行失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())