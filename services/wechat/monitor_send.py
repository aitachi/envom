import json
import time
import os
import socket
from datetime import datetime
from pathlib import Path
from send_chat import wechat_notification_service


class MCPClient:
    def __init__(self, host="localhost", port=8003):
        self.host = host
        self.port = port

    def call_service(self, service_name, params=None):
        try:
            request = {
                "method": "call_tool",
                "params": {
                    "name": service_name,
                    "arguments": params or {}
                },
                "id": str(int(time.time()))
            }

            request_data = json.dumps(request, ensure_ascii=False)

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(30)

            sock.connect((self.host, self.port))
            sock.sendall(request_data.encode('utf-8'))

            response_data = b""
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response_data += chunk

                try:
                    json.loads(response_data.decode('utf-8'))
                    break
                except json.JSONDecodeError:
                    continue

            sock.close()

            if response_data:
                response = json.loads(response_data.decode('utf-8'))
                return response
            else:
                return {"success": False, "error": "无响应数据"}

        except Exception as e:
            return {"success": False, "error": str(e)}


class ChatMonitor:
    def __init__(self, json_file_path=None, check_interval=1):
        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent.parent

        if json_file_path is None:
            self.json_file_path = project_root / "chat.json"
        else:
            self.json_file_path = Path(json_file_path)

        self.memory_file_path = project_root / "services" / "data" / "memory_update.json"
        self.check_interval = check_interval
        self.last_modified_time = 0
        self.last_processed_timestamp = 0
        self.last_memory_check = 0
        self.memory_check_interval = 30

        self.approval_users = ['chu', 'llm-aitachi']
        self.pricing_users = ['llm-aitachi', 'hei']
        self.notification_recipients = ['hei', 'llm-aitachi']

        self.mcp_client = MCPClient()

    def normalize_username(self, username):
        return username.lower() if username else ""

    def is_approval_user(self, username):
        normalized = self.normalize_username(username)
        return normalized in self.approval_users

    def is_pricing_user(self, username):
        normalized = self.normalize_username(username)
        return normalized in self.pricing_users

    def load_memory_data(self):
        try:
            if not self.memory_file_path.exists():
                print(f"文件 {self.memory_file_path} 不存在")
                return None

            if self.memory_file_path.stat().st_size == 0:
                print(f"记忆文件 {self.memory_file_path} 为空")
                return None

            with open(self.memory_file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content:
                    return None

                data = json.loads(content)
                return data
        except json.JSONDecodeError as e:
            print(f"memory_update.json JSON解析错误: {e}")
            return None
        except Exception as e:
            print(f"读取 memory_update.json 文件时发生错误: {e}")
            return None

    def save_memory_data(self, data):
        try:
            self.memory_file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(self.memory_file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存 memory_update.json 文件时发生错误: {e}")
            return False

    def update_pricing_info(self, price, user, timestamp):
        try:
            memory_data = self.load_memory_data()

            if memory_data is None:
                print("❌ 无法加载记忆文件，跳过定价信息更新")
                return False

            if isinstance(memory_data, list):
                if len(memory_data) > 0:
                    latest_record = memory_data[-1]

                    if "pricing_info" not in latest_record:
                        latest_record["pricing_info"] = {}

                    latest_record["pricing_info"]["suggest_price"] = price
                    latest_record["pricing_info"]["currency"] = "CNY"
                    latest_record["pricing_info"]["suggest_user"] = user
                    latest_record["pricing_info"]["suggest_time"] = timestamp

                    print(f"✅ 准备更新数组中最新记录的定价信息")
                else:
                    print("❌ 记忆文件数组为空，无法更新定价信息")
                    return False

            elif isinstance(memory_data, dict):
                if "pricing_info" not in memory_data:
                    memory_data["pricing_info"] = {}

                memory_data["pricing_info"]["suggest_price"] = price
                memory_data["pricing_info"]["currency"] = "CNY"
                memory_data["pricing_info"]["suggest_user"] = user
                memory_data["pricing_info"]["suggest_time"] = timestamp

                print(f"✅ 准备更新对象格式的定价信息")
            else:
                print("❌ 记忆文件格式不正确，无法更新定价信息")
                return False

            if self.save_memory_data(memory_data):
                print(f"✅ 成功更新定价信息: 价格={price}, 用户={user}, 时间={timestamp}")
                return True
            else:
                print("❌ 保存定价信息失败")
                return False

        except Exception as e:
            print(f"❌ 更新定价信息时发生错误: {e}")
            return False

    def load_chat_data(self):
        try:
            if not self.json_file_path.exists():
                print(f"文件 {self.json_file_path} 不存在")
                return []

            if self.json_file_path.stat().st_size == 0:
                print(f"聊天文件 {self.json_file_path} 为空，等待数据写入...")
                return []

            with open(self.json_file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()

                if not content:
                    print(f"聊天文件 {self.json_file_path} 内容为空，等待数据写入...")
                    return []

                data = json.loads(content)
                if isinstance(data, list):
                    return data
                else:
                    print("JSON文件格式错误，应该是数组格式")
                    return []

        except json.JSONDecodeError as e:
            print(f"聊天文件JSON解析错误: {e}")
            print(f"文件内容可能格式不正确，等待有效数据...")
            return []
        except Exception as e:
            print(f"读取聊天文件时发生错误: {e}")
            return []

    def check_file_modified(self):
        try:
            if not self.json_file_path.exists():
                return False

            current_modified_time = self.json_file_path.stat().st_mtime
            if current_modified_time > self.last_modified_time:
                self.last_modified_time = current_modified_time
                return True
            return False
        except Exception as e:
            print(f"检查文件修改时间时发生错误: {e}")
            return False

    def find_approval_message(self, chat_data):
        sorted_data = sorted(chat_data, key=lambda x: x.get('timestamp_unix', 0))

        for i, message in enumerate(sorted_data):
            if message.get('timestamp_unix', 0) <= self.last_processed_timestamp:
                continue

            from_user = message.get('from_user', '')
            content = message.get('content', '').strip()

            if (self.is_approval_user(from_user) and content == '同意'):
                print(f"🎯 发现同意消息: 用户={from_user}, 内容={content}, 时间={message.get('timestamp')}")

                application_message = self.find_previous_application(sorted_data, i)

                if application_message:
                    return message, application_message
                else:
                    print("未找到对应的申请消息")

        return None, None

    def find_numeric_response(self, chat_data):
        sorted_data = sorted(chat_data, key=lambda x: x.get('timestamp_unix', 0))

        for i, message in enumerate(sorted_data):
            if message.get('timestamp_unix', 0) <= self.last_processed_timestamp:
                continue

            from_user = message.get('from_user', '')
            content = message.get('content', '').strip()

            if (self.is_pricing_user(from_user) and content.isdigit()):
                print(f"🔍 检测到 {from_user} 发送的纯数字回复: {content}")

                pricing_message = self.find_previous_pricing_request(sorted_data, i)

                if pricing_message:
                    print(f"✅ 找到匹配的询价消息，准备更新定价信息")

                    self.update_pricing_info(
                        price=content,
                        user=from_user,
                        timestamp=message.get('timestamp', '')
                    )

                    return message, pricing_message
                else:
                    print("❌ 未找到对应的询价消息")

        return None, None

    def find_previous_pricing_request(self, sorted_data, response_index):
        for i in range(response_index - 1, -1, -1):
            message = sorted_data[i]
            content = message.get('content', '')

            pricing_keywords = ['价格', '多少钱', '报价', '费用', '成本', '价格信息', '采购价格']
            if any(keyword in content for keyword in pricing_keywords):
                print(f"找到对应的询价消息: 时间戳 {message.get('timestamp')}")
                return message

        return None

    def find_previous_application(self, sorted_data, approval_index):
        for i in range(approval_index - 1, -1, -1):
            message = sorted_data[i]
            content = message.get('content', '')

            application_keywords = ['申请', '采购', '升级', '申请编号']
            if any(keyword in content for keyword in application_keywords):
                print(f"找到对应的申请消息: 时间戳 {message.get('timestamp')}")
                return message

        return None

    def extract_application_summary(self, application_content):
        lines = application_content.split('\n')
        summary_parts = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if any(keyword in line for keyword in ['申请编号', '申请人', '申请时间', '预估价格', '升级理由']):
                summary_parts.append(line)
            elif line.startswith('📋') and '申请' in line:
                summary_parts.append(line)
            if len(summary_parts) >= 6:
                break

        return '\n'.join(summary_parts) if summary_parts else application_content[:200] + '...'

    def format_notification_message(self, approval_msg, application_msg):
        application_summary = self.extract_application_summary(application_msg.get('content', ''))

        message = f"""🔔 申请审批通知

✅ 审批结果: {approval_msg.get('content', '')}
👤 审批人: {approval_msg.get('from_user', '')}
📅 审批时间: {approval_msg.get('timestamp', '')}

📋 申请摘要:
{application_summary}

⏰ 通知时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""

        return message

    def format_pricing_notification_message(self, numeric_msg, pricing_msg):
        message = f"""💰 定价回复通知

💵 回复价格: {numeric_msg.get('content', '')} CNY
👤 回复人: {numeric_msg.get('from_user', '')}
📅 回复时间: {numeric_msg.get('timestamp', '')}

❓ 原始询价:
{pricing_msg.get('content', '')[:200]}...

📝 定价信息已更新到系统记忆
⏰ 通知时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""

        return message

    def send_notification_to_user(self, user, notification_content):
        try:
            params = {
                'to_user': user,
                'content': notification_content,
                'source': 'monitor_notification'
            }

            print(f"📤 向 {user} 发送通知消息")
            result = wechat_notification_service(params)

            if result.get('success'):
                print(f"✅ 向 {user} 发送通知消息成功")
            else:
                print(f"❌ 向 {user} 发送通知消息失败: {result.get('message')}")

        except Exception as e:
            print(f"向 {user} 发送通知时发生异常: {e}")

    def send_notification(self, primary_msg, related_msg, notification_type="approval"):
        if notification_type == "approval":
            notification_content = self.format_notification_message(primary_msg, related_msg)
        else:
            notification_content = self.format_pricing_notification_message(primary_msg, related_msg)

        print(f"🎯 开始发送{notification_type}通知消息...")

        for user in self.notification_recipients:
            print(f"\n--- 发送给 {user} ---")
            self.send_notification_to_user(user, notification_content)

            if user != self.notification_recipients[-1]:
                time.sleep(2)

        if notification_type == "approval":
            print(f"\n🎯 开始发送完整申请内容...")
            full_content = f"📋 完整申请内容:\n\n{related_msg.get('content', '')}"

            for user in self.notification_recipients:
                print(f"\n--- 发送完整内容给 {user} ---")
                time.sleep(1)

                params = {
                    'to_user': user,
                    'content': full_content,
                    'source': 'monitor_notification'
                }

                print(f"📤 向 {user} 发送完整内容")
                result = wechat_notification_service(params)

                if result.get('success'):
                    print(f"✅ 向 {user} 发送完整内容成功")
                else:
                    print(f"❌ 向 {user} 发送完整内容失败: {result.get('message')}")

                if user != self.notification_recipients[-1]:
                    time.sleep(2)

    def update_last_processed_timestamp(self, chat_data):
        if chat_data:
            max_timestamp = max(msg.get('timestamp_unix', 0) for msg in chat_data)
            self.last_processed_timestamp = max_timestamp

    def check_memory_conditions(self):
        try:
            current_time = time.time()
            if current_time - self.last_memory_check < self.memory_check_interval:
                return

            self.last_memory_check = current_time
            print(f"\n🔍 执行内存条件检查...")

            response = self.mcp_client.call_service("service_013_memory_apply_notice")
            if response.get('success'):
                print("✅ 内存申请通知检查完成")
            else:
                print(f"❌ 内存申请通知检查失败: {response.get('error')}")

            response = self.mcp_client.call_service("service_015_memory_resolved_notice")
            if response.get('success'):
                print("✅ 内存解决通知检查完成")
            else:
                print(f"❌ 内存解决通知检查失败: {response.get('error')}")

        except Exception as e:
            print(f"❌ 内存条件检查异常: {e}")

    def start_monitoring(self):
        print(f"开始监控文件: {self.json_file_path}")
        print(f"记忆文件路径: {self.memory_file_path}")
        print(f"检查间隔: {self.check_interval}秒")
        print(f"审批用户: {self.approval_users}")
        print(f"定价用户: {self.pricing_users}")
        print(f"通知接收者: {self.notification_recipients}")
        print("=" * 50)

        initial_data = self.load_chat_data()
        self.update_last_processed_timestamp(initial_data)
        print(f"初始化完成，最后处理时间戳: {self.last_processed_timestamp}")

        while True:
            try:
                if self.check_file_modified():
                    print(f"\n📄 检测到文件变化: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

                    chat_data = self.load_chat_data()

                    if chat_data:
                        approval_msg, application_msg = self.find_approval_message(chat_data)

                        if approval_msg and application_msg:
                            print("🎯 发现符合条件的审批消息")
                            self.send_notification(approval_msg, application_msg, "approval")

                        numeric_msg, pricing_msg = self.find_numeric_response(chat_data)

                        if numeric_msg and pricing_msg:
                            print("🎯 发现符合条件的定价回复")
                            self.send_notification(numeric_msg, pricing_msg, "pricing")

                        self.update_last_processed_timestamp(chat_data)

                self.check_memory_conditions()

                time.sleep(self.check_interval)

            except KeyboardInterrupt:
                print("\n⏹️ 监控已停止")
                break
            except Exception as e:
                print(f"❌ 监控过程中发生错误: {e}")
                time.sleep(self.check_interval)


def main():
    print("🤖 企业微信聊天监控服务启动")
    print("监控条件:")
    print("- 审批监控: 发送者 Chu/llm-aitachi 发送 '同意'")
    print("- 定价监控: 发送者 llm-aitachi/Hei 发送纯数字")
    print("- 通知接收者: hei, llm-aitachi")
    print("- 内存条件检查: 每30秒检查一次价格询问、申请通知、解决通知")
    print("=" * 50)

    monitor = ChatMonitor(
        check_interval=2
    )

    monitor.start_monitoring()


if __name__ == "__main__":
    main()
