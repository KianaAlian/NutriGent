"""Free chat goes to Hermes (food questions stay with the gate) and every button answers."""
import os, sys, json, unittest, datetime as dt

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "shared"))
sys.path.insert(0, os.path.join(ROOT, "app"))

DB = "/tmp/test_chat_and_buttons.db"
os.environ["DIET_DB"] = DB
os.environ.pop("ALLOWED_TELEGRAM_IDS", None)
os.environ.pop("OPENAI_API_KEY", None)
if os.path.exists(DB): os.remove(DB)
import db; db.DB_PATH = DB; db.init_db()
import safety_gate; safety_gate.conn = db.conn

import telegram_io, handlers, onboarding, bot, hermes_bridge, llm
SENT = []
def _text(chat, text, reply_markup=None): SENT.append({"text": text, "kb": reply_markup})
def _menu(chat, text, kb): SENT.append({"text": text, "kb": kb})
def _photo(chat, path, caption=""): SENT.append({"text": caption, "photo": path, "kb": None})
for mod in (telegram_io, handlers, onboarding, bot):
    for name, fn in (("send_text", _text), ("send_menu", _menu), ("send_photo", _photo),
                     ("send_chat_action", lambda chat, action="typing": None)):
        if hasattr(mod, name): setattr(mod, name, fn)
bot._ack = lambda cq_id: None
bot.RUN_INLINE = True  # chat normally runs in a background thread

ASKED = []
def fake_ask(tid, text, context=""):
    ASKED.append((tid, text, context)); return {"text": "Hi from Hermes!", "images": []}
hermes_bridge.ask = fake_ask
hermes_bridge.estimate_meal = lambda text: {"kcal": 450, "protein_g": 30.0, "carbs_g": 40.0, "fat_g": 16.0}

TODAY = dt.date.today()

def make_user(tid, name="Sara", allergies=(("milk", "severe"),)):
    c = db.conn()
    c.execute("INSERT INTO users(telegram_id,name) VALUES(?,?)", (str(tid), name))
    uid = c.execute("SELECT id FROM users WHERE telegram_id=?", (str(tid),)).fetchone()[0]
    c.execute("INSERT INTO dietary_profiles(user_id,allergies_json,goal,daily_kcal,protein_g,carbs_g,fat_g) "
              "VALUES(?,?,?,?,?,?,?)", (uid, json.dumps([{"allergen": a, "severity": s} for a, s in allergies]),
                                        "maintain", 2000, 150, 200, 67))
    c.commit(); c.close(); return uid

def plan(uid, days):
    """days: list of (date, title, kcal) -> planned dinners."""
    c = db.conn()
    for date, title, kcal in days:
        c.execute("INSERT INTO recipes(title,source,ingredients_json,steps_json,kcal,protein_g,carbs_g,fat_g,cook_minutes,gate_screen_json) "
                  "VALUES(?,?,?,?,?,?,?,?,?,?)", (title, "test", json.dumps([{"name": "chickpeas", "qty": 200, "unit": "g"}]),
                  json.dumps(["Warm the chickpeas.", "Serve."]), kcal, 30, 60, 15, 20, json.dumps({"level": "SAFE", "hits": []})))
        rid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
        c.execute("INSERT INTO meal_schedule(user_id,date,meal_type,recipe_id,status) VALUES(?,?,?,?,'planned')",
                  (uid, date.isoformat(), "dinner", rid))
    c.commit(); c.close()

def shopping_item(uid, name):
    c = db.conn()
    c.execute("INSERT INTO shopping_list_items(user_id,ingredient,quantity,unit,store_section,status) VALUES(?,?,?,?,?,'pending')",
              (uid, name, 1, "pcs", "Produce"))
    iid = c.execute("SELECT last_insert_rowid()").fetchone()[0]; c.commit(); c.close(); return iid

def q(sql, *args):
    c = db.conn(); r = c.execute(sql, args).fetchall(); c.close(); return r

def say(tid, text):
    SENT.clear(); ASKED.clear()
    bot.handle_update({"message": {"chat": {"id": tid}, "from": {"id": tid}, "text": text}}); return list(SENT)

def tap(tid, data):
    SENT.clear(); ASKED.clear()
    bot.handle_update({"callback_query": {"id": "1", "data": data, "from": {"id": tid}, "message": {"chat": {"id": tid}}}})
    return list(SENT)

def texts(sent): return " | ".join(m["text"] or "" for m in sent)
def buttons(sent): return [b["callback_data"] for m in sent if m["kb"] and "inline_keyboard" in m["kb"]
                           for row in m["kb"]["inline_keyboard"] for b in row]


class ChatTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): make_user(601)

    def test_free_text_goes_to_hermes_with_profile_context(self):
        reply = say(601, "what should I eat after the gym?")
        self.assertIn("Hi from Hermes!", texts(reply))
        tid, text, context = ASKED[0]
        self.assertEqual((tid, text), ("601", "what should I eat after the gym?"))
        self.assertIn("milk (severe)", context)
        self.assertIn("Check", context)  # the agent is told to send safety questions to the gate

    def test_food_question_stays_with_the_gate(self):
        reply = say(601, "can I eat milk chocolate?")
        self.assertEqual(ASKED, [])
        self.assertIn("DO NOT EAT", texts(reply))

    def test_hermes_down_falls_back_to_the_menu(self):
        original = hermes_bridge.ask
        hermes_bridge.ask = lambda *a, **k: None
        try:
            reply = say(601, "tell me a joke")
        finally:
            hermes_bridge.ask = original
        self.assertIn("couldn't answer", texts(reply))
        self.assertIn("act:check", buttons(reply))

    def test_unregistered_user_is_signed_up_not_sent_to_hermes(self):
        reply = say(699, "hello")
        self.assertEqual(ASKED, [])
        self.assertIn("what should I call you", texts(reply))


class ButtonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.uid = make_user(611)
        plan(cls.uid, [(TODAY, "Chickpea curry", 620), (TODAY + dt.timedelta(days=1), "Tofu stir-fry", 480)])
        cls.other = make_user(612, "Ali")
        cls.mine = shopping_item(cls.uid, "spinach")
        cls.theirs = shopping_item(cls.other, "lemons")

    # -- check sub-menu
    def test_check_photo_barcode_menu_buttons_answer(self):
        self.assertIn("photo", texts(tap(611, "check:photo")).lower())
        self.assertIn("coming soon", texts(tap(611, "check:barcode")).lower())
        self.assertIn("menu", texts(tap(611, "check:menu")).lower())

    def test_check_text_button_then_typed_food_is_checked_not_chatted(self):
        tap(611, "check:text")
        reply = say(611, "milk chocolate")
        self.assertEqual(ASKED, [])
        self.assertIn("DO NOT EAT", texts(reply))

    # -- logging
    def test_log_command_without_text_offers_the_log_menu(self):
        before = len(q("SELECT * FROM food_log"))
        reply = say(611, "/log")
        self.assertIn("log:text", buttons(reply))
        self.assertEqual(len(q("SELECT * FROM food_log")), before)

    def test_log_text_button_then_meal_is_logged_with_estimate(self):
        tap(611, "log:text")
        reply = say(611, "large chicken salad")
        row = q("SELECT item, kcal FROM food_log WHERE item='large chicken salad'")
        self.assertEqual([tuple(r) for r in row], [("large chicken salad", 450)])
        self.assertIn("450", texts(reply))
        self.assertEqual(ASKED, [])

    def test_log_photo_and_voice_buttons_ask_to_type(self):
        for data in ("log:photo", "log:voice"):
            self.assertIn("type", texts(tap(611, data)).lower())

    # -- symptoms
    def test_symptom_command_without_text_offers_the_picker(self):
        before = len(q("SELECT * FROM symptom_log"))
        self.assertIn("sym:bloating", buttons(say(611, "/symptom")))
        self.assertEqual(len(q("SELECT * FROM symptom_log")), before)

    def test_symptom_buttons_log_the_symptom(self):
        tap(611, "sym:bloating")
        self.assertTrue(q("SELECT 1 FROM symptom_log WHERE symptom='bloating' AND user_id=?", self.uid))
        tap(611, "sym:other")
        say(611, "itchy skin")
        self.assertTrue(q("SELECT 1 FROM symptom_log WHERE symptom='itchy skin' AND user_id=?", self.uid))

    # -- tonight's meal
    def test_tonight_shows_the_planned_meal_with_actions(self):
        reply = say(611, "/tonight")
        self.assertIn("Chickpea curry", texts(reply))
        self.assertIn(f"meal:cook:{TODAY}:dinner", buttons(reply))

    def test_recipe_button_shows_ingredients_and_steps(self):
        reply = tap(611, f"meal:recipe:{TODAY}:dinner")
        self.assertIn("chickpeas", texts(reply))
        self.assertIn("Warm the chickpeas", texts(reply))

    def test_z_swap_then_cook(self):  # runs last in this class: changes the schedule
        reply = tap(611, f"meal:swap:{TODAY}:dinner")
        self.assertIn("Tofu stir-fry", texts(reply))
        tonight = q("SELECT r.title FROM meal_schedule m JOIN recipes r ON r.id=m.recipe_id "
                    "WHERE m.user_id=? AND m.date=?", self.uid, TODAY.isoformat())
        self.assertEqual(tonight[0][0], "Tofu stir-fry")
        tap(611, f"meal:cook:{TODAY}:dinner")
        self.assertEqual(q("SELECT status FROM meal_schedule WHERE user_id=? AND date=?", self.uid, TODAY.isoformat())[0][0], "cooked")
        self.assertTrue(q("SELECT 1 FROM food_log WHERE user_id=? AND item='Tofu stir-fry' AND kcal=480", self.uid))

    # -- shopping
    def test_shopping_list_has_item_buttons(self):
        reply = say(611, "/shopping")
        self.assertIn(f"buy:{self.mine}", buttons(reply))
        self.assertIn(f"nostock:{self.mine}", buttons(reply))
        self.assertNotIn(f"buy:{self.theirs}", buttons(reply))

    def test_unavailable_button_only_changes_own_items(self):
        tap(611, f"nostock:{self.theirs}")
        self.assertEqual(q("SELECT status FROM shopping_list_items WHERE id=?", self.theirs)[0][0], "pending")
        reply = tap(611, f"nostock:{self.mine}")
        self.assertEqual(q("SELECT status FROM shopping_list_items WHERE id=?", self.mine)[0][0], "unavailable")
        self.assertIn("spinach", texts(reply))


class PlanScreeningTests(unittest.TestCase):
    """Planned recipes have a known, complete ingredient list: screen them as a label, not as a photo."""
    @classmethod
    def setUpClass(cls):
        cls.uid = make_user(621, "Mina", allergies=(("milk", "severe"),))
        meal = lambda title, *ings: {"title": title, "meal_type": "dinner", "kcal": 500, "cook_minutes": 20,
                                     "ingredients": [{"name": i, "qty": 100, "unit": "g"} for i in ings]}
        cls.week = {"days": [{"meals": [meal("Lentil soup", "lentils", "carrot", "olive oil")]},
                             {"meals": [meal("Creamy pasta", "pasta", "whey powder")]}]}

    def test_clean_recipe_is_not_flagged_but_allergen_recipe_is(self):
        original = handlers.generate_week
        handlers.generate_week = lambda profile, pantry: self.week
        try:
            say(621, "/plan")
        finally:
            handlers.generate_week = original
        titles = [r[0] for r in q("SELECT r.title FROM meal_schedule m JOIN recipes r ON r.id=m.recipe_id "
                                  "WHERE m.user_id=? ORDER BY m.date", self.uid)]
        self.assertEqual(titles, ["Lentil soup", "Creamy pasta (needs regeneration)"])


class VerdictCardTextTests(unittest.TestCase):
    def test_long_reasons_are_wrapped_not_cut(self):
        import visuals
        reason = "A photo can't prove a cooked dish is allergen-free. Ask for the ingredient list."
        lines = visuals.wrap_reasons([reason])
        self.assertTrue(all(len(text) <= visuals.REASON_WIDTH for _, text in lines))
        self.assertEqual(" ".join(text for _, text in lines), reason)
        self.assertEqual([first for first, _ in lines], [True] + [False] * (len(lines) - 1))


class PlainTextTests(unittest.TestCase):
    def test_messages_are_sent_as_plain_text(self):  # '&' or '<' in user text must not break Telegram
        import importlib
        real = importlib.reload(telegram_io)
        sent = []
        real._post = lambda method, data: sent.append(data)
        real.send_text(1, "mac & cheese <3")
        self.assertNotIn("parse_mode", sent[0])


if __name__ == "__main__":
    unittest.main()
