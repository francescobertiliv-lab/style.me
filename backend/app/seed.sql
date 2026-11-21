-- Dati iniziali. Dopo il primo avvio si cambia tutto dall'app.

INSERT INTO settings(key, value) VALUES
  ('timezone',        '"Europe/Brussels"'),
  ('notify_time',     '"20:30"'),
  ('trip_alert_days', '2'),
  ('the361_url',      '"https://the361.eu/calendar.json"'),
  ('home_city_id',    '1'),
  -- pioggia: precipitazioni in mm o probabilità in % oltre cui conta come pioggia
  ('rain',            '{"mm": 1.0, "probability": 60}'),
  -- peso ideale dei capi in base alla massima del giorno (1 leggero, 2 medio, 3 pesante)
  ('climate',         '{"light_from": 22, "heavy_below": 12, "coat_below": 15, "layer_below": 12}'),
  -- dress code a cui corrisponde un viaggio a Strasburgo
  ('plenary_trip',    '{"week_types": ["plenary"], "depart_weekday": 0, "return_weekday": 3}');

INSERT INTO cities(id, name, lat, lon, country, is_home) VALUES
  (1, 'Bruxelles (Evere)', 50.8706, 4.4031, 'BE', 1),
  (2, 'Strasburgo',        48.5734, 7.7521, 'FR', 0),
  (3, 'Italia (Livorno)',  43.5485, 10.3106, 'IT', 0);

INSERT INTO categories(name, slot, repeat_days, default_formality, default_weight, sort) VALUES
  ('cappotto',          'capospalla', NULL, 4, 3, 10),
  ('impermeabile',      'capospalla', NULL, 3, 2, 11),
  ('piumino',           'capospalla', NULL, 2, 3, 12),
  ('giacca completo',   'giacca',     NULL, 5, 2, 20),
  ('giacca spezzata',   'giacca',     NULL, 4, 2, 21),
  ('overshirt',         'giacca',     NULL, 2, 2, 22),
  ('chore jacket',      'giacca',     NULL, 2, 2, 23),
  ('maglione',          'strato',     NULL, 2, 2, 30),
  ('cardigan',          'strato',     NULL, 2, 2, 31),
  ('camicia',           'top',        10,   4, 1, 40),
  ('polo',              'top',        NULL, 2, 1, 41),
  ('t-shirt',           'top',        NULL, 1, 1, 42),
  ('pantalone completo','sotto',      NULL, 5, 2, 50),
  ('pantalone',         'sotto',      NULL, 3, 2, 51),
  ('chino',             'sotto',      NULL, 3, 2, 52),
  ('jeans',             'sotto',      NULL, 2, 2, 53),
  ('scarpe formali',    'scarpe',     NULL, 5, 2, 60),
  ('mocassini',         'scarpe',     NULL, 3, 2, 61),
  ('stivaletti',        'scarpe',     NULL, 3, 3, 62),
  ('sneakers',          'scarpe',     NULL, 1, 2, 63),
  ('cravatta',          'cravatta',   7,    5, 1, 70),
  ('cintura',           'accessorio', NULL, 3, 2, 80),
  ('sciarpa',           'accessorio', NULL, 3, 2, 81);

-- tone: neutro / caldo / freddo. depth: chiaro / medio / scuro.
INSERT INTO color_families(name, hex, tone, depth) VALUES
  ('bianco',           '#F4F4F0', 'neutro', 'chiaro'),
  ('crema',            '#EDE3CF', 'neutro', 'chiaro'),
  ('beige',            '#D6C3A3', 'neutro', 'chiaro'),
  ('tortora',          '#A39382', 'neutro', 'medio'),
  ('cammello',         '#BE9466', 'neutro', 'medio'),
  ('marrone',          '#5B3A24', 'neutro', 'scuro'),
  ('grigio chiaro',    '#C4C4C2', 'neutro', 'chiaro'),
  ('grigio',           '#808080', 'neutro', 'medio'),
  ('antracite',        '#3C3C3E', 'neutro', 'scuro'),
  ('nero',             '#141414', 'neutro', 'scuro'),
  ('navy',             '#1E2840', 'neutro', 'scuro'),
  ('denim scuro',      '#2C3B57', 'neutro', 'scuro'),
  ('azzurro',          '#AFC8E6', 'freddo', 'chiaro'),
  ('blu',              '#2F5A9A', 'freddo', 'medio'),
  ('grigio freddo',    '#98A4B3', 'freddo', 'medio'),
  ('verde oliva',      '#6B6A3B', 'caldo',  'medio'),
  ('verde bosco',      '#2F4A36', 'caldo',  'scuro'),
  ('ruggine',          '#A2481F', 'caldo',  'medio'),
  ('terracotta',       '#C26A4A', 'caldo',  'medio'),
  ('senape',           '#C79E2A', 'caldo',  'medio'),
  ('bordeaux',         '#6A1B2B', 'caldo',  'scuro'),
  ('rosso',            '#A51D2C', 'caldo',  'medio'),
  ('arancione acceso', '#FF6A00', 'caldo',  'chiaro'),
  ('fucsia',           '#DE2A8A', 'freddo', 'medio'),
  ('pastello',         '#D7E3EA', 'freddo', 'chiaro');

-- Dress code per tipo di settimana del PE (0 = lunedì ... 6 = domenica).
-- committee e group = settimana normale; plenary = Strasburgo, completo lun–gio.
INSERT INTO dress_rules(week_type, weekday, dress_code) VALUES
  ('committee',0,'completo'),('committee',1,'completo'),('committee',2,'completo'),('committee',3,'completo'),
  ('committee',4,'informale'),('committee',5,'libero'),('committee',6,'libero'),
  ('group',0,'completo'),('group',1,'completo'),('group',2,'completo'),('group',3,'completo'),
  ('group',4,'informale'),('group',5,'libero'),('group',6,'libero'),
  ('plenary-brussels',0,'completo'),('plenary-brussels',1,'completo'),('plenary-brussels',2,'completo'),('plenary-brussels',3,'completo'),
  ('plenary-brussels',4,'informale'),('plenary-brussels',5,'libero'),('plenary-brussels',6,'libero'),
  ('plenary',0,'completo'),('plenary',1,'completo'),('plenary',2,'completo'),('plenary',3,'completo'),
  ('plenary',4,'informale'),('plenary',5,'libero'),('plenary',6,'libero'),
  ('green',0,'informale'),('green',1,'informale'),('green',2,'informale'),('green',3,'informale'),
  ('green',4,'informale'),('green',5,'libero'),('green',6,'libero'),
  ('recess',0,'libero'),('recess',1,'libero'),('recess',2,'libero'),('recess',3,'libero'),
  ('recess',4,'libero'),('recess',5,'libero'),('recess',6,'libero');

-- Calendario PE 2026 copiato da the361.eu (20/11/2026). Le settimane mancanti sono "committee".
INSERT INTO ep_weeks(week_start, week_type, place, raw, fetched_at) VALUES
  ('2026-01-05','green',NULL,NULL,'2026-11-20'),('2026-01-12','group',NULL,NULL,'2026-11-20'),
  ('2026-01-19','plenary','Strasburgo',NULL,'2026-11-20'),('2026-01-26','plenary-brussels','Bruxelles',NULL,'2026-11-20'),
  ('2026-02-02','group',NULL,NULL,'2026-11-20'),('2026-02-09','plenary','Strasburgo',NULL,'2026-11-20'),
  ('2026-02-16','green',NULL,NULL,'2026-11-20'),('2026-03-02','group',NULL,NULL,'2026-11-20'),
  ('2026-03-09','plenary','Strasburgo',NULL,'2026-11-20'),('2026-03-23','plenary-brussels','Bruxelles',NULL,'2026-11-20'),
  ('2026-03-30','green',NULL,NULL,'2026-11-20'),('2026-04-20','group',NULL,NULL,'2026-11-20'),
  ('2026-04-27','plenary','Strasburgo',NULL,'2026-11-20'),('2026-05-11','group',NULL,NULL,'2026-11-20'),
  ('2026-05-18','plenary','Strasburgo',NULL,'2026-11-20'),('2026-05-25','green',NULL,NULL,'2026-11-20'),
  ('2026-06-08','group',NULL,NULL,'2026-11-20'),('2026-06-15','plenary','Strasburgo',NULL,'2026-11-20'),
  ('2026-06-29','group',NULL,NULL,'2026-11-20'),('2026-07-06','plenary','Strasburgo',NULL,'2026-11-20'),
  ('2026-07-20','green',NULL,NULL,'2026-11-20'),('2026-07-27','recess',NULL,NULL,'2026-11-20'),
  ('2026-08-03','recess',NULL,NULL,'2026-11-20'),('2026-08-10','recess',NULL,NULL,'2026-11-20'),
  ('2026-08-17','recess',NULL,NULL,'2026-11-20'),('2026-08-24','green',NULL,NULL,'2026-11-20'),
  ('2026-09-07','group',NULL,NULL,'2026-11-20'),('2026-09-14','plenary','Strasburgo',NULL,'2026-11-20'),
  ('2026-09-21','green',NULL,NULL,'2026-11-20'),('2026-09-28','group',NULL,NULL,'2026-11-20'),
  ('2026-10-05','plenary','Strasburgo',NULL,'2026-11-20'),('2026-10-12','group',NULL,NULL,'2026-11-20'),
  ('2026-10-19','plenary','Strasburgo',NULL,'2026-11-20'),('2026-10-26','green',NULL,NULL,'2026-11-20'),
  ('2026-11-09','plenary-brussels','Bruxelles',NULL,'2026-11-20'),('2026-11-16','group',NULL,NULL,'2026-11-20'),
  ('2026-11-23','plenary','Strasburgo',NULL,'2026-11-20'),('2026-12-07','group',NULL,NULL,'2026-11-20'),
  ('2026-12-14','plenary','Strasburgo',NULL,'2026-11-20'),('2026-12-21','green',NULL,NULL,'2026-11-20'),
  ('2026-12-28','recess',NULL,NULL,'2026-11-20');

INSERT INTO ep_holidays(date) VALUES
  ('2026-01-01'),('2026-04-06'),('2026-05-01'),('2026-05-14'),('2026-05-25'),
  ('2026-07-21'),('2026-08-15'),('2026-11-01'),('2026-11-11'),('2026-12-25');

INSERT INTO profile(id, height_cm, build, coloring, sizes, fit_notes, budget_min, budget_max) VALUES
  (1, 173, 'asciutta', 'capelli e occhi scuri, carnagione olivastra calda',
   '{}',
   'Orlo che tocca appena la scarpa. Giacca che copre appena il sedere, non oltre. Spalle al punto giusto. Niente oversize.',
   100, 200);

INSERT INTO palettes(id, name, source, active) VALUES (1, 'Autunno/inverno profondo (stima)', 'stima', 1);
INSERT INTO palette_colors(palette_id, family, role) VALUES
  (1,'navy','base'),(1,'beige','base'),(1,'cammello','base'),(1,'tortora','base'),
  (1,'grigio','base'),(1,'antracite','base'),(1,'verde oliva','base'),(1,'verde bosco','base'),
  (1,'denim scuro','base'),(1,'bianco','base'),(1,'crema','base'),(1,'marrone','base'),
  (1,'azzurro','base'),(1,'grigio chiaro','base'),
  (1,'ruggine','da_aggiungere'),(1,'terracotta','da_aggiungere'),(1,'senape','da_aggiungere'),
  (1,'bordeaux','da_aggiungere'),(1,'rosso','da_aggiungere'),
  (1,'pastello','evita'),(1,'arancione acceso','evita'),(1,'fucsia','evita'),(1,'grigio freddo','evita');

-- Regole di stile. kind riconosciuti dal motore: vieta_coppia, max_accenti,
-- sotto_scarpe_vicini, colore_sopra, max_fantasie, evita_palette.
INSERT INTO style_rules(kind, params, description) VALUES
  ('vieta_coppia', '{"a":{"slot":"scarpe","family":["nero"]},"b":{"family":["beige","tortora"]}}',
   'Niente scarpe nere con beige o tortora'),
  ('max_accenti', '{"max": 2}', 'Al massimo due colori su una base neutra'),
  ('sotto_scarpe_vicini', '{"max_gap": 1}', 'Pantalone e scarpe vicini di tono, niente contrasti netti in vita'),
  ('colore_sopra', '{"bonus": 1}', 'Il colore forte sta sopra'),
  ('max_fantasie', '{"max": 2}', 'Al massimo due capi con fantasia'),
  ('evita_palette', '{}', 'Mai i colori da evitare della palette');

-- Inventario e kit
INSERT INTO items(name, owned_qty, consumable, per_night, refill_from) VALUES
  ('scotch per la bocca', 1, 1, 0, NULL),
  ('mascherina per dormire', 1, 0, 0, NULL),
  ('tappi per le orecchie', 1, 1, 0, NULL),
  ('cuscino da viaggio', 1, 0, 0, NULL),
  ('spazzolino', 2, 0, 0, NULL),
  ('dentifricio', 1, 1, 0, NULL),
  ('pastiglie', 1, 1, 0, NULL),
  ('crema per capelli', 2, 1, 0, NULL),
  ('Gaviscon', 1, 1, 0, NULL),
  ('profumo', 1, 1, 0, NULL),
  ('filo interdentale', 1, 1, 0, NULL),
  ('pettine', 1, 0, 0, NULL),
  ('Oura', 1, 0, 0, NULL),
  ('caricatore Oura', 1, 0, 0, NULL),
  ('caricatore PC', 1, 0, 0, NULL),
  ('cuffie', 1, 0, 0, NULL),
  ('mouse', 1, 0, 0, NULL),
  ('schermo', 1, 0, 0, NULL),
  ('PS5', 1, 0, 0, NULL),
  ('calze', 10, 0, 1, NULL),
  ('mutande', 10, 0, 1, NULL),
  ('canottiera', 5, 0, 1, NULL),
  ('passaporto', 1, 0, 0, NULL),
  ('carta d''identità', 1, 0, 0, NULL),
  ('adattatore universale', 0, 0, 0, NULL),
  ('caricatore telefono', 1, 0, 0, NULL),
  ('powerbank', 0, 0, 0, NULL);

INSERT INTO kits(id, name, place) VALUES
  (1, 'Beauty case grande', 'valigia'),
  (2, 'Beauty case piccolo', 'zaino'),
  (3, 'Kit mattina a casa', 'bagno'),
  (4, 'Tech', 'zaino');

INSERT INTO kit_items(kit_id, item_id, qty)
SELECT 1, id, 1 FROM items WHERE name IN ('scotch per la bocca','mascherina per dormire','tappi per le orecchie',
  'cuscino da viaggio','spazzolino','dentifricio','pastiglie','crema per capelli','Gaviscon','profumo');
INSERT INTO kit_items(kit_id, item_id, qty)
SELECT 2, id, 1 FROM items WHERE name IN ('spazzolino','filo interdentale','crema per capelli','pettine','Gaviscon');
INSERT INTO kit_items(kit_id, item_id, qty)
SELECT 3, id, 1 FROM items WHERE name IN ('spazzolino','crema per capelli','pettine');
INSERT INTO kit_items(kit_id, item_id, qty)
SELECT 4, id, 1 FROM items WHERE name IN ('Oura','caricatore Oura','caricatore PC','cuffie','mouse','schermo','PS5');

-- Modelli di viaggio
INSERT INTO trip_templates(id, name, from_calendar, spare_outfits) VALUES
  (1, 'Plenaria a Strasburgo', 1, 0),
  (2, 'Italia (casa/famiglia)', 0, 1),
  (3, 'Missione all''estero', 0, 1);

-- Righe valide per tutti i viaggi (template_id NULL)
INSERT INTO trip_template_lines(template_id, section, label, qty, kit_id, item_id, applies_if, must_have, on_return) VALUES
  (NULL, 'documenti',   'Carta d''identità', 1, NULL, (SELECT id FROM items WHERE name='carta d''identità'), 'sempre', 1, 0),
  (NULL, 'elettronica', 'Caricatore telefono', 1, NULL, (SELECT id FROM items WHERE name='caricatore telefono'), 'sempre', 1, 1),
  (NULL, 'kit',         'Beauty case grande', 1, 1, NULL, 'sempre', 1, 1),
  (NULL, 'elettronica', 'Oura + caricatore', 1, NULL, (SELECT id FROM items WHERE name='caricatore Oura'), 'sempre', 0, 1),
  (NULL, 'elettronica', 'Caricatore PC', 1, NULL, (SELECT id FROM items WHERE name='caricatore PC'), 'sempre', 0, 1),
  (NULL, 'altro',       'Cuscino, tappi e mascherina dall''albergo', 1, NULL, NULL, 'sempre', 0, 1),
  (NULL, 'documenti',   'Passaporto', 1, NULL, (SELECT id FROM items WHERE name='passaporto'), 'fuori_schengen', 1, 0),
  (NULL, 'elettronica', 'Adattatore per le prese', 1, NULL, (SELECT id FROM items WHERE name='adattatore universale'), 'fuori_ue', 1, 1),
  (NULL, 'altro',       'Controlla il roaming del telefono', 1, NULL, NULL, 'fuori_ue', 1, 0);

INSERT INTO trip_template_lines(template_id, section, label, qty, kit_id, item_id, applies_if, must_have, on_return) VALUES
  (1, 'elettronica', 'Cuffie', 1, NULL, (SELECT id FROM items WHERE name='cuffie'), 'sempre', 0, 1),
  (1, 'elettronica', 'Mouse', 1, NULL, (SELECT id FROM items WHERE name='mouse'), 'sempre', 0, 1),
  (3, 'elettronica', 'Powerbank', 1, NULL, (SELECT id FROM items WHERE name='powerbank'), 'sempre', 0, 1);
