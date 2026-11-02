(function () {
  const root = document.querySelector(".mc-showroom");
  if (!root) return;

  const grid = root.querySelector(".mc-showroom__grid");
  const cards = Array.from(root.querySelectorAll("article.mc-card"));
  const countEl = root.querySelector(".mc-showroom__count");
  const emptyEl = root.querySelector(".mc-showroom__empty");
  const pageSize = Number(root.dataset.pageSize || 12) || 12;

  const facetsScript = root.querySelector('script[type="application/json"]');
  let facets = {};
  try {
    facets = facetsScript ? JSON.parse(facetsScript.textContent).facets || {} : {};
  } catch {
    facets = {};
  }

  const state = {
    year: new Set(),
    make: new Set(),
    model: new Set(),
    miles: null,
    price: null,
    q: "",
    sortField: root.dataset.sortField === "created" ? "created" : "created",
    sortDir: root.dataset.sortDir || "desc",
  };

  function num(value) {
    const n = Number(value);
    return Number.isFinite(n) ? n : null;
  }

  function cardValue(card, key) {
    return (card.dataset[key] || "").toLowerCase();
  }

  function populateSelect(facetName) {
    const filter = root.querySelector(`.mc-filter[data-facet="${facetName}"]`);
    if (!filter) return;
    const menu = filter.querySelector(".mc-select__menu");
    if (!menu) return;
    const options = (facets[facetName] && facets[facetName].options) || [];
    const seen = new Map();
    options.forEach((opt) => seen.set(String(opt.value).toLowerCase(), opt.label || opt.value));
    cards.forEach((card) => {
      const value = cardValue(card, facetName);
      if (value && !seen.has(value)) {
        seen.set(value, value.replace(/\b\w/g, (c) => c.toUpperCase()));
      }
    });
    menu.replaceChildren();
    [...seen.entries()]
      .sort((a, b) => a[1].localeCompare(b[1], undefined, { numeric: true }))
      .forEach(([value, label]) => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "mc-option";
        btn.setAttribute("role", "option");
        btn.dataset.value = value;
        btn.textContent = label;
        menu.append(btn);
      });
  }

  function setupRanges() {
    ["miles", "price"].forEach((facetName) => {
      const filter = root.querySelector(`.mc-filter[data-facet="${facetName}"]`);
      if (!filter) return;
      const conf = facets[facetName] || {};
      let min = num(conf.min);
      let max = num(conf.max);
      if (min == null || max == null) {
        const values = cards.map((card) => num(card.dataset[facetName])).filter((v) => v != null);
        min = values.length ? Math.min(...values) : 0;
        max = values.length ? Math.max(...values) : 0;
      }
      state[facetName] = { min, max, lo: min, hi: max };
      const inner = filter.querySelector(".mc-filter-inner");
      if (!inner) return;
      inner.querySelectorAll("input").forEach((input) => input.remove());
      const lo = document.createElement("input");
      lo.type = "range";
      lo.min = String(min);
      lo.max = String(max);
      lo.value = String(min);
      lo.dataset.bound = "lo";
      const hi = document.createElement("input");
      hi.type = "range";
      hi.min = String(min);
      hi.max = String(max);
      hi.value = String(max);
      hi.dataset.bound = "hi";
      const label = document.createElement("div");
      label.className = "mc-range__values";
      const sync = () => {
        let a = Number(lo.value);
        let b = Number(hi.value);
        if (a > b) [a, b] = [b, a];
        state[facetName].lo = a;
        state[facetName].hi = b;
        label.textContent =
          facetName === "price"
            ? `$${a.toLocaleString()} – $${b.toLocaleString()}`
            : `${a.toLocaleString()} – ${b.toLocaleString()} mi`;
        apply();
      };
      lo.addEventListener("input", sync);
      hi.addEventListener("input", sync);
      inner.append(label, lo, hi);
      sync();
    });
  }

  function closeMenus(except) {
    root.querySelectorAll(".mc-filter").forEach((filter) => {
      const menu = filter.querySelector(".mc-filter-inner");
      const toggle = filter.querySelector(".mc-select__toggle");
      if (filter === except) return;
      if (menu) menu.hidden = true;
      if (toggle) toggle.setAttribute("aria-expanded", "false");
    });
  }

  function matches(card) {
    if (state.year.size && !state.year.has(cardValue(card, "year"))) return false;
    if (state.make.size && !state.make.has(cardValue(card, "make"))) return false;
    if (state.model.size && !state.model.has(cardValue(card, "model"))) return false;
    if (state.miles) {
      const miles = num(card.dataset.miles);
      if (miles == null || miles < state.miles.lo || miles > state.miles.hi) return false;
    }
    if (state.price) {
      const price = num(card.dataset.price);
      if (price == null || price < state.price.lo || price > state.price.hi) return false;
    }
    if (state.q) {
      const hay = [
        cardValue(card, "make"),
        cardValue(card, "model"),
        card.dataset.stock || "",
        card.dataset.engine || "",
        card.textContent || "",
      ]
        .join(" ")
        .toLowerCase();
      if (!hay.includes(state.q)) return false;
    }
    return true;
  }

  function sortCards(list) {
    const field = state.sortField;
    const dir = state.sortDir === "asc" ? 1 : -1;
    return list.sort((a, b) => {
      let av;
      let bv;
      if (field === "make") {
        av = cardValue(a, "make");
        bv = cardValue(b, "make");
        return av.localeCompare(bv) * dir;
      }
      if (field === "created" || field === "create_date") {
        av = num(a.dataset.created) || 0;
        bv = num(b.dataset.created) || 0;
      } else {
        av = num(a.dataset[field]) || 0;
        bv = num(b.dataset[field]) || 0;
      }
      return (av - bv) * dir;
    });
  }

  function apply() {
    const matched = sortCards(cards.filter(matches));
    cards.forEach((card) => {
      card.hidden = true;
      card.style.display = "none";
    });
    matched.forEach((card, index) => {
      const show = index < pageSize || pageSize <= 0;
      card.hidden = !show;
      card.style.display = show ? "" : "none";
      if (show && grid && card.parentElement !== grid) grid.append(card);
      else if (show) grid.append(card);
    });
    if (countEl) {
      countEl.textContent = matched.length
        ? `Showing ${Math.min(matched.length, pageSize || matched.length)} of ${matched.length} coaches`
        : "Showing 0 coaches";
    }
    if (emptyEl) emptyEl.hidden = matched.length > 0;
    const loader = root.querySelector(".mc-showroom__loader");
    if (loader) loader.hidden = true;
  }

  function clearAll() {
    state.year.clear();
    state.make.clear();
    state.model.clear();
    state.q = "";
    root.querySelectorAll(".mc-option.is-selected").forEach((el) => el.classList.remove("is-selected"));
    const search = root.querySelector('input[type="search"], input[data-search], .mc-search input');
    if (search) search.value = "";
    setupRanges();
    apply();
  }

  ["year", "make", "model"].forEach(populateSelect);
  setupRanges();

  root.addEventListener("click", (event) => {
    const toggle = event.target.closest(".mc-select__toggle, .mc-filter__label");
    if (toggle) {
      const filter = toggle.closest(".mc-filter");
      const menu = filter?.querySelector(".mc-filter-inner");
      const open = menu && menu.hidden;
      closeMenus(open ? filter : null);
      if (menu) {
        menu.hidden = !open;
        toggle.setAttribute("aria-expanded", open ? "true" : "false");
      }
      return;
    }

    const option = event.target.closest(".mc-option");
    if (option) {
      const filter = option.closest(".mc-filter");
      const facet = filter?.dataset.facet;
      if (option.dataset.sortField) {
        state.sortField = option.dataset.sortField;
        state.sortDir = option.dataset.sortDir || "desc";
        filter?.querySelectorAll(".mc-option").forEach((el) => el.classList.remove("is-selected"));
        option.classList.add("is-selected");
        closeMenus();
        apply();
        return;
      }
      if (facet && state[facet] instanceof Set) {
        const value = (option.dataset.value || "").toLowerCase();
        if (state[facet].has(value)) {
          state[facet].delete(value);
          option.classList.remove("is-selected");
        } else {
          state[facet].add(value);
          option.classList.add("is-selected");
        }
        apply();
      }
      return;
    }

    if (event.target.closest("[data-clear]")) {
      clearAll();
    }
  });

  const search = root.querySelector('input[type="search"], input[data-search], .mc-search input');
  search?.addEventListener("input", () => {
    state.q = search.value.trim().toLowerCase();
    apply();
  });

  document.addEventListener("click", (event) => {
    if (!root.contains(event.target)) closeMenus();
  });

  // Lazy-load hero video if present
  document.querySelectorAll("video.lazy-bg-video[data-src]").forEach((video) => {
    video.src = video.dataset.src;
    video.load();
    video.play?.().catch(() => {});
  });

  apply();
})();
