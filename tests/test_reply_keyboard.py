"""The persistent button grid under the chat input: clean labels that still work as commands."""
import os, sys, unittest

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "shared"))
sys.path.insert(0, os.path.join(ROOT, "app"))
DB = "/tmp/test_reply_keyboard.db"
os.environ["DIET_DB"] = DB
os.environ.pop("ALLOWED_TELEGRAM_IDS", None)
if os.path.exists(DB): os.remove(DB)
import db; db.DB_PATH = DB; db.init_db()

import telegram_menu as menu
import handlers, bot


def _labels():
    return [b["text"] for row in menu.persistent_main_keyboard()["keyboard"] for b in row]


def _msg(text):
    return {"message": {"chat": {"id": 5}, "from": {"id": 5}, "text": text}}


class ReplyKeyboardTests(unittest.TestCase):
    def test_labels_have_no_slash(self):
        self.assertTrue(_labels())
        for label in _labels():
            self.assertNotIn("/", label)

    def test_keyboard_stays_under_the_input(self):
        kb = menu.persistent_main_keyboard()
        self.assertTrue(kb["is_persistent"])
        self.assertTrue(kb["resize_keyboard"])
        self.assertFalse(kb["one_time_keyboard"])

    def test_every_button_runs_its_command(self):
        called = []
        original = dict(bot.COMMANDS)
        try:
            for name in bot.COMMANDS:
                bot.COMMANDS[name] = lambda ctx, n=name: called.append(n)
            for label in _labels():
                called.clear()
                bot.handle_update(_msg(label))
                expected = label.split()[-1].lower()
                self.assertEqual(called, [expected], f"button {label!r}")
        finally:
            bot.COMMANDS.update(original)

    def test_typed_word_works_like_the_button(self):
        called = []
        original = bot.COMMANDS["today"]
        try:
            bot.COMMANDS["today"] = lambda ctx: called.append("today")
            bot.handle_update(_msg("Today"))
            self.assertEqual(called, ["today"])
        finally:
            bot.COMMANDS["today"] = original

    def test_start_sends_the_keyboard(self):
        sent = []
        original = handlers.send_text
        try:
            handlers.send_text = lambda chat, text, reply_markup=None: sent.append(reply_markup)
            handlers.onboard_start({"chat_id": 77, "telegram_id": "77"})  # a new user of its own
        finally:
            handlers.send_text = original
        self.assertEqual(sent[-1], menu.persistent_main_keyboard())


if __name__ == "__main__":
    unittest.main()
