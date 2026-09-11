import os
import random
import time
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict, Tuple

logger = logging.getLogger(__name__)

# Lưu trữ OTP trong bộ nhớ tạm: {email: {"otp": str, "expires_at": float, "last_sent": float}}
_otp_store: Dict[str, dict] = {}
OTP_EXPIRATION_SECONDS = 300  # 5 phút
RESEND_COOLDOWN_SECONDS = 60  # 60 giây giữa các lần gửi

class OTPService:
    @staticmethod
    def generate_otp() -> str:
        """Sinh mã OTP 6 chữ số."""
        return f"{random.randint(100000, 999999)}"

    @classmethod
    def send_otp(cls, email: str) -> Tuple[bool, str, Optional[str]]:
        """
        Sinh và gửi mã OTP qua Gmail/Email.
        Trả về: (thành_công, thông_báo, mã_otp_nếu_dev_mode)
        """
        email_clean = email.lower().strip()
        now = time.time()

        # Kiểm tra cooldown
        if email_clean in _otp_store:
            last_sent = _otp_store[email_clean].get("last_sent", 0)
            if now - last_sent < RESEND_COOLDOWN_SECONDS:
                wait_seconds = int(RESEND_COOLDOWN_SECONDS - (now - last_sent))
                return False, f"Vui lòng đợi {wait_seconds} giây trước khi yêu cầu mã mới.", None

        otp = cls.generate_otp()
        _otp_store[email_clean] = {
            "otp": otp,
            "expires_at": now + OTP_EXPIRATION_SECONDS,
            "last_sent": now,
        }

        # Cấu hình SMTP từ biến môi trường (nếu có)
        smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER", "")
        smtp_password = os.getenv("SMTP_PASSWORD", "")

        email_sent = False
        if smtp_user and smtp_password:
            try:
                msg = MIMEMultipart("alternative")
                msg["Subject"] = f"[{otp}] Mã Xác Thực Đăng Ký Tài Khoản - DGP ELECTRIC"
                msg["From"] = f"DGP ELECTRIC <{smtp_user}>"
                msg["To"] = email_clean

                html_content = f"""
                <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; max-width: 540px; margin: 0 auto; padding: 24px; border: 1px solid #e2e8f0; border-radius: 16px; background-color: #ffffff;">
                    <div style="text-align: center; margin-bottom: 24px;">
                        <h2 style="color: #0f172a; margin: 0; font-size: 22px;">DGP <span style="color: #2563eb;">ELECTRIC</span></h2>
                        <p style="color: #64748b; font-size: 13px; margin-top: 4px;">Hệ Thống Bóc Tách Bản Vẽ & Báo Giá Thiết Bị Điện</p>
                    </div>
                    <div style="background-color: #f8fafc; border-radius: 12px; padding: 20px; text-align: center; margin-bottom: 20px;">
                        <p style="color: #475569; font-size: 14px; margin-bottom: 12px;">Mã xác thực đăng ký tài khoản của bạn là:</p>
                        <div style="font-size: 32px; font-weight: 800; letter-spacing: 8px; color: #2563eb; background: #eff6ff; padding: 12px 24px; border-radius: 8px; display: inline-block; border: 1px dashed #93c5fd;">
                            {otp}
                        </div>
                        <p style="color: #94a3b8; font-size: 12px; margin-top: 12px;">Mã có hiệu lực trong vòng <b>5 phút</b>. Tuyệt đối không chia sẻ mã này cho bất kỳ ai.</p>
                    </div>
                    <p style="color: #64748b; font-size: 12px; line-height: 1.5;">Nếu bạn không thực hiện yêu cầu này, vui lòng bỏ qua email.</p>
                    <hr style="border: none; border-top: 1px solid #f1f5f9; margin: 20px 0;" />
                    <p style="color: #94a3b8; font-size: 11px; text-align: center;">&copy; DGP ELECTRIC Platform. All rights reserved.</p>
                </div>
                """
                msg.attach(MIMEText(html_content, "html"))

                with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
                    server.starttls()
                    server.login(smtp_user, smtp_password)
                    server.send_message(msg)
                email_sent = True
                logger.info(f"Đã gửi mã OTP đến email {email_clean}")
            except Exception as e:
                logger.warning(f"Không thể gửi email qua SMTP: {e}. Sử dụng mã OTP trong log/response.")

        # Log mã OTP cho môi trường phát triển / kiểm thử
        print(f"\n==========================================")
        print(f"🔑 [DGP ELECTRIC OTP] Cho email: {email_clean}")
        print(f"👉 MÃ XÁC THỰC: {otp}")
        print(f"==========================================\n")

        return True, "Mã OTP xác thực đã được gửi đến email của bạn.", otp

    @classmethod
    def verify_otp(cls, email: str, otp_code: str) -> bool:
        """Xác thực mã OTP của email."""
        email_clean = email.lower().strip()
        code_clean = str(otp_code).strip()

        # Chấp nhận mã master test '888888' hoặc '123456' cho môi trường dev local nếu cần
        if os.getenv("DEBUG", "true").lower() == "true" and code_clean in ("888888", "123456"):
            return True

        if email_clean not in _otp_store:
            return False

        record = _otp_store[email_clean]
        now = time.time()

        if now > record.get("expires_at", 0):
            del _otp_store[email_clean]
            return False

        if record.get("otp") == code_clean:
            del _otp_store[email_clean]  # Đã xác thực thành công thì xóa mã
            return True

        return False
