"""The bridge to the Hermes agent: per-user sessions, safe input, graceful failure."""
import os, sys, subprocess, tempfile, unittest

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "shared"))
sys.path.insert(0, os.path.join(ROOT, "app"))

DB = "/tmp/test_hermes_bridge.db"
os.environ["DIET_DB"] = DB
if os.path.exists(DB): os.remove(DB)
import db; db.DB_PATH = DB; db.init_db()
import hermes_bridge as hb

FAKE_BIN = tempfile.NamedTemporaryFile(prefix="hermes", delete=False).name
os.environ["HERMES_BIN"] = FAKE_BIN


class FakeHermes:
    """Stands in for the hermes CLI: records calls, replays scripted outputs."""
    def __init__(self, *outputs):
        self.outputs, self.calls = list(outputs), []
    def __call__(self, args, stdin, timeout):
        self.calls.append((args, stdin))
        out = self.outputs.pop(0)
        if isinstance(out, Exception): raise out
        return out


class BridgeTests(unittest.TestCase):
    def tearDown(self):
        hb.RUNNER = hb._run

    def test_reply_is_cleaned_of_session_lines(self):
        text, sid, images = hb.parse('↻ Resumed session 2026_x "Chat" (1 user message)\nHello Sara!\n\nsession_id: 2026_x\n')
        self.assertEqual((text, sid, images), ("Hello Sara!", "2026_x", []))

    def test_message_goes_through_stdin_not_arguments(self):
        fake = hb.RUNNER = FakeHermes((0, "Hi\n\nsession_id: s1\n"))
        hb.ask("501", "hello; rm -rf / $(id)")
        args, stdin = fake.calls[0]
        self.assertIn("hello; rm -rf / $(id)", stdin)
        self.assertFalse(any("rm -rf" in a for a in args))
        self.assertIn("--query-file", args)

    def test_only_harmless_toolsets_are_enabled(self):
        fake = hb.RUNNER = FakeHermes((0, "Hi\n\nsession_id: s1\n"))
        hb.ask("502", "hello")
        args, _ = fake.calls[0]
        tools = args[args.index("-t") + 1].split(",")
        for dangerous in ("terminal", "file", "code_execution", "computer_use", "browser", "cronjob", "delegation"):
            self.assertNotIn(dangerous, tools)

    def test_second_message_resumes_the_users_session(self):
        fake = hb.RUNNER = FakeHermes((0, "Noted\n\nsession_id: s-503\n"), (0, "Mango\n\nsession_id: s-503\n"))
        self.assertEqual(hb.ask("503", "my fruit is mango")["text"], "Noted")
        self.assertEqual(hb.ask("503", "what is my fruit?")["text"], "Mango")
        self.assertNotIn("--resume", fake.calls[0][0])
        second = fake.calls[1][0]
        self.assertEqual(second[second.index("--resume") + 1], "s-503")

    def test_sessions_are_per_user(self):
        fake = hb.RUNNER = FakeHermes((0, "A\n\nsession_id: s-a\n"), (0, "B\n\nsession_id: s-b\n"))
        hb.ask("504", "hi"); hb.ask("505", "hi")
        self.assertNotIn("--resume", fake.calls[1][0])

    def test_failure_or_timeout_returns_none(self):
        hb.RUNNER = FakeHermes((1, "error"))
        self.assertIsNone(hb.ask("506", "hi"))
        hb.RUNNER = FakeHermes(subprocess.TimeoutExpired("hermes", 90))
        self.assertIsNone(hb.ask("507", "hi"))

    def test_stale_session_is_retried_fresh(self):
        hb.RUNNER = FakeHermes((0, "x\n\nsession_id: old\n"))
        hb.ask("508", "hi")
        fake = hb.RUNNER = FakeHermes((1, "session not found"), (0, "Fresh\n\nsession_id: new\n"))
        self.assertEqual(hb.ask("508", "hi again")["text"], "Fresh")
        self.assertIn("--resume", fake.calls[0][0])
        self.assertNotIn("--resume", fake.calls[1][0])

    def test_missing_hermes_returns_none(self):
        os.environ["HERMES_BIN"] = "/nonexistent/hermes"
        try:
            self.assertIsNone(hb.ask("509", "hi"))
        finally:
            os.environ["HERMES_BIN"] = FAKE_BIN

    def test_meal_estimate_is_parsed_and_sanity_checked(self):
        hb.RUNNER = FakeHermes((0, 'Sure: {"kcal": 452.4, "protein_g": 31, "carbs_g": 40, "fat_g": 16}\n\nsession_id: e\n'))
        self.assertEqual(hb.estimate_meal("chicken salad"),
                         {"kcal": 452, "protein_g": 31.0, "carbs_g": 40.0, "fat_g": 16.0})
        hb.RUNNER = FakeHermes((0, '{"kcal": 99999, "protein_g": 1, "carbs_g": 1, "fat_g": 1}\n'))
        self.assertIsNone(hb.estimate_meal("everything"))
        hb.RUNNER = FakeHermes((0, "I am not sure.\n"))
        self.assertIsNone(hb.estimate_meal("???"))


if __name__ == "__main__":
    unittest.main()
