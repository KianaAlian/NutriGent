"""Calorie & macro math. Mifflin-St Jeor BMR -> TDEE -> goal-adjusted target."""
ACTIVITY = {"sedentary":1.2,"light":1.375,"moderate":1.55,"active":1.725,"athlete":1.9}
GOAL_DELTA = {"lose":-0.20,"maintain":0.0,"gain":0.12}  # % of TDEE

def bmr(sex, weight_kg, height_cm, age):
    s = 5 if sex == "male" else -161
    return 10*weight_kg + 6.25*height_cm - 5*age + s

def daily_target(sex, weight_kg, height_cm, age, activity="moderate", goal="maintain"):
    tdee = bmr(sex, weight_kg, height_cm, age) * ACTIVITY.get(activity, 1.55)
    kcal = round(tdee * (1 + GOAL_DELTA.get(goal, 0.0)))
    # macro split: 30% protein, 40% carbs, 30% fat (sane default; tune per goal)
    protein_g = round(kcal*0.30/4); carbs_g = round(kcal*0.40/4); fat_g = round(kcal*0.30/9)
    return {"daily_kcal":kcal,"protein_g":protein_g,"carbs_g":carbs_g,"fat_g":fat_g,
            "bmr":round(bmr(sex,weight_kg,height_cm,age)),"tdee":round(tdee)}

def day_summary(logged, target):
    """logged: list of food_log rows for the day. Returns totals + remaining."""
    tot = {k: sum((r.get(k) or 0) for r in logged) for k in ("kcal","protein_g","carbs_g","fat_g")}
    return {"consumed":tot,
            "remaining":{k: round((target.get(k.replace('_g',''),0) if False else target.get(k,0)) - tot[k])
                         for k in tot},
            "pct_kcal": round(100*tot["kcal"]/target["daily_kcal"]) if target.get("daily_kcal") else 0}
