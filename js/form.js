const SALES_EMAIL = "sales@themotorcoach.store";
const SERVICE_EMAIL = "service@themotorcoach.store";
const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const SSN = /\b\d{3}-\d{2}-\d{4}\b/;
const VEHICLE = new Set(["sell", "trade"]);
const HUBSPOT_PORTAL = "47169059";
const HUBSPOT_FORM = "df83503a-34e8-41d1-892f-3021fb7a9a4b";
const BUY_INTENTS = new Set([
  "buy",
  "coach-inquiry",
  "sales-appointment",
  "financing",
  "fractional",
  "insurance",
]);
const SELL_INTENTS = new Set(["sell", "trade"]);
const SERVICE_INTENTS = new Set(["ceramic", "service-appointment"]);

document.querySelectorAll("form.form").forEach((form) => {
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const fields = read(form);
    const errors = validate(fields, form);
    paint(form, errors);
    if (Object.keys(errors).length) return;

    if (fields.company) {
      showSent(form, "Request received", "Thank you.");
      return;
    }

    const button = form.querySelector("[type=submit]");
    const label = button.textContent;
    button.disabled = true;
    button.textContent = "Sending";
    try {
      const payload = await deliverInquiry(fields);
      if (!payload.ok) {
        paint(form, payload.errors || { form: payload.error || "The sales mailbox did not accept the message. Call 941 283 2516." });
        button.disabled = false;
        button.textContent = label;
        return;
      }
      const destination = payload.redirectedFrom
        ? `This request was addressed to ${payload.redirectedFrom} and delivered to ${payload.to || SALES_EMAIL}.`
        : `This request was delivered to ${payload.to || SALES_EMAIL}.`;
      showSent(
        form,
        "Request sent",
        `Reference ${payload.reference}. ${destination} Call 941 283 2516 if you need a time today.`
      );
    } catch {
      paint(form, { form: "The message did not leave this page. Check the connection and try again, or call 941 283 2516." });
      button.disabled = false;
      button.textContent = label;
    }
  });
});

function isLocalDev() {
  const host = location.hostname;
  return host === "localhost" || host === "127.0.0.1" || host === "[::1]";
}

function mailApiBase() {
  if (typeof window.__MAIL_API_BASE__ === "string" && window.__MAIL_API_BASE__) {
    return window.__MAIL_API_BASE__.replace(/\/$/, "");
  }
  if (isLocalDev()) return "";
  return "";
}

async function deliverInquiry(fields) {
  const reference = makeReference();
  const addressed = SERVICE_INTENTS.has(fields.intent) ? SERVICE_EMAIL : SALES_EMAIL;

  /* 1) Local showroom server (python server.py) */
  if (isLocalDev()) {
    const local = await sendJsonApi(sitePath("/api/inquiries"), fields);
    if (local.ok || local.errors) return local;
  }

  /* 2) Optional hosted mail relay (same SMTP → sales@) */
  const relay = mailApiBase();
  if (relay) {
    const remote = await sendJsonApi(`${relay}/api/inquiries`, fields);
    if (remote.ok) {
      return {
        ok: true,
        reference: remote.reference || reference,
        to: SALES_EMAIL,
        redirectedFrom: addressed === SERVICE_EMAIL ? SERVICE_EMAIL : undefined,
      };
    }
  }

  /* 3) Direct mailbox API (Web3Forms → sales@) when configured */
  const direct = await sendWeb3Forms(fields, reference, addressed);
  if (direct.ok) {
    sendHubSpot(fields, reference).catch(() => {});
    return {
      ok: true,
      reference,
      to: SALES_EMAIL,
      redirectedFrom: addressed === SERVICE_EMAIL ? SERVICE_EMAIL : undefined,
    };
  }

  /* 4) GitHub Action SMTP → sales@ (Private Email) when dispatch token configured */
  const dispatched = await sendGitHubDispatch(fields, reference, addressed);
  if (dispatched.ok) {
    sendHubSpot(fields, reference).catch(() => {});
    return {
      ok: true,
      reference,
      to: SALES_EMAIL,
      redirectedFrom: addressed === SERVICE_EMAIL ? SERVICE_EMAIL : undefined,
    };
  }

  /* 5) FormSubmit → sales@ (no API key; first browser submit confirms the mailbox) */
  const formSubmit = await sendFormSubmit(fields, reference, addressed);
  if (formSubmit.ok) {
    sendHubSpot(fields, reference).catch(() => {});
    return {
      ok: true,
      reference,
      to: SALES_EMAIL,
      redirectedFrom: addressed === SERVICE_EMAIL ? SERVICE_EMAIL : undefined,
    };
  }

  /* 6) HubSpot CRM only — does not deliver into sales@ inbox */
  sendHubSpot(fields, reference).catch(() => {});
  return {
    ok: false,
    error:
      formSubmit.error ||
      dispatched.error ||
      direct.error ||
      "The sales mailbox did not accept the message. Call 941 283 2516.",
  };
}

async function sendJsonApi(url, fields) {
  try {
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(fields),
    });
    const payload = await response.json().catch(() => ({}));
    if (response.ok && payload.ok) return payload;
    return {
      ok: false,
      status: response.status,
      errors: payload.errors,
      error: payload.error,
    };
  } catch {
    return { ok: false, status: 0, error: "The sales mailbox could not be reached." };
  }
}


async function sendFormSubmit(fields, reference, addressed) {
  try {
    const response = await fetch("https://formsubmit.co/ajax/" + encodeURIComponent(SALES_EMAIL), {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({
        name: `${fields.firstName || ""} ${fields.lastName || ""}`.trim() || "Showroom visitor",
        email: fields.email || "",
        phone: fields.phone || "",
        _subject: `Showroom request ${reference}`,
        _template: "table",
        _captcha: "false",
        _honey: fields.company || "",
        intent: fields.intent || "contact",
        addressed_to: addressed,
        delivered_to: SALES_EMAIL,
        coach: fields.coach || "",
        year: fields.year || "",
        make: fields.make || "",
        model: fields.model || "",
        miles: fields.miles || "",
        location: fields.location || "",
        preferredDate: fields.preferredDate || "",
        message: buildMessage(fields, reference),
        page: location.href,
      }),
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok || payload.success === "false" || payload.success === false) {
      return {
        ok: false,
        error: payload.message || "The sales mailbox did not accept the message. Call 941 283 2516.",
      };
    }
    return { ok: true };
  } catch {
    return { ok: false, error: "The sales mailbox could not be reached." };
  }
}

async function sendGitHubDispatch(fields, reference, addressed) {
  const token = window.__INQUIRY_TOKEN__;
  const repo = window.__INQUIRY_REPO__ || "pdot609/mcs-inquiry-mail";
  if (!token) return { ok: false, error: "Mailbox dispatch is not configured." };

  const inquiry = {
    intent: fields.intent || "contact",
    firstName: fields.firstName || "",
    lastName: fields.lastName || "",
    email: fields.email || "",
    phone: fields.phone || "",
    preferredDate: fields.preferredDate || "",
    coach: fields.coach || "",
    year: fields.year || "",
    make: fields.make || "",
    model: fields.model || "",
    miles: fields.miles || "",
    location: fields.location || "",
    interest: fields.interest || "",
    smsConsent: fields.smsConsent || "",
    message: fields.message || "",
    company: fields.company || "",
    page: location.href,
    reference,
    addressed_to: addressed,
    delivered_to: SALES_EMAIL,
  };

  try {
    const response = await fetch(`https://api.github.com/repos/${repo}/dispatches`, {
      method: "POST",
      headers: {
        Accept: "application/vnd.github+json",
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
        "X-GitHub-Api-Version": "2022-11-28",
      },
      body: JSON.stringify({
        event_type: "showroom_inquiry",
        client_payload: { inquiry },
      }),
    });
    if (response.status === 204 || response.ok) return { ok: true };
    const detail = await response.json().catch(() => ({}));
    return {
      ok: false,
      error: detail.message || "The sales mailbox did not accept the message. Call 941 283 2516.",
    };
  } catch {
    return { ok: false, error: "The sales mailbox could not be reached." };
  }
}

async function sendWeb3Forms(fields, reference, addressed) {

  const key = window.__WEB3FORMS_KEY__;
  if (!key) return { ok: false, error: "Mailbox relay is not configured." };

  const response = await fetch("https://api.web3forms.com/submit", {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({
      access_key: key,
      subject: `Showroom request ${reference}`,
      from_name: `${fields.firstName || ""} ${fields.lastName || ""}`.trim() || "Showroom visitor",
      email: fields.email || "",
      phone: fields.phone || "",
      name: `${fields.firstName || ""} ${fields.lastName || ""}`.trim(),
      interest: lookingFor(fields),
      intent: fields.intent || "contact",
      addressed_to: addressed,
      delivered_to: SALES_EMAIL,
      coach: fields.coach || "",
      year: fields.year || "",
      make: fields.make || "",
      model: fields.model || "",
      miles: fields.miles || "",
      location: fields.location || "",
      preferredDate: fields.preferredDate || "",
      message: buildMessage(fields, reference),
      page: location.href,
      botcheck: "",
    }),
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok || payload.success === false) {
    return {
      ok: false,
      error: payload.message || "The sales mailbox did not accept the message. Call 941 283 2516.",
    };
  }
  return { ok: true };
}

async function sendHubSpot(fields, reference) {
  const interest = lookingFor(fields);
  const message = buildMessage(fields, reference || makeReference());
  const body = {
    fields: [
      { objectTypeId: "0-1", name: "firstname", value: fields.firstName || "" },
      { objectTypeId: "0-1", name: "lastname", value: fields.lastName || "" },
      { objectTypeId: "0-1", name: "email", value: fields.email || "" },
      { objectTypeId: "0-1", name: "manual_phone_number", value: fields.phone || "" },
      { objectTypeId: "0-1", name: "what_are_you_looking_for_", value: interest },
      { objectTypeId: "0-1", name: "message", value: message },
      { objectTypeId: "0-1", name: "inventory_item", value: fields.coach || "" },
      { objectTypeId: "0-1", name: "inventory_url", value: location.href },
    ],
    context: {
      pageUri: location.href,
      pageName: document.title || "The Motorcoach Store",
    },
  };

  const response = await fetch(
    `https://api.hsforms.com/submissions/v3/integration/submit/${HUBSPOT_PORTAL}/${HUBSPOT_FORM}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(body),
    }
  );
  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    const hubError = detail?.errors?.[0]?.message || detail?.message;
    return {
      ok: false,
      status: response.status,
      error: hubError || "The sales mailbox did not accept the message. Call 941 283 2516.",
    };
  }
  return { ok: true };
}

function lookingFor(fields) {
  if (fields.interest && ["Buy a Coach", "Sell a Coach", "Other"].includes(fields.interest)) {
    return fields.interest;
  }
  const intent = fields.intent || "contact";
  if (SERVICE_INTENTS.has(intent)) return "Other";
  if (BUY_INTENTS.has(intent)) return "Buy a Coach";
  if (SELL_INTENTS.has(intent)) return "Sell a Coach";
  return "Other";
}

function buildMessage(fields, reference) {
  const addressed = SERVICE_INTENTS.has(fields.intent) ? SERVICE_EMAIL : SALES_EMAIL;
  const rows = [
    ["Reference", reference],
    ["Request", fields.intent || "contact"],
    ["Addressed to", addressed],
    ["Delivered to", SALES_EMAIL],
    ["Preferred date", fields.preferredDate],
    ["Coach", fields.coach],
    ["Year", fields.year],
    ["Make", fields.make],
    ["Model", fields.model],
    ["Miles", fields.miles],
    ["Location", fields.location],
    ["Interest", fields.interest],
    ["SMS consent", fields.smsConsent],
    ["Message", fields.message],
    ["Submitted from", location.href],
  ];
  return rows
    .filter(([, value]) => value)
    .map(([label, value]) => `${label}: ${value}`)
    .join("\n");
}

function makeReference() {
  const alphabet = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ";
  let number = Date.now();
  let out = "";
  while (number > 0) {
    out = alphabet[number % 36] + out;
    number = Math.floor(number / 36);
  }
  return `MCS-${out}`;
}

function showSent(form, titleText, copyText) {
  const status = document.createElement("div");
  status.className = "success";
  status.setAttribute("role", "status");
  const title = document.createElement("strong");
  const copy = document.createElement("p");
  title.textContent = titleText;
  copy.textContent = copyText;
  status.append(title, copy);
  form.replaceWith(status);
}

function read(form) {
  const data = new FormData(form);
  const value = {};
  for (const [key, item] of data.entries()) {
    value[key] = String(item).trim();
  }
  return value;
}

function validate(fields, form) {
  const errors = {};
  const intent = fields.intent || "contact";
  if (!fields.firstName) errors.firstName = "Enter a first name.";
  if (!fields.lastName) errors.lastName = "Enter a last name.";
  if (!EMAIL.test(fields.email || "")) errors.email = "Enter a valid email address.";
  if ((fields.phone || "").replace(/\D/g, "").length < 7) errors.phone = "Enter a phone number with at least 7 digits.";

  const combined = Object.values(fields).join(" ");
  if (/[<>]/.test(combined)) errors.form = "Remove brackets from the form. They are not needed.";
  if (SSN.test(combined)) errors.message = "Leave out Social Security numbers. A finance manager collects those on a separate application.";

  if (form.querySelector("[name=year]") && VEHICLE.has(intent)) {
    const year = Number(fields.year);
    if (!Number.isInteger(year) || year < 1990 || year > 2028) errors.year = "Enter a model year from 1990 through 2028.";
    if (!fields.make) errors.make = "Enter the make.";
    if (!fields.model) errors.model = "Enter the model.";
    if (form.querySelector("[name=miles]") && !fields.miles) errors.miles = "Enter the mileage.";
  }
  if (fields.miles) {
    const miles = Number(fields.miles.replace(/,/g, ""));
    if (!Number.isFinite(miles) || miles < 0 || miles > 999999) errors.miles = "Enter mileage between 0 and 999,999.";
  }
  if (fields.preferredDate && !/^\d{4}-\d{2}-\d{2}$/.test(fields.preferredDate)) {
    errors.preferredDate = "Choose a date from the calendar.";
  }
  if (intent === "contact" && form.querySelector("[name=interest]")) {
    if (!["Buy a Coach", "Sell a Coach", "Other"].includes(fields.interest || "")) {
      errors.interest = "Choose Buy a Coach, Sell a Coach, or Other.";
    }
    if (!fields.message) errors.message = "Tell us how we can help.";
  }
  return errors;
}

function paint(form, errors) {
  form.querySelectorAll("[data-for]").forEach((node) => {
    node.textContent = errors[node.dataset.for] || "";
  });
}

const dealSwitch = document.querySelector(".deal-switch");
if (dealSwitch) {
  dealSwitch.addEventListener("click", (event) => {
    const tab = event.target.closest("[data-deal]");
    if (!tab) return;
    const deal = tab.dataset.deal;
    dealSwitch.querySelectorAll("[data-deal]").forEach((button) => {
      const selected = button === tab;
      button.setAttribute("aria-selected", selected ? "true" : "false");
    });
    document.querySelectorAll("[data-deal-form], [data-deal-note]").forEach((node) => {
      const name = node.dataset.dealForm || node.dataset.dealNote;
      node.hidden = name !== deal;
    });
  });
}
