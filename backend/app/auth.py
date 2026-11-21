"""Login per un solo utente: password con hash scrypt nel .env, sessione in un cookie firmato."""
import base64
import hashlib
import hmac
import os
import time

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from . import config
from .db import get_db, get_setting, set_setting

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


def stored_hash(db) -> str:
    """La password scelta al primo avvio (nel database) o, se c'è, quella del .env."""
    return config.PASSWORD_HASH or get_setting(db, "password_hash", "") or ""


@router.post("/login")
def login(body: Login, request: Request, db=Depends(get_db)):
    h = stored_hash(db)
    if not h or not verify(body.password, h):
        time.sleep(1)  # rallenta i tentativi a caso
        raise HTTPException(401, "Password sbagliata")
    request.session["user"] = "me"
    return {"ok": True}


@router.post("/setup")
def setup(body: Login, request: Request, db=Depends(get_db)):
    """Primo avvio: scelgo la password. Funziona una volta sola."""
    if stored_hash(db):
        raise HTTPException(409, "La password esiste già")
    if len(body.password) < 8:
        raise HTTPException(400, "Almeno 8 caratteri")
    set_setting(db, "password_hash", hash_password(body.password))
    request.session["user"] = "me"
    return {"ok": True}


@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return {"ok": True}


@router.get("/me")
def me(request: Request, db=Depends(get_db)):
    return {"logged_in": bool(request.session.get("user")), "needs_setup": not stored_hash(db),
            "onboarded": bool(get_setting(db, "onboarded", False))}
