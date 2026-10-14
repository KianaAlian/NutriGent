"""
Skill action handlers — the bridge between a Telegram event and the shared code.
Each function takes (ctx) and returns nothing; it sends messages/photos itself.
The actual OpenAI vision/planner CALLS are isolated in llm.py (stubbed) so you
drop your own client in one place. Everything else here is real and runnable.
"""
import sys, os, json, threading, datetime as dt
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "shared"))

import db, reporting, visuals, onboarding, pending, hermes_bridge
from safety_gate import safety_verdict
from nutrition import daily_target
from telegram_io import send_text, send_menu, send_photo, send_chat_action
import telegram_menu as menu
from llm import extract_from_image, extract_from_text, generate_week, estimate_meal  # your engine


# ---------- helpers ----------
def _uid(ctx):
    u = db.user_by_telegram(ctx["telegram_id"])
    return u["id"] if u else None

def _need_profile(ctx):
    uid = _uid(ctx)
    if uid and db.get_profile(uid):
        return uid
    if onboarding.in_progress(ctx["telegram_id"]): onboarding.reask(ctx)
    else: onboard_start(ctx)
    return None


# ---------- menu / help ----------
def show_menu(ctx):
    send_menu(ctx["chat_id"], "What do you need?", menu.main_menu())

def show_help(ctx):
    send_text(ctx["chat_id"],
        "I plan your week, guard your allergies, and track your calories.\n"
        "Tap a button or use the / menu. Send me a photo of any food or label "
        "to check if it's safe.", reply_markup=menu.persistent_main_keyboard())


# ---------- onboarding ----------
def onboard_start(ctx):
    """/start: registered users get the menu back; everyone else starts the sign-up (app/onboarding.py)."""
    uid = _uid(ctx)
    if uid and db.get_profile(uid):
        name = db.user_by_telegram(ctx["telegram_id"])["name"] or "there"
        send_text(ctx["chat_id"], f"Welcome back, {name}! Tap a button below.",
                  reply_markup=menu.persistent_main_keyboard())
        return show_menu(ctx)
    onboarding.begin(ctx)
    send_text(ctx["chat_id"],
        "Hi, I'm NutriGent — your personal diet and allergy assistant. I can "
        "help plan your meals, check foods for allergens, build shopping lists, "
        "track macros, and adapt your plan when life gets busy.\n\n"
        "I'm an assistive tool, not a medical device — for severe allergies, "
        "always double-check labels yourself.\n\n"
        "First, what should I call you?", reply_markup=menu.persistent_main_keyboard())

def onboard_save(ctx, parsed):
    """parsed: dict already extracted from the user's answers."""
    c = db.conn()
    c.execute("INSERT OR IGNORE INTO users(telegram_id,name,timezone) VALUES(?,?,?)",
              (ctx["telegram_id"], parsed.get("name"), parsed.get("tz","UTC")))
    c.execute("UPDATE users SET name=? WHERE telegram_id=?", (parsed.get("name"), ctx["telegram_id"]))
    uid = c.execute("SELECT id FROM users WHERE telegram_id=?", (ctx["telegram_id"],)).fetchone()[0]
    t = daily_target(parsed["sex"], parsed["weight"], parsed["height"],
                     parsed["age"], parsed.get("activity","moderate"), parsed.get("goal","maintain"))
    c.execute("""INSERT OR REPLACE INTO dietary_profiles
        (user_id,allergies_json,diet_type,dislikes_json,goal,daily_kcal,
         protein_g,carbs_g,fat_g,max_cook_minutes,health_flags_json,updated_at)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,datetime('now'))""",
        (uid, json.dumps(parsed.get("allergies",[])), parsed.get("diet"),
         json.dumps(parsed.get("dislikes",[])), parsed.get("goal"),
         t["daily_kcal"], t["protein_g"], t["carbs_g"], t["fat_g"],
         parsed.get("max_minutes",45), json.dumps(parsed.get("health_flags",[]))))
    c.commit(); c.close()
    # register the slash menu once
    try:
        from telegram_io import set_commands
        set_commands(menu.COMMANDS)
    except Exception: pass
    show_profile(ctx)
    send_menu(ctx["chat_id"], "You're set. Plan your week?", menu.main_menu())


# ---------- the safety-critical handler ----------
def check_food(ctx):
    uid = _need_profile(ctx)
    if not uid: return
    profile = db.get_profile(uid)
    if ctx.get("photo_path"):
        extraction = extract_from_image(ctx["photo_path"], profile["allergies"])
    elif ctx.get("text"):
        extraction = extract_from_text(ctx["text"])
    else:
        send_menu(ctx["chat_id"], "How do you want to check?", menu.check_menu()); return

    verdict = safety_verdict(extraction, profile)
    # VISUAL: render a verdict card and send it
    card = visuals.verdict_card(verdict.level, ctx.get("text") or "Scanned item",
                                verdict.reasons + [f"{h['matched_term']} → {h['allergen']} "
                                f"({h['severity']})" for h in verdict.hits],
                                name=f"verdict_{uid}.png")
    send_photo(ctx["chat_id"], card, caption=verdict.message())
    # log it
    c = db.conn()
    c.execute("INSERT INTO food_log(user_id,source,item,verdict,flagged_json) VALUES(?,?,?,?,?)",
              (uid, ctx.get("source","photo"), ctx.get("text","scan"),
               verdict.level.lower(), json.dumps(verdict.hits)))
    c.commit(); c.close()


# ---------- visuals: today / week / month ----------
def show_today(ctx):
    uid = _need_profile(ctx)
    if not uid: return
    _, consumed = reporting.today_chart(uid)
    target = reporting._target(uid)
    card = visuals.day_dashboard(consumed, target, name=f"dash_{uid}.png")
    send_photo(ctx["chat_id"], card,
        caption=f"Today: {consumed['kcal']:.0f}/{target['daily_kcal']} kcal")

def show_week(ctx):
    uid = _need_profile(ctx)
    if not uid: return
    send_photo(ctx["chat_id"], reporting.week_chart(uid), caption="📈 This week's calories")

def show_month(ctx):
    uid = _need_profile(ctx)
    if not uid: return
    send_photo(ctx["chat_id"], reporting.month_chart(uid), caption="🗓 This month's trend")

def show_profile(ctx):
    uid = _need_profile(ctx)
    if not uid: return
    p = db.get_profile(uid)
    c = db.conn(); row = c.execute("SELECT name FROM users WHERE id=?", (uid,)).fetchone(); c.close()
    p["name"] = (row["name"] if row else None) or "Your profile"
    send_photo(ctx["chat_id"], visuals.profile_card(p, name=f"profile_{uid}.png"),
               caption="Tap ⚙️ items in chat to edit.")


# ---------- planning + shopping (visual) ----------
def _section_for(ingredient):
    s = (ingredient or "").lower()
    if any(w in s for w in ("spinach", "tomato", "lettuce", "onion", "potato", "apple", "banana")):
        return "Produce"
    if any(w in s for w in ("rice", "pasta", "chickpea", "bean", "flour", "oat")):
        return "Dry goods"
    if any(w in s for w in ("cod", "chicken", "turkey", "tofu", "egg")):
        return "Protein"
    if any(w in s for w in ("milk", "yogurt", "cheese", "butter")):
        return "Dairy / alternatives"
    return "Other"


def plan_week(ctx):
    uid = _need_profile(ctx)
    if not uid: return
    profile = db.get_profile(uid)
    c = db.conn()
    pantry = [dict(r) for r in c.execute("SELECT * FROM pantry WHERE user_id=?", (uid,)).fetchall()]
    week = generate_week(profile, pantry)          # engine returns plan JSON; still not trusted

    safe_days = []
    monday = dt.date.today() - dt.timedelta(days=dt.date.today().weekday())
    week_start = monday.isoformat()

    # Replace this user's current-week generated rows so /plan is idempotent for demos.
    c.execute("DELETE FROM meal_schedule WHERE user_id=? AND date BETWEEN ? AND ?",
              (uid, week_start, (monday + dt.timedelta(days=6)).isoformat()))
    c.execute("DELETE FROM shopping_list_items WHERE user_id=? AND week_start=? AND status='pending'",
              (uid, week_start))

    needed = {}
    for i, day in enumerate(week.get("days", [])[:7]):
        date = (monday + dt.timedelta(days=i)).isoformat()
        for meal in day.get("meals", [])[:1]:
            ingredients = meal.get("ingredients", [])
            # The recipe's ingredient list is complete (we will cook exactly this), so screen it as a label.
            ext = {"image_type":"ingredient_label", "readability":1.0,
                   "identified_ingredients":[ing.get("name", "") for ing in ingredients]}
            gate = safety_verdict(ext, profile)
            if gate.level in ("UNSAFE", "CAUTION"):
                meal["title"] = meal.get("title", "Meal") + " (needs regeneration)"
            c.execute("""INSERT INTO recipes(title,source,ingredients_json,steps_json,kcal,protein_g,carbs_g,fat_g,cook_minutes,gate_screen_json)
                         VALUES(?,?,?,?,?,?,?,?,?,?)""",
                      (meal.get("title"), "llm" if os.environ.get("OPENAI_API_KEY") else "offline-stub",
                       json.dumps(ingredients), json.dumps(meal.get("steps", [])),
                       meal.get("kcal"), meal.get("protein_g"), meal.get("carbs_g"), meal.get("fat_g"),
                       meal.get("cook_minutes"), json.dumps({"level": gate.level, "hits": gate.hits})))
            recipe_id = c.execute("SELECT last_insert_rowid()").fetchone()[0]
            c.execute("INSERT INTO meal_schedule(user_id,date,meal_type,recipe_id,status) VALUES(?,?,?,?, 'planned')",
                      (uid, date, meal.get("meal_type", "dinner"), recipe_id))
            safe_days.append({"day": (monday+dt.timedelta(days=i)).strftime("%a"),
                              "title": meal.get("title", "Meal"), "kcal": meal.get("kcal", 0),
                              "minutes": meal.get("cook_minutes", 0), "tag": meal.get("leftover_of")})
            for ing in ingredients:
                name = ing.get("name", "").strip()
                if not name: continue
                key = (name.lower(), ing.get("unit") or "")
                needed[key] = needed.get(key, 0) + float(ing.get("qty") or 0)

    pantry_have = {}
    for r in pantry:
        key = ((r.get("ingredient") or "").lower(), r.get("unit") or "")
        pantry_have[key] = pantry_have.get(key, 0) + float(r.get("quantity") or 0)
    for (name, unit), qty in needed.items():
        missing = max(0, qty - pantry_have.get((name, unit), 0))
        if missing <= 0: continue
        c.execute("""INSERT INTO shopping_list_items(user_id,week_start,ingredient,quantity,unit,store_section,status)
                     VALUES(?,?,?,?,?,?, 'pending')""",
                  (uid, week_start, name, round(missing, 1), unit, _section_for(name)))

    send_photo(ctx["chat_id"], visuals.meal_plan_card(safe_days, name=f"plan_{uid}.png"),
               caption="Here's your week. Reply 'swap Tue dinner' to change one.")
    c.commit(); c.close()
    show_shopping(ctx)

def show_shopping(ctx):
    uid = _need_profile(ctx)
    if not uid: return
    c = db.conn()
    rows = c.execute("SELECT id,ingredient,quantity,unit,store_section FROM shopping_list_items "
                     "WHERE user_id=? AND status='pending'", (uid,)).fetchall()
    c.close()
    sections = {}
    for r in rows:
        sections.setdefault(r["store_section"] or "Other", []).append(
            (r["ingredient"], f"{r['quantity'] or ''} {r['unit'] or ''}".strip()))
    if not sections:
        send_text(ctx["chat_id"], "Your shopping list is empty — plan a week first."); return
    send_photo(ctx["chat_id"], visuals.shopping_card(sections, name=f"shop_{uid}.png"),
               caption="🛒 Your shopping list")
    send_menu(ctx["chat_id"], "Tap an item when you've bought it (❌ = not available):",
              menu.shopping_list_keyboard([(r["id"], r["ingredient"]) for r in rows]))

def _shopping_status(ctx, item_id, status, done_text):
    """Mark one of THIS user's shopping items; other users' items are never touched."""
    uid = _need_profile(ctx)
    if not uid: return
    c = db.conn()
    row = c.execute("SELECT ingredient FROM shopping_list_items WHERE id=? AND user_id=?", (item_id, uid)).fetchone()
    if row:
        c.execute("UPDATE shopping_list_items SET status=? WHERE id=? AND user_id=?", (status, item_id, uid))
        c.commit()
    c.close()
    send_text(ctx["chat_id"], done_text.format(item=row["ingredient"]) if row else "That item isn't on your list.")

def item_bought(ctx, item_id):
    _shopping_status(ctx, item_id, "bought", "✓ {item} marked as bought.")

def item_unavailable(ctx, item_id):
    _shopping_status(ctx, item_id, "unavailable",
                     "❌ {item} marked as not available. Ask me in chat for a safe substitute.")


# ---------- friction ----------
def too_tired(ctx):
    uid = _need_profile(ctx)
    if not uid: return
    c = db.conn()
    today = dt.date.today().isoformat()
    c.execute("UPDATE meal_schedule SET status='skipped', status_reason='too tired' WHERE user_id=? AND date=? AND status='planned'",
              (uid, today))
    c.commit(); c.close()
    send_text(ctx["chat_id"],
        "No problem — tonight's meal is paused and moved to tomorrow. "
        "Quick safe option from your pantry: boil the gluten-free pasta, stir in "
        "the canned tomatoes and olive oil. ~12 minutes. I've rebalanced your week.")


# ---------- logging / reports / safety support ----------
def log_meal(ctx):
    uid = _need_profile(ctx)
    if not uid: return
    text = (ctx.get("text") or "").replace("/log", "", 1).strip()
    if not text:
        return send_menu(ctx["chat_id"], "How do you want to log your meal?", menu.log_meal_actions())
    send_chat_action(ctx["chat_id"])
    est = estimate_meal(text)  # model estimate; None when no model is reachable
    kcal, protein, carbs, fat = ((est["kcal"], est["protein_g"], est["carbs_g"], est["fat_g"]) if est
                                 else (None, None, None, None))
    c = db.conn()
    c.execute("""INSERT INTO food_log(user_id,source,item,verdict,kcal,protein_g,carbs_g,fat_g)
                 VALUES(?,?,?,?,?,?,?,?)""",
              (uid, ctx.get("source", "text"), text, "logged", kcal, protein, carbs, fat))
    c.commit(); c.close()  # the planned meal is marked cooked only by its own "Cooking it" button
    _, consumed = reporting.today_chart(uid)
    target = reporting._target(uid)
    what = (f"Logged {text}: ~{kcal} kcal (estimate)." if est
            else f"Logged {text}. I couldn't estimate its calories right now.")
    send_photo(ctx["chat_id"], visuals.day_dashboard(consumed, target, name=f"dash_{uid}.png"),
               caption=f"{what} Today: {consumed['kcal']:.0f}/{target['daily_kcal']} kcal")

def prompt_log_text(ctx, intro=""):
    pending.expect(ctx["telegram_id"], "log_text")
    send_text(ctx["chat_id"], intro + "What did you eat? Type it, e.g. \"large chicken salad with rice\".")

def prompt_log_photo(ctx):
    prompt_log_text(ctx, "Logging from a photo is coming soon. ")

def prompt_log_voice(ctx):
    prompt_log_text(ctx, "Logging from a voice note is coming soon. ")


def log_symptom(ctx):
    uid = _need_profile(ctx)
    if not uid: return
    note = (ctx.get("text") or "").replace("/symptom", "", 1).strip()
    if not note:
        return send_menu(ctx["chat_id"], "What are you feeling?", menu.symptom_picker())
    c = db.conn()
    c.execute("INSERT INTO symptom_log(user_id,symptom,severity,note) VALUES(?,?,?,?)",
              (uid, note[:40], 3, note))
    c.commit(); c.close()
    send_text(ctx["chat_id"], f"Logged: {note}. If this is an allergic reaction, use emergency medication and call emergency services. I'm an assistive tool, not a medical device.")

SYMPTOMS = {"bloating": "bloating", "low_energy": "low energy", "headache": "headache", "skin": "skin irritation"}

def symptom_button(ctx, kind):
    if kind == "other":
        pending.expect(ctx["telegram_id"], "symptom_text")
        return send_text(ctx["chat_id"], "Describe the symptom in a few words, e.g. \"itchy skin after dinner\".")
    ctx["text"] = SYMPTOMS.get(kind, kind)
    log_symptom(ctx)


def show_report(ctx):
    uid = _need_profile(ctx)
    if not uid: return
    send_photo(ctx["chat_id"], reporting.week_chart(uid), caption="📈 This week")
    send_photo(ctx["chat_id"], reporting.month_chart(uid), caption="🗓 This month")
    send_photo(ctx["chat_id"], reporting.week_safety_donut(uid), caption="🛡 Safety checks")


def allergy_card(ctx):
    uid = _need_profile(ctx)
    if not uid: return
    profile = db.get_profile(uid)
    allergies = profile.get("allergies", [])
    severe = [a["allergen"] for a in allergies if a.get("severity") in ("severe", "anaphylactic")]
    all_names = ", ".join(a["allergen"] for a in allergies) or "listed allergens"
    if severe:
        msg = f"I have a SEVERE allergy to {', '.join(severe)}. My food must not contain or touch these allergens. Cross-contamination can be life-threatening. Other allergens/intolerances: {all_names}. Thank you."
    else:
        msg = f"I cannot eat: {all_names}. Please confirm ingredients and cross-contamination risk before serving. Thank you."
    send_text(ctx["chat_id"], msg)


# ---------- check sub-menu ----------
def prompt_check_photo(ctx):
    send_text(ctx["chat_id"], "📷 Send me a photo of the food — or better, of its ingredient list. "
                              "I'll check it against your allergies.")

def prompt_check_barcode(ctx):
    send_text(ctx["chat_id"], "Barcode lookup is coming soon. For now, send a clear photo of the ingredient "
                              "list on the package — that works today.")

def prompt_check_text(ctx):
    pending.expect(ctx["telegram_id"], "check_text")
    send_text(ctx["chat_id"], "⌨️ Type the food or dish, e.g. \"tiramisu\", and I'll check it.")

def prompt_check_menu(ctx):
    send_text(ctx["chat_id"], "📋 Send a photo of the menu. I'll flag your allergens where I can see them — "
                              "but a menu isn't an ingredient list, so always confirm with the staff.")


# ---------- tonight's meal ----------
def _slot(uid, date, meal_type):
    c = db.conn()
    row = c.execute("""SELECT m.id, m.status, m.date, r.* FROM meal_schedule m JOIN recipes r ON r.id=m.recipe_id
                       WHERE m.user_id=? AND m.date=? AND m.meal_type=? ORDER BY m.id LIMIT 1""",
                    (uid, date, meal_type)).fetchone()
    c.close()
    return row

def show_tonight(ctx):
    uid = _need_profile(ctx)
    if not uid: return
    today = dt.date.today().isoformat()
    c = db.conn()
    row = c.execute("""SELECT m.meal_type, r.title, r.cook_minutes, r.kcal FROM meal_schedule m
                       JOIN recipes r ON r.id=m.recipe_id WHERE m.user_id=? AND m.date=? AND m.status='planned'
                       ORDER BY CASE m.meal_type WHEN 'dinner' THEN 0 ELSE 1 END LIMIT 1""", (uid, today)).fetchone()
    c.close()
    if not row:
        return send_menu(ctx["chat_id"], "Nothing is planned for tonight yet.", menu.plan_prompt_menu())
    send_menu(ctx["chat_id"], f"🌙 Tonight: {row['title']} — {row['cook_minutes'] or '?'} min, {row['kcal'] or '?'} kcal",
              menu.tonight_actions(today, row["meal_type"]))

def meal_cook(ctx, date, meal_type):
    uid = _need_profile(ctx)
    if not uid: return
    slot = _slot(uid, date, meal_type)
    if not slot:
        return send_text(ctx["chat_id"], "I can't find that meal in your plan.")
    c = db.conn()
    if slot["status"] != "cooked":
        c.execute("UPDATE meal_schedule SET status='cooked' WHERE id=?", (slot[0],))
        c.execute("""INSERT INTO food_log(user_id,source,item,verdict,kcal,protein_g,carbs_g,fat_g)
                     VALUES(?,?,?,?,?,?,?,?)""", (uid, "schedule", slot["title"], "logged",
                     slot["kcal"], slot["protein_g"], slot["carbs_g"], slot["fat_g"]))
        c.commit()
    c.close()
    _, consumed = reporting.today_chart(uid)
    target = reporting._target(uid)
    send_photo(ctx["chat_id"], visuals.day_dashboard(consumed, target, name=f"dash_{uid}.png"),
               caption=f"Enjoy! {slot['title']} logged. Today: {consumed['kcal']:.0f}/{target['daily_kcal']} kcal")

def meal_swap(ctx, date, meal_type):
    """Swap this meal with the next planned one (both stay gate-screened)."""
    uid = _need_profile(ctx)
    if not uid: return
    c = db.conn()
    here = c.execute("SELECT id, recipe_id FROM meal_schedule WHERE user_id=? AND date=? AND meal_type=? AND status='planned'",
                     (uid, date, meal_type)).fetchone()
    other = c.execute("""SELECT m.id, m.recipe_id, m.date FROM meal_schedule m WHERE m.user_id=? AND m.date>?
                         AND m.status='planned' ORDER BY m.date, m.id LIMIT 1""", (uid, date)).fetchone()
    if not here or not other:
        c.close()
        return send_menu(ctx["chat_id"], "There's no other planned meal to swap with. Plan a new week?",
                         menu.plan_prompt_menu())
    c.execute("UPDATE meal_schedule SET recipe_id=? WHERE id=?", (other["recipe_id"], here["id"]))
    c.execute("UPDATE meal_schedule SET recipe_id=? WHERE id=?", (here["recipe_id"], other["id"]))
    c.commit()
    titles = {r["id"]: r["title"] for r in c.execute("SELECT id, title FROM recipes WHERE id IN (?,?)",
                                                         (here["recipe_id"], other["recipe_id"]))}
    c.close()
    day = dt.date.fromisoformat(other["date"]).strftime("%A")
    send_menu(ctx["chat_id"], f"🔁 Swapped. Tonight: {titles[other['recipe_id']]}. "
                              f"{titles[here['recipe_id']]} moved to {day}.", menu.tonight_actions(date, meal_type))

def meal_recipe(ctx, date, meal_type):
    uid = _need_profile(ctx)
    if not uid: return
    slot = _slot(uid, date, meal_type)
    if not slot:
        return send_text(ctx["chat_id"], "I can't find that meal in your plan.")
    ings = json.loads(slot["ingredients_json"] or "[]")
    steps = json.loads(slot["steps_json"] or "[]")
    screen = json.loads(slot["gate_screen_json"] or "{}").get("level", "not screened")
    lines = [f"📖 {slot['title']} — {slot['cook_minutes'] or '?'} min, {slot['kcal'] or '?'} kcal", "", "Ingredients:"]
    lines += [f"• {i.get('qty') or ''} {i.get('unit') or ''} {i.get('name', '')}".replace("  ", " ") for i in ings]
    lines += ["", "Steps:"] + [f"{n}. {st}" for n, st in enumerate(steps, 1)]
    lines += ["", f"Safety screen: {screen}. Always check packaged ingredients against your allergies."]
    send_menu(ctx["chat_id"], "\n".join(lines), menu.tonight_actions(date, meal_type))


# ---------- free chat (Hermes agent) ----------
def _chat_context(uid, ctx):
    p = db.get_profile(uid) or {}
    name = (db.user_by_telegram(ctx["telegram_id"]) or {}).get("name") or "the user"
    allergies = ", ".join(f"{a['allergen']} ({a.get('severity', 'moderate')})" for a in p.get("allergies", [])) or "none"
    return (f"[NutriGent Telegram chat with {name}. Allergies: {allergies}. Diet: {p.get('diet_type') or 'none'}. "
            f"Goal: {p.get('goal') or '-'}, target {p.get('daily_kcal') or '?'} kcal/day. "
            "Rules: reply briefly in the user's language, plain text without markdown tables. "
            "Never decide yourself whether a specific food or product is safe for their allergies: ask them to "
            "send it with the Check button (a photo, or 'can I eat ...') so NutriGent's safety gate decides. "
            "You are an assistive tool, not a medical device; for reaction symptoms tell them to use their "
            "emergency medication and call emergency services.]")

def chat(ctx):
    """Open conversation, answered by the Hermes agent; falls back to the menu if it can't answer."""
    uid = _need_profile(ctx)
    if not uid: return
    send_chat_action(ctx["chat_id"])
    stop = threading.Event()
    def keep_typing():  # Telegram shows "typing…" for ~5 s per call; the agent needs 10-20 s
        while not stop.wait(4): send_chat_action(ctx["chat_id"])
    threading.Thread(target=keep_typing, daemon=True).start()
    try:
        reply = hermes_bridge.ask(ctx["telegram_id"], ctx["text"], context=_chat_context(uid, ctx))
    finally:
        stop.set()
    if not reply:
        return send_menu(ctx["chat_id"], "Sorry, I couldn't answer that right now. Try again in a minute, "
                                         "or use the buttons:", menu.main_menu())
    text = reply["text"]
    for i in range(0, len(text), 4000):  # Telegram's message limit is 4096 characters
        send_text(ctx["chat_id"], text[i:i + 4000])
    for path in reply["images"]:
        send_photo(ctx["chat_id"], path)
