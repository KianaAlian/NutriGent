"""Who may use the standalone bot, and who may change whose data."""
import os, sys, json, unittest

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "shared"))
sys.path.insert(0, os.path.join(ROOT, "app"))

DB = "/tmp/test_access.db"
os.environ["DIET_DB"] = DB
if os.path.exists(DB): os.remove(DB)
import db; db.DB_PATH = DB; db.init_db()
import safety_gate; safety_gate.conn = db.conn

import telegram_io, handlers, bot
SENT = []
def _text(chat, text, reply_markup=None): SENT.append((chat, text))
for mod in (telegram_io, handlers, bot):
    mod.send_text = _text
handlers.send_menu = lambda chat, text, kb: SENT.append((chat, text))
handlers.send_photo = lambda chat, path, caption="": SENT.append((chat, caption))
bot._ack = lambda cq_id: None

def _user(tid):
    c = db.conn()
    c.execute("INSERT INTO users(telegram_id,name) VALUES(?,?)", (tid, tid))
    uid = c.execute("SELECT id FROM users WHERE telegram_id=?", (tid,)).fetchone()[0]
    c.execute("INSERT INTO dietary_profiles(user_id,allergies_json) VALUES(?,?)", (uid, "[]"))
    c.execute("INSERT INTO shopping_list_items(user_id,ingredient) VALUES(?,?)", (uid, "rice"))
    item = c.execute("SELECT last_insert_rowid()").fetchone()[0]
    c.commit(); c.close()
    return item

ITEM_A = _user("111")
_user("222")

def tap(tid, data):
    return {"callback_query": {"id": "1", "data": data, "from": {"id": int(tid)},
                               "message": {"chat": {"id": int(tid)}}}}

def status(item):
    c = db.conn(); s = c.execute("SELECT status FROM shopping_list_items WHERE id=?", (item,)).fetchone()[0]; c.close()
    return s


class AccessTests(unittest.TestCase):
    def setUp(self):
        SENT.clear(); os.environ.pop("ALLOWED_TELEGRAM_IDS", None)
        c = db.conn(); c.execute("UPDATE shopping_list_items SET status='pending'"); c.commit(); c.close()

    def test_user_cannot_mark_another_users_item_bought(self):
        bot.handle_update(tap("222", f"buy:{ITEM_A}"))
        self.assertEqual(status(ITEM_A), "pending")

    def test_owner_can_mark_own_item_bought(self):
        bot.handle_update(tap("111", f"buy:{ITEM_A}"))
        self.assertEqual(status(ITEM_A), "bought")

    def test_allowlist_ignores_unlisted_users(self):
        os.environ["ALLOWED_TELEGRAM_IDS"] = "111"
        bot.handle_update({"message": {"chat": {"id": 222}, "from": {"id": 222}, "text": "/help"}})
        self.assertEqual(SENT, [])

    def test_allowlist_admits_listed_users(self):
        os.environ["ALLOWED_TELEGRAM_IDS"] = "111, 333"
        bot.handle_update({"message": {"chat": {"id": 111}, "from": {"id": 111}, "text": "/help"}})
        self.assertEqual(len(SENT), 1)


if __name__ == "__main__":
    unittest.main()
