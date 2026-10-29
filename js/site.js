const headerToggle = document.querySelector(".utility .menu-toggle");
const nav = document.getElementById("site-nav");

headerToggle?.addEventListener("click", () => {
  const open = nav.classList.toggle("open");
  headerToggle.setAttribute("aria-expanded", String(open));
  headerToggle.textContent = open ? "Close" : "Menu";
});

/* <base href> rewrites bare #hashes to the site root; keep in-page anchors on this document. */
document.addEventListener("click", (event) => {
  const link = event.target.closest('a[href^="#"]');
  if (!link) return;
  const href = link.getAttribute("href");
  if (!href || href === "#" || href.startsWith("#/")) return;
  const id = decodeURIComponent(href.slice(1));
  if (!id) return;
  const target = document.getElementById(id);
  if (!target) return;
  event.preventDefault();
  target.scrollIntoView({ behavior: "smooth", block: "start" });
  history.pushState(null, "", `#${id}`);
  const focusable = target.querySelector("input, textarea, select, button");
  if (focusable instanceof HTMLElement) focusable.focus({ preventScroll: true });
});

document.querySelectorAll(".nav-item > .menu-toggle").forEach((button) => {
  button.addEventListener("click", () => {
    const item = button.closest(".nav-item");
    const open = item.classList.toggle("open");
    button.setAttribute("aria-expanded", String(open));
    button.textContent = open ? "Hide" : "Show";
  });
});

window.addEventListener("keydown", (event) => {
  if (event.key !== "Escape" || !nav?.classList.contains("open")) return;
  nav.classList.remove("open");
  headerToggle?.setAttribute("aria-expanded", "false");
  if (headerToggle) headerToggle.textContent = "Menu";
});

document.addEventListener(
  "error",
  (event) => {
    const img = event.target;
    if (!(img instanceof HTMLImageElement) || !img.dataset.fallback) return;
    if (img.dataset.fallback === "logo") {
      const mark = document.createElement("span");
      mark.className = "wordmark";
      mark.append("The ");
      const name = document.createElement("span");
      name.textContent = "Motorcoach";
      mark.append(name, " Store");
      img.replaceWith(mark);
      return;
    }
    const fallback = document.createElement("div");
    fallback.className = "img-fallback";
    fallback.setAttribute("role", "img");
    fallback.setAttribute("aria-label", img.alt);
    const label = document.createElement("span");
    label.textContent = img.alt;
    fallback.append(label);
    img.replaceWith(fallback);
  },
  true,
);
