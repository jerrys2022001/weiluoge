(function () {
  function $(selector, root) {
    return (root || document).querySelector(selector);
  }

  function createElement(tag, className, text) {
    const element = document.createElement(tag);
    if (className) {
      element.className = className;
    }
    if (typeof text === "string") {
      element.textContent = text;
    }
    return element;
  }

  function fetchJson(path) {
    return fetch(path, { credentials: "same-origin" }).then(function (response) {
      if (!response.ok) {
        throw new Error("Request failed");
      }
      return response.json();
    });
  }

  function formatHistoryDate(value) {
    const parsed = new Date(value + "T12:00:00");
    if (Number.isNaN(parsed.getTime())) {
      return value;
    }
    return parsed.toLocaleDateString("en-US", {
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  }

  function renderItem(item) {
    const article = createElement("article", "va-brief-item va-brief-item-" + (item.slug || "industry"));
    article.dataset.briefSlug = item.slug || "industry";

    const index = createElement("div", "va-brief-index", String(item.index || ""));
    index.setAttribute("aria-hidden", "true");

    const body = createElement("div", "va-brief-body");
    body.appendChild(createElement("p", "va-brief-label", item.eyebrow || ""));

    const heading = createElement("h3");
    const titleLink = createElement("a", "", item.title || item.link || "");
    titleLink.href = item.link || "#";
    titleLink.target = "_blank";
    titleLink.rel = "noopener noreferrer";
    heading.appendChild(titleLink);
    body.appendChild(heading);

    if (item.summary) {
      body.appendChild(createElement("p", "va-brief-summary", item.summary));
    }

    const meta = createElement("p", "va-brief-meta");
    const source = createElement("span", "va-brief-source", item.source_name || "");
    const divider = createElement("span", "", "|");
    divider.setAttribute("aria-hidden", "true");
    meta.appendChild(source);
    meta.appendChild(divider);
    meta.appendChild(document.createTextNode(" " + (item.display_date || "LATEST")));
    body.appendChild(meta);

    const thumbLink = createElement("a", "va-brief-thumb");
    thumbLink.href = item.link || "#";
    thumbLink.target = "_blank";
    thumbLink.rel = "noopener noreferrer";
    thumbLink.setAttribute("aria-label", "Open story: " + (item.title || "story"));

    const image = document.createElement("img");
    image.src = item.image_src || item.fallback_src || "";
    image.alt = (item.title || "Story") + " thumbnail";
    image.loading = "lazy";
    image.decoding = "async";
    image.referrerPolicy = "no-referrer";
    if (item.fallback_src) {
      image.dataset.fallbackSrc = item.fallback_src;
      image.addEventListener("error", function () {
        if (image.dataset.fallbackSrc && image.src !== image.dataset.fallbackSrc) {
          image.src = image.dataset.fallbackSrc;
        }
      });
    }
    thumbLink.appendChild(image);

    article.appendChild(index);
    article.appendChild(body);
    article.appendChild(thumbLink);
    return article;
  }

  function renderGrid(items, panel) {
    panel.innerHTML = "";
    const grid = createElement("div", "va-briefing-grid");
    const left = createElement("div", "va-briefing-column");
    const right = createElement("div", "va-briefing-column");
    const midpoint = Math.ceil(items.length / 2);

    items.slice(0, midpoint).forEach(function (item) {
      left.appendChild(renderItem(item));
    });
    items.slice(midpoint).forEach(function (item) {
      right.appendChild(renderItem(item));
    });

    grid.appendChild(left);
    grid.appendChild(right);
    panel.appendChild(grid);
  }

  function init() {
    const select = $("[data-product-pulse-select]");
    const panel = $("[data-product-pulse-panel]");
    const status = $("[data-product-pulse-status]");
    const controls = $("[data-product-pulse-controls]");
    if (!select || !panel || !status || !controls) {
      return;
    }

    const manifestPath = select.dataset.historyManifest;
    const defaultDate = select.dataset.defaultDate || "";
    if (!manifestPath) {
      return;
    }

    let historyMap = Object.create(null);
    let activeHighlightSlug = "";

    function setStatus(message) {
      status.textContent = message;
    }

    function applyHighlight(slug) {
      activeHighlightSlug = slug || "";
      const items = panel.querySelectorAll(".va-brief-item");
      items.forEach(function (item) {
        const isMatch = !!activeHighlightSlug && item.dataset.briefSlug === activeHighlightSlug;
        item.classList.toggle("is-highlighted", isMatch);
        item.classList.toggle("is-dimmed", !!activeHighlightSlug && !isMatch);
      });
    }

    function annotateExistingItems() {
      const items = panel.querySelectorAll(".va-brief-item");
      items.forEach(function (item) {
        if (item.dataset.briefSlug) {
          return;
        }
        const className = Array.from(item.classList).find(function (name) {
          return name.indexOf("va-brief-item-") === 0 && name !== "va-brief-item";
        });
        if (className) {
          item.dataset.briefSlug = className.replace("va-brief-item-", "");
        }
      });
    }

    function populateSelect(entries) {
      select.innerHTML = "";
      entries.forEach(function (entry) {
        const option = document.createElement("option");
        option.value = entry.date || "";
        option.textContent = formatHistoryDate(entry.date || "");
        if ((entry.date || "") === defaultDate) {
          option.selected = true;
        }
        select.appendChild(option);
      });
    }

    function loadSnapshot(dateValue) {
      const snapshot = historyMap[dateValue];
      if (!snapshot || !snapshot.path) {
        return Promise.resolve();
      }
      setStatus("Loading archived briefing for " + formatHistoryDate(dateValue) + "...");
      return fetchJson(snapshot.path)
        .then(function (payload) {
          const items = Array.isArray(payload.items) ? payload.items : [];
          if (!items.length) {
            panel.innerHTML = '<div class="va-briefing-empty"><p>No stored stories are available for this date yet.</p></div>';
          } else {
            renderGrid(items, panel);
            applyHighlight(activeHighlightSlug);
          }
          setStatus("Viewing " + formatHistoryDate(dateValue) + "'s archived briefing.");
        })
        .catch(function () {
          setStatus("The archived briefing for " + formatHistoryDate(dateValue) + " could not be loaded.");
        });
    }

    fetchJson(manifestPath)
      .then(function (manifest) {
        const entries = Array.isArray(manifest.entries) ? manifest.entries : [];
        if (!entries.length) {
          controls.hidden = true;
          return;
        }

        entries.forEach(function (entry) {
          if (entry && entry.date) {
            historyMap[entry.date] = entry;
          }
        });

        populateSelect(entries);
        const initialDate = historyMap[defaultDate] ? defaultDate : (entries[0] && entries[0].date) || defaultDate;
        if (initialDate) {
          select.value = initialDate;
          loadSnapshot(initialDate);
        }
      })
      .catch(function () {
        controls.hidden = true;
      });

    annotateExistingItems();
    applyHighlight(activeHighlightSlug);

    window.addEventListener("va:product-pulse-highlight-request", function (event) {
      const detail = event && event.detail ? event.detail : {};
      const slug = detail.slug || "";
      applyHighlight(slug);

      if (!slug) {
        return;
      }

      const firstMatch = panel.querySelector('.va-brief-item[data-brief-slug="' + slug + '"]');
      if (firstMatch) {
        firstMatch.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    });

    select.addEventListener("change", function () {
      loadSnapshot(select.value);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
