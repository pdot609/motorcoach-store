(() => {
  const mount = document.getElementById("explore-root");
  if (!mount) {
    bindRails(document);
    return;
  }

  fetch(sitePath("/data/explore-showrooms.json"))
    .then((response) => {
      if (!response.ok) throw new Error(String(response.status));
      return response.json();
    })
    .then((data) => {
      mount.replaceChildren(...buildPage(data));
      bindRails(mount);
    })
    .catch(() => {
      mount.replaceChildren(
        message(
          "Showrooms did not load",
          "Refresh the page or call 941 283 2516 and the desk can walk you through current inventory."
        )
      );
    });
})();

function buildPage(data) {
  return [
    hero(data),
    marquee(data.marquee || []),
    ...((data.bands || []).map(band)),
    closeSection(data.close),
  ].filter(Boolean);
}

function hero(data) {
  const section = el("section", "explore-hero");
  if (data.heroVideo) {
    const video = el("video", "explore-hero-video");
    video.autoplay = true;
    video.muted = true;
    video.loop = true;
    video.playsInline = true;
    video.preload = "auto";
    video.src = data.heroVideo;
    section.append(video);
  }
  const title = el("h1");
  title.textContent = data.title || "Explore Showrooms";
  section.append(title);
  return section;
}

function marquee(logos) {
  if (!logos.length) return null;
  const section = el("section", "logo-marquee");
  section.setAttribute("aria-label", "Brands");
  const track = el("div", "logo-marquee-track");
  track.append(logoList(logos, false), logoList(logos, true));
  section.append(track);
  return section;
}

function logoList(logos, hidden) {
  const list = el("ul");
  if (hidden) list.setAttribute("aria-hidden", "true");
  logos.forEach((logo) => {
    const item = el("li");
    const img = el("img");
    img.src = logo.src;
    img.alt = hidden ? "" : logo.alt || "";
    item.append(img);
    list.append(item);
  });
  return list;
}

function band(showroom) {
  const classes = ["explore-band"];
  if (showroom.wide) classes.push("wide-cards");
  if (showroom.mid) classes.push("mid");
  const section = el("section", classes.join(" "));
  const logoId = `${showroom.id || "brand"}-logo`;
  section.setAttribute("aria-labelledby", logoId);

  const logo = el("img", "explore-brand");
  logo.id = logoId;
  logo.src = showroom.logo;
  logo.alt = showroom.logoAlt || "";
  section.append(logo, enter(showroom), rail(showroom), enter(showroom));
  return section;
}

function enter(showroom) {
  const wrap = el("p", "explore-enter");
  const link = el("a", "btn btn-frame");
  link.href = sitePath(showroom.enterHref);
  link.textContent = showroom.enterLabel;
  wrap.append(link);
  return wrap;
}

function rail(showroom) {
  const wrap = el("div", "explore-rail-wrap");
  const railBox = el("div", "explore-rail");
  const track = el("div", "explore-rail-track");
  (showroom.cards || []).forEach((card) => track.append(railCard(card)));
  const viewAll = el("a", "explore-view-all");
  viewAll.href = sitePath(showroom.enterHref);
  const label = el("span");
  label.textContent = "View All";
  viewAll.append(label, arrowSvg());
  railBox.append(track, viewAll);
  const dots = el("div", "explore-dots");
  dots.setAttribute("role", "tablist");
  dots.setAttribute("aria-label", "Showroom coaches");
  wrap.append(railBox, dots);
  return wrap;
}

function railCard(card) {
  const article = el("article", "rail-card");
  const media = el("a", "rail-media");
  media.href = sitePath(card.href);
  media.setAttribute("aria-label", card.title);
  const img = el("img");
  img.src = card.image;
  img.alt = card.alt || card.title;
  img.dataset.fallback = "media";
  media.append(img);

  const copy = el("div", "rail-copy");
  const heading = el("h3");
  const title = el("a");
  title.href = sitePath(card.href);
  title.textContent = card.title;
  heading.append(title);
  copy.append(heading);
  if (card.msrp) {
    const msrp = el("p", "rail-msrp");
    msrp.textContent = card.msrp;
    copy.append(msrp);
  }
  if (card.price) {
    const price = el("p", "rail-price");
    price.textContent = card.price;
    copy.append(price);
  }
  if (card.monthly) {
    const monthly = el("p", "rail-monthly");
    monthly.textContent = card.monthly;
    copy.append(monthly);
  }

  const more = el("a", "rail-more");
  more.href = sitePath(card.href);
  more.textContent = "Learn More";
  article.append(media, copy, more);
  return article;
}

function closeSection(close) {
  if (!close) return null;
  const section = el("section", "explore-close");
  const heading = el("h2");
  heading.textContent = close.heading || "Begin Your Journey with Confidence";
  const row = el("div", "explore-close-row");
  const copy = el("div", "explore-close-copy");
  const p = el("p");
  p.textContent = close.copy || "";
  const cta = el("a", "btn btn-frame btn-gold");
  cta.href = sitePath(close.ctaHref || "/schedule-appointment");
  cta.textContent = close.ctaLabel || "Schedule Appointment";
  copy.append(p, cta);
  const media = el("div", "explore-close-media");
  const img = el("img");
  img.src = close.image;
  img.alt = "";
  img.dataset.fallback = "media";
  media.append(img);
  row.append(copy, media);
  section.append(heading, row);
  return section;
}

function arrowSvg() {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 64 64");
  svg.setAttribute("aria-hidden", "true");
  const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
  path.setAttribute("d", "M16.7 4.4 41.8 32 16.7 59.6l3.4 3.6 26.7-29.3L20.1.8z");
  path.setAttribute("fill", "#dcdcdc");
  svg.append(path);
  return svg;
}

function message(titleText, copyText) {
  const box = el("div", "empty");
  const title = el("h2");
  title.textContent = titleText;
  const copy = el("p", "lede");
  copy.textContent = copyText;
  box.append(title, copy);
  return box;
}

function el(tag, className) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  return node;
}

function bindRails(root) {
  root.querySelectorAll(".explore-rail-wrap").forEach((wrap) => {
    const rail = wrap.querySelector(".explore-rail-track");
    let dots = wrap.querySelector(".explore-dots");
    if (!rail) return;
    if (!dots) {
      dots = el("div", "explore-dots");
      dots.setAttribute("role", "tablist");
      dots.setAttribute("aria-label", "Showroom coaches");
      wrap.append(dots);
    }

    function pageCount() {
      const maxScroll = Math.max(0, rail.scrollWidth - rail.clientWidth);
      if (maxScroll < 8) return 1;
      const cards = [...rail.querySelectorAll(".rail-card")];
      if (cards.length <= 1) return 1;
      const step = Math.max(cards[0].offsetWidth, 1);
      return Math.max(1, Math.round(maxScroll / step) + 1);
    }

    function activeIndex() {
      const cards = [...rail.querySelectorAll(".rail-card")];
      if (!cards.length) return 0;
      return cards.reduce((best, card, index) => {
        const distance = Math.abs(card.offsetLeft - rail.offsetLeft - rail.scrollLeft);
        const bestDistance = Math.abs(cards[best].offsetLeft - rail.offsetLeft - rail.scrollLeft);
        return distance < bestDistance ? index : best;
      }, 0);
    }

    function mark(index) {
      const tabs = [...dots.querySelectorAll("[role=tab]")];
      const safe = Math.max(0, Math.min(index, tabs.length - 1));
      tabs.forEach((tab, tabIndex) => {
        const selected = tabIndex === safe;
        tab.classList.toggle("is-active", selected);
        tab.setAttribute("aria-selected", String(selected));
      });
    }

    function rebuild() {
      const count = pageCount();
      const current = Math.min(activeIndex(), count - 1);
      dots.replaceChildren();
      for (let i = 0; i < count; i += 1) {
        const tab = el("button");
        tab.type = "button";
        tab.setAttribute("role", "tab");
        tab.setAttribute("aria-label", `Go to slide ${i + 1}`);
        tab.addEventListener("click", () => {
          const cards = [...rail.querySelectorAll(".rail-card")];
          const card = cards[Math.min(i, cards.length - 1)];
          if (!card) return;
          rail.scrollTo({ left: card.offsetLeft - rail.offsetLeft, behavior: "smooth" });
          mark(i);
        });
        dots.append(tab);
      }
      mark(current);
    }

    rail.addEventListener("scroll", () => mark(activeIndex()), { passive: true });
    window.addEventListener("resize", rebuild);
    rebuild();
  });
}
