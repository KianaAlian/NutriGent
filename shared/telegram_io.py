"""
Thin Telegram Bot API wrapper. Skills use send_text / send_photo / send_menu.
Set TELEGRAM_TOKEN in the environment. Pure stdlib (urllib) — no deps.
"""
import os, json, urllib.request, urllib.parse, mimetypes, uuid

API = "https://api.telegram.org/bot{}/{}".format

def _token():
    t = os.environ.get("TELEGRAM_TOKEN")
    if not t: raise RuntimeError("Set TELEGRAM_TOKEN")
    return t

def _post(method, data):
    req = urllib.request.Request(API(_token(), method),
        data=json.dumps(data).encode(), headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req) as r: return json.load(r)

def send_text(chat_id, text, reply_markup=None):
    d = {"chat_id":chat_id, "text":text}  # plain text: '&' or '<' in user input can't break a reply
    if reply_markup: d["reply_markup"] = reply_markup
    return _post("sendMessage", d)

def send_menu(chat_id, text, keyboard):
    return send_text(chat_id, text, reply_markup=keyboard)

def send_photo(chat_id, photo_path, caption=""):
    boundary = uuid.uuid4().hex
    fields = {"chat_id":str(chat_id), "caption":caption}
    body = b""
    for k,v in fields.items():
        body += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n").encode()
    fn = os.path.basename(photo_path); ctype = mimetypes.guess_type(fn)[0] or "image/png"
    body += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"photo\"; filename=\"{fn}\"\r\n"
             f"Content-Type: {ctype}\r\n\r\n").encode()
    body += open(photo_path,"rb").read() + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(API(_token(),"sendPhoto"), data=body,
        headers={"Content-Type":f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(req) as r: return json.load(r)

def send_chat_action(chat_id, action="typing"):
    """Shows 'typing…' in the chat for ~5 s (used while the agent thinks)."""
    try: return _post("sendChatAction", {"chat_id": chat_id, "action": action})
    except Exception: return None

def set_commands(commands):
    """commands: list of (command, description). Registers the persistent / menu."""
    return _post("setMyCommands",
        {"commands":[{"command":c,"description":d} for c,d in commands]})
