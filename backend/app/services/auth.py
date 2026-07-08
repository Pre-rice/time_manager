"""认证业务逻辑"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest
from app.core.security import hash_password, verify_password, create_access_token


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register(self, req: RegisterRequest) -> User:
        """注册新用户"""
        # 检查用户名/邮箱是否已存在
        result = await self.db.execute(
            select(User).where(
                (User.username == req.username) | (User.email == req.email)
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            raise ValueError("用户名或邮箱已存在")

        user = User(
            username=req.username,
            email=req.email,
            hashed_password=hash_password(req.password),
        )
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def login(self, req: LoginRequest) -> tuple[str, User]:
        """登录，返回 (token, user)"""
        result = await self.db.execute(
            select(User).where(User.username == req.username)
        )
        user = result.scalar_one_or_none()
        if not user or not verify_password(req.password, user.hashed_password):
            raise ValueError("用户名或密码错误")
        if not user.is_active:
            raise ValueError("账号已被禁用")

        token = create_access_token({"sub": str(user.id), "username": user.username})
        return token, user