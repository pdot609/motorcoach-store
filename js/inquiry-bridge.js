/* Deliver showroom inquiries to sales@ / service@themotorcoach.store.
   HubSpot embeds on the cloned site post to the original dealer portal — replace them. */
(function () {
  const SALES = "sales@themotorcoach.store";
  const SERVICE = "service@themotorcoach.store";
  const PHONE = "941 283 2516";
  const PHONE_TEL = "9412832516";
  const WEB3_KEY = window.__WEB3FORMS_KEY__ || "200e0f0b-da5c-46f8-bdab-5ca29f8a16b0";
  const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  const TRADE_FORMS = new Set(["895e3cbb-00a7-4585-9e39-89a41da3b2d1"]);
  const FINANCE_FORMS = new Set(["4457fa31-8c71-4d87-9377-64556c5313b8"]);
  const SERVICE_FORMS = new Set([]);

  const STYLE_ID = "mcs-inquiry-bridge-style";
  if (!document.getElementById(STYLE_ID)) {
    const style = document.createElement("style");
    style.id = STYLE_ID;
    style.textContent = `
.mcs-inquiry-form{display:flex;flex-direction:column;gap:12px;max-width:560px;width:100%;color:inherit;font:inherit}
.mcs-inquiry-form label{display:flex;flex-direction:column;gap:6px;font-size:12px;letter-spacing:.04em;text-transform:uppercase;opacity:.85}
.mcs-inquiry-form input,.mcs-inquiry-form textarea,.mcs-inquiry-form select{
  background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.28);border-radius:4px;
  padding:12px 14px;color:inherit;font:inherit;text-transform:none;letter-spacing:normal
}
.mcs-inquiry-form input:focus,.mcs-inquiry-form textarea:focus,.mcs-inquiry-form select:focus{
  outline:none;border-color:#c9a24a
}
.mcs-inquiry-form .mcs-row{display:grid;grid-template-columns:1fr 1fr;gap:12px}
@media (max-width:640px){.mcs-inquiry-form .mcs-row{grid-template-columns:1fr}}
.mcs-inquiry-form button[type=submit]{
  background:#c9a24a;color:#111;border:0;border-radius:4px;padding:14px 22px;
  font:inherit;font-weight:600;letter-spacing:.06em;text-transform:uppercase;cursor:pointer;align-self:flex-start
}
.mcs-inquiry-form button[type=submit][disabled]{opacity:.6;cursor:wait}
.mcs-inquiry-form .mcs-error{color:#ffb4b4;font-size:13px;text-transform:none;letter-spacing:normal}
.mcs-inquiry-form .mcs-honey{position:absolute;left:-9999px;opacity:0;height:0;width:0;overflow:hidden}
.mcs-inquiry-success{padding:18px 0;line-height:1.5}
.mcs-inquiry-success strong{display:block;margin-bottom:8px;font-size:1.1em}
`;
    document.head.appendChild(style);
  }

  function intentFromFormId(formId) {
    if (TRADE_FORMS.has(formId)) return "trade";
    if (FINANCE_FORMS.has(formId)) return "financing";
    if (SERVICE_FORMS.has(formId)) return "service-appointment";
    return "contact";
  }

  function destinationFor(intent) {
    return intent === "service-appointment" || intent === "ceramic" || intent === "paint-appointment"
      ? SERVICE
      : SALES;
  }

  function makeReference() {
    return "MCS-" + Date.now().toString(36).toUpperCase();
  }

  function buildForm({ intent, coach, title }) {
    const form = document.createElement("form");
    form.className = "mcs-inquiry-form";
    form.noValidate = true;
    form.innerHTML = `
      <input class="mcs-honey" type="text" name="company" tabindex="-1" autocomplete="off" aria-hidden="true">
      <input type="hidden" name="intent" value="${escapeAttr(intent || "contact")}">
      <input type="hidden" name="coach" value="${escapeAttr(coach || "")}">
      <div class="mcs-row">
        <label>First name<input name="firstName" required autocomplete="given-name"></label>
        <label>Last name<input name="lastName" required autocomplete="family-name"></label>
      </div>
      <div class="mcs-row">
        <label>Email<input name="email" type="email" required autocomplete="email"></label>
        <label>Phone<input name="phone" type="tel" required autocomplete="tel" placeholder="${PHONE}"></label>
      </div>
      <label>How can we help?
        <textarea name="message" rows="4" required placeholder="${escapeAttr(title || "Tell us what you need")}"></textarea>
      </label>
      <div class="mcs-error" data-error hidden></div>
      <button type="submit">Send to showroom</button>
      <p style="margin:0;opacity:.7;font-size:12px;text-transform:none;letter-spacing:normal">
        Delivers to ${destinationFor(intent)}. Or call <a href="tel:${PHONE_TEL}" style="color:inherit">${PHONE}</a>.
      </p>
    `;
    form.addEventListener("submit", onSubmit);
    return form;
  }

  function escapeAttr(value) {
    return String(value || "")
      .replace(/&/g, "&amp;")
      .replace(/"/g, "&quot;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function read(form) {
    const data = new FormData(form);
    const out = {};
    for (const [k, v] of data.entries()) out[k] = String(v).trim();
    return out;
  }

  async function onSubmit(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const fields = read(form);
    const error = form.querySelector("[data-error]");
    error.hidden = true;
    error.textContent = "";

    if (fields.company) {
      showSuccess(form, "Request received", "Thank you.");
      return;
    }
    if (!fields.firstName || !fields.lastName) {
      return showError(error, "Enter your first and last name.");
    }
    if (!EMAIL_RE.test(fields.email || "")) {
      return showError(error, "Enter a valid email address.");
    }
    if ((fields.phone || "").replace(/\D/g, "").length < 7) {
      return showError(error, "Enter a phone number with at least 7 digits.");
    }
    if (!fields.message) {
      return showError(error, "Tell us how we can help.");
    }

    const button = form.querySelector("[type=submit]");
    const label = button.textContent;
    button.disabled = true;
    button.textContent = "Sending";

    const reference = makeReference();
    const to = destinationFor(fields.intent);
    try {
      const ok =
        (await sendWeb3Forms(fields, reference, to)) ||
        (await sendFormSubmit(fields, reference, to));
      if (!ok) {
        showError(error, `The mailbox did not accept the message. Call ${PHONE}.`);
        button.disabled = false;
        button.textContent = label;
        return;
      }
      showSuccess(
        form,
        "Request sent",
        `Reference ${reference}. Delivered to ${to}. Call ${PHONE} if you need someone today.`
      );
    } catch {
      showError(error, `The message did not leave this page. Call ${PHONE}.`);
      button.disabled = false;
      button.textContent = label;
    }
  }

  function showError(node, message) {
    node.hidden = false;
    node.textContent = message;
  }

  function showSuccess(form, title, copy) {
    const box = document.createElement("div");
    box.className = "mcs-inquiry-success";
    box.setAttribute("role", "status");
    box.innerHTML = `<strong></strong><p></p>`;
    box.querySelector("strong").textContent = title;
    box.querySelector("p").textContent = copy;
    form.replaceWith(box);
  }

  function messageBody(fields, reference, to) {
    return [
      `Reference: ${reference}`,
      `Request: ${fields.intent || "contact"}`,
      `Delivered to: ${to}`,
      `Name: ${fields.firstName} ${fields.lastName}`,
      `Email: ${fields.email}`,
      `Phone: ${fields.phone}`,
      fields.coach ? `Coach: ${fields.coach}` : "",
      `Message: ${fields.message}`,
      `Page: ${location.href}`,
    ]
      .filter(Boolean)
      .join("\n");
  }

  async function sendWeb3Forms(fields, reference, to) {
    if (!WEB3_KEY) return false;
    const response = await fetch("https://api.web3forms.com/submit", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({
        access_key: WEB3_KEY,
        subject: `Showroom request ${reference}`,
        from_name: `${fields.firstName} ${fields.lastName}`.trim(),
        name: `${fields.firstName} ${fields.lastName}`.trim(),
        email: fields.email,
        phone: fields.phone,
        intent: fields.intent || "contact",
        delivered_to: to,
        coach: fields.coach || "",
        message: messageBody(fields, reference, to),
        page: location.href,
        botcheck: "",
      }),
    });
    const payload = await response.json().catch(() => ({}));
    return response.ok && payload.success !== false;
  }

  async function sendFormSubmit(fields, reference, to) {
    const response = await fetch("https://formsubmit.co/ajax/" + encodeURIComponent(to), {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({
        name: `${fields.firstName} ${fields.lastName}`.trim(),
        email: fields.email,
        phone: fields.phone,
        _subject: `Showroom request ${reference}`,
        _template: "table",
        _captcha: "false",
        _honey: fields.company || "",
        intent: fields.intent || "contact",
        delivered_to: to,
        coach: fields.coach || "",
        message: messageBody(fields, reference, to),
        page: location.href,
      }),
    });
    const payload = await response.json().catch(() => ({}));
    return response.ok && payload.success !== false && payload.success !== "false";
  }

  function mountInto(container, opts) {
    if (!container || container.dataset.mcsInquiry === "1") return;
    container.dataset.mcsInquiry = "1";
    container.innerHTML = "";
    container.appendChild(buildForm(opts || {}));
  }

  function replaceStaticHubSpotForms() {
    document.querySelectorAll(".hs-form-html, .tmcs-hs-form__embed, .hs-form-frame").forEach((node) => {
      const host = node.classList.contains("tmcs-hs-form__embed") ? node : node.parentElement || node;
      const formId = node.getAttribute("data-form-id") || "";
      const coach =
        document.querySelector("[data-nvx-inventory]")?.getAttribute("data-nvx-inventory") ||
        document.querySelector("h1")?.textContent?.trim() ||
        "";
      mountInto(host, { intent: intentFromFormId(formId), coach });
    });
  }

  function ensurePopup() {
    let popup = document.getElementById("nvx-popup");
    if (popup) return popup;
    popup = document.createElement("div");
    popup.id = "nvx-popup";
    popup.style.cssText =
      "visibility:hidden;opacity:0;position:fixed;inset:0;background:rgba(0,0,0,.72);z-index:9999;display:flex;align-items:center;justify-content:center;transition:opacity .25s,visibility .25s";
    popup.innerHTML = `
      <div class="nvx-popup-wrapper" style="background:#111;color:#fff;max-width:640px;width:min(92vw,640px);max-height:90vh;overflow:auto;padding:28px;border:1px solid rgba(255,255,255,.15);position:relative">
        <button type="button" class="nvx-close" aria-label="Close" style="position:absolute;top:10px;right:14px;background:none;border:0;color:#fff;font-size:28px;cursor:pointer">×</button>
        <div class="nvx-form-header"><h2 class="nvx-form-title" style="margin:0 0 8px"></h2><p class="nvx-form-description" style="margin:0 0 16px;opacity:.8"></p></div>
        <div class="nvx-form-container" style="min-height:100px"></div>
      </div>`;
    document.body.appendChild(popup);
    popup.querySelector(".nvx-close").addEventListener("click", () => closePopup(popup));
    popup.addEventListener("click", (e) => {
      if (e.target === popup) closePopup(popup);
    });
    return popup;
  }

  function openPopup(opts) {
    const popup = ensurePopup();
    popup.querySelector(".nvx-form-title").textContent = opts.title || "Get in touch";
    popup.querySelector(".nvx-form-description").textContent = opts.description || "";
    const container = popup.querySelector(".nvx-form-container");
    container.dataset.mcsInquiry = "";
    mountInto(container, opts);
    popup.style.visibility = "visible";
    popup.style.opacity = "1";
  }

  function closePopup(popup) {
    popup.style.opacity = "0";
    popup.style.visibility = "hidden";
  }

  function bindNvxButtons() {
    document.addEventListener(
      "click",
      (event) => {
        const trigger = event.target.closest("[data-nvx-form]");
        if (!trigger) return;
        event.preventDefault();
        event.stopPropagation();
        if (typeof event.stopImmediatePropagation === "function") event.stopImmediatePropagation();

        const raw = trigger.getAttribute("data-nvx-form") || "";
        const formIdMatch = raw.match(/data-form-id=&quot;([^&]+)&quot;/) || raw.match(/data-form-id="([^"]+)"/);
        const formId = formIdMatch ? formIdMatch[1] : "";
        openPopup({
          intent: intentFromFormId(formId),
          coach: trigger.getAttribute("data-nvx-inventory") || "",
          title: trigger.getAttribute("data-nvx-title") || "Get in touch",
          description: trigger.getAttribute("data-nvx-description") || "",
        });
      },
      true
    );
  }

  function boot() {
    replaceStaticHubSpotForms();
    bindNvxButtons();
    const observer = new MutationObserver(() => replaceStaticHubSpotForms());
    observer.observe(document.documentElement, { childList: true, subtree: true });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
