from threading import Lock
from time import monotonic

import httpx
from fastapi import HTTPException

from app.core.config import settings

_lock = Lock()
_token = ""
_expires_at = 0.0


def _access_token() -> str:
    global _token, _expires_at
    with _lock:
        if monotonic() < _expires_at:
            return _token
        response = httpx.post(
            "https://api.weixin.qq.com/cgi-bin/stable_token",
            json={
                "grant_type": "client_credential",
                "appid": settings.wechat_appid,
                "secret": settings.wechat_secret,
            },
            timeout=5,
        )
        response.raise_for_status()
        body = response.json()
        _token = body["access_token"]
        _expires_at = monotonic() + max(0, int(body["expires_in"]) - 60)
        return _token


def check_alumni_message(openid: str | None, message: str) -> None:
    if not message or (settings.is_dev and settings.wechat_mock_login):
        return
    if not openid or not settings.wechat_appid or not settings.wechat_secret:
        raise HTTPException(503, "文字审核暂不可用，请稍后重试")
    try:
        response = httpx.post(
            "https://api.weixin.qq.com/wxa/msg_sec_check",
            params={"access_token": _access_token()},
            json={"content": message, "openid": openid, "scene": 2, "version": 2},
            timeout=5,
        )
        response.raise_for_status()
        body = response.json()
        if body.get("errcode") == 87014:
            raise HTTPException(422, "留言未通过审核，请修改后重试")
        if body.get("errcode") != 0:
            raise ValueError("WeChat content check returned an error")
        decision = body["result"]["suggest"]
    except (httpx.HTTPError, KeyError, TypeError, ValueError):
        raise HTTPException(503, "文字审核暂不可用，请稍后重试") from None
    if decision != "pass":
        raise HTTPException(422, "留言未通过审核，请修改后重试")
