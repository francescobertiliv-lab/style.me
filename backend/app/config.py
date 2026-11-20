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
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{DATA_DIR / 'app.db'}")
DB_SCHEMA = os.environ.get("DB_SCHEMA", "styleme")
PHOTOS_DIR = DATA_DIR / "photos"

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")
PASSWORD_HASH = os.environ.get("APP_PASSWORD_HASH", "")
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "0") == "1"

VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY", "")
VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY", "")
VAPID_SUBJECT = os.environ.get("VAPID_SUBJECT", "mailto:admin@localhost")

APP_URL = os.environ.get("APP_URL", "http://localhost:5173")


# Mail con Resend, come LAURUS (canale principale degli avvisi)
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
EMAIL_FROM = os.environ.get("EMAIL_FROM", "")
MAIL_TO = os.environ.get("MAIL_TO", "")

# Foto su Supabase Storage. Se mancano, le foto restano in DATA_DIR/photos.
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
SUPABASE_BUCKET = os.environ.get("SUPABASE_BUCKET", "styleme")

# Segreto che il cron deve mandare per avviare i lavori pianificati
CRON_SECRET = os.environ.get("CRON_SECRET", "")
