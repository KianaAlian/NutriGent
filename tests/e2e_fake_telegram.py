"""
End-to-end test against a simulated Telegram.

Starts a fake Telegram Bot API (getUpdates, sendMessage, sendPhoto, getFile,
answerCallbackQuery) on 127.0.0.1 that rejects messages breaking Telegram's HTML
rules and non-PNG photos, points the UNMODIFIED app/bot.py polling loop at it,
then drives a scripted session: every command, every button, photos, free text
and a full sign-up by a brand-new user. No real Telegram token or network needed.

Usage:  python3 tests/e2e_fake_telegram.py [work_dir]
Output: a line per action, a summary, <work_dir>/report.json, <work_dir>/photos/*.png
"""
import sys, os, json, re, time, threading, datetime as dt, urllib.parse
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
WORK = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "/tmp/nutrigent-e2e")
os.makedirs(os.path.join(WORK, "photos"), exist_ok=True)
DB = os.path.join(WORK, "e2e.db")
if os.path.exists(DB): os.remove(DB)
os.environ.update(DIET_DB=DB, DIET_CHART_DIR=os.path.join(WORK, "charts"),
                  TELEGRAM_TOKEN="123:LOCALTEST", MPLBACKEND="Agg")
os.environ.pop("OPENAI_API_KEY", None)

# ---------------- fake Telegram Bot API ----------------
LOCK = threading.Lock()
UPDATES, SENT, SEEN_OFFSET = [], [], [0]
ALLOWED_TAGS = {"b", "strong", "i", "em", "u", "ins", "s", "strike", "del", "a", "code",
                "pre", "span", "tg-spoiler", "blockquote", "tg-emoji"}

def html_error(text):
    """Mimic Telegram parse_mode=HTML validation."""
    for m in re.finditer(r"<(/?)([a-zA-Z-]*)", text or ""):
        if m.group(2).lower() not in ALLOWED_TAGS:
            return f"Bad Request: can't parse entities: Unsupported start tag \"{m.group(2)}\""
    for m in re.finditer(r"&(?!(lt|gt|amp|quot|#\d+);)", text or ""):
        return "Bad Request: can't parse entities: Can't find end of the entity"
    return None

def parse_multipart(body, ctype):
    boundary = ctype.split("boundary=")[1].encode()
    fields, files = {}, {}
    for part in body.split(b"--" + boundary):
        if b"Content-Disposition" not in part: continue
        head, _, data = part.partition(b"\r\n\r\n")
        data = data[:-2] if data.endswith(b"\r\n") else data
        name = re.search(rb'name="([^"]+)"', head).group(1).decode()
        if b"filename=" in head: files[name] = data
        else: fields[name] = data.decode()
    return fields, files

class FakeTelegram(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _json(self, code, obj):
        b = json.dumps(obj).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

    def do_GET(self):
        u = urllib.parse.urlparse(self.path); q = dict(urllib.parse.parse_qsl(u.query))
        if u.path.startswith("/file/"):
            b = open(os.path.join(REPO, "sample-visuals", "06_verdict_safe.png"), "rb").read()
            self.send_response(200); self.send_header("Content-Length", str(len(b)))
            self.end_headers(); self.wfile.write(b); return
        method = u.path.rsplit("/", 1)[-1]
        if method == "getUpdates":
            off = int(q.get("offset", 0))
            with LOCK: SEEN_OFFSET[0] = max(SEEN_OFFSET[0], off)
            for _ in range(20):
                with LOCK: res = [x for x in UPDATES if x["update_id"] >= off]
                if res: return self._json(200, {"ok": True, "result": res})
                time.sleep(0.05)
            return self._json(200, {"ok": True, "result": []})
        if method == "getFile":
            return self._json(200, {"ok": True, "result": {"file_path": "photos/f.jpg"}})
        if method == "answerCallbackQuery":
            return self._json(200, {"ok": True, "result": True})
        self._json(404, {"ok": False, "description": "unknown " + method})

    def do_POST(self):
        method = self.path.rsplit("/", 1)[-1]
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        ctype = self.headers.get("Content-Type", "")
        if method == "sendPhoto":
            fields, files = parse_multipart(body, ctype)
            photo = files.get("photo", b"")
            err = html_error(fields.get("caption")) or (None if photo[:8] == b"\x89PNG\r\n\x1a\n" else "photo is not a PNG")
            fname = None
            if not err:
                with LOCK: fname = f"{len(SENT):03d}.png"
                open(os.path.join(WORK, "photos", fname), "wb").write(photo)
            rec = {"method": "photo", "caption": fields.get("caption", ""), "file": fname, "error": err}
        else:
            data = json.loads(body or b"{}")
            err = html_error(data.get("text")) if method == "sendMessage" else None
            rec = {"method": method, "text": data.get("text"), "error": err,
                   "buttons": [b["text"] for row in (data.get("reply_markup") or {}).get("inline_keyboard", []) for b in row]}
        with LOCK: SENT.append(rec)
        if err: return self._json(400, {"ok": False, "description": err})
        self._json(200, {"ok": True, "result": {}})

srv = ThreadingHTTPServer(("127.0.0.1", 0), FakeTelegram)
BASE = f"http://127.0.0.1:{srv.server_address[1]}"
threading.Thread(target=srv.serve_forever, daemon=True).start()

# ---------------- the real bot, pointed at the fake API ----------------
sys.path.insert(0, os.path.join(REPO, "shared")); sys.path.insert(0, os.path.join(REPO, "app"))
import telegram_io
telegram_io.API = lambda tok, m: f"{BASE}/bot{tok}/{m}"
import db; db.init_db()
import bot, urllib.request
LOGS = []
bot.print = lambda *a: LOGS.append(" ".join(map(str, a)))
def _download_photo(file_id):  # same as bot._download_photo, but the file host is local
    info = json.load(urllib.request.urlopen(bot.API(bot._token(), "getFile") + f"?file_id={file_id}"))
    dest = os.path.join(WORK, f"tg_{file_id}.jpg")
    urllib.request.urlretrieve(f"{BASE}/file/bot{bot._token()}/{info['result']['file_path']}", dest); return dest
bot._download_photo = _download_photo

# seed: existing user with profile, logs, pantry, weights
c = db.conn()
c.execute("INSERT INTO users(telegram_id,name,timezone) VALUES('1001','Sara','Europe/Rome')")
c.execute("""INSERT INTO dietary_profiles(user_id,allergies_json,diet_type,goal,daily_kcal,protein_g,carbs_g,fat_g,max_cook_minutes)
             VALUES(1,?,?,?,?,?,?,?,?)""",
          (json.dumps([{"allergen": "peanut", "severity": "anaphylactic"}, {"allergen": "milk", "severity": "mild"}]),
           "vegetarian", "lose", 1729, 130, 173, 58, 30))
today = dt.date.today()
for i in range(20):
    d = (today - dt.timedelta(days=i)).isoformat()
    c.execute("INSERT INTO food_log(user_id,ts,source,item,verdict,kcal,protein_g,carbs_g,fat_g) VALUES(1,?,?,?,?,?,?,?,?)",
              (d + " 12:00", "text", "lunch", "logged", 1400 + (i * 37) % 500, 80, 150, 50))
    if i % 3 == 0: c.execute("INSERT INTO weight_log(user_id,date,weight_kg) VALUES(1,?,?)", (d, 70 + i * 0.05))
for ing, q, u in [("chickpeas", 400, "g"), ("rice", 1000, "g"), ("spinach", 100, "g")]:
    c.execute("INSERT INTO pantry(user_id,ingredient,quantity,unit) VALUES(1,?,?,?)", (ing, q, u))
c.commit(); c.close()

threading.Thread(target=bot.main, daemon=True).start()
for _ in range(200):  # wait until the bot is polling, so its start-up line is not counted
    if any("Bot polling" in l for l in LOGS): break
    time.sleep(0.05)

# ---------------- driver ----------------
NEXT = [1]
def fire(label, payload, who=1001):
    uid = NEXT[0]; NEXT[0] += 1
    upd = {"update_id": uid}
    if payload.get("cb"):
        upd["callback_query"] = {"id": str(uid), "data": payload["cb"], "from": {"id": who},
                                 "message": {"chat": {"id": who}}}
    else:
        m = {"message_id": uid, "chat": {"id": who}, "from": {"id": who}}
        m.update({k: v for k, v in payload.items()}); upd["message"] = m
    with LOCK: n_sent, n_log = len(SENT), len(LOGS); UPDATES.append(upd)
    t0 = time.time()
    while time.time() - t0 < 30:
        with LOCK:
            if SEEN_OFFSET[0] > uid: break
        time.sleep(0.02)
    time.sleep(0.15)
    with LOCK: out, logs = SENT[n_sent:], LOGS[n_log:]
    status = "ERROR" if (logs or any(o["error"] for o in out)) else ("NO REPLY" if not out else "replied")
    return {"label": label, "user": who, "input": payload, "status": status, "sent": out, "logs": logs,
            "secs": round(time.time() - t0, 2)}

T = lambda t: {"text": t}
CB = lambda d: {"cb": d}
SCRIPT = [
  # ---- existing user: slash commands
  ("/start", T("/start")), ("/menu", T("/menu")), ("/help", T("/help")),
  ("/check (no arg)", T("/check")), ("/check peanut butter cookies", T("/check peanut butter cookies")),
  ("/check rice salad", T("/check rice salad")),
  ("/today", T("/today")), ("/week", T("/week")), ("/month", T("/month")),
  ("/plan", T("/plan")), ("/shopping", T("/shopping")), ("/tonight", T("/tonight")),
  ("/log chicken salad", T("/log chicken salad")), ("/tired", T("/tired")),
  ("/symptom bloating after lunch", T("/symptom bloating after lunch")),
  ("/report", T("/report")), ("/card", T("/card")), ("/profile", T("/profile")),
  ("/unknowncommand", T("/unknowncommand")),
  # ---- main menu buttons
  *[(f"button {d}", CB(d)) for d in ["act:menu", "act:check", "act:today", "act:plan", "act:shopping",
     "act:tonight", "act:tired", "act:week", "act:month", "act:log", "act:symptom", "act:report",
     "act:profile", "act:card"]],
  # ---- other inline keyboards the code defines
  *[(f"button {d}", CB(d)) for d in ["check:photo", "check:barcode", "check:text", "check:menu",
     "log:photo", "log:text", "log:voice", "sym:bloating", "sym:other",
     f"meal:cook:{today}:dinner", f"meal:swap:{today}:dinner", f"meal:recipe:{today}:dinner",
     "buy:1", "nostock:2", "onboard:goal:lose"]],
  # ---- photos & free text
  ("photo of a label", {"photo": [{"file_id": "small"}, {"file_id": "big"}]}),
  ("photo with caption", {"photo": [{"file_id": "cap"}], "caption": "is this ok?"}),
  ("text: hello", T("hello")), ("text: thanks!", T("thanks!")),
  ("text: can I eat tiramisu?", T("can I eat tiramisu?")),
  ("text: I'm so tired today", T("I'm so tired today")), ("text: plan my week", T("plan my week")),
  ("text with <: is <3 cookies safe?", T("is <3 cookies safe?")),
  ("text with &: mac & cheese", T("mac & cheese")),
  ("Persian text", T("سلام، امروز چی بخورم؟")),
  ("voice note (no text)", {"voice": {"file_id": "v1", "duration": 3}}),
]
NEW_USER = [
  ("NEW: /start", T("/start")), ("NEW: name", T("Nima")),
  ("NEW: tap Milk", CB("onboard:allergy:milk")), ("NEW: types kiwi", T("kiwi")),
  ("NEW: grid button mid-signup", T("📊 Today")), ("NEW: tap Done", CB("onboard:allergy:done")),
  ("NEW: severity milk", CB("onboard:severity:severe")), ("NEW: severity kiwi", CB("onboard:severity:mild")),
  ("NEW: diet", CB("onboard:diet:halal")), ("NEW: goal", CB("onboard:goal:gain")), ("NEW: sex", CB("onboard:sex:male")),
  ("NEW: age bad", T("abc")), ("NEW: age", T("25")), ("NEW: height", T("190 cm")), ("NEW: weight", T("70kg")),
  ("NEW: activity", CB("onboard:activity:moderate")), ("NEW: cook time", CB("onboard:max_minutes:15")),
  ("NEW: /today after signup", T("/today")), ("NEW: /profile", T("/profile")), ("NEW: /start again", T("/start")),
  ("NEW: check milk chocolate", T("/check milk chocolate")),
]
results = [fire(l, p) for l, p in SCRIPT] + [fire(l, p, who=2002) for l, p in NEW_USER]
db_users = db.conn().execute("SELECT COUNT(*) FROM users").fetchone()[0]
json.dump({"base": BASE, "results": results, "users_in_db_after": db_users},
          open(os.path.join(WORK, "report.json"), "w"), indent=1, ensure_ascii=False, default=str)
for r in results:
    first = (r["sent"][0].get("caption") or r["sent"][0].get("text") or "") if r["sent"] else ""
    extra = (" | " + r["logs"][0][:90]) if r["logs"] else (" | " + next((o["error"] for o in r["sent"] if o["error"]), "")[:90] if any(o["error"] for o in r["sent"]) else "")
    print(f"{r['status']:8} {r['label'][:38]:38} -> {len(r['sent'])} msg | {first[:55]!r}{extra}")
print("users in DB after test:", db_users)
import collections
print("SUMMARY:", len(results), "actions |", dict(collections.Counter(r["status"] for r in results)))
