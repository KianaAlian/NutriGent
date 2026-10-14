"""
Bridge from the Telegram bot to the Hermes agent, used for open conversation
and for meal-calorie estimates.

- One Hermes session per Telegram user (table hermes_sessions), resumed on every
  message, so the agent remembers the conversation.
- The user's text goes in on stdin (--query-file -), never through a shell or
  the argument list.
- Only harmless toolsets are enabled: no terminal, files, code execution,
  browser or computer use — a Telegram user cannot make the agent run commands.
- Every function returns None when Hermes is missing, slow or failing, so the
  bot can fall back to its menu.
Configure with HERMES_BIN (path to the hermes command) and HERMES_TIMEOUT.
"""
import os, sys, re, json, shutil, subprocess
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "shared"))
import db

TOOLSETS = "memory,session_search,skills,web,vision"
MAX_TURNS = "6"


def _bin():
    b = os.environ.get("HERMES_BIN") or shutil.which("hermes")
    return b if b and os.path.exists(b) else None

def _run(args, stdin, timeout):
    p = subprocess.run(args, input=stdin, capture_output=True, text=True, timeout=timeout)
    return p.returncode, p.stdout

RUNNER = _run  # tests replace this with a fake


def parse(out):
    """Hermes quiet output -> (reply text, session id, image paths from MEDIA: lines)."""
    lines, sid, images = [], None, []
    for line in (out or "").splitlines():
        s = line.strip()
        if s.startswith("session_id:"):
            sid = s.split(":", 1)[1].strip(); continue
        if s.startswith("↻ Resumed session"):
            continue
        if s.startswith("MEDIA:"):
            path = s[len("MEDIA:"):].strip()
            if os.path.isfile(path): images.append(path)
            continue
        lines.append(line)
    return "\n".join(lines).strip(), sid, images


# ---------- per-user sessions ----------
def _session(tid):
    c = db.conn()
    row = c.execute("SELECT session_id FROM hermes_sessions WHERE telegram_id=?", (str(tid),)).fetchone()
    c.close()
    return row["session_id"] if row else None

def _save_session(tid, sid):
    c = db.conn()
    c.execute("INSERT OR REPLACE INTO hermes_sessions(telegram_id,session_id,updated_at) VALUES(?,?,datetime('now'))",
              (str(tid), sid))
    c.commit(); c.close()

def _forget(tid):
    c = db.conn(); c.execute("DELETE FROM hermes_sessions WHERE telegram_id=?", (str(tid),)); c.commit(); c.close()


def _call(stdin, extra, source, timeout):
    b = _bin()
    if not b:
        return None
    args = [b, "chat", "--query-file", "-", "-Q", "--oneshot", "-t", TOOLSETS,
            "--max-turns", MAX_TURNS, "--source", source] + extra
    try:
        rc, out = RUNNER(args, stdin, timeout)
    except (subprocess.TimeoutExpired, OSError):
        return None
    return parse(out) if rc == 0 else None


def ask(telegram_id, text, context=""):
    """Send a chat message to the user's Hermes session. -> {"text", "images"} or None."""
    timeout = int(os.environ.get("HERMES_TIMEOUT", "120"))
    stdin = f"{context}\n\nUser message: {text}" if context else text
    sid = _session(telegram_id)
    res = _call(stdin, ["--resume", sid] if sid else [], "nutrigent-bot", timeout)
    if res is None and sid:  # stale or broken session: start a fresh one
        _forget(telegram_id)
        res = _call(stdin, [], "nutrigent-bot", timeout)
    if res is None or (not res[0] and not res[2]):
        return None
    reply, new_sid, images = res
    if new_sid:
        _save_session(telegram_id, new_sid)
    return {"text": reply, "images": images}


def estimate_meal(text):
    """Calories and macros for a described meal -> dict or None. Not tied to a user session."""
    prompt = ("Estimate the nutrition of this meal as one adult portion: " + json.dumps(text) +
              '\nReply with ONLY one JSON object, e.g. {"kcal": 450, "protein_g": 30, "carbs_g": 40, "fat_g": 15}.')
    res = _call(prompt, ["--ignore-rules"], "nutrigent-estimate", 60)
    if not res:
        return None
    m = re.search(r"\{.*?\}", res[0], re.S)
    try:
        d = json.loads(m.group()) if m else None
        est = {k: float(d[k]) for k in ("kcal", "protein_g", "carbs_g", "fat_g")}
    except (ValueError, TypeError, KeyError):
        return None
    if not 0 < est["kcal"] < 5000 or any(not 0 <= est[k] <= 500 for k in ("protein_g", "carbs_g", "fat_g")):
        return None
    est["kcal"] = round(est["kcal"])
    return est
