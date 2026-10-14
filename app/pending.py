"""
What a user's next plain message means after they tapped a button such as
"Type it" (log a meal), "Type a food name" (check it) or "Other" (symptom).
Stored in pending_input so it survives restarts; expires after 30 minutes.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "shared"))
import db


def expect(tid, kind):
    c = db.conn()
    c.execute("INSERT OR REPLACE INTO pending_input(telegram_id,kind,created_at) VALUES(?,?,datetime('now'))",
              (str(tid), kind))
    c.commit(); c.close()

def take(tid):
    """Return and clear the pending kind, or None (also None when older than 30 min)."""
    c = db.conn()
    row = c.execute("SELECT kind FROM pending_input WHERE telegram_id=? AND created_at >= datetime('now','-30 minutes')",
                    (str(tid),)).fetchone()
    c.execute("DELETE FROM pending_input WHERE telegram_id=?", (str(tid),))
    c.commit(); c.close()
    return row["kind"] if row else None
