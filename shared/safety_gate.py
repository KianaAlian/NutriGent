"""
The deterministic safety gate — the heart of the system.
PRINCIPLE: the LLM proposes (extracts ingredients); this code disposes (decides).
It is reproducible, auditable, and FAILS CLOSED: when in doubt, NOT safe.
"""
import json, re
from dataclasses import dataclass, field
from db import conn

SEVERITY_BLOCKS_TRACES = {"anaphylactic", "severe"}
READABILITY_FLOOR = 0.85  # labels below this -> UNVERIFIED
SEVERITY_RANK = {"mild": 0, "moderate": 1, "severe": 2, "anaphylactic": 3}

# What users actually type -> the canonical allergen(s) in allergen_synonyms.
# Ambiguous words map to EVERY allergen they could mean (fail closed).
ALLERGEN_ALIASES = {
    "dairy": ["milk"], "lactose": ["milk"], "milk protein": ["milk"], "cow milk": ["milk"],
    "casein": ["milk"], "whey": ["milk"],
    "gluten": ["wheat"], "celiac": ["wheat"], "coeliac": ["wheat"],
    "nut": ["tree nut", "peanut"], "nuts": ["tree nut", "peanut"], "groundnut": ["peanut"],
    "soya": ["soy"], "sulfite": ["sulphite"], "sulfites": ["sulphite"],
    "crustacean": ["shellfish"], "crustaceans": ["shellfish"], "seafood": ["shellfish", "mollusc", "fish"],
}

@dataclass
class Verdict:
    level: str                       # UNSAFE | CAUTION | SAFE | LIKELY_SAFE | UNVERIFIED
    reasons: list = field(default_factory=list)
    hits: list = field(default_factory=list)  # [{allergen, matched_term, severity, where}]

    EMOJI = {"UNSAFE":"🛑","CAUTION":"⚠️","SAFE":"✅","LIKELY_SAFE":"✅","UNVERIFIED":"❓"}
    HEAD  = {"UNSAFE":"DO NOT EAT","CAUTION":"CAUTION","SAFE":"SAFE",
             "LIKELY_SAFE":"LIKELY SAFE","UNVERIFIED":"CAN'T VERIFY"}

    def message(self):
        lines = [f"{self.EMOJI[self.level]} {self.HEAD[self.level]}"]
        for h in self.hits:
            lines.append(f"• {h['matched_term']} → {h['allergen']} "
                         f"(severity: {h['severity']}, found in: {h['where']})")
        lines += [f"• {r}" for r in self.reasons]
        if self.level in ("UNSAFE","UNVERIFIED"):
            lines.append("If you have any reaction, use your emergency medication and call emergency services.")
        return "\n".join(lines)

def _normalize(term):
    return re.sub(r"[^a-z0-9 ]", " ", term.lower()).strip()

def _load_rules():
    c = conn()
    syn = [dict(r) for r in c.execute(
        "SELECT canonical, synonym, match_type FROM allergen_synonyms").fetchall()]
    exc = {}
    for r in c.execute("SELECT canonical, pattern FROM synonym_exceptions").fetchall():
        exc.setdefault(r["canonical"], []).append(r["pattern"].lower())
    c.close()
    return syn, exc

def _match(terms, user_allergens, where, syn, exc):
    """Return hits for the user's allergens found in `terms`."""
    hits = []
    for raw in terms:
        norm = _normalize(raw)
        for rule in syn:
            canon = rule["canonical"]
            if canon not in user_allergens:
                continue
            s = rule["synonym"]
            matched = (norm == s) if rule["match_type"] == "exact" else (s in norm)
            if not matched:
                continue
            if any(p in norm for p in exc.get(canon, [])):  # false-positive guard
                continue
            hits.append({"allergen": canon, "matched_term": raw,
                         "severity": user_allergens[canon], "where": where})
    return hits

def _resolve(name, known):
    """Map a user-typed allergen to canonical names; [] if we have no synonym list."""
    n = _normalize(name)
    if n in known: return [n]
    if n in ALLERGEN_ALIASES: return ALLERGEN_ALIASES[n]
    if n.endswith("s") and n[:-1] in known: return [n[:-1]]
    return []

def _user_allergens(profile, known):
    """-> ({canonical: strictest severity}, [names we can only match literally])"""
    resolved, unknown = {}, []
    for a in profile.get("allergies", []):
        sev = a.get("severity", "moderate")
        canons = _resolve(a["allergen"], known)
        if not canons:
            unknown.append(_normalize(a["allergen"])); canons = [_normalize(a["allergen"])]
        for canon in canons:
            if SEVERITY_RANK.get(sev, 1) >= SEVERITY_RANK.get(resolved.get(canon), -1):
                resolved[canon] = sev
    return resolved, unknown

def safety_verdict(extraction: dict, profile: dict) -> Verdict:
    itype = extraction.get("image_type", "prepared_food")

    # 0) FAIL CLOSED on unusable input
    if itype in ("unreadable", "not_food"):
        return Verdict("UNVERIFIED", ["Image could not be analyzed. Send a clear photo of the ingredient list."])
    if itype == "ingredient_label" and extraction.get("readability", 1.0) < READABILITY_FLOOR:
        return Verdict("UNVERIFIED", ["I can't read the full ingredient list. Treat as NOT safe until you send the whole label."])

    syn, exc = _load_rules()
    user_allergens, unknown = _user_allergens(profile, {r["canonical"] for r in syn})
    # No synonym list for these: still match the literal name, but never call the food SAFE.
    syn = syn + [{"canonical": u, "synonym": u, "match_type": "contains"} for u in unknown]
    direct =_match(extraction.get("identified_ingredients", []), user_allergens, "ingredients", syn, exc)
    hidden = _match(extraction.get("likely_hidden_ingredients", []), user_allergens, "likely hidden", syn, exc)
    traces = _match(extraction.get("precautionary_warnings", []), user_allergens, "may-contain warning", syn, exc)

    # 1) Policy, strictest first
    if direct:
        return Verdict("UNSAFE", hits=direct)
    severe_trace = [h for h in traces if h["severity"] in SEVERITY_BLOCKS_TRACES]
    if severe_trace:
        return Verdict("UNSAFE", ["Cross-contamination risk at your severity level."], hits=severe_trace)
    if traces or hidden:
        return Verdict("CAUTION", hits=traces + hidden)
    if unknown:
        return Verdict("CAUTION", [f"I don't have a label-synonym list for {', '.join(unknown)} — "
                                   "check the ingredient list yourself for other names."])
    if itype in ("prepared_food", "menu"):  # neither shows the full recipe
        what = "A menu" if itype == "menu" else "A photo"
        if any(s in SEVERITY_BLOCKS_TRACES for s in user_allergens.values()):
            return Verdict("CAUTION", [f"{what} can't prove a cooked dish is allergen-free. Ask for the ingredient list."])
        return Verdict("LIKELY_SAFE", ["No visible allergen, but I can't see hidden ingredients."])
    return Verdict("SAFE", ["No allergen from your profile detected against the full ingredient list."])
