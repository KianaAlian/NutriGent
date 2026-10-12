"""
Sign-up conversation: one question at a time. The current question and the
answers so far live in the onboarding_state table, so a restart never loses
them and an answer is never asked for twice. bot.py sends every message and
onboard:* tap from a user who is mid-sign-up to handle().
"""
import os, sys, re, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "shared"))

import db
from telegram_io import send_text, send_menu
import telegram_menu as menu

SEVERITIES = ("mild", "moderate", "severe", "anaphylactic")
# step -> accepted values (callback value or a typed word containing it); order matters ("female" before "male")
CHOICES = {
    "diet": ("none", "vegetarian", "vegan", "halal", "keto", "paleo", "gluten_free", "other"),
    "goal": ("lose", "maintain", "gain", "energy_health"),
    "sex": ("female", "male"),
    "activity": ("sedentary", "light", "moderate", "active", "athlete"),
    "max_minutes": ("15", "30", "45", "60"),
}
NUMBERS = {"age": (13, 100), "height": (120, 230), "weight": (30, 300)}  # sane human ranges
ORDER = ["name", "allergies", "severity", "diet", "goal", "sex", "age", "height", "weight", "activity", "max_minutes"]
FIELD = {"allergies": "allergy"}  # callback field name when it differs from the step name


# ---------- state ----------
def _load(tid):
    c = db.conn()
    row = c.execute("SELECT step, answers_json FROM onboarding_state WHERE telegram_id=?", (str(tid),)).fetchone()
    c.close()
    return (row["step"], json.loads(row["answers_json"])) if row else None

def _save(tid, step, answers):
    c = db.conn()
    c.execute("INSERT OR REPLACE INTO onboarding_state(telegram_id,step,answers_json,updated_at) "
              "VALUES(?,?,?,datetime('now'))", (str(tid), step, json.dumps(answers)))
    c.commit(); c.close()

def _clear(tid):
    c = db.conn(); c.execute("DELETE FROM onboarding_state WHERE telegram_id=?", (str(tid),)); c.commit(); c.close()

def in_progress(tid):
    return _load(tid) is not None

def begin(ctx):
    """Start (or restart) sign-up at the name question. The caller sends the welcome."""
    _save(ctx["telegram_id"], "name", {})


# ---------- questions ----------
def _pending_severity(a):
    return next((p for p in a.get("allergies", []) if not p.get("severity")), None)

def _question(step, a):
    name = a.get("name", "")
    if step == "name":
        return "First, what should I call you?", None
    if step == "allergies":
        picked = [p["allergen"] for p in a.get("allergies", [])]
        return (f"Nice to meet you, {name}! Do you have any food allergies? Tap all that apply "
                "(or type others, e.g. kiwi), then tap Done.", menu.onboarding_allergy_menu(picked))
    if step == "severity":
        return f"How severe is your {_pending_severity(a)['allergen']} allergy?", menu.onboarding_severity_menu()
    if step == "diet":
        return "Do you follow a particular diet?", menu.onboarding_diet_menu()
    if step == "goal":
        return f"What's your main goal, {name}?", menu.onboarding_goal_menu()
    if step == "sex":
        return "For your calorie target: are you male or female?", menu.onboarding_sex_menu()
    if step == "age":
        return "How old are you? (years)", None
    if step == "height":
        return "Your height in cm?", None
    if step == "weight":
        return "Your weight in kg?", None
    if step == "activity":
        return "How active are you on a normal week?", menu.onboarding_activity_menu()
    if step == "max_minutes":
        return "How long can you usually spend cooking?", menu.onboarding_cook_time_menu()

def _ask(ctx, step, a, prefix=""):
    text, kb = _question(step, a)
    if kb: send_menu(ctx["chat_id"], prefix + text, kb)
    else: send_text(ctx["chat_id"], prefix + text)

def reask(ctx):
    st = _load(ctx["telegram_id"])
    if st: _ask(ctx, st[0], st[1], prefix="Let's finish setting you up first.\n\n")

def _advance(ctx, a, step):
    _save(ctx["telegram_id"], step, a)
    _ask(ctx, step, a)


# ---------- answers ----------
def _tap(ctx):
    """'onboard:<field>:<value>' -> (field, value); (None, None) for typed text."""
    parts = (ctx.get("data") or "").split(":", 2)
    return (parts[1], parts[2]) if len(parts) == 3 and parts[0] == "onboard" else (None, None)

def _choice(step, value, text):
    if value is not None:
        return value if value in CHOICES[step] else None
    word = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return next((c for c in CHOICES[step] if c in word), None)

def handle(ctx):
    tid = ctx["telegram_id"]
    st = _load(tid)
    if st is None:  # stale onboarding button after sign-up finished, or never started
        import handlers
        return handlers.onboard_start(ctx)
    step, a = st
    field, value = _tap(ctx)
    text = (ctx.get("text") or "").strip()
    if field is not None and field != FIELD.get(step, step):  # a button from an earlier question
        return _ask(ctx, step, a)

    if step == "name":
        if field or not text:
            return _ask(ctx, step, a)
        a["name"] = text[:40]
        return _advance(ctx, a, "allergies")

    if step == "allergies":
        picked = a.setdefault("allergies", [])
        names = [p["allergen"] for p in picked]
        word = (value or text).lower()
        if word in ("done", "ok", "finished"):
            return _advance(ctx, a, "severity" if picked else "diet")
        if word in ("none", "no", "nothing", "no allergies"):
            a["allergies"] = []
            return _advance(ctx, a, "diet")
        if field:  # a tap toggles
            if value in names: picked[:] = [p for p in picked if p["allergen"] != value]
            else: picked.append({"allergen": value, "severity": None})
        else:      # typed: "kiwi, mustard and celery"
            for n in (w.strip().lower() for w in re.split(r",|\band\b", text)):
                if n and n not in names:
                    picked.append({"allergen": n, "severity": None}); names.append(n)
        _save(tid, step, a)
        now = ", ".join(p["allergen"] for p in picked) or "nothing yet"
        return send_menu(ctx["chat_id"], f"Your allergies: {now}. Tap more, or Done.",
                         menu.onboarding_allergy_menu([p["allergen"] for p in picked]))

    if step == "severity":
        level = (value or text).lower().split(":")[0]
        if level not in SEVERITIES:
            return _ask(ctx, step, a, prefix="Please tap one of the buttons.\n\n")
        _pending_severity(a)["severity"] = level
        return _advance(ctx, a, "severity" if _pending_severity(a) else "diet")

    if step in CHOICES:
        picked = _choice(step, value, text)
        if picked is None:
            if step == "diet" and text and not field:  # any other diet, typed
                picked = text[:40].lower()
            else:
                return _ask(ctx, step, a, prefix="Please tap one of the buttons.\n\n")
        a[step] = picked
        nxt = ORDER[ORDER.index(step) + 1] if step != "max_minutes" else None
        return _advance(ctx, a, nxt) if nxt else _finish(ctx, a)

    if step in NUMBERS:
        lo, hi = NUMBERS[step]
        m = None if field else re.search(r"\d+(?:[.,]\d+)?", text)
        num = float(m.group().replace(",", ".")) if m else None
        if num is None or not lo <= num <= hi:
            return _ask(ctx, step, a, prefix=f"Please send a number between {lo} and {hi}.\n\n")
        a[step] = num
        return _advance(ctx, a, ORDER[ORDER.index(step) + 1])


def _finish(ctx, a):
    import handlers
    _clear(ctx["telegram_id"])
    handlers.onboard_save(ctx, {
        "name": a["name"], "sex": a["sex"], "age": a["age"], "height": a["height"], "weight": a["weight"],
        "activity": a["activity"], "goal": a["goal"], "diet": a["diet"],
        "allergies": [{"allergen": p["allergen"], "severity": p["severity"]} for p in a.get("allergies", [])],
        "max_minutes": int(a["max_minutes"]),
    })
