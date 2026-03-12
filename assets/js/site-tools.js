(function () {
  const STORAGE_KEY = "velocai-site-locale";
  const SEARCH_ENDPOINT = "/assets/data/site-search-index.json";
  const LOCALES = ["auto", "en-US", "zh-CN"];

  const copy = {
    "en-US": {
      searchLabel: "Search site",
      closeLabel: "Close search",
      searchPlaceholder: "Search apps, posts, Bluetooth docs, or guides",
      searchHint: "Quick links",
      resultsHint: "Top matches",
      noResults: "No matching pages yet. Try product names, Bluetooth topics, or cleanup terms.",
      loading: "Loading search index...",
      ready: "Search is ready.",
      localeName: {
        "en-US": "English",
        "zh-CN": "中文",
      },
    },
    "zh-CN": {
      searchLabel: "搜索站点",
      closeLabel: "关闭搜索",
      searchPlaceholder: "搜索应用、文章、蓝牙文档或指南",
      searchHint: "快捷入口",
      resultsHint: "搜索结果",
      noResults: "暂时没有匹配页面，试试产品名、蓝牙主题或清理关键词。",
      loading: "正在加载搜索索引...",
      ready: "搜索已就绪。",
      localeName: {
        "en-US": "English",
        "zh-CN": "中文",
      },
    },
  };

  let searchData = null;
  let loadPromise = null;
  const HIGHLIGHT_QUERY_KEY = "stq";
  const HIGHLIGHT_FOCUS_KEY = "stfocus";

  function normalizePath(pathname) {
    if (!pathname) return "/";
    if (pathname === "/index.html") return "/";
    return pathname.endsWith("/index.html") ? pathname.slice(0, -10) || "/" : pathname;
  }

  function detectInitialLocale() {
    const saved = window.localStorage.getItem(STORAGE_KEY);
    if (LOCALES.includes(saved)) {
      return saved;
    }
    if (document.documentElement.lang && document.documentElement.lang.toLowerCase().startsWith("zh")) {
      return "zh-CN";
    }
    return "auto";
  }

  function resolveUiLocale(preference) {
    if (preference === "auto") {
      return document.documentElement.lang && document.documentElement.lang.toLowerCase().startsWith("zh")
        ? "zh-CN"
        : "en-US";
    }
    return preference;
  }

  function loadSearchIndex() {
    if (searchData) return Promise.resolve(searchData);
    if (loadPromise) return loadPromise;

    loadPromise = fetch(SEARCH_ENDPOINT, { credentials: "same-origin" })
      .then(function (response) {
        if (!response.ok) {
          throw new Error("Search index request failed");
        }
        return response.json();
      })
      .then(function (payload) {
        searchData = Array.isArray(payload.items) ? payload.items : [];
        return searchData;
      })
      .catch(function () {
        searchData = [];
        return searchData;
      });

    return loadPromise;
  }

  function scoreItem(item, tokens, preferredLocale) {
    let score = 0;
    const title = (item.title || "").toLowerCase();
    const heading = (item.heading || "").toLowerCase();
    const description = (item.description || "").toLowerCase();
    const terms = (item.terms || "").toLowerCase();
    const url = (item.url || "").toLowerCase();

    tokens.forEach(function (token) {
      if (!token) return;
      if (title.includes(token)) score += 14;
      if (heading.includes(token)) score += 10;
      if (description.includes(token)) score += 6;
      if (terms.includes(token)) score += 4;
      if (url.includes(token)) score += 2;
      if (title.startsWith(token)) score += 3;
    });

    if (preferredLocale !== "auto" && item.locale === preferredLocale) {
      score += 5;
    }
    if (score > 0) {
      score += Number(item.priority || 0);
    }
    return score;
  }

  function pickDefaultResults(items, preferredLocale) {
    return items
      .slice()
      .sort(function (left, right) {
        const leftLocaleBoost = preferredLocale !== "auto" && left.locale === preferredLocale ? 1 : 0;
        const rightLocaleBoost = preferredLocale !== "auto" && right.locale === preferredLocale ? 1 : 0;
        if (leftLocaleBoost !== rightLocaleBoost) {
          return rightLocaleBoost - leftLocaleBoost;
        }
        return (left.url || "").length - (right.url || "").length;
      })
      .slice(0, 6);
  }

  function queryResults(items, query, preferredLocale) {
    const tokens = query
      .toLowerCase()
      .split(/\s+/)
      .map(function (part) {
        return part.trim();
      })
      .filter(Boolean);

    if (!tokens.length) {
      return pickDefaultResults(items, preferredLocale);
    }

    return items
      .map(function (item) {
        return {
          item: item,
          score: scoreItem(item, tokens, preferredLocale),
        };
      })
      .filter(function (entry) {
        return entry.score > 0;
      })
      .sort(function (left, right) {
        return right.score - left.score;
      })
      .slice(0, 10)
      .map(function (entry) {
        return entry.item;
      });
  }

  function renderResult(item, ui, index) {
    const link = document.createElement("a");
    link.className = "vs-search-result";
    link.href = item.url;
    link.dataset.resultIndex = String(index);
    link.tabIndex = -1;
    link.setAttribute("aria-selected", "false");

    const meta = document.createElement("div");
    meta.className = "vs-result-meta";

    const category = document.createElement("span");
    category.className = "vs-result-badge";
    category.textContent = item.category || "Site";
    meta.appendChild(category);

    const title = document.createElement("p");
    title.className = "vs-result-title";
    title.textContent = item.title || item.heading || item.url;

    const description = document.createElement("p");
    description.className = "vs-result-description";
    description.textContent = item.description || item.heading || item.url;

    link.appendChild(meta);
    link.appendChild(title);
    link.appendChild(description);
    return link;
  }

  function findNavContainer() {
    const selectors = [".va-nav", ".topbar .nav", ".top nav", "header nav", "nav[aria-label='Main']", ".nav"];
    for (let index = 0; index < selectors.length; index += 1) {
      const candidate = document.querySelector(selectors[index]);
      if (candidate) {
        return candidate;
      }
    }
    return null;
  }

  function iconSvg(type) {
    if (type === "close") {
      return '<svg class="vs-header-tool-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12"></path><path d="M18 6L6 18"></path></svg>';
    }
    return '<svg class="vs-header-tool-icon" viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="6.5"></circle><path d="M16 16l4.5 4.5"></path></svg>';
  }

  function escapeRegExp(value) {
    return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  }

  function buildNavigationUrl(item, query) {
    const rawUrl = item && item.url ? item.url : "";
    if (!rawUrl) {
      return "";
    }

    if (/^https?:\/\//i.test(rawUrl)) {
      return rawUrl;
    }

    const nextUrl = new URL(rawUrl, window.location.origin);
    if (query) {
      nextUrl.searchParams.set(HIGHLIGHT_QUERY_KEY, query);
    }
    if (item.focus) {
      nextUrl.searchParams.set(HIGHLIGHT_FOCUS_KEY, item.focus);
    }
    return nextUrl.pathname + nextUrl.search + nextUrl.hash;
  }

  function applySearchHighlight() {
    const params = new URLSearchParams(window.location.search);
    const focus = params.get(HIGHLIGHT_FOCUS_KEY) || "";
    const query = params.get(HIGHLIGHT_QUERY_KEY) || "";
    const targetText = (focus || query).trim();
    if (!targetText) {
      return;
    }

    const terms = Array.from(
      new Set(
        [focus.trim(), ...query.split(/\s+/).map(function (part) { return part.trim(); })]
          .filter(function (part) {
            return part && part.length >= 2;
          })
      )
    ).sort(function (left, right) {
      return right.length - left.length;
    });

    if (!terms.length) {
      return;
    }

    const root = document.querySelector("main") || document.body;
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode: function (node) {
        if (!node.nodeValue || !node.nodeValue.trim()) {
          return NodeFilter.FILTER_REJECT;
        }
        const parent = node.parentElement;
        if (!parent) {
          return NodeFilter.FILTER_REJECT;
        }
        if (parent.closest(".vs-header-tools-anchor, .vs-search-highlight, script, style, noscript")) {
          return NodeFilter.FILTER_REJECT;
        }
        return NodeFilter.FILTER_ACCEPT;
      },
    });

    const textNodes = [];
    let currentNode = walker.nextNode();
    while (currentNode) {
      textNodes.push(currentNode);
      currentNode = walker.nextNode();
    }

    const matcher = new RegExp(terms.map(escapeRegExp).join("|"), "gi");
    let firstHighlight = null;

    textNodes.forEach(function (node) {
      const text = node.nodeValue;
      matcher.lastIndex = 0;
      if (!matcher.test(text)) {
        return;
      }
      matcher.lastIndex = 0;

      const fragment = document.createDocumentFragment();
      let lastIndex = 0;
      let match = matcher.exec(text);

      while (match) {
        const start = match.index;
        const end = start + match[0].length;
        if (start > lastIndex) {
          fragment.appendChild(document.createTextNode(text.slice(lastIndex, start)));
        }
        const highlight = document.createElement("mark");
        highlight.className = "vs-search-highlight";
        highlight.textContent = text.slice(start, end);
        if (!firstHighlight) {
          firstHighlight = highlight;
        }
        fragment.appendChild(highlight);
        lastIndex = end;
        match = matcher.exec(text);
      }

      if (lastIndex < text.length) {
        fragment.appendChild(document.createTextNode(text.slice(lastIndex)));
      }

      const parent = node.parentNode;
      if (!parent) {
        return;
      }
      parent.replaceChild(fragment, node);
    });

    const highlights = root.querySelectorAll(".vs-search-highlight");
    if (!highlights.length || !firstHighlight) {
      return;
    }

    firstHighlight.scrollIntoView({ block: "center", behavior: "smooth" });
    window.setTimeout(function () {
      highlights.forEach(function (highlight) {
        highlight.classList.add("is-visible");
      });
    }, 20);
  }

  function init() {
    const nav = findNavContainer();
    if (!nav || document.querySelector(".vs-header-tools-anchor")) {
      return;
    }

    const initialPreference = detectInitialLocale();
    const anchor = document.createElement("div");
    const backdrop = document.createElement("button");
    const panel = document.createElement("div");

    anchor.className = "vs-header-tools-anchor";
    anchor.innerHTML = [
      '<button class="vs-header-tool-button vs-search-trigger" type="button" aria-expanded="false">',
      iconSvg("search"),
      "</button>"
    ].join("");

    backdrop.className = "vs-search-backdrop";
    backdrop.hidden = true;
    backdrop.type = "button";
    backdrop.setAttribute("aria-hidden", "true");

    panel.className = "vs-search-panel";
    panel.hidden = true;
    panel.innerHTML = [
      '<div class="vs-search-panel-inner">',
      '  <div class="vs-search-bar">',
      '    <div class="vs-search-input-wrap">',
      '      <button class="vs-search-submit-icon" type="button">',
      iconSvg("search"),
      "      </button>",
      '      <input class="vs-search-input" type="search" autocomplete="off">',
      "    </div>",
      '    <button class="vs-search-close" type="button">',
      iconSvg("close"),
      "    </button>",
      "  </div>",
      '  <div class="vs-search-results-wrap">',
      '    <p class="vs-search-section-title" data-role="results-title"></p>',
      '    <div class="vs-search-results" data-role="results"></div>',
      "  </div>",
      "</div>",
    ].join("");

    nav.appendChild(anchor);
    document.body.appendChild(backdrop);
    document.body.appendChild(panel);

    const trigger = anchor.querySelector(".vs-search-trigger");
    const closeButton = panel.querySelector(".vs-search-close");
    const submitIcon = panel.querySelector(".vs-search-submit-icon");
    const input = panel.querySelector(".vs-search-input");
    const resultsTitle = panel.querySelector('[data-role="results-title"]');
    const resultsNode = panel.querySelector('[data-role="results"]');
    let currentResults = [];
    let activeResultIndex = -1;

    function getSavedPreference() {
      return window.localStorage.getItem(STORAGE_KEY) || initialPreference;
    }

    function getUi() {
      return copy[resolveUiLocale(getSavedPreference())];
    }

    function isOpen() {
      return !panel.hidden;
    }

    function positionPanel() {
      const rect = trigger.getBoundingClientRect();
      if (window.innerWidth <= 760) {
        panel.style.top = "72px";
        panel.style.right = "12px";
        panel.style.left = "auto";
        return;
      }
      panel.style.top = rect.bottom + 10 + "px";
      panel.style.right = Math.max(12, window.innerWidth - rect.right) + "px";
      panel.style.left = "auto";
    }

    function closePanel() {
      panel.hidden = true;
      backdrop.hidden = true;
      document.body.classList.remove("vs-search-open");
      trigger.setAttribute("aria-expanded", "false");
    }

    function openPanel() {
      positionPanel();
      panel.hidden = false;
      backdrop.hidden = false;
      document.body.classList.add("vs-search-open");
      trigger.setAttribute("aria-expanded", "true");
      window.setTimeout(function () {
        input.focus();
      }, 30);
    }

    function getResultNodes() {
      return Array.from(resultsNode.querySelectorAll(".vs-search-result"));
    }

    function setActiveResult(index, scrollIntoView) {
      const resultNodes = getResultNodes();
      activeResultIndex = -1;
      resultNodes.forEach(function (node, nodeIndex) {
        const isActive = nodeIndex === index;
        node.classList.toggle("is-active", isActive);
        node.setAttribute("aria-selected", String(isActive));
        if (isActive) {
          activeResultIndex = nodeIndex;
          if (scrollIntoView) {
            node.scrollIntoView({ block: "nearest" });
          }
        }
      });
    }

    function goToActiveResult() {
      if (!currentResults.length) {
        return;
      }
      const targetIndex = activeResultIndex >= 0 ? activeResultIndex : 0;
      const target = currentResults[targetIndex];
      if (target && target.url) {
        window.location.href = buildNavigationUrl(target, input.value.trim());
      }
    }

    function renderResults(items, query) {
      const ui = getUi();
      resultsNode.innerHTML = "";
      currentResults = items.slice();
      activeResultIndex = -1;
      resultsTitle.textContent = query ? ui.resultsHint : ui.searchHint;

      if (!items.length) {
        const empty = document.createElement("p");
        empty.className = "vs-search-empty";
        empty.textContent = ui.noResults;
        resultsNode.appendChild(empty);
        return;
      }

      items.forEach(function (item, index) {
        const node = renderResult(item, ui, index);
        node.href = buildNavigationUrl(item, query);
        node.addEventListener("mouseenter", function () {
          setActiveResult(index, false);
        });
        node.addEventListener("focus", function () {
          setActiveResult(index, false);
        });
        resultsNode.appendChild(node);
      });
      setActiveResult(0, false);
    }

    function runSearch(query) {
      const preference = getSavedPreference();

      return loadSearchIndex().then(function (items) {
        renderResults(queryResults(items, query, preference), query);
      });
    }

    function updateCopy() {
      const ui = getUi();

      trigger.setAttribute("aria-label", ui.searchLabel);
      closeButton.setAttribute("aria-label", ui.closeLabel);
      input.placeholder = ui.searchPlaceholder;
      resultsTitle.textContent = ui.searchHint;
    }

    trigger.addEventListener("click", function () {
      if (isOpen()) {
        closePanel();
      } else {
        openPanel();
        runSearch(input.value.trim());
      }
    });

    closeButton.addEventListener("click", closePanel);
    submitIcon.addEventListener("click", function () {
      runSearch(input.value.trim());
      input.focus();
    });
    backdrop.addEventListener("click", closePanel);

    input.addEventListener("input", function () {
      runSearch(input.value.trim());
    });

    input.addEventListener("keydown", function (event) {
      if (event.key === "Escape") {
        event.preventDefault();
        closePanel();
        return;
      }

      if (event.key === "Enter") {
        event.preventDefault();
        goToActiveResult();
        return;
      }

      if (event.key === "ArrowDown" || event.key === "ArrowUp") {
        if (!currentResults.length) {
          return;
        }
        event.preventDefault();
        const delta = event.key === "ArrowDown" ? 1 : -1;
        const nextIndex = activeResultIndex < 0
          ? 0
          : (activeResultIndex + delta + currentResults.length) % currentResults.length;
        setActiveResult(nextIndex, true);
      }
    });

    document.addEventListener("keydown", function (event) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        if (!isOpen()) {
          openPanel();
        }
        runSearch(input.value.trim());
      } else if (event.key === "Escape" && isOpen()) {
        closePanel();
      }
    });

    document.addEventListener("click", function (event) {
      if (!isOpen()) {
        return;
      }
      if (!anchor.contains(event.target) && !panel.contains(event.target)) {
        closePanel();
      }
    });

    window.addEventListener("resize", function () {
      if (isOpen()) {
        positionPanel();
      }
    });

    updateCopy();
    closePanel();
    loadSearchIndex();

    const initialQuery = new URLSearchParams(window.location.search).get("q");
    if (initialQuery) {
      input.value = initialQuery;
      openPanel();
      runSearch(initialQuery);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      applySearchHighlight();
      init();
    });
  } else {
    applySearchHighlight();
    init();
  }
})();
