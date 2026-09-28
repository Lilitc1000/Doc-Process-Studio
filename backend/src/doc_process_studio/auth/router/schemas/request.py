from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=20)
    password: str = Field(..., min_length=6)


class SetupAdminRequest(RegisterRequest):
    """首个管理员创建请求。

    校验规则刻意与普通注册完全一致（继承 RegisterRequest），
    差别只在服务端语义：仅当系统中不存在任何全局管理员时可用。
    """


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., min_length=1)


class UpdateProfileRequest(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=20)
    avatar_color: str | None = Field(default=None, min_length=7, max_length=7)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=6)


class LogoutRequest(BaseModel):
    refresh_token: str = Field(..., min_length=1)
