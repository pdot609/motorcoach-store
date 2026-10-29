const root = document.getElementById("inventory");
if (root) loadInventory(root);

const LABELS = {
  prevost: "Prevost",
  newmar: "Newmar",
  newell: "Newell",
  tiffin: "Tiffin",
  foretravel: "Foretravel",
  ogv: "OGV",
  featherlite: "Featherlite",
  showhauler: "ShowHauler",
  "cargo mate": "Cargo Mate",
  "cargo-mate": "Cargo Mate",
};

function money(value) {
  if (value == null || value <= 0) return null;
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(value);
}

function miles(value) {
  if (value == null) return null;
  return `${new Intl.NumberFormat("en-US").format(value)} mi`;
}

function makeLabel(make) {
  return LABELS[make] ?? make.replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function conditionLabel(condition) {
  if (condition === "certified") return "Certified Pre-Owned";
  if (condition === "pre-owned") return "Pre-Owned";
  if (condition === "new") return "New";
  return condition;
}

function inScope(coach, query) {
  if (query.channel && !coach.channels.includes(query.channel)) return false;
  if (query.brand && coach.brand !== query.brand) return false;
  if (query.status && query.status !== "all" && coach.status !== query.status) return false;
  return true;
}

async function loadInventory(mount) {
  const fixed = {
    channel: mount.dataset.channel || "",
    brand: mount.dataset.brand || "",
    status: mount.dataset.status || "available",
  };
  let coaches = [];
  try {
    const response = await fetch("/data/coaches.json");
    if (!response.ok) throw new Error(String(response.status));
    coaches = await response.json();
    mount._coaches = coaches;
  } catch {
    mount.replaceChildren(empty("The showroom list did not load", "Call 941 283 2516 and the desk can read the current inventory."));
    return;
  }
  render(mount, coaches, fixed, queryFromLocation());
}

function render(mount, coaches, fixed, query) {
  const showroom = mount.dataset.layout === "showroom";
  let form = mount.querySelector("form.filters");
  let column = mount.querySelector("[data-results]");
  if (!form || !column) {
    const layout = document.createElement("div");
    layout.className = showroom ? "layout showroom" : "layout";
    const pool = coaches.filter((coach) => inScope(coach, fixed));
    form = showroom ? showroomFilters(pool, query) : filters(facetMakes(coaches, fixed), query);
    column = document.createElement("div");
    column.dataset.results = "true";
    layout.append(form, column);
    mount.replaceChildren(layout);
    form.addEventListener("change", (event) => {
      const target = event.target;
      if (!(target instanceof HTMLSelectElement) && !(target instanceof HTMLInputElement)) return;
      if (target.name === "q") return;
      writeQuery(target.name, target.value);
      mount.dataset.page = "1";
      render(mount, coaches, fixed, queryFromLocation());
    });
    form.addEventListener("submit", (event) => event.preventDefault());
    form.querySelector("[data-search]")?.addEventListener("input", (event) => {
      writeQuery("q", event.target.value);
      mount.dataset.page = "1";
      render(mount, coaches, fixed, queryFromLocation());
    });
    form.querySelector("[data-clear]")?.addEventListener("click", () => reset(mount, coaches, fixed));
  }
  const results = filterCoaches(coaches, { ...query, ...fixed });
  if (showroom) {
    column.replaceChildren(showroomList(mount, results, () => reset(mount, coaches, fixed)));
  } else {
    column.replaceChildren(list(results, () => reset(mount, coaches, fixed)));
  }
}

function reset(mount, coaches, fixed) {
  history.replaceState(null, "", location.pathname);
  mount.dataset.page = "1";
  const form = mount.querySelector("form.filters");
  if (form) {
    form.querySelectorAll("input, select").forEach((control) => {
      if (control.name === "sort") control.value = mount.dataset.layout === "showroom" ? "newest" : "year-desc";
      else control.value = "";
    });
  }
  render(mount, coaches, fixed, clearQuery());
}

function filters(makes, query) {
  const form = document.createElement("form");
  form.className = "filters";
  form.append(
    field("Search", input("q", query.q, "Prevost, stock, floorplan")),
    field("Make", select("make", query.make, [["", "All makes"], ...makes.map((make) => [make, makeLabel(make)])])),
    field("Condition", select("condition", query.condition, [["", "Any condition"], ["new", "New"], ["pre-owned", "Pre-owned"], ["certified", "Certified pre-owned"]])),
    field("Price", select("price", query.price, [["", "Any price"], ["under-200", "Under $200,000"], ["200-500", "$200,000 – $499,999"], ["500-1000", "$500,000 – $999,999"], ["over-1000", "$1,000,000 and up"]])),
    field("Mileage", select("miles", query.miles, [["", "Any mileage"], ["under-25", "Under 25,000"], ["under-50", "Under 50,000"], ["under-100", "Under 100,000"]])),
    field("Sort", select("sort", query.sort || "year-desc", [["year-desc", "Newest year"], ["price-asc", "Price, low to high"], ["price-desc", "Price, high to low"], ["miles-asc", "Lowest miles"]])),
  );
  const clear = document.createElement("button");
  clear.className = "btn";
  clear.type = "button";
  clear.dataset.clear = "true";
  clear.textContent = "Clear filters";
  form.append(clear);
  return form;
}

function list(results, onClear) {
  const column = document.createElement("div");
  const meta = document.createElement("div");
  meta.className = "result-meta";
  const count = document.createElement("p");
  count.textContent = `${results.length} ${results.length === 1 ? "coach" : "coaches"}`;
  meta.append(count);
  column.append(meta);
  if (results.length === 0) {
    const box = empty("No coaches match", "Clear a filter or search a make, stock number, or floorplan.");
    const button = document.createElement("button");
    button.className = "btn";
    button.type = "button";
    button.dataset.clear = "true";
    button.textContent = "Show the full list";
    button.addEventListener("click", onClear);
    box.append(button);
    column.append(box);
    return column;
  }
  const grid = document.createElement("div");
  grid.className = "grid";
  results.forEach((coach) => grid.append(card(coach)));
  column.append(grid);
  return column;
}

function card(coach) {
  const article = document.createElement("article");
  article.className = "coach-card";
  const media = document.createElement("a");
  media.className = "media";
  media.href = `/coaches/${coach.slug}`;
  media.setAttribute("aria-label", coach.title);
  const img = document.createElement("img");
  img.src = coach.image;
  img.alt = coach.title;
  img.dataset.fallback = "media";
  const badges = document.createElement("div");
  badges.className = "badge-row";
  if (coach.status === "sold") badges.append(badge("Sold", "sold"));
  if (coach.condition === "certified") badges.append(badge("CPO"));
  if (coach.condition === "new") badges.append(badge("New"));
  media.append(img, badges);

  const body = document.createElement("div");
  body.className = "coach-body";
  const heading = document.createElement("h3");
  const title = document.createElement("a");
  title.href = `/coaches/${coach.slug}`;
  title.textContent = coach.title;
  heading.append(title);
  const specs = document.createElement("div");
  specs.className = "specs";
  [String(coach.year), makeLabel(coach.make), miles(coach.miles), coach.engine].filter(Boolean).forEach((item) => {
    const span = document.createElement("span");
    span.textContent = item;
    specs.append(span);
  });
  const prices = document.createElement("div");
  prices.className = "price-row";
  const price = money(coach.price);
  const msrp = money(coach.msrp);
  if (msrp && coach.price > 0 && coach.msrp > coach.price) {
    const was = document.createElement("span");
    was.className = "msrp";
    was.textContent = `MSRP ${msrp}`;
    prices.append(was);
  }
  const now = document.createElement("span");
  now.className = "price";
  now.textContent = price ?? (coach.status === "sold" ? "Sold" : "Call for price");
  prices.append(now);
  body.append(heading, specs, prices);
  if (coach.monthly) {
    const monthly = document.createElement("p");
    monthly.className = "monthly";
    monthly.textContent = `Monthly payment ${money(coach.monthly)}`;
    body.append(monthly);
  }
  const more = document.createElement("a");
  more.className = "btn";
  more.href = `/coaches/${coach.slug}`;
  more.textContent = coach.status === "sold" ? "View record" : "Learn more";
  const stock = document.createElement("p");
  stock.className = "specs";
  stock.textContent = `${conditionLabel(coach.condition)} · Stock ${coach.stock}`;
  body.append(more, stock);
  article.append(media, body);
  return article;
}

function showroomFilters(pool, query) {
  const form = document.createElement("form");
  form.className = "filters";
  const years = [...new Set(pool.map((coach) => String(coach.year)))].sort((a, b) => b - a);
  const makes = [...new Set(pool.map((coach) => coach.make))].sort();
  const models = [...new Set(pool.map((coach) => coach.model).filter(Boolean))].sort();
  form.append(
    field("Year", select("year", query.year, [["", "Year"], ...years.map((year) => [year, year])])),
    field("Make", select("make", query.make, [["", "Make"], ...makes.map((make) => [make, makeLabel(make)])])),
    field("Model", select("model", query.model, [["", "Model"], ...models.map((model) => [model, makeLabel(model)])])),
    field("Mileage", rangePair("milesMin", "milesMax", query.milesMin, query.milesMax)),
    field("Price", rangePair("priceMin", "priceMax", query.priceMin, query.priceMax)),
    field("Sort by", select("sort", !query.sort || query.sort === "year-desc" ? "newest" : query.sort, [
      ["newest", "Newest"],
      ["oldest", "Oldest"],
      ["make-asc", "Make (A → Z)"],
      ["make-desc", "Make (Z → A)"],
      ["hp-asc", "Horse power (Low→High)"],
      ["hp-desc", "Horse power (High→Low)"],
      ["price-asc", "Price (Low→High)"],
      ["price-desc", "Price (High→Low)"],
      ["miles-asc", "Miles (Low→High)"],
      ["miles-desc", "Miles (High→Low)"],
    ])),
  );
  const search = input("q", query.q, "Search");
  search.setAttribute("aria-label", "Search coaches");
  form.append(field("Search", search));
  const clear = document.createElement("button");
  clear.className = "btn";
  clear.type = "button";
  clear.dataset.clear = "true";
  clear.textContent = "Clear all";
  form.append(clear);
  return form;
}

function rangePair(minName, maxName, minValue, maxValue) {
  const wrap = document.createElement("div");
  wrap.className = "range-pair";
  wrap.append(rangeInput(minName, minValue, "Min"), rangeInput(maxName, maxValue, "Max"));
  return wrap;
}

function rangeInput(name, value, placeholder) {
  const node = document.createElement("input");
  node.name = name;
  node.type = "number";
  node.min = "0";
  node.inputMode = "numeric";
  node.value = value || "";
  node.placeholder = placeholder;
  node.setAttribute("aria-label", placeholder);
  return node;
}

function showroomList(mount, results, onClear) {
  const column = document.createElement("div");
  if (results.length === 0) {
    const box = empty("No coaches match your filters.", "Adjust filters or clear them and try again.");
    const button = document.createElement("button");
    button.className = "btn";
    button.type = "button";
    button.textContent = "Clear all Filters and Search";
    button.addEventListener("click", onClear);
    box.append(button);
    column.append(box);
    return column;
  }
  const page = Math.max(1, Number(mount.dataset.page || 1));
  const visible = results.slice(0, page * 5);
  const list = document.createElement("div");
  list.className = "showroom-list";
  visible.forEach((coach) => list.append(showroomCard(coach)));
  column.append(list);
  if (visible.length < results.length) {
    const more = document.createElement("button");
    more.className = "btn load-more";
    more.type = "button";
    more.textContent = "Load more";
    more.addEventListener("click", () => {
      mount.dataset.page = String(page + 1);
      const inventory = mount;
      const coaches = inventory._coaches;
      if (!coaches) return;
      render(inventory, coaches, {
        channel: inventory.dataset.channel || "",
        brand: inventory.dataset.brand || "",
        status: inventory.dataset.status || "available",
      }, queryFromLocation());
    });
    column.append(more);
  }
  return column;
}

function showroomCard(coach) {
  const article = document.createElement("article");
  article.className = "showroom-card";
  const media = document.createElement("a");
  media.className = "media";
  media.href = `/coaches/${coach.slug}`;
  media.setAttribute("aria-label", coach.title);
  const img = document.createElement("img");
  img.src = coach.image;
  img.alt = coach.title;
  img.dataset.fallback = "media";
  media.append(img);

  const body = document.createElement("div");
  body.className = "showroom-body";
  const heading = document.createElement("h2");
  const title = document.createElement("a");
  title.href = `/coaches/${coach.slug}`;
  title.textContent = coach.title;
  heading.append(title);
  const specs = document.createElement("div");
  specs.className = "showroom-specs";
  [
    ["Year", String(coach.year)],
    ["Make", makeLabel(coach.make)],
    ["Model", makeLabel(coach.model || "")],
    ["Floorplan", coach.floorplan],
    ["Slides", coach.slides],
    ["Bath(s)", coach.baths],
    ["Bunk Beds", coach.bunks ? String(coach.bunks).toUpperCase() : ""],
    ["Engine", coach.engine],
    ["Mileage", coach.miles == null ? (coach.condition === "new" ? "New" : "") : miles(coach.miles)],
    ["Stock #", coach.stock],
  ].forEach(([label, value]) => {
    if (!value) return;
    const row = document.createElement("p");
    const name = document.createElement("span");
    name.textContent = label;
    const strong = document.createElement("strong");
    strong.textContent = value;
    row.append(name, strong);
    specs.append(row);
  });
  const prices = document.createElement("p");
  prices.className = "showroom-price";
  const sale = money(coach.price);
  const msrp = money(coach.msrp);
  if (msrp && coach.price > 0 && coach.msrp > coach.price) {
    const label = document.createElement("span");
    label.textContent = "MSRP";
    const was = document.createElement("s");
    was.textContent = msrp;
    prices.append(label, was);
  }
  const now = document.createElement("strong");
  now.textContent = sale ?? (coach.status === "sold" ? "Sold" : "Call for price");
  prices.append(now);
  body.append(heading, specs, prices);
  if (coach.monthly) {
    const monthly = document.createElement("p");
    monthly.className = "showroom-monthly";
    monthly.textContent = `Monthly Payment: ${money(coach.monthly)}`;
    body.append(monthly);
  }
  const more = document.createElement("a");
  more.className = "btn";
  more.href = `/coaches/${coach.slug}`;
  more.textContent = "Learn More";
  body.append(more);
  article.append(media, body);
  return article;
}

function badge(text, extra) {
  const span = document.createElement("span");
  span.className = extra ? `badge ${extra}` : "badge";
  span.textContent = text;
  return span;
}

function empty(title, lede) {
  const box = document.createElement("div");
  box.className = "empty";
  const heading = document.createElement("h2");
  heading.textContent = title;
  const copy = document.createElement("p");
  copy.className = "lede";
  copy.textContent = lede;
  box.append(heading, copy);
  return box;
}

function field(label, control) {
  const wrap = document.createElement("label");
  wrap.append(label, control);
  if (control.name === "q") control.setAttribute("aria-label", "Search coaches");
  return wrap;
}

function input(name, value, placeholder) {
  const node = document.createElement("input");
  node.name = name;
  node.value = value || "";
  node.placeholder = placeholder;
  node.dataset.search = "true";
  return node;
}

function select(name, value, options) {
  const node = document.createElement("select");
  node.name = name;
  options.forEach(([optionValue, label]) => {
    const option = document.createElement("option");
    option.value = optionValue;
    option.textContent = label;
    option.selected = optionValue === (value || "");
    node.append(option);
  });
  return node;
}

function queryFromLocation() {
  const params = new URLSearchParams(location.search);
  return {
    q: params.get("q") ?? "",
    make: params.get("make") ?? "",
    model: params.get("model") ?? "",
    year: params.get("year") ?? "",
    condition: params.get("condition") ?? "",
    price: params.get("price") ?? "",
    miles: params.get("miles") ?? "",
    milesMin: params.get("milesMin") ?? "",
    milesMax: params.get("milesMax") ?? "",
    priceMin: params.get("priceMin") ?? "",
    priceMax: params.get("priceMax") ?? "",
    sort: params.get("sort") || "year-desc",
  };
}

function clearQuery() {
  return {
    q: "", make: "", model: "", year: "", condition: "", price: "", miles: "",
    milesMin: "", milesMax: "", priceMin: "", priceMax: "", sort: "year-desc",
  };
}

function writeQuery(name, value) {
  const params = new URLSearchParams(location.search);
  if (!value || (name === "sort" && value === "year-desc")) params.delete(name);
  else params.set(name, value);
  const search = params.toString();
  history.replaceState(null, "", search ? `${location.pathname}?${search}` : location.pathname);
}

function priceMatches(price, bucket) {
  if (!bucket) return true;
  if (price <= 0) return false;
  if (bucket === "under-200") return price < 200000;
  if (bucket === "200-500") return price >= 200000 && price < 500000;
  if (bucket === "500-1000") return price >= 500000 && price < 1000000;
  return price >= 1000000;
}

function milesMatch(value, bucket) {
  if (!bucket) return true;
  if (value == null) return false;
  if (bucket === "under-25") return value < 25000;
  if (bucket === "under-50") return value < 50000;
  return value < 100000;
}

function filterCoaches(coaches, query) {
  const q = (query.q ?? "").trim().toLowerCase();
  const filtered = coaches.filter((coach) => {
    if (query.channel && !coach.channels.includes(query.channel)) return false;
    if (query.brand && coach.brand !== query.brand) return false;
    if (query.status && query.status !== "all" && coach.status !== query.status) return false;
    if (query.make && coach.make !== query.make) return false;
    if (query.model && coach.model !== query.model) return false;
    if (query.year && String(coach.year) !== query.year) return false;
    if (query.condition && coach.condition !== query.condition) return false;
    if (!priceMatches(coach.price, query.price ?? "")) return false;
    if (!milesMatch(coach.miles, query.miles ?? "")) return false;
    if (!numberInRange(coach.price, query.priceMin, query.priceMax, true)) return false;
    if (!numberInRange(coach.miles, query.milesMin, query.milesMax, false)) return false;
    if (!q) return true;
    return [coach.title, coach.make, coach.model, coach.stock, coach.engine, coach.floorplan, coach.slides, coach.year]
      .join(" ")
      .toLowerCase()
      .includes(q);
  });
  return filtered.sort((a, b) => compare(a, b, query.sort || "year-desc"));
}

function numberInRange(value, min, max, priced) {
  const low = min ? Number(min) : null;
  const high = max ? Number(max) : null;
  if (low == null && high == null) return true;
  if (value == null || (priced && value <= 0)) return false;
  if (low != null && value < low) return false;
  if (high != null && value > high) return false;
  return true;
}

function horsepower(coach) {
  const match = String(coach.engine || "").match(/(\d+)\s*hp/i);
  return match ? Number(match[1]) : null;
}

function priceOrEnd(price, direction) {
  if (price <= 0) return direction === "asc" ? Number.POSITIVE_INFINITY : Number.NEGATIVE_INFINITY;
  return direction === "asc" ? price : -price;
}

function compare(a, b, sort) {
  if (sort === "price-asc" || sort === "price-desc") {
    const direction = sort === "price-asc" ? "asc" : "desc";
    const diff = priceOrEnd(a.price, direction) - priceOrEnd(b.price, direction);
    if (diff !== 0) return diff;
  }
  if (sort === "miles-asc" || sort === "miles-desc") {
    const am = a.miles ?? Number.POSITIVE_INFINITY;
    const bm = b.miles ?? Number.POSITIVE_INFINITY;
    const diff = sort === "miles-desc" ? bm - am : am - bm;
    if (diff !== 0) return diff;
  }
  if (sort === "make-asc" || sort === "make-desc") {
    const diff = makeLabel(a.make).localeCompare(makeLabel(b.make));
    if (diff !== 0) return sort === "make-desc" ? -diff : diff;
  }
  if (sort === "hp-asc" || sort === "hp-desc") {
    const ah = horsepower(a) ?? Number.POSITIVE_INFINITY;
    const bh = horsepower(b) ?? Number.POSITIVE_INFINITY;
    const diff = sort === "hp-desc" ? bh - ah : ah - bh;
    if (diff !== 0) return diff;
  }
  if (sort === "oldest") {
    if (a.year !== b.year) return a.year - b.year;
  }
  if (a.year !== b.year) return b.year - a.year;
  return b.price - a.price;
}

function facetMakes(coaches, query) {
  const makes = new Set();
  coaches.forEach((coach) => {
    if (query.channel && !coach.channels.includes(query.channel)) return;
    if (query.brand && coach.brand !== query.brand) return;
    if (query.status && query.status !== "all" && coach.status !== query.status) return;
    if (coach.make) makes.add(coach.make);
  });
  return [...makes].sort();
}
