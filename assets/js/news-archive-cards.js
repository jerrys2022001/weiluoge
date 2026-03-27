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

  function createTodayCard(group) {
    var article = createElement("article", "va-archive-card");
    var link = createElement("a", "va-archive-card-link");
    link.href = group.leadLink || "#";
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.setAttribute("aria-label", "Open headline collection " + group.title);

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
    body.appendChild(createElement("p", "va-archive-card-kicker", "Today"));
    body.appendChild(createElement("h4", "va-archive-card-title", group.title));
    body.appendChild(
      createElement(
        "p",
        "va-archive-card-text",
        group.sources.length
          ? group.sources.slice(0, 3).join(", ") + " coverage from today'" + "s stored briefing."
          : "Open the lead story from today'" + "s stored briefing."
      )
    );

    var footer = createElement("div", "va-archive-card-footer");
    footer.appendChild(createElement("span", "va-archive-card-count", pluralize(group.count, "story", "stories")));
    footer.appendChild(createElement("span", "va-archive-card-meta", "Open lead story"));

    link.appendChild(media);
    link.appendChild(body);
    link.appendChild(footer);
    article.appendChild(link);
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
    body.appendChild(createElement("p", "va-archive-card-kicker", "Snapshot"));
    body.appendChild(createElement("h4", "va-archive-card-title", formatDate(entry.date || "")));
    body.appendChild(
      createElement(
        "p",
        "va-archive-card-text",
        "Reload the stored Product Pulse lineup for this day and compare headline shifts."
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
        historyRoot.innerHTML = "";
        entries.slice(0, 8).forEach(function (entry) {
          historyRoot.appendChild(createHistoryCard(entry, historySelect));
        });
        syncActiveHistoryCard(historyRoot, historySelect);

        if (historySelect) {
          historySelect.addEventListener("change", function () {
            syncActiveHistoryCard(historyRoot, historySelect);
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
            todayRoot.appendChild(createTodayCard(group));
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
