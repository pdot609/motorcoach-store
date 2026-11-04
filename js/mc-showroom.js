(function () {
  const root = document.querySelector(".mc-showroom");
  if (!root) return;

  const grid = root.querySelector(".mc-showroom__grid");
  const cards = Array.from(root.querySelectorAll("article.mc-card"));
  const countEl = root.querySelector(".mc-showroom__count");
  const emptyEl = root.querySelector(".mc-showroom__empty");
  const pageSize = Number(root.dataset.pageSize || 12) || 12;
  const canLoadMore = root.dataset.loadmore === "1";

  const facetsScript = root.querySelector('script[type="application/json"]');
  let facets = {};
  try {
    facets = facetsScript ? JSON.parse(facetsScript.textContent).facets || {} : {};
  } catch {
    facets = {};
  }

  const params = new URLSearchParams(location.search);
  const state = {
    year: new Set(),
    make: new Set(),
    model: new Set(),
    condition: normalizeCondition(params.get("condition") || ""),
    miles: null,
    price: null,
    q: (params.get("q") || "").trim().toLowerCase(),
    sortField: root.dataset.sortField === "created" ? "created" : root.dataset.sortField || "created",
    sortDir: root.dataset.sortDir || "desc",
    page: 1,
  };

  function normalizeCondition(value) {
    const v = String(value || "").trim().toLowerCase();
    if (!v) return "";
    if (v === "certified" || v === "cpo" || v.includes("certified")) return "certified";
    if (v.includes("pre")) return "pre-owned";
    if (v === "new") return "new";
    return v;
  }

  function cardCondition(card) {
    return normalizeCondition(card.dataset.condition || "");
  }

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
        if (state[facetName] instanceof Set && state[facetName].has(value)) {
          btn.classList.add("is-selected");
        }
        menu.append(btn);
      });
  }

  function setupRanges() {
    ["miles", "price"].forEach((facetName) => {
      const filter = root.querySelector(`.mc-filter[data-facet="${facetName}"]`);
      const conf = facets[facetName] || {};
      const values = cards.map((card) => num(card.dataset[facetName])).filter((v) => v != null);
      // Always derive from live cards so stale facet JSON cannot hide inventory
      // after price updates. Expand with facet bounds when present.
      let min = values.length ? Math.min(...values) : num(conf.min);
      let max = values.length ? Math.max(...values) : num(conf.max);
      const confMin = num(conf.min);
      const confMax = num(conf.max);
      if (confMin != null) min = min == null ? confMin : Math.min(min, confMin);
      if (confMax != null) max = max == null ? confMax : Math.max(max, confMax);
      if (min == null || max == null || min === max) {
        state[facetName] = null;
        return;
      }
      state[facetName] = { min, max, lo: min, hi: max };
      if (!filter) return;
      const inner = filter.querySelector(".mc-filter-inner");
      if (!inner) return;
      inner.querySelectorAll("input, .mc-range__values").forEach((el) => el.remove());
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
    if (state.condition) {
      const cond = cardCondition(card);
      if (state.condition === "certified") {
        if (cond !== "certified") return false;
      } else if (cond !== state.condition) {
        return false;
      }
    }
    if (state.year.size && !state.year.has(cardValue(card, "year"))) return false;
    if (state.make.size && !state.make.has(cardValue(card, "make"))) return false;
    if (state.model.size && !state.model.has(cardValue(card, "model"))) return false;
    if (state.miles) {
      const miles = num(card.dataset.miles);
      if (miles != null && (miles < state.miles.lo || miles > state.miles.hi)) return false;
    }
    if (state.price) {
      const price = num(card.dataset.price);
      if (price != null && (price < state.price.lo || price > state.price.hi)) return false;
    }
    if (state.q) {
      const hay = [
        cardValue(card, "make"),
        cardValue(card, "model"),
        card.dataset.stock || "",
        card.dataset.engine || "",
        card.dataset.condition || "",
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
      if (field === "created" || field === "create_date" || field === "sale_date") {
        av = num(a.dataset.created) || num(a.dataset.saleDate) || 0;
        bv = num(b.dataset.created) || num(b.dataset.saleDate) || 0;
      } else {
        av = num(a.dataset[field]) || 0;
        bv = num(b.dataset[field]) || 0;
      }
      return (av - bv) * dir;
    });
  }

  function loadMoreButtons() {
    const found = Array.from(
      root.querySelectorAll("[data-load-more], .mc-showroom__loadmore, button.mc-showroom__loadmore")
    );
    return found.filter((btn, index, all) => all.indexOf(btn) === index);
  }

  function bindLoadMore(btn) {
    if (!btn || btn.dataset.bound === "1") return;
    btn.dataset.bound = "1";
    btn.dataset.loadMore = "1";
    btn.addEventListener("click", (event) => {
      event.preventDefault();
      state.page += 1;
      apply();
    });
  }

  function ensureLoadMore(matchedCount, visibleCount) {
    let buttons = loadMoreButtons();
    if (!canLoadMore || visibleCount >= matchedCount) {
      buttons.forEach((btn) => {
        btn.hidden = true;
        btn.style.display = "none";
      });
      return;
    }
    if (!buttons.length) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "mc-btn mc-showroom__loadmore";
      btn.dataset.loadMore = "1";
      btn.textContent = "Load more";
      grid?.parentElement?.append(btn);
      buttons = [btn];
    }
    // Keep one visible control; hide extras so users always hit a bound button.
    buttons.forEach((btn, index) => {
      bindLoadMore(btn);
      const show = index === 0;
      btn.hidden = !show;
      btn.style.display = show ? "" : "none";
      btn.textContent = "Load more";
    });
  }

  function apply() {
    const matched = sortCards(cards.filter(matches));
    const limit = canLoadMore ? pageSize * state.page : matched.length;
    cards.forEach((card) => {
      card.hidden = true;
      card.style.display = "none";
    });
    matched.forEach((card, index) => {
      const show = !canLoadMore || index < limit;
      card.hidden = !show;
      card.style.display = show ? "" : "none";
      if (show && grid) grid.append(card);
    });
    const shown = canLoadMore ? Math.min(matched.length, limit) : matched.length;
    if (countEl) {
      countEl.textContent = matched.length
        ? `Showing ${shown} of ${matched.length} coaches`
        : "Showing 0 coaches";
    }
    if (emptyEl) emptyEl.hidden = matched.length > 0;
    const loader = root.querySelector(".mc-showroom__loader");
    if (loader) loader.hidden = true;
    ensureLoadMore(matched.length, shown);
  }

  function clearAll() {
    state.year.clear();
    state.make.clear();
    state.model.clear();
    state.condition = "";
    state.q = "";
    state.page = 1;
    const url = new URL(location.href);
    url.search = "";
    history.replaceState({}, "", url);
    root.querySelectorAll(".mc-option.is-selected").forEach((el) => el.classList.remove("is-selected"));
    const search = root.querySelector('input[type="search"], input[data-search], .mc-search input');
    if (search) search.value = "";
    setupRanges();
    apply();
  }

  ["year", "make", "model"].forEach(populateSelect);
  setupRanges();

  const search = root.querySelector('input[type="search"], input[data-search], .mc-search input');
  if (search && state.q) search.value = state.q;

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
        state.page = 1;
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
        state.page = 1;
        apply();
      }
      return;
    }

    if (event.target.closest("[data-clear]")) {
      clearAll();
    }
  });

  search?.addEventListener("input", () => {
    state.q = search.value.trim().toLowerCase();
    state.page = 1;
    apply();
  });

  document.addEventListener("click", (event) => {
    if (!root.contains(event.target)) closeMenus();
  });

  document.querySelectorAll("video.lazy-bg-video[data-src]").forEach((video) => {
    video.src = video.dataset.src;
    video.load();
    video.play?.().catch(() => {});
  });

  apply();
})();
