"""Style.me: API FastAPI. In locale: uvicorn app.main:app --reload"""
from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from . import auth, config, db
from .routers import days, kits, style, system, trips, wardrobe

app = FastAPI(title="Style.me", docs_url="/api/docs", openapi_url="/api/openapi.json")
app.add_middleware(SessionMiddleware, secret_key=config.SECRET_KEY, session_cookie="styleme",
                   max_age=60 * 60 * 24 * 180, same_site="lax", https_only=config.COOKIE_SECURE)

for r in (auth.router, days.router, wardrobe.router, trips.router, kits.router, style.router,
          system.router, system.cron):
    app.include_router(r)

_ready = False


@app.middleware("http")
async def ensure_db(request, call_next):
    """Crea il database alla prima richiesta (anche su Vercel, dove non c'è un avvio vero)."""
    global _ready
    if not _ready:
        if not config.SUPABASE_URL:
            config.PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
        db.init_db()
        _ready = True
    return await call_next(request)


@app.get("/api/health")
def health():
    return {"ok": True}
