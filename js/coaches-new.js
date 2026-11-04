(function () {
  const grid = document.querySelector("[data-units], .listing-grid, main");
  const cards = Array.from(document.querySelectorAll("article.unit[data-unit]"));
  if (!cards.length) return;

  const params = new URLSearchParams(location.search);
  const empty = document.querySelector("[data-empty], .listing-empty");
  const search = document.querySelector('input[type="search"], input[data-search], .filters__search input');
  const priceRoot = document.querySelector("[data-price-filter]");
  const sortRoot = document.querySelector(".sort-filter, [data-sort-filter]");

  const cardPrices = cards.map((card) => num(card.dataset.price)).filter((v) => v != null);
  const derivedMax = cardPrices.length ? Math.max(...cardPrices) : null;
  const state = {
    q: (params.get("q") || "").trim().toLowerCase(),
    sort: params.get("sort") || "",
    priceMin: num(priceRoot?.dataset.min) ?? 0,
    priceMax: Math.max(num(priceRoot?.dataset.max) ?? 0, derivedMax ?? 0) || Number.MAX_SAFE_INTEGER,
    lo: null,
    hi: null,
  };
  state.lo = state.priceMin;
  state.hi = state.priceMax;
  if (priceRoot) priceRoot.dataset.max = String(state.priceMax);

  function num(value) {
    const n = Number(value);
    return Number.isFinite(n) ? n : null;
  }

  function money(n) {
    return "$" + Math.round(n).toLocaleString();
  }

  function apply() {
    const matched = cards
      .filter((card) => {
        const price = num(card.dataset.price) || 0;
        if (price < state.lo || price > state.hi) return false;
        if (state.q) {
          const hay = (card.dataset.search || card.textContent || "").toLowerCase();
          if (!hay.includes(state.q)) return false;
        }
        return true;
      })
      .sort((a, b) => {
        const pa = num(a.dataset.price) || 0;
        const pb = num(b.dataset.price) || 0;
        const ya = num(a.dataset.year) || 0;
        const yb = num(b.dataset.year) || 0;
        const ca = num(a.dataset.created) || 0;
        const cb = num(b.dataset.created) || 0;
        if (state.sort === "price-asc") return pa - pb;
        if (state.sort === "price-desc") return pb - pa;
        if (state.sort === "year-desc") return yb - ya;
        return cb - ca;
      });

    cards.forEach((card) => {
      card.hidden = true;
      card.style.display = "none";
    });
    matched.forEach((card) => {
      card.hidden = false;
      card.style.display = "";
      card.parentElement?.append(card);
    });
    if (empty) empty.hidden = matched.length > 0;
  }

  function setupPrice() {
    if (!priceRoot) return;
    const from = priceRoot.querySelector("[data-price-from]");
    const to = priceRoot.querySelector("[data-price-to]");
    const range = priceRoot.querySelector("[data-price-range]");
    const handles = Array.from(priceRoot.querySelectorAll("[data-price-handle]"));
    const toggle = priceRoot.querySelector("[data-price-toggle]");
    const panel = priceRoot.querySelector("[data-price-panel]");
    const clear = priceRoot.querySelector("[data-price-clear]");
    const min = state.priceMin;
    const max = state.priceMax;
    const span = Math.max(1, max - min);

    function sync() {
      if (state.lo > state.hi) [state.lo, state.hi] = [state.hi, state.lo];
      if (from) from.textContent = money(state.lo);
      if (to) to.textContent = money(state.hi);
      const left = ((state.lo - min) / span) * 100;
      const right = ((state.hi - min) / span) * 100;
      if (range) {
        range.style.left = left + "%";
        range.style.width = Math.max(0, right - left) + "%";
      }
      handles.forEach((handle) => {
        const which = handle.dataset.priceHandle;
        const value = which === "min" ? state.lo : state.hi;
        handle.style.left = ((value - min) / span) * 100 + "%";
      });
      apply();
    }

    handles.forEach((handle) => {
      const move = (clientX) => {
        const track = priceRoot.querySelector("[data-price-slider]");
        if (!track) return;
        const rect = track.getBoundingClientRect();
        const ratio = Math.min(1, Math.max(0, (clientX - rect.left) / rect.width));
        const value = min + ratio * span;
        if (handle.dataset.priceHandle === "min") state.lo = value;
        else state.hi = value;
        sync();
      };
      handle.addEventListener("pointerdown", (event) => {
        event.preventDefault();
        handle.setPointerCapture(event.pointerId);
        const onMove = (e) => move(e.clientX);
        const onUp = () => {
          handle.releasePointerCapture(event.pointerId);
          window.removeEventListener("pointermove", onMove);
          window.removeEventListener("pointerup", onUp);
        };
        window.addEventListener("pointermove", onMove);
        window.addEventListener("pointerup", onUp);
        move(event.clientX);
      });
    });

    toggle?.addEventListener("click", () => {
      const open = panel?.hasAttribute("hidden");
      if (!panel) return;
      if (open) {
        panel.removeAttribute("hidden");
        priceRoot.classList.add("is-open");
        toggle.setAttribute("aria-expanded", "true");
      } else {
        panel.setAttribute("hidden", "");
        priceRoot.classList.remove("is-open");
        toggle.setAttribute("aria-expanded", "false");
      }
    });

    clear?.addEventListener("click", () => {
      state.lo = min;
      state.hi = max;
      sync();
    });

    sync();
  }

  function setupSort() {
    if (!sortRoot) return;
    const toggle = sortRoot.querySelector(".sort-filter__toggle, [data-sort-toggle]");
    const menu = sortRoot.querySelector(".sort-filter__menu, [data-sort-menu]");
    toggle?.addEventListener("click", () => {
      if (!menu) return;
      const open = menu.hasAttribute("hidden");
      if (open) {
        menu.removeAttribute("hidden");
        sortRoot.classList.add("is-open");
      } else {
        menu.setAttribute("hidden", "");
        sortRoot.classList.remove("is-open");
      }
    });
    sortRoot.querySelectorAll("[data-sort]").forEach((btn) => {
      btn.addEventListener("click", () => {
        state.sort = btn.dataset.sort || "";
        sortRoot.querySelectorAll("[data-sort]").forEach((el) => el.classList.remove("is-selected"));
        btn.classList.add("is-selected");
        menu?.setAttribute("hidden", "");
        sortRoot.classList.remove("is-open");
        apply();
      });
    });
  }

  search?.addEventListener("input", () => {
    state.q = search.value.trim().toLowerCase();
    apply();
  });
  if (search && state.q) search.value = state.q;

  document.addEventListener("click", (event) => {
    if (priceRoot && !priceRoot.contains(event.target)) {
      priceRoot.querySelector("[data-price-panel]")?.setAttribute("hidden", "");
      priceRoot.classList.remove("is-open");
    }
    if (sortRoot && !sortRoot.contains(event.target)) {
      sortRoot.querySelector(".sort-filter__menu")?.setAttribute("hidden", "");
      sortRoot.classList.remove("is-open");
    }
  });

  setupPrice();
  setupSort();
  apply();
})();
