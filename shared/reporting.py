"""
Bridges the database and charts.py. Skills call these to get a PNG path
ready to send with Telegram sendPhoto.
"""
import datetime as dt
from db import conn, get_profile
import charts

def _logs_between(user_id, start, end):
    c = conn()
    rows = [dict(r) for r in c.execute(
        "SELECT * FROM food_log WHERE user_id=? AND date(ts) BETWEEN ? AND ? "
        "AND verdict IN ('logged','safe')", (user_id, start, end)).fetchall()]
    c.close(); return rows

def _target(user_id):
    p = get_profile(user_id) or {}
    return {"daily_kcal":p.get("daily_kcal") or 2000, "protein_g":p.get("protein_g") or 100,
            "carbs_g":p.get("carbs_g") or 250, "fat_g":p.get("fat_g") or 70}

def today_chart(user_id):
    today = dt.date.today().isoformat()
    logs = _logs_between(user_id, today, today)
    consumed = {k: sum((r.get(k) or 0) for r in logs)
                for k in ("kcal","protein_g","carbs_g","fat_g")}
    return charts.daily_macro_chart(consumed, _target(user_id), f"today_{user_id}.png"), consumed

def week_chart(user_id):
    t = _target(user_id)["daily_kcal"]
    today = dt.date.today(); monday = today - dt.timedelta(days=today.weekday())
    days, kcals = [], []
    for i in range(7):
        d = monday + dt.timedelta(days=i)
        logs = _logs_between(user_id, d.isoformat(), d.isoformat())
        days.append(d.strftime("%a")); kcals.append(sum((r.get("kcal") or 0) for r in logs))
    return charts.weekly_calorie_chart(days, kcals, t, f"week_{user_id}.png")

def month_chart(user_id, with_weight=True):
    t = _target(user_id)["daily_kcal"]
    today = dt.date.today(); start = today - dt.timedelta(days=29)
    dates, kcals = [], []
    for i in range(30):
        d = start + dt.timedelta(days=i)
        logs = _logs_between(user_id, d.isoformat(), d.isoformat())
        dates.append(d.strftime("%b %d")); kcals.append(sum((r.get("kcal") or 0) for r in logs))
    weights = None
    if with_weight:
        c = conn()
        wmap = {r["date"]: r["weight_kg"] for r in c.execute(
            "SELECT date, weight_kg FROM weight_log WHERE user_id=? AND date>=?",
            (user_id, start.isoformat())).fetchall()}
        c.close()
        weights = [wmap.get((start+dt.timedelta(days=i)).isoformat()) for i in range(30)]
    return charts.monthly_trend_chart(dates, kcals, t, weights, f"month_{user_id}.png")

def week_safety_donut(user_id):
    today = dt.date.today(); monday = today - dt.timedelta(days=today.weekday())
    c = conn()
    rows = c.execute("SELECT verdict, COUNT(*) n FROM food_log WHERE user_id=? "
        "AND date(ts)>=? GROUP BY verdict", (user_id, monday.isoformat())).fetchall()
    c.close()
    d = {r["verdict"]: r["n"] for r in rows}
    return charts.adherence_donut(safe=d.get("safe",0)+d.get("logged",0),
        caution=d.get("caution",0), unsafe=d.get("unsafe",0), name=f"safety_{user_id}.png")
