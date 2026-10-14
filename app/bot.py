"""
Main bot loop — long polling (getUpdates). No public server / webhook needed,
ideal for a self-hosted exam project. Run:  python3 app/bot.py
Requires: TELEGRAM_TOKEN, DIET_DB env vars; run db.init_db() once first.

This is the ROUTER: it turns each Telegram update into a ctx dict and dispatches
to the right handler in handlers.py. Slash commands, button taps (callback_query),
photos, and free text are all routed here.
"""
import sys, os, re, time, json, urllib.request
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "shared"))
import handlers as H
import onboarding, db, pending
from concurrent.futures import ThreadPoolExecutor
from telegram_io import API, _token, send_text
import telegram_menu as menu

# command -> handler
COMMANDS = {
    "start": H.onboard_start, "menu": H.show_menu, "help": H.show_help,
    "check": lambda c: H.check_food(c) if c.get("text") or c.get("photo_path")
             else __import__("telegram_io").send_menu(c["chat_id"],"How to check?",menu.check_menu()),
    "today": H.show_today, "week": H.show_week, "month": H.show_month,
    "plan": H.plan_week, "shopping": H.show_shopping, "tonight": H.show_tonight,
    "log": H.log_meal, "symptom": H.log_symptom, "report": H.show_report,
    "card": H.allergy_card, "tired": H.too_tired, "profile": H.show_profile,
}
# callback_data -> handler
CALLBACKS = {
    "act:menu": H.show_menu, "act:check": lambda c: H.check_food(c),
    "act:today": H.show_today, "act:week": H.show_week, "act:month": H.show_month,
    "act:plan": H.plan_week, "act:shopping": H.show_shopping,
    "act:tonight": H.show_tonight, "act:tired": H.too_tired, "act:profile": H.show_profile,
    "act:log": H.log_meal, "act:symptom": H.log_symptom, "act:report": H.show_report,
    "act:card": H.allergy_card,
    "check:photo": H.prompt_check_photo, "check:barcode": H.prompt_check_barcode,
    "check:text": H.prompt_check_text, "check:menu": H.prompt_check_menu,
    "log:text": H.prompt_log_text, "log:photo": H.prompt_log_photo, "log:voice": H.prompt_log_voice,
}
MEAL_ACTIONS = {"cook": H.meal_cook, "swap": H.meal_swap, "reswap": H.meal_swap, "recipe": H.meal_recipe}
# what a plain message means right after a "Type it"-style button (see app/pending.py)
PENDING = {"check_text": H.check_food, "log_text": H.log_meal, "symptom_text": H.log_symptom}
SAFETY_QUESTION = re.compile(r"\b(can i (eat|have|drink)|is (this|it|that) safe|safe to eat|does (this|it) (have|contain))\b")
TIRED = re.compile(r"\b(tired|exhausted|no time|lazy)\b")
PLAN_REQUEST = re.compile(r"\bplan (my|the|a|this) (week|meals)\b")

# Free chat goes to the Hermes agent, which takes 10-20 s: run it off the polling
# loop so other users are not kept waiting. Two workers bound the memory used.
RUN_INLINE = False  # tests set True
_POOL = ThreadPoolExecutor(max_workers=2)

def _background(fn, ctx):
    if RUN_INLINE: return fn(ctx)
    def run():
        try: fn(ctx)
        except Exception as e: print("background error:", e)
    _POOL.submit(run)

def _ctx(chat_id, telegram_id, **kw):
    d = {"chat_id": chat_id, "telegram_id": str(telegram_id)}; d.update(kw); return d

def _download_photo(file_id):
    info = json.load(urllib.request.urlopen(API(_token(),"getFile")+f"?file_id={file_id}"))
    path = info["result"]["file_path"]
    url = f"https://api.telegram.org/file/bot{_token()}/{path}"
    dest = f"/tmp/tg_{file_id}.jpg"
    urllib.request.urlretrieve(url, dest); return dest

def _allowed(telegram_id):
    """ALLOWED_TELEGRAM_IDS="id1,id2" restricts the bot; unset = open to everyone."""
    ids = os.environ.get("ALLOWED_TELEGRAM_IDS", "").strip()
    return not ids or str(telegram_id) in {i.strip() for i in ids.split(",")}

def handle_update(u):
    sender = (u.get("message") or u.get("callback_query") or {}).get("from", {}).get("id")
    if not _allowed(sender):
        return
    if "message" in u:
        m = u["message"]; chat = m["chat"]["id"]; uid = m["from"]["id"]
        if onboarding.in_progress(uid):  # mid-sign-up: answers go to the current question
            text = (m.get("text") or "").strip()
            if text.split("@")[0] == "/start": H.onboard_start(_ctx(chat, uid)); return
            if text and not text.startswith("/") and re.sub(r"[^a-z]", "", text.lower()) not in COMMANDS:
                onboarding.handle(_ctx(chat, uid, text=text))
            else:
                onboarding.reask(_ctx(chat, uid))
            return
        if "photo" in m:
            pending.take(uid)
            p = _download_photo(m["photo"][-1]["file_id"])
            H.check_food(_ctx(chat, uid, photo_path=p, source="photo")); return
        text = (m.get("text") or "").strip()
        if not text:  # voice note, sticker, file...
            send_text(chat, "I can read text and photos. Voice notes aren't supported yet — please type instead.")
            return
        word = re.sub(r"[^a-z]", "", text.lower())
        if word in COMMANDS:  # a button from the grid ("📊 Today") or a typed command word
            text = "/" + word
        if text.startswith("/"):
            pending.take(uid)  # a new command cancels a pending "type it" prompt
            cmd = text[1:].split()[0].split("@")[0]
            arg = text[len(cmd)+1:].strip()
            fn = COMMANDS.get(cmd, H.show_menu)
            fn(_ctx(chat, uid, text=arg or None)); return
        ctx = _ctx(chat, uid, text=text, source="text")
        kind = pending.take(uid)
        if kind in PENDING:
            PENDING[kind](ctx); return
        low = text.lower()
        if SAFETY_QUESTION.search(low):
            H.check_food(ctx); return
        if TIRED.search(low):
            H.too_tired(ctx); return
        if PLAN_REQUEST.search(low):
            H.plan_week(ctx); return
        _background(H.chat, ctx)  # everything else: conversation with the Hermes agent
    elif "callback_query" in u:
        cq = u["callback_query"]; chat = cq["message"]["chat"]["id"]; uid = cq["from"]["id"]
        data = cq.get("data","")
        ctx = _ctx(chat, uid)
        if data.startswith("onboard:"): onboarding.handle(_ctx(chat, uid, data=data))
        elif onboarding.in_progress(uid): onboarding.reask(ctx)
        else:
            pending.take(uid)  # a tap cancels a pending "type it" prompt (handlers may set a new one)
            if data in CALLBACKS: CALLBACKS[data](ctx)
            elif data.startswith("sym:"): H.symptom_button(ctx, data[4:])
            elif data.startswith("meal:") and data.count(":") == 3:
                _, action, date, meal_type = data.split(":")
                if action in MEAL_ACTIONS: MEAL_ACTIONS[action](ctx, date, meal_type)
            elif data.startswith("buy:"): H.item_bought(ctx, data[4:])
            elif data.startswith("nostock:"): H.item_unavailable(ctx, data[8:])
        _ack(cq["id"])

def _ack(cq_id):
    try: urllib.request.urlopen(API(_token(),"answerCallbackQuery")+f"?callback_query_id={cq_id}")
    except Exception: pass

def main():
    db.init_db()  # creates tables added since the DB was made (idempotent)
    offset = None
    print("Bot polling… (Ctrl-C to stop)")
    while True:
        url = API(_token(),"getUpdates")+"?timeout=30"+(f"&offset={offset}" if offset else "")
        try:
            data = json.load(urllib.request.urlopen(url, timeout=35))
        except Exception as e:
            print("poll error:", e); time.sleep(3); continue
        for u in data.get("result", []):
            offset = u["update_id"] + 1
            try: handle_update(u)
            except Exception as e: print("handler error:", e)

if __name__ == "__main__":
    main()
