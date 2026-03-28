(function () {
  function $(selector, root) {
    return (root || document).querySelector(selector);
  }

  function createElement(tag, className, text) {
    var element = document.createElement(tag);
    if (className) {
      element.className = className;
    }
    if (typeof text === "string") {
      element.textContent = text;
    }
    return element;
  }

  function emitHighlightRequest(slug, title) {
    window.dispatchEvent(
      new CustomEvent("va:product-pulse-highlight-request", {
        detail: {
          slug: slug || "",
          title: title || ""
        }
      })
    );
  }

  function fetchJson(path) {
    return fetch(path, { credentials: "same-origin" }).then(function (response) {
      if (!response.ok) {
        throw new Error("Request failed");
      }
      return response.json();
    });
  }

  function formatDate(value, options) {
    var parsed = new Date(value + "T12:00:00");
    if (Number.isNaN(parsed.getTime())) {
      return value;
    }
    return parsed.toLocaleDateString("en-US", options || {
      year: "numeric",
      month: "long",
      day: "numeric"
    });
  }

  function formatTime(value) {
    if (!value) {
      return "Updated recently";
    }
    var parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) {
      return "Updated recently";
    }
    return parsed.toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit"
    });
  }

  function renderEmpty(container, message) {
    container.innerHTML = "";
    var empty = createElement("div", "va-archive-empty");
    empty.appendChild(createElement("p", "", message));
    container.appendChild(empty);
  }

  function pluralize(count, singular, plural) {
    return String(count) + " " + (count === 1 ? singular : plural);
  }

  function formatMonthLabel(year, monthIndex) {
    return new Date(year, monthIndex, 1).toLocaleDateString("en-US", {
      month: "long"
    });
  }

  function toDateParts(value) {
    var parsed = new Date(value + "T12:00:00");
    if (Number.isNaN(parsed.getTime())) {
      return null;
    }
    return {
      year: parsed.getFullYear(),
      month: parsed.getMonth(),
      day: parsed.getDate()
    };
  }

  function groupItems(items) {
    var map = Object.create(null);
    items.forEach(function (item) {
      var slug = item.slug || "news";
      if (!map[slug]) {
        map[slug] = {
          slug: slug,
          title: item.eyebrow || "Latest News",
          image: item.image_src || item.fallback_src || "",
          leadLink: item.link || "#",
          leadTitle: item.title || "Open latest story",
          sources: [],
          count: 0
        };
      }
      map[slug].count += 1;
      if (item.source_name && map[slug].sources.indexOf(item.source_name) === -1) {
        map[slug].sources.push(item.source_name);
      }
      if (!map[slug].image && (item.image_src || item.fallback_src)) {
        map[slug].image = item.image_src || item.fallback_src;
      }
    });

    return Object.keys(map)
      .map(function (key) {
        return map[key];
      })
      .sort(function (left, right) {
        if (right.count !== left.count) {
          return right.count - left.count;
        }
        return left.title.localeCompare(right.title);
      });
  }

  function setSelectedTodayCard(container, slug) {
    if (!container) {
      return;
    }
    var cards = container.querySelectorAll(".va-archive-card-today");
    cards.forEach(function (card) {
      var isSelected = card.dataset.slug === slug;
      card.classList.toggle("is-selected", isSelected);
      var button = card.querySelector(".va-archive-card-button");
      if (button) {
        button.setAttribute("aria-pressed", isSelected ? "true" : "false");
      }
    });
  }

  function createTodayCard(group, todayRoot) {
    var article = createElement("article", "va-archive-card");
    article.classList.add("va-archive-card-today");
    article.dataset.slug = group.slug || "";
    var button = createElement("button", "va-archive-card-button");
    button.type = "button";
    button.setAttribute("aria-label", "Highlight " + group.title + " stories in Product Pulse");
    button.setAttribute("aria-pressed", "false");

    var media = createElement("div", "va-archive-card-media");
    if (group.image) {
      var image = document.createElement("img");
      image.src = group.image;
      image.alt = group.title + " collection thumbnail";
      image.loading = "lazy";
      image.decoding = "async";
      image.referrerPolicy = "no-referrer";
      media.appendChild(image);
    } else {
      media.appendChild(createElement("div", "va-archive-emblem", group.title.slice(0, 2).toUpperCase()));
    }

    var body = createElement("div", "va-archive-card-body");
    body.appendChild(createElement("p", "va-archive-card-kicker", "Featured File"));
    body.appendChild(createElement("h4", "va-archive-card-title", group.title));
    body.appendChild(
      createElement(
        "p",
        "va-archive-card-text",
        group.sources.length
          ? group.sources.slice(0, 3).join(", ") + " indexed in today'" + "s stored briefing."
          : "Open the lead story from today'" + "s stored briefing."
      )
    );

    var footer = createElement("div", "va-archive-card-footer");
    footer.appendChild(createElement("span", "va-archive-card-count", pluralize(group.count, "story", "stories")));
    footer.appendChild(createElement("span", "va-archive-card-meta", "Open collection"));

    button.appendChild(media);
    button.appendChild(body);
    button.appendChild(footer);
    button.addEventListener("click", function () {
      setSelectedTodayCard(todayRoot, group.slug || "");
      emitHighlightRequest(group.slug || "", group.title || "");
      var briefingPanel = $(".va-briefing-panel");
      if (briefingPanel) {
        briefingPanel.scrollIntoView({ behavior: "smooth", block: "nearest" });
      }
    });
    article.appendChild(button);
    return article;
  }

  function createHistoryCard(entry, select) {
    var article = createElement("article", "va-archive-card va-archive-card-history");
    article.dataset.date = entry.date || "";

    var button = createElement("button", "va-archive-card-button");
    button.type = "button";
    button.setAttribute("aria-label", "Load archived briefing for " + formatDate(entry.date || ""));

    var media = createElement("div", "va-archive-card-media va-archive-card-media-badge");
    var parsed = new Date((entry.date || "") + "T12:00:00");
    var month = Number.isNaN(parsed.getTime())
      ? "ARCH"
      : parsed.toLocaleDateString("en-US", { month: "short" }).toUpperCase();
    var day = Number.isNaN(parsed.getTime()) ? "--" : String(parsed.getDate());
    var badge = createElement("div", "va-archive-date-badge");
    badge.appendChild(createElement("span", "va-archive-date-month", month));
    badge.appendChild(createElement("strong", "va-archive-date-day", day));
    media.appendChild(badge);

    var body = createElement("div", "va-archive-card-body");
    body.appendChild(createElement("p", "va-archive-card-kicker", "Archived Issue"));
    body.appendChild(createElement("h4", "va-archive-card-title", formatDate(entry.date || "")));
    body.appendChild(
      createElement(
        "p",
        "va-archive-card-text",
        "Reload the stored Product Pulse lineup for this date and compare headline movement."
      )
    );

    var footer = createElement("div", "va-archive-card-footer");
    footer.appendChild(
      createElement(
        "span",
        "va-archive-card-count",
        pluralize(entry.item_count || 0, "item", "items")
      )
    );
    footer.appendChild(createElement("span", "va-archive-card-meta", formatTime(entry.refreshed_at)));

    button.appendChild(media);
    button.appendChild(body);
    button.appendChild(footer);
    button.addEventListener("click", function () {
      if (select) {
        select.value = entry.date || "";
        select.dispatchEvent(new Event("change", { bubbles: true }));
      }
      var briefing = $(".va-briefing");
      if (briefing) {
        briefing.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    });

    article.appendChild(button);
    return article;
  }

  function createPlaceholderHistoryCard(dateValue) {
    var article = createElement("article", "va-archive-card va-archive-card-history is-placeholder");
    article.dataset.date = dateValue || "";

    var button = createElement("div", "va-archive-card-button");
    button.setAttribute("aria-hidden", "true");

    var media = createElement("div", "va-archive-card-media va-archive-card-media-badge");
    var parsed = new Date(dateValue + "T12:00:00");
    var month = Number.isNaN(parsed.getTime())
      ? "---"
      : parsed.toLocaleDateString("en-US", { month: "short" }).toUpperCase();
    var day = Number.isNaN(parsed.getTime()) ? "--" : String(parsed.getDate());
    var badge = createElement("div", "va-archive-date-badge");
    badge.appendChild(createElement("span", "va-archive-date-month", month));
    badge.appendChild(createElement("strong", "va-archive-date-day", day));
    media.appendChild(badge);

    var body = createElement("div", "va-archive-card-body");
    body.appendChild(createElement("h4", "va-archive-card-title", String(day)));

    var footer = createElement("div", "va-archive-card-footer");
    footer.appendChild(createElement("span", "va-archive-card-count", ""));

    button.appendChild(media);
    button.appendChild(body);
    button.appendChild(footer);
    article.appendChild(button);
    return article;
  }

  function populateMonthYearControls(entries, monthSelect, yearSelect) {
    var yearMap = Object.create(null);
    entries.forEach(function (entry) {
      var parts = toDateParts(entry.date || "");
      if (!parts) {
        return;
      }
      if (!yearMap[parts.year]) {
        yearMap[parts.year] = Object.create(null);
      }
      yearMap[parts.year][parts.month] = true;
    });

    var years = Object.keys(yearMap).map(Number).sort(function (a, b) { return b - a; });
    yearSelect.innerHTML = "";
    years.forEach(function (year) {
      var option = document.createElement("option");
      option.value = String(year);
      option.textContent = String(year);
      yearSelect.appendChild(option);
    });

    function refreshMonths(selectedYear) {
      var months = Object.keys(yearMap[selectedYear] || {})
        .map(Number)
        .sort(function (a, b) { return b - a; });
      monthSelect.innerHTML = "";
      months.forEach(function (monthIndex) {
        var option = document.createElement("option");
        option.value = String(monthIndex);
        option.textContent = formatMonthLabel(Number(selectedYear), monthIndex);
        monthSelect.appendChild(option);
      });
    }

    return {
      years: years,
      refreshMonths: refreshMonths
    };
  }

  function renderHistoryMonth(container, entries, monthIndex, yearValue, select) {
    var entryMap = Object.create(null);
    entries.forEach(function (entry) {
      if (entry && entry.date) {
        entryMap[entry.date] = entry;
      }
    });

    container.innerHTML = "";

    var firstDay = new Date(yearValue, monthIndex, 1);
    var startOffset = firstDay.getDay();
    var daysInMonth = new Date(yearValue, monthIndex + 1, 0).getDate();
    var totalCells = Math.ceil((startOffset + daysInMonth) / 7) * 7;

    for (var cellIndex = 0; cellIndex < totalCells; cellIndex += 1) {
      var dayNumber = cellIndex - startOffset + 1;
      if (dayNumber < 1 || dayNumber > daysInMonth) {
        var pad = createElement("article", "va-archive-card va-archive-card-history is-placeholder");
        pad.setAttribute("aria-hidden", "true");
        container.appendChild(pad);
        continue;
      }

      var dateValue = [
        String(yearValue),
        String(monthIndex + 1).padStart(2, "0"),
        String(dayNumber).padStart(2, "0")
      ].join("-");
      var entry = entryMap[dateValue];
      container.appendChild(entry ? createHistoryCard(entry, select) : createPlaceholderHistoryCard(dateValue));
    }

    syncActiveHistoryCard(container, select);
  }

  function syncActiveHistoryCard(container, select) {
    if (!container || !select) {
      return;
    }
    var cards = container.querySelectorAll(".va-archive-card-history");
    cards.forEach(function (card) {
      var isActive = card.dataset.date === select.value;
      card.classList.toggle("is-active", isActive);
    });
  }

  function init() {
    var todayRoot = $("[data-news-archive-today]");
    var historyRoot = $("[data-news-archive-history]");
    var monthSelect = $("[data-news-archive-month]");
    var yearSelect = $("[data-news-archive-year]");
    if (!todayRoot || !historyRoot) {
      return;
    }

    var manifestPath = todayRoot.dataset.historyManifest || historyRoot.dataset.historyManifest;
    var historySelect = $("[data-product-pulse-select]");
    if (!manifestPath) {
      renderEmpty(todayRoot, "The news archive manifest is missing.");
      renderEmpty(historyRoot, "The history vault is unavailable right now.");
      return;
    }

    fetchJson(manifestPath)
      .then(function (manifest) {
        var entries = Array.isArray(manifest.entries) ? manifest.entries : [];
        if (!entries.length) {
          renderEmpty(todayRoot, "Today's collections will appear after the first stored snapshot is published.");
          renderEmpty(historyRoot, "Archive cards will appear after the first stored snapshot is published.");
          return;
        }

        var latestEntry = entries[0];
        var controls = monthSelect && yearSelect
          ? populateMonthYearControls(entries, monthSelect, yearSelect)
          : null;
        var latestParts = toDateParts(latestEntry.date || "");

        function redrawCalendar() {
          if (!monthSelect || !yearSelect) {
            return;
          }
          renderHistoryMonth(
            historyRoot,
            entries,
            Number(monthSelect.value),
            Number(yearSelect.value),
            historySelect
          );
        }

        if (controls && latestParts) {
          yearSelect.value = String(latestParts.year);
          controls.refreshMonths(latestParts.year);
          monthSelect.value = String(latestParts.month);
          redrawCalendar();

          yearSelect.addEventListener("change", function () {
            controls.refreshMonths(yearSelect.value);
            redrawCalendar();
          });

          monthSelect.addEventListener("change", redrawCalendar);
        } else {
          renderEmpty(historyRoot, "Archived briefings could not be grouped into a month view.");
        }

        if (historySelect) {
          historySelect.addEventListener("change", function () {
            syncActiveHistoryCard(historyRoot, historySelect);
            var selectedParts = toDateParts(historySelect.value || "");
            if (!selectedParts || !monthSelect || !yearSelect || !controls) {
              return;
            }
            if (yearSelect.value !== String(selectedParts.year)) {
              yearSelect.value = String(selectedParts.year);
              controls.refreshMonths(selectedParts.year);
            }
            if (monthSelect.value !== String(selectedParts.month)) {
              monthSelect.value = String(selectedParts.month);
              redrawCalendar();
            } else {
              syncActiveHistoryCard(historyRoot, historySelect);
            }
          });
        }

        return fetchJson(latestEntry.path).then(function (payload) {
          var items = Array.isArray(payload.items) ? payload.items : [];
          var groups = groupItems(items);
          if (!groups.length) {
            renderEmpty(todayRoot, "Today's stored briefing does not have collection data yet.");
            return;
          }
          todayRoot.innerHTML = "";
          groups.forEach(function (group) {
            todayRoot.appendChild(createTodayCard(group, todayRoot));
          });
        });
      })
      .catch(function () {
        renderEmpty(todayRoot, "Today's collections could not be loaded.");
        renderEmpty(historyRoot, "Archived briefings could not be loaded.");
      });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
