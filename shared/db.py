"""SQLite helpers shared by every skill. One file, zero ops."""
import sqlite3, json, os

DB_PATH = os.environ.get("DIET_DB", os.path.join(os.path.dirname(__file__), "diet.db"))

def conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    return c

def init_db():
    """Create tables and seed the allergen table if empty."""
    here = os.path.dirname(__file__)
    c = conn()
    c.executescript(open(os.path.join(here, "schema.sql")).read())
    if c.execute("SELECT COUNT(*) FROM allergen_synonyms").fetchone()[0] == 0:
        c.executescript(open(os.path.join(here, "allergen_seed.sql")).read())
    # False-positive guards added after first release; applied to existing DBs too.
    for canon, pattern in (("egg", "eggplant"),):
        if not c.execute("SELECT 1 FROM synonym_exceptions WHERE canonical=? AND pattern=?",
                         (canon, pattern)).fetchone():
            c.execute("INSERT INTO synonym_exceptions(canonical,pattern) VALUES(?,?)", (canon, pattern))
    c.commit(); c.close()

def get_profile(user_id):
    c = conn()
    row = c.execute("SELECT * FROM dietary_profiles WHERE user_id=?", (user_id,)).fetchone()
    c.close()
    if not row: return None
    p = dict(row)
    for k in ("allergies_json","intolerances_json","dislikes_json","health_flags_json"):
        p[k.replace("_json","")] = json.loads(p.get(k) or "[]")
    return p

def user_by_telegram(telegram_id):
    c = conn()
    row = c.execute("SELECT * FROM users WHERE telegram_id=?", (str(telegram_id),)).fetchone()
    c.close()
    return dict(row) if row else None
