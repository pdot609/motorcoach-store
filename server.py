#!/usr/bin/env python3
"""Serve the showroom site and deliver form requests to the sales mailbox."""

import json
import re
import smtplib
import ssl
import threading
import time
from email.message import EmailMessage
from email.utils import formataddr
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
SECRET = ROOT / "private" / "mail.env"
HOST = "127.0.0.1"
PORT = 3460
SALES = "sales@themotorcoach.store"
SERVICE = "service@themotorcoach.store"
SERVICE_INTENTS = {"ceramic", "service-appointment", "paint-appointment"}
MAX_BODY = 12_000
WINDOW = 600
LIMIT = 8
REDIRECTS = {
    "/showrooms": "/explore-showrooms/",
    "/showrooms/": "/explore-showrooms/",
    "/motorcoach-showroom-new-prevost-loki-coach": "/showrooms/prevost-loki/",
    "/motorcoach-showroom-new-prevost-loki-coach/": "/showrooms/prevost-loki/",
    "/motorcoach-showroom-new-adventure-showhauler": "/showrooms/adventure/",
    "/motorcoach-showroom-new-adventure-showhauler/": "/showrooms/adventure/",
    "/motorcoach-showroom-new-featherlite-stacker-trailers": "/showrooms/featherlite/",
    "/motorcoach-showroom-new-featherlite-stacker-trailers/": "/showrooms/featherlite/",
    "/motorcoach-showroom-ogv": "/showrooms/ogv/",
    "/motorcoach-showroom-ogv/": "/showrooms/ogv/",
    "/sold-units": "/sold/",
    "/sold-units/": "/sold/",
    "/motorcoach-showroom-sold-pre-owned": "/pre-owned/sold/",
    "/motorcoach-showroom-sold-pre-owned/": "/pre-owned/sold/",
    "/contact-us": "/contact/",
    "/contact-us/": "/contact/",
    "/sell-your-coach": "/sell/",
    "/sell-your-coach/": "/sell/",
    "/trade-rv": "/trade-in/",
    "/trade-rv/": "/trade-in/",
    "/rv-financing": "/financing/",
    "/rv-financing/": "/financing/",
    "/rv-insurance": "/insurance/",
    "/rv-insurance/": "/insurance/",
    "/schedule-appointment": "/schedule/",
    "/schedule-appointment/": "/schedule/",
    "/fractionalmotorcoachownership-page": "/fractional-ownership/",
    "/fractionalmotorcoachownership-page/": "/fractional-ownership/",
}
INTENTS = {
    "buy",
    "ceramic",
    "coach-inquiry",
    "contact",
    "financing",
    "fractional",
    "insurance",
    "paint-appointment",
    "sales-appointment",
    "sell",
    "service-appointment",
    "trade",
}
VEHICLE = {"sell", "trade"}
EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
SSN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
HITS = {}
LOCK = threading.Lock()


def load_secret():
    data = {}
    for line in SECRET.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip()
    missing = [key for key in ("SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD") if not data.get(key)]
    if missing:
        raise SystemExit("private/mail.env is missing " + ", ".join(missing))
    return data


def reference():
    digits = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    number = int(time.time() * 1000)
    chars = []
    while number:
        number, remainder = divmod(number, 36)
        chars.append(digits[remainder])
    return "MCS-" + "".join(reversed(chars))


def field(value, limit):
    return str(value or "").strip()[:limit]


def single_line(value, limit):
    return field(value, limit).replace("\r", " ").replace("\n", " ")


def validate(raw):
    if not isinstance(raw, dict):
        return {"form": "Send the form fields as one request."}, {}
    fields = {
        "intent": single_line(raw.get("intent"), 40) or "contact",
        "firstName": single_line(raw.get("firstName"), 80),
        "lastName": single_line(raw.get("lastName"), 80),
        "email": single_line(raw.get("email"), 120),
        "phone": single_line(raw.get("phone"), 40),
        "preferredDate": single_line(raw.get("preferredDate"), 10),
        "coach": single_line(raw.get("coach"), 200),
        "year": single_line(raw.get("year"), 4),
        "make": single_line(raw.get("make"), 80),
        "model": single_line(raw.get("model"), 80),
        "miles": single_line(raw.get("miles"), 12),
        "location": single_line(raw.get("location"), 160),
        "interest": single_line(raw.get("interest"), 40),
        "smsConsent": single_line(raw.get("smsConsent"), 10),
        "message": field(raw.get("message"), 4000),
        "company": single_line(raw.get("company"), 80),
    }
    errors = {}
    if fields["intent"] not in INTENTS:
        errors["form"] = "This form is not a showroom request."
    if not fields["firstName"]:
        errors["firstName"] = "Enter a first name."
    if not fields["lastName"]:
        errors["lastName"] = "Enter a last name."
    if not EMAIL.match(fields["email"]):
        errors["email"] = "Enter a valid email address."
    if len(re.sub(r"\D", "", fields["phone"])) < 7:
        errors["phone"] = "Enter a phone number with at least 7 digits."
    combined = " ".join(fields.values())
    if re.search(r"[<>]", combined):
        errors["form"] = "Remove brackets from the form. They are not needed."
    if SSN.search(combined):
        errors["message"] = "Leave out Social Security numbers. A finance manager collects those on a separate application."
    if fields["intent"] in VEHICLE:
        year = int(fields["year"]) if fields["year"].isdigit() else 0
        if year < 1990 or year > 2028:
            errors["year"] = "Enter a model year from 1990 through 2028."
        if not fields["make"]:
            errors["make"] = "Enter the make."
        if not fields["model"]:
            errors["model"] = "Enter the model."
        if not fields["miles"]:
            errors["miles"] = "Enter the mileage."
    if fields["miles"]:
        miles = fields["miles"].replace(",", "")
        if not miles.isdigit() or int(miles) > 999999:
            errors["miles"] = "Enter mileage between 0 and 999,999."
    if fields["preferredDate"] and not DATE.match(fields["preferredDate"]):
        errors["preferredDate"] = "Choose a date from the calendar."
    if fields["intent"] == "contact":
        if fields["interest"] not in {"Buy a Coach", "Sell a Coach", "Other"}:
            errors["interest"] = "Choose Buy a Coach, Sell a Coach, or Other."
        if not fields["message"]:
            errors["message"] = "Tell us how we can help."
    return errors, fields


def allow(ip):
    now = time.time()
    with LOCK:
        recent = [stamp for stamp in HITS.get(ip, []) if now - stamp < WINDOW]
        if len(recent) >= LIMIT:
            HITS[ip] = recent
            return False
        recent.append(now)
        HITS[ip] = recent
        return True


def same_origin(origin, host):
    """Accept matching hosts, and treat localhost / 127.0.0.1 as equivalent."""
    if not origin or not host:
        return False
    origin_host = urlparse(origin).netloc.lower()
    request_host = host.lower().split(",")[0].strip()
    if origin_host == request_host:
        return True

    def normalize(netloc):
        name, sep, port = netloc.partition(":")
        if name in {"localhost", "127.0.0.1", "::1", "[::1]"}:
            name = "local"
        return f"{name}{sep}{port}"

    return normalize(origin_host) == normalize(request_host)


def deliver(config, fields, ref):
    destination = SERVICE if fields["intent"] in SERVICE_INTENTS else SALES
    rows = [
        ("Reference", ref),
        ("Request", fields["intent"]),
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
        ("SMS consent", "yes" if fields["smsConsent"].lower() in {"yes", "on", "true", "1"} else ""),
        ("Message", fields["message"]),
    ]
    message = EmailMessage()
    message["Subject"] = f"Showroom request {ref}"
    message["From"] = formataddr(("The Motorcoach Store", SALES))
    message["To"] = destination
    message["Reply-To"] = formataddr((f"{fields['firstName']} {fields['lastName']}", fields["email"]))
    message.set_content("\n".join(f"{label}: {value}" for label, value in rows if value))
    context = ssl.create_default_context()
    with smtplib.SMTP(config["SMTP_HOST"], int(config["SMTP_PORT"]), timeout=30) as smtp:
        smtp.ehlo()
        smtp.starttls(context=context)
        smtp.ehlo()
        smtp.login(config["SMTP_USER"], config["SMTP_PASSWORD"])
        smtp.send_message(message)


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def blocked(self):
        parts = [part for part in urlparse(self.path).path.split("/") if part]
        return any(part.startswith(".") for part in parts) or (parts[:1] == ["private"]) or parts == ["server.py"]

    def end_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def redirect_target(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        if path.startswith("/coach/") and not path.startswith("/coaches/"):
            slug = path[len("/coach/") :].strip("/")
            if slug and "/" not in slug:
                target = f"/coaches/{slug}/"
                if parsed.query:
                    target += "?" + parsed.query
                return target
        target = REDIRECTS.get(parsed.path) or REDIRECTS.get(path if path.endswith("/") else path + "/")
        if not target:
            target = REDIRECTS.get(path)
        if target and parsed.query:
            return target + ("&" if "?" in target else "?") + parsed.query
        return target

    def send_redirect(self, target):
        self.send_response(302)
        self.send_header("Location", target)
        self.end_headers()

    def do_GET(self):
        if self.blocked():
            self.send_error(404)
            return
        target = self.redirect_target()
        if target:
            self.send_redirect(target)
            return
        super().do_GET()

    def do_HEAD(self):
        if self.blocked():
            self.send_error(404)
            return
        target = self.redirect_target()
        if target:
            self.send_redirect(target)
            return
        super().do_HEAD()

    def do_POST(self):
        if urlparse(self.path).path != "/api/inquiries":
            self.send_error(404)
            return
        host = self.headers.get("Host", "")
        origin = self.headers.get("Origin", "")
        if not same_origin(origin, host):
            self.respond(403, {"error": "Open the showroom site and send the form from there."})
            return
        if not allow(self.client_address[0]):
            self.respond(429, {"error": "Too many requests from this connection. Call 941 283 2516."})
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        if length <= 0 or length > MAX_BODY:
            self.respond(400, {"error": "The form was empty or too long."})
            return
        try:
            raw = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self.respond(400, {"error": "The form could not be read."})
            return
        errors, fields = validate(raw)
        if errors:
            self.respond(400, {"errors": errors})
            return
        ref = reference()
        if fields["company"]:
            self.respond(200, {"ok": True, "reference": ref})
            return
        destination = SERVICE if fields["intent"] in SERVICE_INTENTS else SALES
        try:
            deliver(CONFIG, fields, ref)
        except (OSError, smtplib.SMTPException) as exc:
            print(f"smtp_fail {ref} {type(exc).__name__}: {exc}", flush=True)
            self.respond(502, {"error": "The mailbox did not accept the message. Call 941 283 2516."})
            return
        print(f"sent {ref} to {destination}", flush=True)
        self.respond(200, {"ok": True, "reference": ref, "to": destination})

    def respond(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    CONFIG = load_secret()
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Showroom site at http://{HOST}:{PORT}/", flush=True)
    server.serve_forever()
