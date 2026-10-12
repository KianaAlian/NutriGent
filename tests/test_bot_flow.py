"""End-to-end offline test: simulate Telegram updates, capture what the bot sends."""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "shared"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

os.environ["DIET_DB"] = "/tmp/bot_flow.db"
if os.path.exists("/tmp/bot_flow.db"): os.remove("/tmp/bot_flow.db")
import db; db.DB_PATH = "/tmp/bot_flow.db"; db.init_db()
import safety_gate; safety_gate.conn = db.conn

# --- monkeypatch telegram_io so nothing hits the network ---
import telegram_io
SENT = []
telegram_io.send_text  = lambda chat, text, reply_markup=None: SENT.append(("text", text[:70]))
telegram_io.send_menu  = lambda chat, text, kb: SENT.append(("menu", text[:40]))
telegram_io.send_photo = lambda chat, path, caption="": SENT.append(("photo", os.path.basename(path), caption[:50]))
telegram_io.set_commands = lambda cmds: None
# handlers imported these names already; patch there too
import handlers
handlers.send_text, handlers.send_menu, handlers.send_photo = (
    telegram_io.send_text, telegram_io.send_menu, telegram_io.send_photo)

# seed a user with a profile + some logs + a shopping list
c = db.conn()
c.execute("INSERT INTO users(telegram_id,name) VALUES('999','Sara')")
uid = c.execute("SELECT id FROM users WHERE telegram_id='999'").fetchone()[0]
c.execute("""INSERT INTO dietary_profiles(user_id,allergies_json,diet_type,goal,
    daily_kcal,protein_g,carbs_g,fat_g,max_cook_minutes) VALUES(?,?,?,?,?,?,?,?,?)""",
    (uid, json.dumps([{"allergen":"peanut","severity":"anaphylactic"},
                      {"allergen":"milk","severity":"mild"}]),
     "vegetarian","lose",1729,130,173,58,30))
import datetime as dt
for _ in range(3):
    c.execute("INSERT INTO food_log(user_id,ts,source,item,verdict,kcal,protein_g,carbs_g,fat_g) "
              "VALUES(?,?,?,?,?,?,?,?,?)",(uid,dt.date.today().isoformat()+" 12:00",
              'schedule','meal','logged',420,30,55,15))
for ing,qty,unit,sec in [("spinach",200,"g","Produce"),("chickpeas",2,"cans","Dry goods"),
                          ("oat milk",1,"L","Dairy-free")]:
    c.execute("INSERT INTO shopping_list_items(user_id,ingredient,quantity,unit,store_section) "
              "VALUES(?,?,?,?,?)",(uid,ing,qty,unit,sec))
c.commit(); c.close()

import bot

def fire(update, label):
    SENT.clear(); bot.handle_update(update)
    print(f"\n>>> {label}")
    for s in SENT: print("   ", s)

msg = lambda t: {"message":{"chat":{"id":999},"from":{"id":999},"text":t}}
photo = {"message":{"chat":{"id":999},"from":{"id":999},
         "photo":[{"file_id":"X"}]}}
cb = lambda d: {"callback_query":{"id":"1","data":d,"from":{"id":999},
                "message":{"chat":{"id":999}}}}

# patch photo download + llm to stay offline
bot._download_photo = lambda fid: "/tmp/fake.jpg"

fire(msg("/today"), "/today  -> dashboard card")
fire(msg("/week"),  "/week   -> weekly chart")
fire(msg("/month"), "/month  -> monthly trend")
fire(msg("/plan"),  "/plan   -> plan card + shopping card")
fire(msg("/profile"), "/profile -> profile card")
fire(msg("/shopping"), "/shopping -> shopping card")
fire(msg("can I eat peanut butter cookies?"), "text safety check -> verdict card")
fire(msg("I'm exhausted"), "friction -> tired fallback")
fire(cb("act:week"), "button tap act:week -> chart")
fire(cb("buy:1"), "button tap buy:1 -> mark bought")

print("\nALL FLOWS RAN ✓")
