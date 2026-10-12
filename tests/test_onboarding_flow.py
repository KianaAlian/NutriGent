"""Sign-up conversation: one question at a time, saved in the DB, never loops."""
import os, sys, json, unittest

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "shared"))
sys.path.insert(0, os.path.join(ROOT, "app"))

DB = "/tmp/test_onboarding_flow.db"
os.environ["DIET_DB"] = DB
os.environ.pop("ALLOWED_TELEGRAM_IDS", None)
if os.path.exists(DB): os.remove(DB)
import db; db.DB_PATH = DB; db.init_db()
import safety_gate; safety_gate.conn = db.conn
from nutrition import daily_target

import telegram_io, handlers, onboarding, bot
SENT = []
def _text(chat, text, reply_markup=None): SENT.append(text)
def _menu(chat, text, kb): SENT.append(text)
def _photo(chat, path, caption=""): SENT.append("[photo] " + caption)
for mod in (telegram_io, handlers, onboarding, bot):
    for name, fn in (("send_text", _text), ("send_menu", _menu), ("send_photo", _photo)):
        if hasattr(mod, name): setattr(mod, name, fn)
bot._ack = lambda cq_id: None

NAME_Q = "what should I call you"

def say(tid, text):
    SENT.clear()
    bot.handle_update({"message": {"chat": {"id": tid}, "from": {"id": tid}, "text": text}})
    return list(SENT)

def tap(tid, data):
    SENT.clear()
    bot.handle_update({"callback_query": {"id": "1", "data": data, "from": {"id": tid},
                                          "message": {"chat": {"id": tid}}}})
    return list(SENT)

def state(tid):
    c = db.conn()
    row = c.execute("SELECT step FROM onboarding_state WHERE telegram_id=?", (str(tid),)).fetchone()
    c.close()
    return row["step"] if row else None

def profile(tid):
    u = db.user_by_telegram(tid)
    return db.get_profile(u["id"]) if u else None


class OnboardingFlowTests(unittest.TestCase):
    def test_new_user_completes_signup(self):
        tid = 101
        self.assertTrue(any(NAME_Q in m for m in say(tid, "/start")))
        say(tid, "Sara")
        tap(tid, "onboard:allergy:peanut")
        say(tid, "kiwi")
        tap(tid, "onboard:allergy:done")
        tap(tid, "onboard:severity:anaphylactic")
        tap(tid, "onboard:severity:mild")
        tap(tid, "onboard:diet:vegetarian")
        tap(tid, "onboard:goal:lose")
        tap(tid, "onboard:sex:female")
        say(tid, "29")
        say(tid, "165 cm")
        say(tid, "60kg")
        tap(tid, "onboard:activity:moderate")
        tap(tid, "onboard:max_minutes:30")

        p = profile(tid)
        self.assertIsNotNone(p)
        self.assertEqual(p["allergies"], [{"allergen": "peanut", "severity": "anaphylactic"},
                                          {"allergen": "kiwi", "severity": "mild"}])
        self.assertEqual(p["diet_type"], "vegetarian")
        self.assertEqual(p["goal"], "lose")
        self.assertEqual(p["max_cook_minutes"], 30)
        self.assertEqual(p["daily_kcal"], daily_target("female", 60, 165, 29, "moderate", "lose")["daily_kcal"])
        self.assertEqual(db.user_by_telegram(tid)["name"], "Sara")
        self.assertIsNone(state(tid))

    def test_answering_the_name_moves_on(self):  # the reported loop
        tid = 102
        say(tid, "/start")
        reply = say(tid, "Nima")
        self.assertFalse(any(NAME_Q in m for m in reply), reply)
        self.assertTrue(any("allerg" in m.lower() for m in reply), reply)
        self.assertEqual(state(tid), "allergies")

    def test_bad_number_is_asked_again(self):
        tid = 103
        for step in (lambda: say(tid, "/start"), lambda: say(tid, "Ali"),
                     lambda: tap(tid, "onboard:allergy:none"), lambda: tap(tid, "onboard:diet:none"),
                     lambda: tap(tid, "onboard:goal:maintain"), lambda: tap(tid, "onboard:sex:male")):
            step()
        self.assertEqual(state(tid), "age")
        self.assertTrue(any("number" in m for m in say(tid, "abc")))
        self.assertTrue(any("number" in m for m in say(tid, "500")))
        self.assertEqual(state(tid), "age")
        say(tid, "30")
        self.assertEqual(state(tid), "height")

    def test_no_allergies_skips_severity(self):
        tid = 104
        say(tid, "/start"); say(tid, "Mina")
        reply = tap(tid, "onboard:allergy:none")
        self.assertEqual(state(tid), "diet")
        self.assertTrue(any("diet" in m.lower() for m in reply), reply)

    def test_command_during_signup_resumes_the_question(self):
        tid = 105
        say(tid, "/start"); say(tid, "Reza")
        reply = say(tid, "/today")
        self.assertEqual(state(tid), "allergies")
        self.assertFalse(any(m.startswith("[photo]") for m in reply), reply)
        self.assertTrue(any("allerg" in m.lower() for m in reply), reply)

    def test_registered_user_start_says_welcome_back(self):
        tid = 106
        c = db.conn()
        c.execute("INSERT INTO users(telegram_id,name) VALUES(?,?)", (str(tid), "Lea"))
        uid = c.execute("SELECT id FROM users WHERE telegram_id=?", (str(tid),)).fetchone()[0]
        c.execute("INSERT INTO dietary_profiles(user_id,allergies_json,daily_kcal) VALUES(?,?,?)", (uid, "[]", 2000))
        c.commit(); c.close()
        reply = say(tid, "/start")
        self.assertTrue(any("Welcome back, Lea" in m for m in reply), reply)
        self.assertFalse(any(NAME_Q in m for m in reply), reply)
        self.assertIsNone(state(tid))


if __name__ == "__main__":
    unittest.main()
