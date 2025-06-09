import requests
import json


def send_wechat_work_message(corp_id, corp_secret, agent_id, to_user, content):
    """
    发送企业微信消息

    参数:
    - corp_id: 企业ID
    - corp_secret: 应用Secret
    - agent_id: 应用ID
    - to_user: 接收消息的用户ID，多个用|分隔
    - content: 消息内容
    """

    # 1. 获取access_token
    token_url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={corp_id}&corpsecret={corp_secret}"
    response = requests.get(token_url)
    access_token = response.json().get('access_token')

    if not access_token:
        print("获取access_token失败")
        return False

    # 2. 发送消息
    send_url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"

    data = {
        "touser": to_user,
        "msgtype": "text",
        "agentid": agent_id,
        "text": {
            "content": content
        },
        "safe": 0
    }

    response = requests.post(send_url, data=json.dumps(data))
    result = response.json()

    if result.get('errcode') == 0:
        print("消息发送成功")
        return True
    else:
        print(f"消息发送失败: {result.get('errmsg')}")
        return False


def send_wechat_work_message_simple(to_user, content):
    CORP_ID = "ww568874482f006b53"
    CORP_SECRET = "zJM1d6Ljk86fiK4WUptdi4gmA7Gj0RkaHDYiFW6wM8g"
    AGENT_ID = "1000008"
    send_wechat_work_message(CORP_ID, CORP_SECRET, AGENT_ID, to_user, content)

    # 使用示例


if __name__ == "__main__":
    #     # 替换为你的企业微信配置
    CORP_ID = "ww568874482f006b53"
    CORP_SECRET = "zJM1d6Ljk86fiK4WUptdi4gmA7Gj0RkaHDYiFW6wM8g"
    AGENT_ID = "1000008"

    #     # 接收消息的用户ID（企业微信中的用户账号）
    TO_USER = "llm-aitachi"  # 或者使用用户ID如"XiaoMing"

    #     # 消息内容
    MESSAGE_CONTENT = "1+1=2"

    #     # 发送消息
    send_wechat_work_message(CORP_ID, CORP_SECRET, AGENT_ID, TO_USER, MESSAGE_CONTENT)
