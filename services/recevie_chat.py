# -*- coding: utf-8 -*-
"""
企业微信消息加解密处理工具 - 增强版
增加了请求信息存储和解密信息存储功能，以及价格信息自动更新功能
"""
import base64
from datetime import datetime
import struct
import time
import os
import json
import re
from Crypto.Cipher import AES
from flask import Flask, request, jsonify
import xml.etree.ElementTree as ET


class WorkWeixinCrypt:
    """企业微信消息加解密类"""

    def __init__(self, token=None, encoding_aes_key=None, corp_id=None):
        """
        初始化
        :param token: 企业微信设置的Token
        :param encoding_aes_key: 企业微信设置的EncodingAESKey
        :param corp_id: 企业微信的CorpID
        """
        self.token = token or "RF2tZ75YQtSTsy9z"
        self.encoding_aes_key = base64.b64decode(
            (encoding_aes_key or "ulKUK3i9wxVvTplM4C9KN8zE8mJJ7Rp1f2JwWmj8tEu") + "=")
        self.corp_id = corp_id or "ww568874482f006b53"
        self.iv = self.encoding_aes_key[:16]  # 初始向量

    def decrypt_message(self, encrypted_msg):
        """
        解密企业微信消息
        :param encrypted_msg: 加密的消息字符串
        :return: 解密后的XML字符串
        """
        if not encrypted_msg:
            return ""

        try:
            # Base64解码
            ciphertext = base64.b64decode(encrypted_msg)

            # AES解密
            cipher = AES.new(self.encoding_aes_key, AES.MODE_CBC, self.iv)
            decrypted = cipher.decrypt(ciphertext)

            # 去除补位
            plaintext = self._remove_padding(decrypted)

            # 验证消息长度
            if len(plaintext) < 16:
                raise ValueError("Invalid message length")

            # 提取消息内容
            content = plaintext[16:]  # 去除16字节随机字符串
            xml_len = struct.unpack(">I", content[:4])[0]  # 大端序读取长度
            xml_content = content[4:4 + xml_len]  # 获取XML内容
            from_corp_id = content[4 + xml_len:]  # 获取企业ID

            # 验证企业ID
            if from_corp_id.decode('utf-8') != self.corp_id:
                raise ValueError("CorpID mismatch")

            return xml_content.decode('utf-8')

        except Exception as e:
            print(f"解密失败: {str(e)}")
            return ""

    def _remove_padding(self, text):
        """去除PKCS#7补位"""
        pad = text[-1]
        if pad < 1 or pad > 32:
            pad = 0
        return text[:-pad]

    def verify_url(self, msg_signature, timestamp, nonce, echostr):
        """
        验证URL有效性（用于首次配置）
        :return: 成功返回解密后的echostr，失败返回空字符串
        """
        # 实际开发中需要验证签名，此处简化处理
        return self.decrypt_message(echostr)


def send_wechat_work_message_simple(to_user, content):
    """
    简单的企业微信消息发送函数
    这里只是一个占位符函数，你需要根据实际情况实现
    """
    try:
        # 这里可以添加实际的消息发送逻辑
        # 比如调用企业微信API发送消息
        print(f"发送消息给 {to_user}: {content}")

        # 可以记录到日志文件
        save_to_file('sent_messages.log', f"发送给 {to_user}:\n{content}")

        return True
    except Exception as e:
        print(f"发送消息失败: {str(e)}")
        save_to_file('error.log', f"发送消息失败: {str(e)}")
        return False


def update_memory_pricing(memory_id, price, user):
    """
    更新内存定价信息到 services/data/memory_update.json
    :param memory_id: 内存ID，如 MEM15220250605001
    :param price: 价格，如 1600
    :param user: 提供价格的用户，如 HeiHa
    """
    try:
        memory_file = 'services/data/memory_update.json'

        # 确保目录存在
        os.makedirs(os.path.dirname(memory_file), exist_ok=True)

        # 读取现有数据
        if os.path.exists(memory_file):
            try:
                with open(memory_file, 'r', encoding='utf-8') as f:
                    memory_data = json.load(f)
            except (json.JSONDecodeError, IOError):
                print(f"读取内存数据文件失败，使用空数据")
                memory_data = []
        else:
            print(f"内存数据文件不存在: {memory_file}")
            return False

        # 查找并更新对应的memory_id记录
        updated = False
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        for record in memory_data:
            if record.get('memory_id') == memory_id:
                # 更新价格信息
                record['pricing_info'] = {
                    "suggest_price": str(price),
                    "currency": "CNY",
                    "suggest_user": user,
                    "suggest_time": current_time
                }
                updated = True
                print(f"成功更新 {memory_id} 的价格信息: {price} CNY (提供者: {user})")
                break

        if not updated:
            print(f"未找到 memory_id: {memory_id} 的记录")
            return False

        # 保存更新后的数据
        with open(memory_file, 'w', encoding='utf-8') as f:
            json.dump(memory_data, f, ensure_ascii=False, indent=2)

        # 记录更新日志
        log_content = f"价格更新成功:\nMemory ID: {memory_id}\n价格: {price} CNY\n提供者: {user}\n时间: {current_time}"
        save_to_file('pricing_updates.log', log_content)

        return True

    except Exception as e:
        error_msg = f"更新内存价格失败: {str(e)}"
        print(error_msg)
        save_to_file('error.log', error_msg)
        return False


def parse_price_message(content, from_user):
    """
    解析价格回复消息
    支持格式: MEM15220250605001,1600 或类似格式
    :param content: 消息内容
    :param from_user: 发送用户
    :return: 是否成功解析并更新价格
    """
    try:
        # 正则匹配 MEM开头的ID和价格
        # 支持格式: MEM15220250605001,1600 或 MEM15220250605001，1600
        pattern = r'(MEM\d+)[,，]\s*(\d+)'
        match = re.search(pattern, content)

        if match:
            memory_id = match.group(1)
            price = match.group(2)

            print(f"检测到价格回复: Memory ID={memory_id}, Price={price}, User={from_user}")

            # 更新价格信息
            success = update_memory_pricing(memory_id, price, from_user)

            if success:
                # 发送确认消息
                confirm_msg = f"✅ 价格信息已更新\n内存ID: {memory_id}\n价格: {price} CNY\n感谢您的报价！"
                send_wechat_work_message_simple(to_user=from_user, content=confirm_msg)

            return success
        else:
            print(f"消息格式不匹配价格回复格式: {content}")
            return False

    except Exception as e:
        print(f"解析价格消息失败: {str(e)}")
        return False


# Flask 应用示例
app = Flask(__name__)

# 初始化加解密工具
crypt = WorkWeixinCrypt()


def save_to_file(filename, content):
    """将内容保存到文件"""
    try:
        # 确保logs目录存在
        if not os.path.exists('logs'):
            os.makedirs('logs')

        # 写入文件
        with open(f'logs/{filename}', 'a', encoding='utf-8') as f:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            f.write(f"\n\n===== {timestamp} =====\n")
            f.write(content)
    except Exception as e:
        print(f"保存文件失败: {str(e)}")


def save_chat_message(message_data):
    """将聊天消息保存到chat.json文件"""
    try:
        chat_file = 'chat.json'

        # 读取现有数据
        if os.path.exists(chat_file):
            try:
                with open(chat_file, 'r', encoding='utf-8') as f:
                    chat_history = json.load(f)
            except (json.JSONDecodeError, IOError):
                chat_history = []
        else:
            chat_history = []

        # 添加时间戳
        message_data['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        message_data['timestamp_unix'] = int(time.time())

        # 添加新消息
        chat_history.append(message_data)

        # 保存到文件（实时写入）
        with open(chat_file, 'w', encoding='utf-8') as f:
            json.dump(chat_history, f, ensure_ascii=False, indent=2)

        print(
            f"消息已实时保存到chat.json: {message_data.get('from_user', 'unknown')} -> {message_data.get('content', '')[:50]}...")

    except Exception as e:
        print(f"保存聊天消息失败: {str(e)}")


@app.route('/envom/maintain', methods=['GET', 'POST'])
def callback():
    """企业微信回调接口"""
    if request.method == 'GET':
        # URL验证
        msg_signature = request.args.get('msg_signature', '')
        timestamp = request.args.get('timestamp', '')
        nonce = request.args.get('nonce', '')
        echostr = request.args.get('echostr', '')

        # 记录请求信息
        request_info = f"GET 请求参数:\nmsg_signature: {msg_signature}\ntimestamp: {timestamp}\nnonce: {nonce}\nechostr: {echostr}"
        save_to_file('request.log', request_info)

        # 验证URL并返回echostr
        decrypted_echostr = crypt.verify_url(msg_signature, timestamp, nonce, echostr)

        # 记录解密结果
        if decrypted_echostr:
            save_to_file('decrypted.log', f"解密后的echostr:\n{decrypted_echostr}")
        else:
            save_to_file('decrypted.log', "echostr解密失败")

        return decrypted_echostr

    elif request.method == 'POST':
        # 处理消息
        encrypted_msg = request.data.decode('utf-8')

        # 记录请求信息
        request_info = f"POST 请求数据:\n{encrypted_msg}"
        save_to_file('request.log', request_info)

        try:
            root = ET.fromstring(encrypted_msg)

            # 查找Encrypt标签
            encrypt_element = root.find('Encrypt')

            if encrypt_element is not None:
                encrypt_data = encrypt_element.text
                save_to_file('request.log', encrypt_data)
                # 解密消息
                decrypted_xml = crypt.decrypt_message(encrypt_data)

                # 记录解密结果
                if decrypted_xml:
                    save_to_file('decrypted.log', f"解密后的XML:\n{decrypted_xml}")

                    # 解析XML
                    xml_root = ET.fromstring(decrypted_xml)
                    to_user = xml_root.find('ToUserName').text if xml_root.find('ToUserName') is not None else ''
                    from_user = xml_root.find('FromUserName').text if xml_root.find('FromUserName') is not None else ''
                    create_time = xml_root.find('CreateTime').text if xml_root.find('CreateTime') is not None else ''
                    msg_type = xml_root.find('MsgType').text if xml_root.find('MsgType') is not None else ''
                    content = xml_root.find('Content').text if xml_root.find('Content') is not None else ''
                    msg_id = xml_root.find('MsgId').text if xml_root.find('MsgId') is not None else ''
                    agent_id = xml_root.find('AgentID').text if xml_root.find('AgentID') is not None else ''

                    # 构造聊天消息数据（JSON格式）
                    chat_message = {
                        "to_user": to_user,
                        "from_user": from_user,
                        "create_time": create_time,
                        "create_time_formatted": datetime.fromtimestamp(int(create_time)).strftime(
                            '%Y-%m-%d %H:%M:%S') if create_time else '',
                        "msg_type": msg_type,
                        "content": content,
                        "msg_id": msg_id,
                        "agent_id": agent_id
                    }

                    # 实时保存到chat.json文件
                    save_chat_message(chat_message)

                    # 检查是否为价格回复消息
                    if from_user == "HeiHa" and parse_price_message(content, from_user):
                        print(f"成功处理来自 {from_user} 的价格回复")
                    else:
                        # 转换为markdown格式（保持原有功能）
                        md_content = f"""## 企业微信消息详情
- **接收方**: {to_user}
- **发送方**: {from_user}
- **时间**: {datetime.fromtimestamp(int(create_time)).strftime('%Y-%m-%d %H:%M:%S') if create_time else '未知'}
- **消息类型**: {msg_type}
- **内容**: {content}
- **消息ID**: {msg_id}
- **应用ID**: {agent_id}
"""

                        # 调用发送方法（修改目标用户为llm-aitachi）
                        send_wechat_work_message_simple(to_user="llm-aitachi", content=md_content)

                else:
                    save_to_file('decrypted.log', "消息解密失败")
        except Exception as e:
            error_msg = f"处理POST请求时发生错误: {str(e)}"
            print(error_msg)
            save_to_file('error.log', error_msg)

        return "success"


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8003, debug=True)