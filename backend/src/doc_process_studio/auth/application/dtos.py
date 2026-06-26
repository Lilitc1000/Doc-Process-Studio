"""认证应用层数据传输对象。

端口返回类型，供 application 服务和 router 层使用。
"""

from datetime import datetime

from pydantic import BaseModel, Field


class RegisterResponse(BaseModel):
    user_id: str = Field(..., description="用户标识")
    username: str = Field(..., description="用户名")
    created_at: datetime = Field(..., description="创建时间")


class TokenResponse(BaseModel):
    access_token: str = Field(..., description="访问令牌")
    refresh_token: str = Field(..., description="刷新令牌")
    token_type: str = Field(default="bearer", description="令牌类型")


class UserInfoResponse(BaseModel):
    user_id: str = Field(..., description="用户标识")
    username: str = Field(..., description="用户名")
    avatar_color: str = Field(..., description="头像背景色")
    created_at: datetime = Field(..., description="创建时间")


class UpdateProfileResponse(BaseModel):
    user_id: str = Field(..., description="用户标识")
    username: str = Field(..., description="用户名")
    avatar_color: str = Field(..., description="头像背景色")
    created_at: datetime = Field(..., description="创建时间")


class MessageResponse(BaseModel):
    message: str = Field(..., description="响应消息")
