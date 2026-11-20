# Style.me

App personale per vestirsi bene ogni giorno. Ogni sera ti manda una mail con l'outfit di domani, ti prepara la valigia quando parti, ti dice cosa manca nei kit e ti aiuta a comprare capi che si abbinano a quelli che hai.

Il piano iniziale (database, cartelle, schermate) è in [docs/piano.md](docs/piano.md).

## Come è fatta

- **Frontend**: React + Vite + Tailwind, componenti in stile shadcn, font Inter, PWA installabile. Cartella `frontend/`.
- **Backend**: FastAPI in Python. Cartella `backend/`. Su Vercel gira come funzione (`api/index.py`).
- **Database**: SQLite in locale, Postgres su Supabase online. Lo stesso codice va su tutti e due.
- **Foto**: cartella locale in sviluppo, Supabase Storage online. Lo scontorno lo fa il telefono quando scatti la foto.
- **Avvisi**: mail con Resend, come LAURUS. Push web facoltativo.
- **Sveglia**: GitHub Actions chiama l'app ogni 15 minuti la sera e una volta al mattino. Il cron di Vercel fa da riserva una volta al giorno.
- **Calendario PE**: da the361. Il 2026 è già caricato. Quando the361 pubblica `calendar.json`, l'app lo legge da sola.
- **Meteo**: Open-Meteo, gratis e senza chiave.

## Provarla sul tuo computer

Servono Python 3.11 o più recente e Node 20 o più recente.

```bash
# 1. backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
python scripts/hash_password.py        # scegli la password, copia la riga che stampa
cp ../.env.example ../.env              # incolla la riga in APP_PASSWORD_HASH
uvicorn app.main:app --reload --port 8000

# 2. frontend, in un altro terminale
cd frontend
npm ci
npm run dev
```

Apri http://localhost:5173 ed entra con la password. Il database si crea da solo in `backend/data/`.

Per i test: `cd backend && pytest`. Per provarli anche su Postgres, aggiungi `TEST_PG_URL=postgresql://...`.

## Metterla online

Una volta sola, in quest'ordine. Non serve copiare chiavi a mano: password, chiave Resend e segreti si sistemano dall'app.

**1. Vercel**
- *Add New → Project*, scegli il repo `style.me` e lascia la cartella principale com'è: `vercel.json` sa già cosa fare.
- Finché la PR non è unita, in *Settings → Git* metti `fase-1` come *Production Branch*.

**2. Supabase (database e foto)**
- Dal progetto Vercel, *Storage → Connect Database → Supabase*. L'integrazione crea il progetto e mette da sola `POSTGRES_URL`, `SUPABASE_URL` e `SUPABASE_SERVICE_ROLE_KEY`.
- In alternativa puoi usare il progetto di LAURUS: le tabelle di Style.me stanno nello schema `styleme` e non toccano niente. In quel caso metti a mano `DATABASE_URL` (Transaction pooler, porta 6543), `SUPABASE_URL` e `SUPABASE_SERVICE_ROLE_KEY`.
- Il bucket privato `styleme` per le foto lo crea l'app al primo caricamento.
- Dopo aver collegato il database, rifai il deploy (*Deployments → Redeploy*).

**3. GitHub**
- Il cron di GitHub chiama già https://style-me-delta.vercel.app. Se cambi indirizzo, metti il nuovo nel secret `APP_URL` del repo. I cron di GitHub partono solo dal ramo principale: finché la PR non è unita, la mail della sera la manda il cron di Vercel (20:40 d'inverno).
- `CRON_SECRET` è facoltativo: se lo metti, va uguale qui e su Vercel.

**4. Primo avvio**
- Apri l'indirizzo: parte il primo avvio guidato. Scegli la password, la città, l'ora della mail.
- Al passo della mail scrivi la chiave Resend (la stessa di LAURUS va bene) e premi *Salva e mandami una prova*.
- Su iPhone: Safari → Condividi → *Aggiungi alla schermata Home*.

## Cose da sapere

- **Costi**: Vercel Hobby, Supabase Free, Resend Free e GitHub Actions bastano. Le foto di 200 capi occupano circa 150 MB. Supabase Free mette in pausa i progetti fermi da una settimana, ma il cron lo tiene sveglio ogni giorno.
- **Orario della mail**: parte al primo passaggio del cron dopo l'ora scelta, quindi con al massimo un quarto d'ora di ritardo. I cron gratuiti di GitHub a volte slittano di qualche minuto.
- **GitHub sospende i cron** dei repo senza commit da 60 giorni. Se succede, riattivali dalla scheda *Actions*. Intanto la riserva di Vercel continua a mandare la mail, anche se in un orario meno preciso.
- **Se una fonte non risponde** (the361 o meteo), la mail lo scrive e l'app usa le regole di base.
- **Lo scontorno** usa `@imgly/background-removal`, che gira sul telefono. Ha licenza AGPL: va bene per un'app personale con il codice pubblico. La prima volta scarica il modello (alcune decine di MB), poi resta in cache.
- **Il motore degli abbinamenti** è a regole, senza AI. Le regole si cambiano da *Stile → Profilo*, il dress code da *Impostazioni*.

## Formato del calendario di the361

`GET https://the361.eu/calendar.json`

```json
{
  "weeks": [{ "weekOf": "2027-01-04", "type": "green" }],
  "holidays": ["2027-01-01"]
}
```

`type` è uno tra `committee`, `group`, `green`, `plenary`, `plenary-brussels`, `recess`. Le settimane mancanti contano come `committee`.
