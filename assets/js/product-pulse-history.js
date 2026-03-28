(function () {
  const APPLE_ARCHIVE_FALLBACK = "/assets/images/hero-2026-03/Apple-Park-Rainbow-Arches.jpg";
  const BROKEN_BRIEFING_PLACEHOLDER = "/assets/images/stock-2026-03/stock-08.jpg";

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

  function toDateParts(value) {
    const parsed = new Date(value + "T12:00:00");
    if (Number.isNaN(parsed.getTime())) {
      return null;
    }
    return {
      year: parsed.getFullYear(),
      month: parsed.getMonth(),
      day: parsed.getDate(),
    };
  }

  function normalizeBriefingImage(candidate) {
    if (!candidate) {
      return "";
    }
    return String(candidate).trim().replace(/\\/g, "/");
  }

  function resolveBriefingImage(item) {
    const primary = normalizeBriefingImage(item.image_src);
    const fallback = normalizeBriefingImage(item.fallback_src);
    const isAppleItem =
      item.slug === "apple" || /apple/i.test(item.eyebrow || "") || /apple/i.test(item.title || "");
    const hasBrokenPlaceholder =
      primary === BROKEN_BRIEFING_PLACEHOLDER || fallback === BROKEN_BRIEFING_PLACEHOLDER;

    if (hasBrokenPlaceholder) {
      return {
        src: APPLE_ARCHIVE_FALLBACK,
        fallback: APPLE_ARCHIVE_FALLBACK,
      };
    }

    if (primary) {
      return {
        src: primary,
        fallback: fallback || (isAppleItem ? APPLE_ARCHIVE_FALLBACK : ""),
      };
    }

    if (fallback) {
      return {
        src: fallback,
        fallback: isAppleItem ? APPLE_ARCHIVE_FALLBACK : fallback,
      };
    }

    return {
      src: isAppleItem ? APPLE_ARCHIVE_FALLBACK : "",
      fallback: isAppleItem ? APPLE_ARCHIVE_FALLBACK : "",
    };
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
    const resolvedImage = resolveBriefingImage(item);
    image.src = resolvedImage.src;
    image.alt = (item.title || "Story") + " thumbnail";
    image.loading = "lazy";
    image.decoding = "async";
    image.referrerPolicy = "no-referrer";
    if (resolvedImage.fallback) {
      image.dataset.fallbackSrc = resolvedImage.fallback;
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
    const calendarRoot = $("[data-briefing-calendar]");
    const calendarTrigger = $("[data-briefing-calendar-trigger]");
    const calendarTriggerLabel = $("[data-briefing-calendar-trigger-label]");
    const calendarPanel = $("[data-briefing-calendar-panel]");
    const calendarTitle = $("[data-briefing-calendar-title]");
    const calendarGrid = $("[data-briefing-calendar-grid]");
    const calendarPrev = $("[data-briefing-calendar-prev]");
    const calendarNext = $("[data-briefing-calendar-next]");
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
    let monthKeys = [];
    let activeMonthKey = "";

    function getMonthKey(parts) {
      return String(parts.year) + "-" + String(parts.month).padStart(2, "0");
    }

    function parseMonthKey(monthKey) {
      const chunks = String(monthKey || "").split("-");
      if (chunks.length !== 2) {
        return null;
      }
      return {
        year: Number(chunks[0]),
        month: Number(chunks[1]),
      };
    }

    function closeCalendar() {
      if (!calendarPanel || !calendarTrigger) {
        return;
      }
      calendarPanel.hidden = true;
      calendarTrigger.setAttribute("aria-expanded", "false");
    }

    function openCalendar() {
      if (!calendarPanel || !calendarTrigger) {
        return;
      }
      calendarPanel.hidden = false;
      calendarTrigger.setAttribute("aria-expanded", "true");
    }

    function updateTriggerLabel(dateValue) {
      if (!calendarTriggerLabel) {
        return;
      }
      calendarTriggerLabel.textContent = formatHistoryDate(dateValue || "");
    }

    function renderCalendarMonth() {
      if (!calendarGrid || !calendarTitle || !monthKeys.length) {
        return;
      }

      const monthParts = parseMonthKey(activeMonthKey);
      if (!monthParts) {
        return;
      }

      calendarGrid.innerHTML = "";
      calendarTitle.textContent = new Date(monthParts.year, monthParts.month, 1).toLocaleDateString("en-US", {
        year: "numeric",
        month: "long",
      });

      const firstWeekday = new Date(monthParts.year, monthParts.month, 1).getDay();
      const daysInMonth = new Date(monthParts.year, monthParts.month + 1, 0).getDate();

      for (let offset = 0; offset < firstWeekday; offset += 1) {
        calendarGrid.appendChild(createElement("div", "va-briefing-calendar-day-empty"));
      }

      for (let day = 1; day <= daysInMonth; day += 1) {
        const dateValue = [
          String(monthParts.year),
          String(monthParts.month + 1).padStart(2, "0"),
          String(day).padStart(2, "0"),
        ].join("-");
        const button = createElement("button", "va-briefing-calendar-day", String(day));
        button.type = "button";
        button.dataset.date = dateValue;

        if (select.value === dateValue) {
          button.classList.add("is-active");
        }

        if (!historyMap[dateValue]) {
          button.classList.add("is-disabled");
          button.disabled = true;
        } else {
          button.addEventListener("click", function () {
            select.value = dateValue;
            updateTriggerLabel(dateValue);
            closeCalendar();
            select.dispatchEvent(new Event("change", { bubbles: true }));
          });
        }

        calendarGrid.appendChild(button);
      }

      if (calendarPrev) {
        calendarPrev.disabled = monthKeys.indexOf(activeMonthKey) <= 0;
      }
      if (calendarNext) {
        calendarNext.disabled = monthKeys.indexOf(activeMonthKey) >= monthKeys.length - 1;
      }
    }

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

    function clearHighlight() {
      applyHighlight("");
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
      const monthSet = new Set();
      entries.forEach(function (entry) {
        const option = document.createElement("option");
        option.value = entry.date || "";
        option.textContent = formatHistoryDate(entry.date || "");
        if ((entry.date || "") === defaultDate) {
          option.selected = true;
        }
        select.appendChild(option);

        const parts = toDateParts(entry.date || "");
        if (parts) {
          monthSet.add(getMonthKey(parts));
        }
      });

      monthKeys = Array.from(monthSet).sort();
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
          const initialParts = toDateParts(initialDate);
          if (initialParts) {
            activeMonthKey = getMonthKey(initialParts);
          }
          select.value = initialDate;
          updateTriggerLabel(initialDate);
          renderCalendarMonth();
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

    document.addEventListener("click", function (event) {
      if (!activeHighlightSlug) {
        return;
      }

      const insideTodayArchive = !!event.target.closest("[data-news-archive-today]");
      const insideBriefingPanel = !!event.target.closest("[data-product-pulse-panel]");
      if (insideTodayArchive || insideBriefingPanel) {
        return;
      }

      clearHighlight();
    });

    select.addEventListener("change", function () {
      const parts = toDateParts(select.value);
      if (parts) {
        activeMonthKey = getMonthKey(parts);
      }
      updateTriggerLabel(select.value);
      renderCalendarMonth();
      loadSnapshot(select.value);
    });

    if (calendarTrigger && calendarPanel) {
      calendarTrigger.addEventListener("click", function () {
        if (calendarPanel.hidden) {
          openCalendar();
          renderCalendarMonth();
        } else {
          closeCalendar();
        }
      });
    }

    if (calendarPrev) {
      calendarPrev.addEventListener("click", function () {
        const index = monthKeys.indexOf(activeMonthKey);
        if (index > 0) {
          activeMonthKey = monthKeys[index - 1];
          renderCalendarMonth();
        }
      });
    }

    if (calendarNext) {
      calendarNext.addEventListener("click", function () {
        const index = monthKeys.indexOf(activeMonthKey);
        if (index > -1 && index < monthKeys.length - 1) {
          activeMonthKey = monthKeys[index + 1];
          renderCalendarMonth();
        }
      });
    }

    document.addEventListener("click", function (event) {
      if (!calendarRoot || !calendarPanel || calendarPanel.hidden) {
        return;
      }
      if (calendarRoot.contains(event.target)) {
        return;
      }
      closeCalendar();
    });

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") {
        closeCalendar();
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
