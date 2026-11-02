(function () {
  const virtual = document.getElementById("virtual-tour");
  const galleryLb = document.getElementById("gallery-lb");
  const galleryImg = galleryLb?.querySelector("img");
  const items = Array.from(document.querySelectorAll(".js-lb-gallery"));
  let index = 0;

  function lightboxSrc(href) {
    try {
      const url = new URL(href, location.href);
      url.searchParams.set("width", "1600");
      return url.href;
    } catch {
      return href;
    }
  }

  function showGallery(i) {
    index = i;
    if (galleryImg) {
      galleryImg.decoding = "async";
      galleryImg.src = lightboxSrc(items[index].href);
    }
  }

  function activateFrame(el) {
    const frame = el?.querySelector("iframe[data-src]");
    if (frame && (!frame.src || frame.src === "about:blank")) {
      frame.src = frame.dataset.src;
    }
  }

  function open(el) {
    if (!el) return;
    activateFrame(el);
    el.hidden = false;
    el.classList.add("is-open");
    document.body.style.overflow = "hidden";
  }
  function close(el) {
    if (!el) return;
    el.classList.remove("is-open");
    el.hidden = true;
    document.body.style.overflow = "";
  }

  document.querySelectorAll("[data-open-virtual]").forEach((btn) => {
    btn.addEventListener(
      "click",
      (event) => {
        event.preventDefault();
        event.stopPropagation();
        open(virtual);
      },
      true,
    );
  });

  document.querySelectorAll("[data-open-video]").forEach((btn) => {
    btn.addEventListener(
      "click",
      (event) => {
        const video = document.getElementById("coach-video");
        event.preventDefault();
        event.stopPropagation();
        open(video);
      },
      true,
    );
  });

  items.forEach((link, i) => {
    link.addEventListener("click", (event) => {
      event.preventDefault();
      showGallery(i);
      open(galleryLb);
    });
  });

  document.querySelectorAll("[data-close-lb]").forEach((btn) => {
    btn.addEventListener("click", () => {
      close(virtual);
      close(galleryLb);
      close(document.getElementById("coach-video"));
    });
  });
  [virtual, galleryLb, document.getElementById("coach-video")].forEach((el) => {
    el?.addEventListener("click", (event) => {
      if (event.target === el) {
        close(virtual);
        close(galleryLb);
        close(el);
      }
    });
  });
  galleryLb?.querySelector("[data-lb-prev]")?.addEventListener("click", (event) => {
    event.stopPropagation();
    showGallery((index - 1 + items.length) % items.length);
  });
  galleryLb?.querySelector("[data-lb-next]")?.addEventListener("click", (event) => {
    event.stopPropagation();
    showGallery((index + 1) % items.length);
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      close(virtual);
      close(galleryLb);
      close(document.getElementById("coach-video"));
    }
  });

  /* Deep-link support: /coach/?#virtual-tour opens the Matterport tour. */
  if (location.hash === "#virtual-tour" && virtual) {
    open(virtual);
  }
})();
