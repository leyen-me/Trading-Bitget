import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import Config
from lib.MyFlask import get_current_app

def send_email(subject: str, body: str):
    smtp_user = Config.MSG_SMTP_USERNAME
    smtp_pass = Config.MSG_SMTP_PASSWORD

    if not smtp_user or not smtp_pass:
        get_current_app().logger.error("SMTP 凭据未配置")
        return

    msg = MIMEMultipart()
    msg["From"] = smtp_user
    msg["To"] = smtp_user
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "plain"))

    try:
        server = smtplib.SMTP_SSL("smtp.qq.com", 465)
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, smtp_user, msg.as_string())
        server.quit()
        get_current_app().logger.info("📧 邮件发送成功")
    except Exception as e:
        get_current_app().logger.error(f"📧 邮件发送失败: {e}")


def send_to_qq_group(message, group_id, api_url, token, timeout=10):
    """
    向指定 QQ 群发送消息（通过支持 Bearer 认证的 HTTP API，如 go-cqhttp）

    :param message: 要发送的消息内容 (str 或 list)
    :param group_id: 目标群号 (int 或 str)
    :param api_url: go-cqhttp 或 Mirai 的 HTTP API 地址，例如 "http://127.0.0.1:5700/send_group_msg"
    :param token: Bearer Token（如果 API 需要认证）
    :param timeout: 请求超时时间（秒）
    :return: 成功返回响应 JSON，失败返回 None
    """
    payload = {
        "group_id": f"{group_id}",
        "message": [{"type": "text", "data": {"text": str(message)}}],
    }

    # 设置请求头
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    try:
        response = requests.post(
            url=api_url + "/send_group_msg",
            json=payload,
            headers=headers,
            timeout=timeout,
        )

        # 检查状态码
        if response.status_code == 200:
            result = response.json()
            # 可根据实际 API 判断 'status' 字段是否成功
            if result.get("status") == "ok":
                # print(f"✅ 成功发送消息到群 {group_id}: {message}")
                return result
            else:
                print(f"❌ API 返回错误: {result}")
        else:
            print(f"❌ 请求失败，HTTP 状态码: {response.status_code}")
            print(f"响应内容: {response.text}")

    except requests.exceptions.Timeout:
        print("⏰ 请求超时，请检查网络或调整 timeout 参数")
    except requests.exceptions.ConnectionError:
        print("🔌 连接失败，请确认 API 服务已启动且地址正确")
    except Exception as e:
        print(f"💥 发生未知错误: {e}")

    return None


def send_text(subject: str, body: str, enable_email=True, enable_qq=True):
    if Config.ENABLE_EMAIL_MSG and enable_email:
        send_email(subject, body)
    if Config.ENABLE_QQ_MSG and enable_qq:
        send_to_qq_group(
            message=body,
            group_id=Config.MSG_QQ_GROUP_ID,
            api_url=Config.MSG_QQ_BASE_URL,
            token=Config.MSG_QQ_TOKEN,
        )