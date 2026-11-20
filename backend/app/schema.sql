PRAGMA foreign_keys = ON;

-- ============ BASE ============

-- Impostazioni modificabili dall'app (valore in JSON).
-- Chiavi previste: notify_time, timezone, trip_alert_days, the361_url,
-- home_city_id. Password e chiavi VAPID stanno nel file .env, non qui.
CREATE TABLE settings (
  key   TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

-- Luoghi dove tengo vestiti e da cui prendo il meteo.
CREATE TABLE cities (
  id      INTEGER PRIMARY KEY,
  name    TEXT NOT NULL UNIQUE,          -- Evere/Bruxelles, Strasburgo, Italia
  lat     REAL NOT NULL,
  lon     REAL NOT NULL,
  country TEXT NOT NULL,                 -- codice ISO a 2 lettere
  is_home INTEGER NOT NULL DEFAULT 0
);

-- ============ SEZIONE 1: GUARDAROBA ============

-- Categorie modificabili. slot = posto del capo nell'outfit.
CREATE TABLE categories (
  id          INTEGER PRIMARY KEY,
  name        TEXT NOT NULL UNIQUE,      -- camicia, cravatta, chino, giacca completo...
  slot        TEXT NOT NULL CHECK (slot IN
              ('capospalla','giacca','strato','top','sotto','scarpe','cravatta','accessorio')),
  repeat_days INTEGER,                   -- giorni prima di riproporre lo stesso capo (NULL = nessun limite)
  default_formality INTEGER NOT NULL DEFAULT 3,
  default_weight    INTEGER NOT NULL DEFAULT 2,
  sort        INTEGER NOT NULL DEFAULT 0
);

-- Famiglie di colore: servono a regole, palette e grafico.
CREATE TABLE color_families (
  name  TEXT PRIMARY KEY,                -- navy, cammello, ruggine, bordeaux, nero...
  hex   TEXT NOT NULL,                   -- colore di riferimento
  tone  TEXT NOT NULL CHECK (tone IN ('neutro','caldo','freddo')),
  depth TEXT NOT NULL CHECK (depth IN ('chiaro','medio','scuro'))
);

CREATE TABLE garments (
  id           INTEGER PRIMARY KEY,
  name         TEXT NOT NULL,
  category_id  INTEGER NOT NULL REFERENCES categories(id),
  set_key      TEXT,                     -- lega giacca e pantalone dello stesso completo
  color_hex    TEXT NOT NULL,            -- colore principale estratto dalla foto
  color_family TEXT NOT NULL REFERENCES color_families(name),
  colors       TEXT NOT NULL DEFAULT '[]', -- JSON: colori dominanti [{hex, quota}]
  pattern      TEXT NOT NULL DEFAULT 'tinta unita', -- righe, quadri, gessato, regimental, pois, fantasia
  formality    INTEGER NOT NULL CHECK (formality BETWEEN 1 AND 5), -- 1 sportivo, 5 completo scuro
  weight       INTEGER NOT NULL CHECK (weight BETWEEN 1 AND 3),    -- 1 leggero, 2 medio, 3 pesante
  material     TEXT,                     -- lana, cotone, lino, pelle, scamosciato...
  rain_ok      INTEGER NOT NULL DEFAULT 1, -- 0 = da evitare con la pioggia (scamosciato)
  rain_gear    INTEGER NOT NULL DEFAULT 0, -- 1 = cappotto o impermeabile da pioggia
  size         TEXT,
  brand        TEXT,
  price_eur    REAL,
  bought_on    TEXT,
  status       TEXT NOT NULL DEFAULT 'pulito' CHECK (status IN
               ('pulito','da_lavare','tintoria','valigia','sarta')),
  city_id      INTEGER NOT NULL REFERENCES cities(id),
  photo        TEXT NOT NULL,            -- foto originale
  cutout       TEXT,                     -- PNG scontornato
  model_glb    TEXT,                     -- fase 2, facoltativo
  model_status TEXT CHECK (model_status IN ('in_coda','pronto','fallito')),
  notes        TEXT,
  archived     INTEGER NOT NULL DEFAULT 0,
  created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX garments_available ON garments(status, city_id) WHERE archived = 0;

-- Settimane del PE prese da the361 (cache: se the361 non risponde uso l'ultima copia).
CREATE TABLE ep_weeks (
  week_start TEXT PRIMARY KEY,           -- lunedì, AAAA-MM-GG
  week_type  TEXT NOT NULL,              -- come the361: green, group, committee, plenary, plenary-brussels, recess
  place      TEXT,
  raw        TEXT,                       -- risposta originale in JSON
  fetched_at TEXT NOT NULL
);

-- Festivi del PE (da the361): giorno libero.
CREATE TABLE ep_holidays (
  date TEXT PRIMARY KEY
);

-- Dress code per tipo di settimana e giorno: modificabile, non nel codice.
CREATE TABLE dress_rules (
  week_type  TEXT NOT NULL,              -- committee, group, green, plenary, plenary-brussels, recess
  weekday    INTEGER NOT NULL CHECK (weekday BETWEEN 0 AND 6), -- 0 = lunedì
  dress_code TEXT NOT NULL CHECK (dress_code IN ('completo','informale','libero')),
  PRIMARY KEY (week_type, weekday)
);

-- Giorni forzati a mano ("non vado in ufficio", "evento formale").
CREATE TABLE day_overrides (
  date       TEXT PRIMARY KEY,
  dress_code TEXT NOT NULL CHECK (dress_code IN ('completo','informale','libero')),
  note       TEXT
);

CREATE TABLE weather_cache (
  lat        REAL NOT NULL,              -- arrotondati a 2 decimali
  lon        REAL NOT NULL,
  date       TEXT NOT NULL,
  data       TEXT NOT NULL,              -- JSON: min, max, pioggia, vento
  fetched_at TEXT NOT NULL,
  PRIMARY KEY (lat, lon, date)
);

-- ============ SEZIONE 2: VIAGGI E VALIGIE ============

CREATE TABLE trip_templates (
  id            INTEGER PRIMARY KEY,
  name          TEXT NOT NULL UNIQUE,    -- Plenaria Strasburgo, Italia, Missione estero
  from_calendar INTEGER NOT NULL DEFAULT 0, -- 1 = creato da solo dal calendario the361
  spare_outfits INTEGER NOT NULL DEFAULT 1  -- outfit di scorta
);

-- Righe dei modelli. template_id NULL = vale per tutti i viaggi.
CREATE TABLE trip_template_lines (
  id          INTEGER PRIMARY KEY,
  template_id INTEGER REFERENCES trip_templates(id) ON DELETE CASCADE,
  section     TEXT NOT NULL CHECK (section IN ('documenti','elettronica','kit','vestiti','altro')),
  label       TEXT NOT NULL,
  qty         INTEGER NOT NULL DEFAULT 1,
  kit_id      INTEGER REFERENCES kits(id),
  item_id     INTEGER REFERENCES items(id),
  applies_if  TEXT NOT NULL DEFAULT 'sempre' CHECK (applies_if IN ('sempre','fuori_schengen','fuori_ue')),
  must_have   INTEGER NOT NULL DEFAULT 0, -- in evidenza in cima, non si spunta in silenzio
  on_return   INTEGER NOT NULL DEFAULT 0  -- compare anche nella checklist di ritorno
);

CREATE TABLE trips (
  id          INTEGER PRIMARY KEY,
  template_id INTEGER NOT NULL REFERENCES trip_templates(id),
  destination TEXT NOT NULL,
  lat         REAL NOT NULL,
  lon         REAL NOT NULL,
  country     TEXT NOT NULL,             -- ISO 2: da qui schengen ed eu
  schengen    INTEGER NOT NULL,
  eu          INTEGER NOT NULL,
  city_id     INTEGER REFERENCES cities(id), -- se lì ho già vestiti (Strasburgo, Italia)
  start_date  TEXT NOT NULL,
  end_date    TEXT NOT NULL,
  status      TEXT NOT NULL DEFAULT 'pianificato' CHECK (status IN
              ('pianificato','in_corso','rientrato','annullato')),
  source      TEXT NOT NULL DEFAULT 'manuale' CHECK (source IN ('manuale','the361')),
  ep_week     TEXT REFERENCES ep_weeks(week_start),
  notes       TEXT,
  CHECK (end_date >= start_date)
);

CREATE TABLE packing_lines (
  id         INTEGER PRIMARY KEY,
  trip_id    INTEGER NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
  phase      TEXT NOT NULL CHECK (phase IN ('andata','ritorno')),
  section    TEXT NOT NULL,
  label      TEXT NOT NULL,
  qty        INTEGER NOT NULL DEFAULT 1,
  garment_id INTEGER REFERENCES garments(id),
  kit_id     INTEGER REFERENCES kits(id),
  item_id    INTEGER REFERENCES items(id),
  must_have  INTEGER NOT NULL DEFAULT 0,
  checked    INTEGER NOT NULL DEFAULT 0,
  sort       INTEGER NOT NULL DEFAULT 0
);

-- Outfit: quelli proposti ogni sera, quelli dei viaggi e lo storico (status = indossato).
CREATE TABLE outfits (
  id         INTEGER PRIMARY KEY,
  date       TEXT NOT NULL,
  city_id    INTEGER REFERENCES cities(id),
  trip_id    INTEGER REFERENCES trips(id) ON DELETE SET NULL,
  dress_code TEXT NOT NULL,
  day_type   TEXT,                       -- "plenaria", "settimana verde"...
  weather    TEXT,                       -- JSON, con nota se il meteo non ha risposto
  source     TEXT NOT NULL CHECK (source IN ('motore','manuale','viaggio')),
  status     TEXT NOT NULL DEFAULT 'proposto' CHECK (status IN ('proposto','indossato','scartato')),
  rating     INTEGER CHECK (rating IN (-1, 1)),
  image      TEXT,                       -- immagine composta dai ritagli
  missing    TEXT,                       -- JSON: cosa manca se non c'è un abbinamento valido
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX outfits_date ON outfits(date);

CREATE TABLE outfit_items (
  outfit_id  INTEGER NOT NULL REFERENCES outfits(id) ON DELETE CASCADE,
  garment_id INTEGER NOT NULL REFERENCES garments(id),
  PRIMARY KEY (outfit_id, garment_id)
);

-- ============ SEZIONE 3: INVENTARIO E KIT ============

-- Oggetti che possiedo. Anche calze e intimo stanno qui, contati e non fotografati.
CREATE TABLE items (
  id          INTEGER PRIMARY KEY,
  name        TEXT NOT NULL UNIQUE,
  owned_qty   INTEGER NOT NULL DEFAULT 0,
  consumable  INTEGER NOT NULL DEFAULT 0,
  running_low INTEGER NOT NULL DEFAULT 0, -- "quasi finito"
  refill_from TEXT,                       -- chi chiedere per la ricarica
  per_night   INTEGER NOT NULL DEFAULT 0, -- quanti per notte di viaggio (calze, intimo)
  notes       TEXT
);

CREATE TABLE kits (
  id    INTEGER PRIMARY KEY,
  name  TEXT NOT NULL UNIQUE,
  place TEXT,                            -- dove sta
  notes TEXT
);

CREATE TABLE kit_items (
  kit_id  INTEGER NOT NULL REFERENCES kits(id) ON DELETE CASCADE,
  item_id INTEGER NOT NULL REFERENCES items(id),
  qty     INTEGER NOT NULL DEFAULT 1 CHECK (qty > 0),
  PRIMARY KEY (kit_id, item_id)
);

-- Lista della spesa calcolata, mai scritta a mano.
CREATE VIEW shopping_list AS
SELECT i.id, i.name, r.needed - i.owned_qty AS qty, 'per completare i kit' AS reason
FROM items i
JOIN (SELECT item_id, SUM(qty) AS needed FROM kit_items GROUP BY item_id) r ON r.item_id = i.id
WHERE r.needed > i.owned_qty
UNION ALL
SELECT id, name, NULL, 'quasi finito' FROM items WHERE running_low = 1;

-- ============ SEZIONE 4: STILE, ACQUISTI, SARTA ============

CREATE TABLE profile (
  id         INTEGER PRIMARY KEY CHECK (id = 1), -- una sola riga
  height_cm  INTEGER,
  build      TEXT,
  coloring   TEXT,                       -- capelli, occhi, carnagione
  sizes      TEXT NOT NULL DEFAULT '{}', -- JSON: {"camicia":..., "giacca":..., "pantalone":..., "scarpe":...}
  fit_notes  TEXT,                       -- orlo, lunghezza giacca, spalle, niente oversize
  budget_min INTEGER,
  budget_max INTEGER
);

-- La palette stimata e, in seguito, quella della consulente (attiva = 1 una sola).
CREATE TABLE palettes (
  id         INTEGER PRIMARY KEY,
  name       TEXT NOT NULL,
  source     TEXT NOT NULL CHECK (source IN ('stima','consulente')),
  active     INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE UNIQUE INDEX one_active_palette ON palettes(active) WHERE active = 1;

CREATE TABLE palette_colors (
  id         INTEGER PRIMARY KEY,
  palette_id INTEGER NOT NULL REFERENCES palettes(id) ON DELETE CASCADE,
  family     TEXT NOT NULL REFERENCES color_families(name),
  role       TEXT NOT NULL CHECK (role IN ('base','da_aggiungere','evita'))
);

-- Regole di stile del motore, con parametri in JSON. Esempio:
-- kind 'vieta_coppia', params {"a":{"slot":"scarpe","family":"nero"},"b":{"family":["beige","tortora"]}}
CREATE TABLE style_rules (
  id          INTEGER PRIMARY KEY,
  kind        TEXT NOT NULL,
  params      TEXT NOT NULL,
  description TEXT NOT NULL,
  active      INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE wishlist (
  id           INTEGER PRIMARY KEY,
  description  TEXT NOT NULL,            -- "overshirt in lana, ruggine"
  category_id  INTEGER REFERENCES categories(id),
  color_family TEXT REFERENCES color_families(name),
  url          TEXT,                     -- solo link incollati da me o verificati
  image        TEXT,
  cutout       TEXT,
  price_eur    REAL,
  status       TEXT NOT NULL DEFAULT 'idea' CHECK (status IN ('idea','desiderato','comprato','scartato')),
  garment_id   INTEGER REFERENCES garments(id), -- il capo vero, dopo l'acquisto
  created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE tailor_jobs (
  id           INTEGER PRIMARY KEY,
  garment_id   INTEGER NOT NULL REFERENCES garments(id) ON DELETE CASCADE,
  kind         TEXT NOT NULL CHECK (kind IN ('orlo','spalle','lunghezza_giacca','stringere','altro')),
  note         TEXT,
  status       TEXT NOT NULL DEFAULT 'da_portare' CHECK (status IN ('da_portare','dalla_sarta','fatto')),
  brought_on   TEXT,
  picked_up_on TEXT,
  cost_eur     REAL
);

-- ============ AVVISI ============

CREATE TABLE reminders (
  id      INTEGER PRIMARY KEY,
  title   TEXT NOT NULL,
  due_at  TEXT NOT NULL,                 -- data e ora locali
  kind    TEXT NOT NULL CHECK (kind IN ('ricarica','viaggio_prep','partenza','ritorno','sarta','libero')),
  trip_id INTEGER REFERENCES trips(id) ON DELETE CASCADE,
  item_id INTEGER REFERENCES items(id) ON DELETE CASCADE,
  link    TEXT,                          -- pagina dell'app da aprire
  sent_at TEXT,
  done    INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE push_subscriptions (
  id         INTEGER PRIMARY KEY,
  endpoint   TEXT NOT NULL UNIQUE,
  p256dh     TEXT NOT NULL,
  auth       TEXT NOT NULL,
  device     TEXT,                       -- "iPhone", "Mac"...
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE notification_log (
  id      INTEGER PRIMARY KEY,
  sent_at TEXT NOT NULL DEFAULT (datetime('now')),
  kind    TEXT NOT NULL,
  title   TEXT,
  body    TEXT,
  sources TEXT                           -- JSON: {"the361":"ok","meteo":"non risponde"}
);
