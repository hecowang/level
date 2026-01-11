import os 
import markdown
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.header import Header

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
sender = str(os.environ.get("EMAIL_SENDER"))
sender = str(os.environ.get("EMAIL_SENDER"))
receiver = str(os.environ.get("EMAIL_RECEIVER"))
passwd = str(os.environ.get("EMAIL_PASSWD"))


def send_mail(subject, content):
    send_email_smtp(
        subject=subject,
        body=markdown.markdown(content),
        to_emails=[receiver],
        auth_code=passwd,
    )


def send_email_smtp(subject, body, to_emails, auth_code, attachments=None):
    """
    使用SMTP协议发送邮件。

    Args:
        subject (str): 邮件主题。
        body (str): 邮件正文，支持HTML格式。
        to_emails (list): 收件人邮箱地址列表。
        auth_code (str): 发件人邮箱的授权码。
        attachments (list, optional): 附件文件路径列表，默认为None。

    Returns:
        None

    Raises:
        Exception: 如果邮件发送失败，则抛出异常。
    """
    # 邮箱配置
    smtp_server = 'smtp.163.com'
    smtp_port = 465  # 使用 SSL
    sender_email = sender

    # 构建邮件
    msg = MIMEMultipart()
    msg['From'] = Header("量化机器人", 'utf-8')
    msg['To'] = Header(", ".join(to_emails), 'utf-8')
    msg['Subject'] = Header(subject, 'utf-8')

    # 邮件正文
    msg.attach(MIMEText(body, 'html', 'utf-8'))

    # 添加附件
    if attachments:
        for file_path in attachments:
            with open(file_path, 'rb') as f:
                part = MIMEApplication(f.read())
                part.add_header('Content-Disposition', 'attachment', filename=file_path.split('/')[-1])
                msg.attach(part)

    # 发送邮件
    try:
        with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
            server.login(sender_email, auth_code)
            server.sendmail(sender_email, to_emails, msg.as_string())
        print("📧 邮件发送成功")
    except Exception as e:
        print("❌ 邮件发送失败:", e)
