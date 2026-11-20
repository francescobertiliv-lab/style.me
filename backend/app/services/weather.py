"""Meteo da Open-Meteo (gratis, senza chiave), con cache in SQLite."""
import json
from datetime import date, datetime

import httpx

from ..db import get_setting

URL = "https://api.open-meteo.com/v1/forecast"

# Codici WMO principali, in italiano
CODES = {
    0: "sereno", 1: "quasi sereno", 2: "poco nuvoloso", 3: "nuvoloso",
    45: "nebbia", 48: "nebbia", 51: "pioviggine", 53: "pioviggine", 55: "pioviggine",
    61: "pioggia debole", 63: "pioggia", 65: "pioggia forte", 66: "pioggia gelata", 67: "pioggia gelata",
    71: "neve debole", 73: "neve", 75: "neve forte", 77: "neve", 80: "rovesci", 81: "rovesci",
    82: "rovesci forti", 85: "neve", 86: "neve", 95: "temporale", 96: "temporale", 99: "temporale",
}


def _key(lat: float, lon: float) -> tuple[float, float]:
    return round(lat, 2), round(lon, 2)


def forecast(conn, lat: float, lon: float, day: date, timeout: float = 10.0) -> dict:
    """Ritorna il meteo del giorno. Se Open-Meteo non risponde: ok=False e regole di base."""
    lat, lon = _key(lat, lon)
    cached = conn.execute(
        "SELECT data, fetched_at FROM weather_cache WHERE lat=? AND lon=? AND date=?",
        (lat, lon, day.isoformat()),
    ).fetchone()
    if cached and (datetime.now() - datetime.fromisoformat(cached["fetched_at"])).total_seconds() < 3 * 3600:
        return json.loads(cached["data"])

    tz = get_setting(conn, "timezone", "Europe/Brussels")
    try:
        resp = httpx.get(
            URL,
            params={
                "latitude": lat, "longitude": lon, "timezone": tz,
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,"
                         "precipitation_probability_max,weather_code,wind_speed_10m_max",
                "start_date": day.isoformat(), "end_date": day.isoformat(),
            },
            timeout=timeout,
        )
        resp.raise_for_status()
        d = resp.json()["daily"]
        data = {
            "ok": True,
            "tmax": d["temperature_2m_max"][0],
            "tmin": d["temperature_2m_min"][0],
            "rain_mm": d["precipitation_sum"][0] or 0.0,
            "rain_prob": d["precipitation_probability_max"][0] or 0,
            "wind": d["wind_speed_10m_max"][0],
            "code": d["weather_code"][0],
        }
        data["summary"] = CODES.get(data["code"], "")
    except Exception as exc:
        if cached:  # meglio una previsione vecchia che niente
            data = json.loads(cached["data"])
            data["stale"] = True
            return data
        return {"ok": False, "message": f"meteo non disponibile ({type(exc).__name__})"}

    conn.execute(
        "INSERT INTO weather_cache(lat, lon, date, data, fetched_at) VALUES (?,?,?,?,?) "
        "ON CONFLICT(lat, lon, date) DO UPDATE SET data=excluded.data, fetched_at=excluded.fetched_at",
        (lat, lon, day.isoformat(), json.dumps(data), datetime.now().isoformat(timespec="seconds")),
    )
    return data


def is_rainy(conn, w: dict) -> bool:
    if not w.get("ok"):
        return False
    r = get_setting(conn, "rain", {"mm": 1.0, "probability": 60})
    return w["rain_mm"] >= r["mm"] or w["rain_prob"] >= r["probability"]


def describe(w: dict) -> str:
    if not w.get("ok"):
        return w.get("message", "meteo non disponibile")
    s = f"{round(w['tmin'])}–{round(w['tmax'])}°, {w['summary']}"
    if w.get("rain_prob"):
        s += f", pioggia {w['rain_prob']}%"
    if w.get("stale"):
        s += " (previsione non aggiornata)"
    return s
