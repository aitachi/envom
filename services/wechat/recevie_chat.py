# -*- coding: utf-8 -*-
"""
企业微信消息加解密处理工具 - 增强版
增加了请求信息存储和解密信息存储功能
"""
import base64
from datetime import datetime 
import struct
import time
import os
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
        self.encoding_aes_key = base64.b64decode((encoding_aes_key or "ulKUK3i9wxVvTplM4C9KN8zE8mJJ7Rp1f2JwWmj8tEu") + "=")
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
            xml_content = content[4:4+xml_len]  # 获取XML内容
            from_corp_id = content[4+xml_len:]  # 获取企业ID
            
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
                    
                    # 转换为markdown格式
                    md_content = f"""## 企业微信消息详情
- **接收方**: {to_user}
- **发送方**: {from_user}
- **时间**: {datetime.fromtimestamp(int(create_time)).strftime('%Y-%m-%d %H:%M:%S') if create_time else '未知'}
- **消息类型**: {msg_type}
- **内容**: {content}
- **消息ID**: {msg_id}
- **应用ID**: {agent_id}
"""
                                                    
                    # 调用发送方法
                    send_wechat_work_message_simple(to_user="YuJian", content=md_content)
                    
                else:
                    save_to_file('decrypted.log', "消息解密失败")
        except Exception as e:
            error_msg = f"处理POST请求时发生错误: {str(e)}"
            print(error_msg)
            save_to_file('error.log', error_msg)
        
        return "success"
    
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8003, debug=True)
