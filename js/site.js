const headerToggle = document.querySelector(".utility .menu-toggle");
const nav = document.getElementById("site-nav");

headerToggle?.addEventListener("click", () => {
  const open = nav.classList.toggle("open");
  headerToggle.setAttribute("aria-expanded", String(open));
  headerToggle.textContent = open ? "Close" : "Menu";
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
