"""Dove stanno le foto: cartella locale in sviluppo, Supabase Storage online."""
import httpx

from .. import config


def _supabase() -> bool:
    return bool(config.SUPABASE_URL and config.SUPABASE_SERVICE_KEY)


def _headers(content_type: str | None = None) -> dict:
    h = {"Authorization": f"Bearer {config.SUPABASE_SERVICE_KEY}", "apikey": config.SUPABASE_SERVICE_KEY}
    if content_type:
        h["Content-Type"] = content_type
    return h


def put(path: str, data: bytes, content_type: str) -> str:
    if _supabase():
        r = httpx.post(f"{config.SUPABASE_URL}/storage/v1/object/{config.SUPABASE_BUCKET}/{path}",
                       content=data, headers={**_headers(content_type), "x-upsert": "true"}, timeout=30)
        r.raise_for_status()
    else:
        full = config.PHOTOS_DIR / path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_bytes(data)
    return path


def get(path: str) -> bytes | None:
    if _supabase():
        r = httpx.get(f"{config.SUPABASE_URL}/storage/v1/object/{config.SUPABASE_BUCKET}/{path}",
                      headers=_headers(), timeout=30)
        return r.content if r.status_code == 200 else None
    full = config.PHOTOS_DIR / path
    return full.read_bytes() if full.exists() else None


def signed_url(path: str, seconds: int = 3600) -> str | None:
    """Link temporaneo alla foto (solo Supabase). In locale ritorna None."""
    if not _supabase():
        return None
    r = httpx.post(f"{config.SUPABASE_URL}/storage/v1/object/sign/{config.SUPABASE_BUCKET}/{path}",
                   json={"expiresIn": seconds}, headers=_headers("application/json"), timeout=15)
    r.raise_for_status()
    return f"{config.SUPABASE_URL}/storage/v1{r.json()['signedURL']}"


def delete(path: str) -> None:
    if _supabase():
        httpx.request("DELETE", f"{config.SUPABASE_URL}/storage/v1/object/{config.SUPABASE_BUCKET}",
                      json={"prefixes": [path]}, headers=_headers("application/json"), timeout=15)
    else:
        (config.PHOTOS_DIR / path).unlink(missing_ok=True)
