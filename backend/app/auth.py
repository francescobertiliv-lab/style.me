"""Login per un solo utente: password con hash scrypt nel .env, sessione in un cookie firmato."""
import base64
import hashlib
import hmac
import os
import time

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from . import config

router = APIRouter(prefix="/api/auth")


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return f"scrypt${base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}"


def verify(password: str, stored: str) -> bool:
    try:
        _, salt, digest = stored.split("$")
        calc = hashlib.scrypt(password.encode(), salt=base64.b64decode(salt), n=2**14, r=8, p=1)
        return hmac.compare_digest(calc, base64.b64decode(digest))
    except ValueError:
        return False


def require_user(request: Request) -> None:
    """Dipendenza: blocca chi non ha fatto login."""
    if not request.session.get("user"):
        raise HTTPException(401, "Fai login")


class Login(BaseModel):
    password: str


@router.post("/login")
def login(body: Login, request: Request):
    if not config.PASSWORD_HASH or not verify(body.password, config.PASSWORD_HASH):
        time.sleep(1)  # rallenta i tentativi a caso
        raise HTTPException(401, "Password sbagliata")
    request.session["user"] = "me"
    return {"ok": True}


@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return {"ok": True}


@router.get("/me")
def me(request: Request):
    return {"logged_in": bool(request.session.get("user"))}
