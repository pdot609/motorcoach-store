#!/usr/bin/env python3
"""Public-facing inquiry relay → sales@themotorcoach.store via Private Email SMTP."""
import json, re, smtplib, ssl, time
from email.message import EmailMessage
from email.utils import formataddr
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SECRET = ROOT / "private" / "mail.env"
SALES = "sales@themotorcoach.store"
SERVICE = "service@themotorcoach.store"
SERVICE_INTENTS = {"ceramic", "service-appointment", "paint-appointment"}
ALLOWED = {
    "https://themotorcoach.store",
    "https://www.themotorcoach.store",
    "https://pdot609.github.io",
    "http://127.0.0.1:3460",
    "http://localhost:3460",
}
EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

def load_secret():
    data = {}
    for line in SECRET.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        data[k.strip()] = v.strip()
    return data

CONFIG = load_secret()

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print("[%s] %s" % (self.log_date_time_string(), fmt % args), flush=True)

    def _cors(self):
        origin = self.headers.get("Origin", "")
        if origin in ALLOWED or origin.endswith("github.io"):
            self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Accept")
        self.send_header("Vary", "Origin")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def respond(self, status, payload):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self._cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path.rstrip("/") != "/api/inquiries":
            self.respond(404, {"error": "Not found"})
            return
        origin = self.headers.get("Origin", "")
        if origin and origin not in ALLOWED and not origin.endswith("github.io"):
            self.respond(403, {"error": "Open the showroom site and send the form from there."})
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        if length <= 0 or length > 12000:
            self.respond(400, {"error": "The form was empty or too long."})
            return
        try:
            raw = json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception:
            self.respond(400, {"error": "The form could not be read."})
            return
        fields = {k: str(raw.get(k) or "").strip() for k in (
            "intent","firstName","lastName","email","phone","preferredDate","coach",
            "year","make","model","miles","location","interest","smsConsent","message","company"
        )}
        if fields.get("company"):
            self.respond(200, {"ok": True, "reference": "MCS-HP"})
            return
        if not fields["firstName"] or not fields["lastName"] or not EMAIL.match(fields["email"]):
            self.respond(400, {"error": "Name and email are required."})
            return
        if len(re.sub(r"\D", "", fields["phone"])) < 7:
            self.respond(400, {"error": "Enter a phone number with at least 7 digits."})
            return
        ref = "MCS-" + format(int(time.time() * 1000), "X")
        destination = SERVICE if fields["intent"] in SERVICE_INTENTS else SALES
        rows = [
            ("Reference", ref),
            ("Request", fields["intent"] or "contact"),
            ("Delivered to", destination),
            ("Name", f"{fields['firstName']} {fields['lastName']}"),
            ("Email", fields["email"]),
            ("Phone", fields["phone"]),
            ("Preferred date", fields["preferredDate"]),
            ("Coach", fields["coach"]),
            ("Year", fields["year"]),
            ("Make", fields["make"]),
            ("Model", fields["model"]),
            ("Miles", fields["miles"]),
            ("Location", fields["location"]),
            ("Interest", fields["interest"]),
            ("Message", fields["message"]),
        ]
        msg = EmailMessage()
        msg["Subject"] = f"Showroom request {ref}"
        msg["From"] = formataddr(("The Motorcoach Store", SALES))
        msg["To"] = destination
        msg["Reply-To"] = formataddr((f"{fields['firstName']} {fields['lastName']}", fields["email"]))
        msg.set_content("\n".join(f"{k}: {v}" for k, v in rows if v))
        try:
            ctx = ssl.create_default_context()
            with smtplib.SMTP(CONFIG["SMTP_HOST"], int(CONFIG["SMTP_PORT"]), timeout=30) as smtp:
                smtp.ehlo(); smtp.starttls(context=ctx); smtp.ehlo()
                smtp.login(CONFIG["SMTP_USER"], CONFIG["SMTP_PASSWORD"])
                smtp.send_message(msg)
        except Exception as exc:
            print("smtp_fail", type(exc).__name__, exc, flush=True)
            self.respond(502, {"error": "The mailbox did not accept the message. Call 941 283 2516."})
            return
        print(f"sent {ref} to {destination}", flush=True)
        self.respond(200, {"ok": True, "reference": ref, "to": destination})

if __name__ == "__main__":
    host, port = "127.0.0.1", 8765
    print(f"Mail relay on http://{host}:{port}/api/inquiries", flush=True)
    ThreadingHTTPServer((host, port), Handler).serve_forever()
