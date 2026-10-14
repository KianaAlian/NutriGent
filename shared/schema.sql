PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  telegram_id   TEXT UNIQUE NOT NULL,
  name          TEXT,
  timezone      TEXT DEFAULT 'UTC',
  locale        TEXT DEFAULT 'en',
  household_id  INTEGER,
  created_at    TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS dietary_profiles (
  user_id          INTEGER PRIMARY KEY REFERENCES users(id),
  allergies_json   TEXT NOT NULL DEFAULT '[]',
  intolerances_json TEXT DEFAULT '[]',
  diet_type        TEXT,
  dislikes_json    TEXT DEFAULT '[]',
  goal             TEXT,
  daily_kcal       INTEGER,
  protein_g        INTEGER,
  carbs_g          INTEGER,
  fat_g            INTEGER,
  cooking_skill    TEXT DEFAULT 'beginner',
  max_cook_minutes INTEGER DEFAULT 45,
  budget_level     TEXT DEFAULT 'normal',
  eating_window    TEXT,
  health_flags_json TEXT DEFAULT '[]',
  updated_at       TEXT
);

-- THE SAFETY TABLES: power the deterministic gate
CREATE TABLE IF NOT EXISTS allergen_synonyms (
  id         INTEGER PRIMARY KEY,
  canonical  TEXT NOT NULL,
  synonym    TEXT NOT NULL,
  match_type TEXT DEFAULT 'contains',     -- 'exact' | 'contains'
  certainty  TEXT DEFAULT 'definite'      -- 'definite' | 'possible'
);
CREATE INDEX IF NOT EXISTS idx_synonym ON allergen_synonyms(synonym);

-- Known false-positive traps ("coconut milk" is not dairy)
CREATE TABLE IF NOT EXISTS synonym_exceptions (
  id        INTEGER PRIMARY KEY,
  canonical TEXT NOT NULL,
  pattern   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pantry (
  id          INTEGER PRIMARY KEY,
  user_id     INTEGER REFERENCES users(id),
  ingredient  TEXT NOT NULL,
  quantity    REAL,
  unit        TEXT,
  expires_on  TEXT,
  updated_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS recipes (
  id               INTEGER PRIMARY KEY,
  title            TEXT NOT NULL,
  source           TEXT,
  ingredients_json TEXT NOT NULL,
  steps_json       TEXT NOT NULL,
  kcal INTEGER, protein_g REAL, carbs_g REAL, fat_g REAL,
  cook_minutes     INTEGER,
  gate_screen_json TEXT
);

CREATE TABLE IF NOT EXISTS meal_schedule (
  id            INTEGER PRIMARY KEY,
  user_id       INTEGER REFERENCES users(id),
  date          TEXT NOT NULL,
  meal_type     TEXT NOT NULL,
  recipe_id     INTEGER REFERENCES recipes(id),
  status        TEXT DEFAULT 'planned',   -- planned/cooked/skipped/swapped
  status_reason TEXT
);

CREATE TABLE IF NOT EXISTS shopping_list_items (
  id            INTEGER PRIMARY KEY,
  user_id       INTEGER REFERENCES users(id),
  week_start    TEXT,
  ingredient    TEXT, quantity REAL, unit TEXT,
  store_section TEXT,
  status        TEXT DEFAULT 'pending',   -- pending/bought/unavailable
  est_cost      REAL
);

CREATE TABLE IF NOT EXISTS food_log (
  id           INTEGER PRIMARY KEY,
  user_id      INTEGER REFERENCES users(id),
  ts           TEXT DEFAULT (datetime('now')),
  source       TEXT,                      -- photo/barcode/text/schedule/voice/receipt
  item         TEXT,
  verdict      TEXT,                      -- safe/unsafe/caution/unverified/logged
  flagged_json TEXT,
  kcal INTEGER, protein_g REAL, carbs_g REAL, fat_g REAL,
  image_ref    TEXT
);

CREATE TABLE IF NOT EXISTS preference_events (
  id        INTEGER PRIMARY KEY,
  user_id   INTEGER REFERENCES users(id),
  ts        TEXT DEFAULT (datetime('now')),
  recipe_id INTEGER REFERENCES recipes(id),
  event     TEXT,                          -- accepted/swapped/skipped/loved/hated
  note      TEXT
);

CREATE TABLE IF NOT EXISTS weight_log (
  id INTEGER PRIMARY KEY,
  user_id INTEGER REFERENCES users(id),
  date TEXT, weight_kg REAL
);

-- Symptom-food correlation journal (gut health / energy / skin)
CREATE TABLE IF NOT EXISTS symptom_log (
  id       INTEGER PRIMARY KEY,
  user_id  INTEGER REFERENCES users(id),
  ts       TEXT DEFAULT (datetime('now')),
  symptom  TEXT,                           -- bloating/low_energy/headache/skin/other
  severity INTEGER,                        -- 1-5
  note     TEXT
);

-- Sign-up in progress: which question each Telegram user is on (survives restarts)
CREATE TABLE IF NOT EXISTS onboarding_state (
  telegram_id  TEXT PRIMARY KEY,
  step         TEXT NOT NULL,
  answers_json TEXT NOT NULL DEFAULT '{}',
  updated_at   TEXT DEFAULT (datetime('now'))
);

-- One Hermes agent conversation per Telegram user (free chat keeps its context)
CREATE TABLE IF NOT EXISTS hermes_sessions (
  telegram_id TEXT PRIMARY KEY,
  session_id  TEXT NOT NULL,
  updated_at  TEXT DEFAULT (datetime('now'))
);

-- What the user's next plain message means after tapping e.g. "Type it" (expires after 30 min)
CREATE TABLE IF NOT EXISTS pending_input (
  telegram_id TEXT PRIMARY KEY,
  kind        TEXT NOT NULL,              -- check_text / log_text / symptom_text
  created_at  TEXT DEFAULT (datetime('now'))
);
