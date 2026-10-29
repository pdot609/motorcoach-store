const SALES_EMAIL = "sales@themotorcoach.store";
const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const SSN = /\b\d{3}-\d{2}-\d{4}\b/;
const VEHICLE = new Set(["sell", "trade"]);

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
      const response = await fetch("/api/inquiries", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify(fields),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok || !payload.ok) {
        paint(form, payload.errors || { form: payload.error || "The sales mailbox did not accept the message. Call 941 896 4819." });
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
        `Reference ${payload.reference}. ${destination} Call 941 896 4819 if you need a time today.`
      );
    } catch {
      paint(form, { form: "The message did not leave this page. Check the connection and try again, or call 941 896 4819." });
      button.disabled = false;
      button.textContent = label;
    }
  });
});

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
