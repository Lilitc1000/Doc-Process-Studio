"""认证应用层数据传输对象。

端口返回类型，供 application 服务和 router 层使用。
"""

from datetime import datetime

from pydantic import BaseModel, Field

from ..domain.roles import ROLE_MEMBER


class RegisterResponse(BaseModel):
    user_id: str = Field(..., description="用户标识")
    username: str = Field(..., description="用户名")
    created_at: datetime = Field(..., description="创建时间")


class TokenResponse(BaseModel):
    access_token: str = Field(..., description="访问令牌")
    refresh_token: str = Field(..., description="刷新令牌")


class UserInfoResponse(BaseModel):
    user_id: str = Field(..., description="用户标识")
    username: str = Field(..., description="用户名")
    avatar_color: str = Field(..., description="头像背景色")
    role: str = Field(default=ROLE_MEMBER, description="全局角色：admin / member")
    created_at: datetime = Field(..., description="创建时间")


class UpdateProfileResponse(BaseModel):
    """资料更新结果。

    刻意不含 ``role``：角色不通过"改资料"这条路径变更，也不该被前端顺手改写。
    前端更新资料后如需刷新角色，重新拉一次 ``GET /api/auth/me`` 即可。
    """

    user_id: str = Field(..., description="用户标识")
    username: str = Field(..., description="用户名")
    avatar_color: str = Field(..., description="头像背景色")
    created_at: datetime = Field(..., description="创建时间")


class MessageResponse(BaseModel):
    message: str = Field(..., description="响应消息")
