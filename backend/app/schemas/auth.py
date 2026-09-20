from pydantic import BaseModel, ConfigDict


class UserBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    avatar_url: str | None = None
    role: str
    status: str


class UserProfile(UserBase):
    openid: str | None = None
    phone: str | None = None
    verified_phone: str | None = None
    wechat_id: str | None = None
    email: str | None = None
    bio: str | None = None


class LoginRequest(BaseModel):
    # value returned by wx.login()
    code: str
    # Separate, one-use code returned by the getPhoneNumber button.
    phone_code: str | None = None


class DevImpersonateRequest(BaseModel):
    user_id: int


class LoginResult(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    user: UserProfile


class DevUserOut(BaseModel):
    id: int
    name: str
    role: str
    org_path: str = ""
