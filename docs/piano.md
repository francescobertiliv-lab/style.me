# Style.me — piano prima del codice

Tre cose, come chiesto: schema del database, cartelle, schermate. Nessuna riga di codice dell'app finché non mi dai l'ok.

## 1. Schema SQLite

Il file completo è [schema.sql](../backend/app/schema.sql). L'ho già fatto girare su SQLite: si crea senza errori, le chiavi esterne tornano e la lista della spesa calcola giusto.

27 tabelle e una vista. Ecco cosa fanno, per sezione.

**Base**
- `settings` — orario notifica, giorni di preavviso viaggi, URL the361, fuso orario. Tutto modificabile dall'app. Password e chiavi VAPID stanno nel file `.env`, non nel database.
- `cities` — Evere/Bruxelles, Strasburgo, Italia, con coordinate per il meteo.

**Sezione 1 — Guardaroba**
- `categories` — camicia, cravatta, chino, giacca del completo… Ognuna ha uno *slot* (capospalla, giacca, top, sotto, scarpe, cravatta…) e i giorni prima di riproporla. Così la regola "niente stessa camicia per N giorni" sta nei dati, non nel codice.
- `color_families` — navy, cammello, ruggine, bordeaux, nero… con tono (neutro/caldo/freddo) e profondità. La usano il motore, la palette e il grafico.
- `garments` — il capo: colore principale, colori dominanti, fantasia, formalità 1–5, peso 1–3, materiale, stato, città, foto originale e ritaglio. `rain_ok` esclude lo scamosciato con la pioggia, `rain_gear` segna cappotti e impermeabili. `set_key` tiene insieme giacca e pantalone dello stesso completo. I campi del 3D ci sono già ma restano vuoti finché non arriviamo alla fase 2.
- `ep_weeks` — copia locale del calendario the361. Se the361 non risponde, uso l'ultima copia e lo scrivo nella notifica.
- `dress_rules` — tipo di settimana + giorno → dress code. Lunedì–giovedì completo, venerdì informale, settimana verde informale, plenaria completo. Si cambia dall'app.
- `day_overrides` — i giorni forzati a mano.
- `weather_cache` — meteo Open-Meteo salvato per luogo e giorno.
- `outfits` + `outfit_items` — una sola tabella per tre cose: la proposta della sera, gli outfit dei viaggi e lo storico (stato `indossato`, con pollice su/giù). Se il motore non trova un abbinamento, in `missing` scrive cosa manca.

**Sezione 2 — Viaggi**
- `trip_templates` + `trip_template_lines` — i modelli (Plenaria, Italia, Missione). Le righe senza modello valgono per tutti i viaggi. Ogni riga può valere sempre, solo fuori Schengen (passaporto) o solo fuori UE (adattatore, roaming). `must_have` la mette in cima in evidenza, `on_return` la ripete nella checklist di ritorno.
- `trips` — destinazione, date, paese (da cui Schengen/UE), stato. Le plenarie arrivano da the361 con `source = the361`.
- `packing_lines` — la checklist vera del singolo viaggio, andata e ritorno, con spunta.

**Sezione 3 — Kit**
- `items` — cosa possiedo e quanti. Calze e intimo stanno qui, contati e non fotografati: `per_night` dice quanti ne servono per notte. `running_low` è il "quasi finito", `refill_from` dice a chi chiedere.
- `kits` + `kit_items` — cosa contiene ogni kit e dove sta.
- vista `shopping_list` — calcola da sola cosa manca ("2 pettini per completare i kit") più i prodotti quasi finiti.

**Sezione 4 — Stile, acquisti, sarta**
- `profile` — una riga: statura, corporatura, colori, taglie, note di vestibilità, budget.
- `palettes` + `palette_colors` — la palette stimata adesso e quella della consulente dopo. Una sola è attiva; ogni colore è *base*, *da aggiungere* o *da evitare*.
- `style_rules` — le regole del motore con parametri in JSON (es. "niente scarpe nere con beige o tortora", "niente contrasto netto in vita"). Si accendono e spengono dall'app.
- `wishlist` — idee e capi da comprare, anche con foto o link incollati per la prova. Quando compro, il capo passa in `garments`.
- `tailor_jobs` — orlo, spalle, lunghezza giacca, stringere. Quando un lavoro passa a "dalla sarta", il capo esce dagli outfit finché non lo riprendo.

**Avvisi**
- `reminders` — partenza, ritorno, capi da preparare, ricariche, sarta.
- `push_subscriptions` — i dispositivi abilitati al push.
- `notification_log` — cosa ho mandato e quali fonti hanno risposto.

**Dati iniziali.** Al primo avvio carico da un file di seed: le tre città, categorie, famiglie di colore, regole del dress code, la palette stimata (autunno/inverno profondo), le regole di stile del tuo profilo, i quattro kit e i tre modelli di viaggio. Da lì in poi si cambia tutto dall'app.

## 2. Struttura delle cartelle

```
style-me/
├── README.md                  avvio in locale e messa online
├── .env.example               password, chiavi VAPID, percorsi
├── backend/
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py            FastAPI, login, avvio scheduler
│   │   ├── config.py          legge .env
│   │   ├── db.py              connessione SQLite (sqlite3 puro, niente ORM)
│   │   ├── schema.sql
│   │   ├── seed.sql           dati iniziali
│   │   ├── auth.py            login a un utente, cookie firmato
│   │   ├── routers/           un file per area
│   │   │   ├── garments.py    catalogo, foto, stati
│   │   │   ├── outfits.py     proposta, storico, voti, giorni forzati
│   │   │   ├── trips.py       viaggi, checklist, rientro
│   │   │   ├── kits.py        kit, inventario, lista spesa
│   │   │   ├── style.py       profilo, palette, analisi, suggerimenti, prova, desideri
│   │   │   ├── tailor.py      sarta
│   │   │   └── system.py      impostazioni, push, stato delle fonti
│   │   └── services/          la logica, senza HTTP
│   │       ├── images.py      scontorno (rembg) e colori dominanti (Pillow)
│   │       ├── colors.py      famiglie di colore e compatibilità
│   │       ├── engine.py      motore a regole degli abbinamenti
│   │       ├── composer.py    immagine dell'outfit dai ritagli
│   │       ├── calendar.py    the361 + dress code del giorno
│   │       ├── weather.py     Open-Meteo
│   │       ├── packing.py     lista valigia da modello + giorni + meteo
│   │       ├── shopping.py    analisi colori e suggerimenti
│   │       ├── push.py        web push VAPID
│   │       └── jobs.py        lavori pianificati: notifica serale, avvisi viaggi
│   ├── tests/                 soprattutto engine e packing
│   └── data/                  fuori da git
│       ├── app.db
│       └── photos/  originals/  cutouts/  outfits/  models/
├── frontend/
│   ├── package.json
│   ├── vite.config.ts         con vite-plugin-pwa
│   ├── tailwind.config.ts
│   ├── index.html
│   ├── public/                icone e manifest
│   └── src/
│       ├── main.tsx
│       ├── App.tsx            router e barra in basso
│       ├── sw.ts              service worker: push e cache
│       ├── lib/               api.ts, push.ts, utils.ts
│       ├── components/
│       │   ├── ui/            componenti shadcn
│       │   ├── OutfitCard.tsx
│       │   ├── GarmentTile.tsx
│       │   ├── ChecklistRow.tsx
│       │   └── ColorChart.tsx
│       └── pages/             una cartella per sezione (vedi schermate)
└── deploy/
    ├── Caddyfile              HTTPS automatico (il push lo richiede)
    └── style-me.service       servizio systemd
```

Dipendenze del backend: fastapi, uvicorn, pillow, rembg, httpx, pywebpush, apscheduler, itsdangerous, python-multipart. Niente ORM, niente Redis, niente Celery. L'unica pesante è rembg (porta onnxruntime, qualche centinaio di MB): è il prezzo dello scontorno in locale con le foto che restano sul tuo server.

Frontend in TypeScript, come vuole shadcn. Il grafico colori usa Recharts, che è già quello dei grafici shadcn.

## 3. Schermate

Barra in basso con cinque voci: **Domani · Guardaroba · Viaggi · Kit · Stile**. Impostazioni dall'icona in alto.

**Accesso**
1. Login.
2. Primo avvio: su iPhone ti guida ad aggiungere il sito alla schermata Home, poi chiede il permesso per le notifiche e fa una notifica di prova.

**Domani**
3. Domani — tipo di giornata, meteo, outfit con immagine, due alternative, "cambia questo capo", forza il giorno, avviso se una fonte non ha risposto. Se manca qualcosa, dice cosa.
4. Oggi indossato — conferma cosa hai messo davvero, pollice su/giù.
5. Storico — calendario degli outfit indossati con i voti.

**Guardaroba**
6. Catalogo — griglia di ritagli, filtri per categoria, stato, città, colore.
7. Nuovo capo — foto, ritaglio, proposta di categoria/colore/fantasia/formalità/peso, tu confermi o correggi.
8. Scheda capo — dati, stato e città con un tocco, quando l'hai messo l'ultima volta, interventi della sarta. Nella fase 2 qui compare il 3D.

**Viaggi**
9. Elenco viaggi — prossimi e passati, plenarie già create da the361.
10. Nuovo / modifica viaggio — destinazione, date, modello.
11. Viaggio — giorno per giorno: dress code, meteo, outfit. Avvisi sui capi da lavare o in tintoria.
12. Valigia — checklist da spuntare, gli oggetti "sempre" fissi in cima.
13. Rientro — checklist di ritorno e, per ogni capo, "disponibile" o "da lavare" con un tocco.
14. Modelli di viaggio — editor delle righe e delle condizioni (fuori Schengen, fuori UE).

**Kit**
15. Kit — elenco dei kit, cosa contengono, dove stanno.
16. Inventario — oggetti, quantità, "quasi finito", a chi chiedere.
17. Lista della spesa — cosa manca e perché.

**Stile**
18. Profilo — fisico, taglie, vestibilità, budget, regole di stile on/off.
19. Palette — colori base, da aggiungere, da evitare; caricamento della palette della consulente.
20. Analisi colori — grafico dei capi informali contro la palette, buchi per categoria.
21. Suggerimenti — capi descritti per tipo, colore e tessuto, ognuno con i 3+ outfit che fa con quello che hai già.
22. Prova prima di comprare — incolli foto o link, vedi il capo abbinato ai tuoi.
23. Lista desideri — e "l'ho comprato", che apre il Nuovo capo.
24. Sarta — da portare, dalla sarta, ritirati.

**Impostazioni**
25. Orario notifica, giorni di preavviso, città, URL the361, stato delle fonti, dispositivi push, backup del database.

Una nota su iPhone: le notifiche web su iOS mostrano testo e titolo ma, a quanto mi risulta, non l'immagine allegata. La notifica dirà quindi tipo giornata, meteo e outfit a parole; toccandola si apre la schermata Domani con l'immagine.
