"""Fernet 对称加密工具，用于加密存储用户的 AI API Key"""

from cryptography.fernet import Fernet
import base64
import hashlib

from app.core.config import settings


def _get_fernet() -> Fernet:
    """从配置的 ENCRYPTION_KEY 生成 Fernet 实例"""
    key = hashlib.sha256(settings.ENCRYPTION_KEY.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def encrypt_api_key(plain_text: str) -> str:
    """加密 API Key"""
    f = _get_fernet()
    return f.encrypt(plain_text.encode()).decode()


def decrypt_api_key(encrypted_text: str) -> str:
    """解密 API Key"""
    f = _get_fernet()
    return f.decrypt(encrypted_text.encode()).decode()