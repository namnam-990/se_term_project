"""메일 어댑터 — 설계서 'Clock·메일/QR 분리로 Mock 검증'. 테스트에서는 FakeMailSender로 교체."""

import logging
import smtplib
from email.message import EmailMessage

from app.core.config import get_settings

log = logging.getLogger("lsrs.mail")


class MailSender:
    def send(self, to: str, subject: str, body: str) -> None:
        raise NotImplementedError


class ConsoleMailSender(MailSender):
    """로컬 개발용: 실제 발송 대신 서버 콘솔에 출력."""

    def send(self, to: str, subject: str, body: str) -> None:
        log.warning("[MAIL] to=%s | %s\n%s", to, subject, body)
        print(f"\n===== [MAIL to {to}] {subject} =====\n{body}\n", flush=True)


class SmtpMailSender(MailSender):
    def send(self, to: str, subject: str, body: str) -> None:
        s = get_settings()
        msg = EmailMessage()
        msg["From"], msg["To"], msg["Subject"] = s.mail_from, to, subject
        msg.set_content(body)
        with smtplib.SMTP(s.smtp_host, s.smtp_port) as smtp:
            smtp.starttls()
            smtp.login(s.smtp_user, s.smtp_password)
            smtp.send_message(msg)


class FakeMailSender(MailSender):
    """테스트용: 보낸 메일을 리스트에 저장."""

    def __init__(self):
        self.sent: list[dict] = []

    def send(self, to: str, subject: str, body: str) -> None:
        self.sent.append({"to": to, "subject": subject, "body": body})


def get_mail_sender() -> MailSender:
    return SmtpMailSender() if get_settings().mail_backend == "smtp" else ConsoleMailSender()
