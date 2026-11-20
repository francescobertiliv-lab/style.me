"""Impostazioni da variabili d'ambiente (file .env)."""
import os
from pathlib import Path


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


BASE_DIR = Path(__file__).resolve().parent.parent
_load_dotenv(BASE_DIR.parent / ".env")

DATA_DIR = Path(os.environ.get("DATA_DIR", BASE_DIR / "data"))
DB_PATH = DATA_DIR / "app.db"
PHOTOS_DIR = DATA_DIR / "photos"

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")
PASSWORD_HASH = os.environ.get("APP_PASSWORD_HASH", "")
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "0") == "1"

VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY", "")
VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY", "")
VAPID_SUBJECT = os.environ.get("VAPID_SUBJECT", "mailto:admin@localhost")

APP_URL = os.environ.get("APP_URL", "http://localhost:5173")
RUN_SCHEDULER = os.environ.get("RUN_SCHEDULER", "1") == "1"

for sub in ("originals", "cutouts", "outfits", "models"):
    (PHOTOS_DIR / sub).mkdir(parents=True, exist_ok=True)

# Mail (canale principale degli avvisi). Va bene qualunque SMTP: Gmail con password per app, Resend, ecc.
SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
MAIL_FROM = os.environ.get("MAIL_FROM", "")
MAIL_TO = os.environ.get("MAIL_TO", "")
