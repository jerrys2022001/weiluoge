(function () {
  const STORAGE_KEY = "velocai-site-locale";
  const SEARCH_ENDPOINT = "/assets/data/site-search-index.json";
  const DEFAULT_UI_LOCALE = "en-US";
  const LOCALE_OPTIONS = [
    { value: "auto", code: "AUTO", label: "Auto", uiLocale: "auto" },
    { value: "fr-FR", code: "FR", label: "French", uiLocale: "en-US" },
    { value: "en-US", code: "GB", label: "English", uiLocale: "en-US" },
    { value: "ro-RO", code: "RO", label: "Romanian", uiLocale: "en-US" },
    { value: "de-DE", code: "DE", label: "German", uiLocale: "en-US" },
    { value: "es-ES", code: "ES", label: "Spanish", uiLocale: "en-US" },
    { value: "it-IT", code: "IT", label: "Italian", uiLocale: "en-US" },
    { value: "pt-BR", code: "BR", label: "Portuguese", uiLocale: "en-US" },
    { value: "nl-NL", code: "NL", label: "Dutch", uiLocale: "en-US" },
    { value: "sv-SE", code: "SE", label: "Swedish", uiLocale: "en-US" },
    { value: "pl-PL", code: "PL", label: "Polish", uiLocale: "en-US" },
    { value: "cs-CZ", code: "CZ", label: "Czech", uiLocale: "en-US" },
  ];
  const LOCALES = LOCALE_OPTIONS.map(function (option) {
    return option.value;
  });

  const copy = {
    "en-US": {
      languageLabel: "Language",
      searchLabel: "Search site",
      closeLabel: "Close search",
      searchPlaceholder: "Search apps, posts, Bluetooth docs, or guides",
      searchHint: "Quick links",
      resultsHint: "Top matches",
      noResults: "No matching pages yet. Try product names, Bluetooth topics, or cleanup terms.",
      loading: "Loading search index...",
      ready: "Search is ready.",
    },
    "zh-CN": {
      languageLabel: "\u8bed\u8a00",
      searchLabel: "\u641c\u7d22\u7ad9\u70b9",
      closeLabel: "\u5173\u95ed\u641c\u7d22",
      searchPlaceholder: "\u641c\u7d22 App\u3001Blog\u3001Bluetooth \u6587\u6863\u6216\u6307\u5357",
      searchHint: "\u5feb\u6377\u5165\u53e3",
      resultsHint: "\u641c\u7d22\u7ed3\u679c",
      noResults: "\u6682\u65f6\u6ca1\u6709\u5339\u914d\u9875\u9762\uff0c\u8bd5\u8bd5\u4ea7\u54c1\u540d\u79f0\u3001Bluetooth \u4e3b\u9898\u6216\u6e05\u7406\u5173\u952e\u8bcd\u3002",
      loading: "\u6b63\u5728\u52a0\u8f7d\u641c\u7d22\u7d22\u5f15...",
      ready: "\u641c\u7d22\u5df2\u5c31\u7eea\u3002",
    },
  };

  const PAGE_TRANSLATIONS = {
    "/": {
      "en-US": {
        pageTitle: "VelocAI | AI Apps for Recovery, Cleanup, and Bluetooth Diagnostics",
        metaDescription: "VelocAI creates focused iPhone apps for finding lost devices, cleaning storage, and debugging Bluetooth workflows with a calm, modern experience.",
        selectorTexts: {
          ".va-brand": { ariaLabel: "VelocAI Home" },
          ".va-nav": { ariaLabel: "Primary" },
          ".va-nav-toggle": { ariaLabel: "Toggle navigation" },
          ".va-nav-list li:nth-child(1) a": "Apps Hub",
          ".va-nav-list li:nth-child(2) a": "Blog",
          ".va-nav-list li:nth-child(3) a": "Find AI",
          ".va-nav-list li:nth-child(4) a": "AI Cleanup PRO",
          ".va-nav-list li:nth-child(5) a": "Bluetooth Explorer",
          ".va-hero": { ariaLabel: "Hero" },
          ".va-eyebrow": ["VelocAI Studio", "Visual Flow", "Contact"],
          ".va-hero-title": { html: 'A <span class="is-accent">cleaner</span> way to run everyday AI workflows.' },
          ".va-hero-subtitle": "From lost-device recovery to photo cleanup and BLE diagnostics, VelocAI brings focused mobile tools into one visual system that feels fast, clear, and modern.",
          ".va-hero-actions .va-btn-primary": "Explore Apps",
          ".va-hero-actions .va-btn-secondary": "Read Guides",
          ".va-proof-list": { ariaLabel: "Key strengths" },
          ".va-proof-list li": [
            "Privacy-first by default",
            "Designed for iPhone daily use",
            "Fast task completion with less friction"
          ],
          ".va-hero-visual": { ariaLabel: "Product preview collage" },
          ".va-float-card-a": { ariaLabel: "Open Find AI page" },
          ".va-float-card-b": { ariaLabel: "Open AI Cleanup PRO page" },
          ".va-float-card-c": { ariaLabel: "Open Bluetooth Explorer page" },
          ".va-showcase": { ariaLabel: "Product cards" },
          ".va-showcase .va-app-card:nth-child(1) .va-app-kicker": "Recovery",
          ".va-showcase .va-app-card:nth-child(1) h2": "Find AI: Bluetooth Finder App",
          ".va-showcase .va-app-card:nth-child(1) .va-app-body > p:nth-of-type(2)": "Recover nearby AirPods and Bluetooth accessories with distance radar and last-seen location hints.",
          ".va-showcase .va-app-card:nth-child(2) .va-app-kicker": "Cleanup",
          ".va-showcase .va-app-card:nth-child(2) h2": "AI Cleanup PRO",
          ".va-showcase .va-app-card:nth-child(2) .va-app-body > p:nth-of-type(2)": "Clear duplicate photos, large videos, and outdated contacts with safe and understandable cleanup flows.",
          ".va-showcase .va-app-card:nth-child(3) .va-app-kicker": "Diagnostics",
          ".va-showcase .va-app-card:nth-child(3) h2": "Bluetooth Explorer",
          ".va-showcase .va-app-card:nth-child(3) .va-app-body > p:nth-of-type(2)": "Scan devices, inspect services, test packets, and debug BLE sessions with structured logs and guides.",
          ".va-showcase .va-app-links a:nth-child(1)": ["Product Page", "Product Page", "Product Page"],
          ".va-showcase .va-app-links a:nth-child(2)": ["App Store", "App Store", "App Store"],
          ".va-briefing": { ariaLabel: "Today's briefing" },
          ".va-briefing-section-label": "Top Stories",
          ".va-briefing-heading": { html: 'Product <span class="is-accent">Pulse</span>' },
          ".va-briefing-stamp": { html: 'Updated daily 08:30 <span aria-hidden="true">|</span> March 25, 2026 at 08:30 (UTC+08:00)' },
          ".va-brief-label": [
            "Apple Releases",
            "Industry Product Watch",
            "Apple Releases",
            "Apple Releases",
            "Apple Releases",
            "Apple Releases",
            "AI Developments",
            "AI Developments",
            "Semiconductor Breakthroughs",
            "Bluetooth Standards & Uses"
          ],
          ".va-gallery": { ariaLabel: "Visual highlights" },
          ".va-gallery-head h2": "Every screen stays clear, tactile, and focused.",
          ".va-gallery-head > p:last-of-type": "The interface language is consistent across discovery, cleanup, and terminal-level troubleshooting.",
          ".va-contact": { ariaLabel: "Contact" },
          ".va-contact-panel h2": "Need product support or a partnership conversation?",
          ".va-contact-panel > p:last-of-type": { html: 'Write to <a href="mailto:vp@velocai.net">vp@velocai.net</a>. We usually respond within one business day.' }
        }
      },
      "zh-CN": {
        pageTitle: "VelocAI | 恢复、清理与蓝牙诊断 AI 应用",
        metaDescription: "VelocAI 提供专注的 iPhone 应用，用于查找丢失设备、清理存储空间以及调试 Bluetooth 工作流，体验简洁而现代。",
        selectorTexts: {
          ".va-brand": { ariaLabel: "VelocAI 首页" },
          ".va-nav": { ariaLabel: "主导航" },
          ".va-nav-toggle": { ariaLabel: "切换导航" },
          ".va-nav-list li:nth-child(1) a": "应用中心",
          ".va-nav-list li:nth-child(2) a": "博客",
          ".va-nav-list li:nth-child(3) a": "Find AI",
          ".va-nav-list li:nth-child(4) a": "AI Cleanup PRO",
          ".va-nav-list li:nth-child(5) a": "Bluetooth Explorer",
          ".va-hero": { ariaLabel: "首页主视觉" },
          ".va-eyebrow": ["VelocAI Studio", "视觉体验", "联系"],
          ".va-hero-title": { html: '让日常 AI 工作流更<span class="is-accent">清爽高效</span>。' },
          ".va-hero-subtitle": "从丢失设备找回、照片清理到 BLE 诊断，VelocAI 将专注型移动工具整合进一套快速、清晰、现代的视觉系统。",
          ".va-hero-actions .va-btn-primary": "浏览应用",
          ".va-hero-actions .va-btn-secondary": "阅读指南",
          ".va-proof-list": { ariaLabel: "核心优势" },
          ".va-proof-list li": [
            "默认隐私优先",
            "为 iPhone 日常使用而设计",
            "更少阻力，更快完成任务"
          ],
          ".va-hero-visual": { ariaLabel: "产品预览拼贴" },
          ".va-float-card-a": { ariaLabel: "打开 Find AI 页面" },
          ".va-float-card-b": { ariaLabel: "打开 AI Cleanup PRO 页面" },
          ".va-float-card-c": { ariaLabel: "打开 Bluetooth Explorer 页面" },
          ".va-showcase": { ariaLabel: "产品卡片" },
          ".va-showcase .va-app-card:nth-child(1) .va-app-kicker": "找回",
          ".va-showcase .va-app-card:nth-child(1) h2": "Find AI：蓝牙查找应用",
          ".va-showcase .va-app-card:nth-child(1) .va-app-body > p:nth-of-type(2)": "通过距离雷达和最后出现位置提示，帮助你找回附近的 AirPods 和其他蓝牙配件。",
          ".va-showcase .va-app-card:nth-child(2) .va-app-kicker": "清理",
          ".va-showcase .va-app-card:nth-child(2) h2": "AI Cleanup PRO",
          ".va-showcase .va-app-card:nth-child(2) .va-app-body > p:nth-of-type(2)": "安全、易懂地清理重复照片、大体积视频和过期联系人。",
          ".va-showcase .va-app-card:nth-child(3) .va-app-kicker": "诊断",
          ".va-showcase .va-app-card:nth-child(3) h2": "Bluetooth Explorer",
          ".va-showcase .va-app-card:nth-child(3) .va-app-body > p:nth-of-type(2)": "扫描设备、检查服务、测试数据包，并通过结构化日志与指南调试 BLE 会话。",
          ".va-showcase .va-app-links a:nth-child(1)": ["产品页面", "产品页面", "产品页面"],
          ".va-showcase .va-app-links a:nth-child(2)": ["App Store", "App Store", "App Store"],
          ".va-briefing": { ariaLabel: "今日简报" },
          ".va-briefing-section-label": "今日焦点",
          ".va-briefing-heading": { html: '产品<span class="is-accent">脉搏</span>' },
          ".va-briefing-stamp": { html: '每日 08:30 更新 <span aria-hidden="true">|</span> 2026年3月25日 08:30 (UTC+08:00)' },
          ".va-brief-label": [
            "Apple 动态",
            "行业产品观察",
            "Apple 动态",
            "Apple 动态",
            "Apple 动态",
            "Apple 动态",
            "AI 进展",
            "AI 进展",
            "半导体突破",
            "Bluetooth 标准与应用"
          ],
          ".va-gallery": { ariaLabel: "视觉亮点" },
          ".va-gallery-head h2": "每个页面都保持清晰、顺手、聚焦。",
          ".va-gallery-head > p:last-of-type": "从发现、清理到终端级排障，整套界面语言始终一致。",
          ".va-contact": { ariaLabel: "联系" },
          ".va-contact-panel h2": "需要产品支持或合作沟通？",
          ".va-contact-panel > p:last-of-type": { html: '欢迎发送邮件至 <a href="mailto:vp@velocai.net">vp@velocai.net</a>，我们通常会在 1 个工作日内回复。' }
        }
      }
    },
    "/apps/": {
      "en-US": {
        pageTitle: "VelocAI Apps | AI Cleanup PRO, Find AI, Bluetooth Explorer",
        metaDescription: "Explore VelocAI iOS apps: AI Cleanup PRO for storage cleanup, Find AI for lost Bluetooth devices, and Bluetooth Explorer for BLE debugging.",
        selectorTexts: {
          "header .brand span": "VelocAI Apps",
          "header nav": { ariaLabel: "Main" },
          "header nav a:nth-child(1)": "Home",
          "header nav a:nth-child(2)": "Apps",
          "header nav a:nth-child(3)": "Blog",
          "header nav a:nth-child(4)": "Privacy",
          "main > h1": "Choose the right VelocAI app for your workflow",
          ".lede": "VelocAI builds practical iOS apps for storage cleanup, lost-device recovery, and professional Bluetooth troubleshooting. Compare the latest App Store versions, review official release-note highlights, and download the release that matches your immediate goal.",
          ".grid": { ariaLabel: "VelocAI products" },
          ".card:nth-child(1) > p": "Clean duplicate photos, remove large videos, and organize contacts with privacy-first on-device processing.",
          ".card:nth-child(1) .tags span": ["Photo Cleaner iPhone", "Duplicate Photo Cleanup", "Storage Optimizer"],
          ".card:nth-child(1) .update-panel": { ariaLabel: "AI Cleanup PRO latest App Store update" },
          ".card:nth-child(1) .update-label": "Latest on App Store",
          ".card:nth-child(1) .update-date": { html: '<time datetime="2026-03-06">Updated Mar 6, 2026</time>' },
          ".card:nth-child(1) .update-source": "Official App Store release notes",
          ".card:nth-child(1) .update-list li": [
            "New Super Cleaner flow speeds up grouping for duplicate photos, similar photos, duplicate videos, and similar videos.",
            "Expanded cleanup categories improve detection for screenshots, blurry photos, and Live Photos.",
            "Contact cleanup performance is faster for quicker bulk actions.",
            "Performance optimizations and bug fixes make the release smoother overall."
          ],
          ".card:nth-child(1) .actions a:nth-child(1)": "Download on App Store",
          ".card:nth-child(1) .actions a:nth-child(2)": "Product Page",
          ".card:nth-child(1) .actions a:nth-child(3)": "Privacy Policy",
          ".card:nth-child(2) > p": "Find lost AirPods and nearby Bluetooth devices with live signal distance radar and last-seen location guidance.",
          ".card:nth-child(2) .tags span": ["Bluetooth Finder", "Find Lost AirPods", "Device Recovery"],
          ".card:nth-child(2) .update-panel": { ariaLabel: "Find AI latest App Store update" },
          ".card:nth-child(2) .update-label": "Latest on App Store",
          ".card:nth-child(2) .update-date": { html: '<time datetime="2026-03-04">Updated Mar 4, 2026</time>' },
          ".card:nth-child(2) .update-source": "Official App Store release notes",
          ".card:nth-child(2) .update-list li": [
            "More precise location tracking helps narrow down missing Bluetooth devices faster.",
            "More real-time location updates improve live recovery guidance while you move."
          ],
          ".card:nth-child(2) .actions a:nth-child(1)": "Download on App Store",
          ".card:nth-child(2) .actions a:nth-child(2)": "Product Page",
          ".card:nth-child(2) .actions a:nth-child(3)": "Privacy Policy",
          ".card:nth-child(3) > p": "Scan BLE devices, inspect GATT services, send packets, and diagnose connection issues with AI-assisted insights.",
          ".card:nth-child(3) .tags span": ["BLE Scanner", "GATT Inspector", "Bluetooth Debug Tool"],
          ".card:nth-child(3) .update-panel": { ariaLabel: "Bluetooth Explorer latest App Store update" },
          ".card:nth-child(3) .update-label": "Latest on App Store",
          ".card:nth-child(3) .update-date": { html: '<time datetime="2026-03-09">Updated Mar 9, 2026</time>' },
          ".card:nth-child(3) .update-source": "Official App Store release notes",
          ".card:nth-child(3) .update-list li": [
            "Premium features are free for a limited time in the current App Store release.",
            "Real-Time Signal Display is now available for nearby and connected Bluetooth devices.",
            "Live RSSI changes are easier to inspect when tracking movement or connection quality.",
            "Faster device finding, stronger favorites monitoring, and clearer debugging improve the overall workflow."
          ],
          ".card:nth-child(3) .actions a:nth-child(1)": "Download on App Store",
          ".card:nth-child(3) .actions a:nth-child(2)": "Product Page",
          ".card:nth-child(3) .actions a:nth-child(3)": "User Guide",
          ".resources": { ariaLabel: "Resources" },
          ".resources h2": "Related resources",
          ".resources p": "Read SEO-focused product guides and troubleshooting walkthroughs from the VelocAI blog.",
          ".resource-links a:nth-child(1)": "Open Blog Hub",
          ".resource-links a:nth-child(2)": "Find lost AirPods guide",
          ".resource-links a:nth-child(3)": "iPhone storage cleanup checklist"
        }
      },
      "zh-CN": {
        pageTitle: "VelocAI Apps | AI Cleanup PRO、Find AI、Bluetooth Explorer",
        metaDescription: "浏览 VelocAI iOS 应用：AI Cleanup PRO 用于存储清理，Find AI 用于查找蓝牙设备，Bluetooth Explorer 用于 BLE 调试。",
        selectorTexts: {
          "header .brand span": "VelocAI 应用",
          "header nav": { ariaLabel: "主导航" },
          "header nav a:nth-child(1)": "首页",
          "header nav a:nth-child(2)": "应用",
          "header nav a:nth-child(3)": "博客",
          "header nav a:nth-child(4)": "隐私",
          "main > h1": "为你的工作流选择合适的 VelocAI 应用",
          ".lede": "VelocAI 打造实用型 iOS 应用，覆盖存储清理、丢失设备找回和专业 Bluetooth 排障。你可以对比最新 App Store 版本、查看官方更新要点，并下载最适合当前需求的版本。",
          ".grid": { ariaLabel: "VelocAI 产品" },
          ".card:nth-child(1) > p": "通过隐私优先的本地处理，清理重复照片、删除大视频并整理联系人。",
          ".card:nth-child(1) .tags span": ["iPhone 照片清理", "重复照片清理", "存储优化"],
          ".card:nth-child(1) .update-panel": { ariaLabel: "AI Cleanup PRO 最新 App Store 更新" },
          ".card:nth-child(1) .update-label": "App Store 最新版本",
          ".card:nth-child(1) .update-date": { html: '<time datetime="2026-03-06">更新于 2026年3月6日</time>' },
          ".card:nth-child(1) .update-source": "官方 App Store 发布说明",
          ".card:nth-child(1) .update-list li": [
            "新的 Super Cleaner 流程加快了重复照片、相似照片、重复视频和相似视频的分组速度。",
            "扩展后的清理分类提升了对截图、模糊照片和 Live Photos 的识别能力。",
            "联系人清理性能更快，批量操作更高效。",
            "整体性能优化与问题修复，让本次版本更顺滑。"
          ],
          ".card:nth-child(1) .actions a:nth-child(1)": "前往 App Store 下载",
          ".card:nth-child(1) .actions a:nth-child(2)": "产品页面",
          ".card:nth-child(1) .actions a:nth-child(3)": "隐私政策",
          ".card:nth-child(2) > p": "通过实时信号距离雷达和最后出现位置提示，帮助找回丢失的 AirPods 和附近蓝牙设备。",
          ".card:nth-child(2) .tags span": ["蓝牙查找", "查找丢失 AirPods", "设备找回"],
          ".card:nth-child(2) .update-panel": { ariaLabel: "Find AI 最新 App Store 更新" },
          ".card:nth-child(2) .update-label": "App Store 最新版本",
          ".card:nth-child(2) .update-date": { html: '<time datetime="2026-03-04">更新于 2026年3月4日</time>' },
          ".card:nth-child(2) .update-source": "官方 App Store 发布说明",
          ".card:nth-child(2) .update-list li": [
            "更精准的位置跟踪可更快缩小丢失蓝牙设备的范围。",
            "更多实时位置更新让你在移动过程中获得更好的找回引导。"
          ],
          ".card:nth-child(2) .actions a:nth-child(1)": "前往 App Store 下载",
          ".card:nth-child(2) .actions a:nth-child(2)": "产品页面",
          ".card:nth-child(2) .actions a:nth-child(3)": "隐私政策",
          ".card:nth-child(3) > p": "扫描 BLE 设备、检查 GATT 服务、发送数据包，并借助 AI 辅助洞察诊断连接问题。",
          ".card:nth-child(3) .tags span": ["BLE 扫描器", "GATT 检查器", "蓝牙调试工具"],
          ".card:nth-child(3) .update-panel": { ariaLabel: "Bluetooth Explorer 最新 App Store 更新" },
          ".card:nth-child(3) .update-label": "App Store 最新版本",
          ".card:nth-child(3) .update-date": { html: '<time datetime="2026-03-09">更新于 2026年3月9日</time>' },
          ".card:nth-child(3) .update-source": "官方 App Store 发布说明",
          ".card:nth-child(3) .update-list li": [
            "当前 App Store 版本中，Premium 功能限时免费开放。",
            "附近和已连接的蓝牙设备现已支持实时信号显示。",
            "在追踪移动或连接质量时，Live RSSI 变化更容易观察。",
            "更快的设备查找、更强的收藏监控和更清晰的调试流程提升了整体体验。"
          ],
          ".card:nth-child(3) .actions a:nth-child(1)": "前往 App Store 下载",
          ".card:nth-child(3) .actions a:nth-child(2)": "产品页面",
          ".card:nth-child(3) .actions a:nth-child(3)": "用户指南",
          ".resources": { ariaLabel: "资源" },
          ".resources h2": "相关资源",
          ".resources p": "阅读 VelocAI 博客中的 SEO 导向产品指南与排障文章。",
          ".resource-links a:nth-child(1)": "打开博客中心",
          ".resource-links a:nth-child(2)": "查找丢失 AirPods 指南",
          ".resource-links a:nth-child(3)": "iPhone 存储清理清单"
        }
      }
    }
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

  function isChineseLocale(locale) {
    return typeof locale === "string" && locale.toLowerCase().startsWith("zh");
  }

  function detectDocumentLocale() {
    const htmlLocale = (document.documentElement.lang || "").trim();
    if (isChineseLocale(htmlLocale)) {
      return "zh-CN";
    }

    const browserLocales = []
      .concat(Array.isArray(window.navigator.languages) ? window.navigator.languages : [])
      .concat([window.navigator.language || ""]);
    return browserLocales.some(isChineseLocale) ? "zh-CN" : DEFAULT_UI_LOCALE;
  }

  function detectInitialLocale() {
    const saved = window.localStorage.getItem(STORAGE_KEY);
    if (LOCALES.includes(saved)) {
      return saved;
    }
    return "auto";
  }

  function resolveUiLocale(preference) {
    if (preference === "auto") {
      return detectDocumentLocale();
    }
    return isChineseLocale(preference) ? "zh-CN" : DEFAULT_UI_LOCALE;
  }

  function localeOptionFor(preference) {
    return LOCALE_OPTIONS.find(function (option) {
      return option.value === preference;
    }) || LOCALE_OPTIONS.find(function (option) {
      return option.value === DEFAULT_UI_LOCALE;
    }) || LOCALE_OPTIONS[0];
  }

  function applyValueToNodes(nodes, value) {
    if (!nodes || !nodes.length || value == null) {
      return;
    }

    if (Array.isArray(value)) {
      nodes.forEach(function (node, index) {
        const entry = value[index];
        if (entry == null) {
          return;
        }
        node.textContent = entry;
      });
      return;
    }

    nodes.forEach(function (node) {
      node.textContent = value;
    });
  }

  function applyDescriptorToNodes(nodes, descriptor) {
    if (!nodes || !nodes.length || descriptor == null) {
      return;
    }

    if (typeof descriptor === "string" || Array.isArray(descriptor)) {
      applyValueToNodes(nodes, descriptor);
      return;
    }

    if (Object.prototype.hasOwnProperty.call(descriptor, "html")) {
      nodes.forEach(function (node) {
        node.innerHTML = descriptor.html;
      });
    }

    if (Object.prototype.hasOwnProperty.call(descriptor, "text")) {
      applyValueToNodes(nodes, descriptor.text);
    }

    Object.keys(descriptor).forEach(function (key) {
      if (key === "html" || key === "text") {
        return;
      }
      nodes.forEach(function (node) {
        node.setAttribute(key, descriptor[key]);
      });
    });
  }

  function applyMetaTranslation(translation) {
    if (!translation) {
      return;
    }

    if (translation.pageTitle) {
      document.title = translation.pageTitle;
      const ogTitle = document.querySelector('meta[property="og:title"]');
      const twitterTitle = document.querySelector('meta[name="twitter:title"]');
      if (ogTitle) ogTitle.setAttribute("content", translation.pageTitle);
      if (twitterTitle) twitterTitle.setAttribute("content", translation.pageTitle);
    }

    if (translation.metaDescription) {
      const description = document.querySelector('meta[name="description"]');
      const ogDescription = document.querySelector('meta[property="og:description"]');
      const twitterDescription = document.querySelector('meta[name="twitter:description"]');
      if (description) description.setAttribute("content", translation.metaDescription);
      if (ogDescription) ogDescription.setAttribute("content", translation.metaDescription);
      if (twitterDescription) twitterDescription.setAttribute("content", translation.metaDescription);
    }
  }

  function applyPageTranslations() {
    const path = normalizePath(window.location.pathname);
    const pageTranslation = PAGE_TRANSLATIONS[path];
    if (!pageTranslation) {
      return;
    }

    const uiLocale = resolveUiLocale(window.localStorage.getItem(STORAGE_KEY) || detectInitialLocale());
    const translation = pageTranslation[uiLocale] || pageTranslation[DEFAULT_UI_LOCALE];
    if (!translation || !translation.selectorTexts) {
      return;
    }

    applyMetaTranslation(translation);

    Object.keys(translation.selectorTexts).forEach(function (selector) {
      const nodes = Array.from(document.querySelectorAll(selector));
      if (!nodes.length) {
        return;
      }
      applyDescriptorToNodes(nodes, translation.selectorTexts[selector]);
    });
  }

  function findAlternateLocaleUrl(preference) {
    if (!preference || preference === "auto") {
      return "";
    }

    const alternates = Array.from(document.querySelectorAll('link[rel="alternate"][hreflang]'));
    if (!alternates.length) {
      return "";
    }

    const exact = alternates.find(function (link) {
      return (link.getAttribute("hreflang") || "").toLowerCase() === preference.toLowerCase();
    });
    if (exact && exact.href) {
      return exact.href;
    }

    const languageCode = preference.split("-")[0].toLowerCase();
    const partial = alternates.find(function (link) {
      return (link.getAttribute("hreflang") || "").toLowerCase().startsWith(languageCode);
    });
    return partial && partial.href ? partial.href : "";
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

  function collectHighlightTerms(query, focus) {
    return Array.from(
      new Set(
        [(focus || "").trim(), ...(query || "").split(/\s+/).map(function (part) { return part.trim(); })]
          .filter(function (part) {
            return part && part.length >= 2;
          })
      )
    ).sort(function (left, right) {
      return right.length - left.length;
    });
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

  function clearSearchHighlights() {
    const root = document.querySelector("main") || document.body;
    const highlights = root.querySelectorAll(".vs-search-highlight");
    highlights.forEach(function (highlight) {
      const parent = highlight.parentNode;
      if (!parent) {
        return;
      }
      parent.replaceChild(document.createTextNode(highlight.textContent || ""), highlight);
      parent.normalize();
    });
  }

  function applyImageFallback(img) {
    if (!img) return;
    const fallbackSrc = (img.getAttribute("data-fallback-src") || "").trim();
    if (!fallbackSrc) return;
    const currentSrc = img.getAttribute("src") || "";
    if (currentSrc === fallbackSrc) return;
    img.setAttribute("src", fallbackSrc);
  }

  function bindImageFallbacks() {
    const images = document.querySelectorAll("img[data-fallback-src]");
    images.forEach(function (img) {
      img.addEventListener("error", function handleError() {
        applyImageFallback(img);
      });

      if (img.complete && img.naturalWidth === 0) {
        applyImageFallback(img);
      }
    });
  }

  bindImageFallbacks();

  function scoreHighlightTarget(node, focus) {
    if (!node) {
      return -1;
    }
    let score = 0;
    const text = (node.textContent || "").trim().toLowerCase();
    const focusText = (focus || "").trim().toLowerCase();

    if (focusText && text.includes(focusText)) {
      score += 200;
    }

    const heading = node.closest("h1, h2, h3, h4, h5, h6, [role='heading']");
    if (heading) {
      const tagName = heading.tagName ? heading.tagName.toLowerCase() : "";
      const level = tagName.startsWith("h") ? Number(tagName.slice(1)) || 6 : 6;
      score += 140 - level * 10;
    }

    if (node.closest(".va-app-card, .card, article, .va-brief-item, .step")) {
      score += 28;
    }

    if (node.closest("strong, b, em")) {
      score += 10;
    }

    const ownTextLength = (node.textContent || "").trim().length;
    if (ownTextLength <= 60) {
      score += 12;
    } else if (ownTextLength <= 120) {
      score += 6;
    }

    return score;
  }

  function pageContainsSearchTerm(query, focus) {
    const terms = collectHighlightTerms(query, focus);
    if (!terms.length) {
      return false;
    }
    const root = document.querySelector("main") || document.body;
    const text = (root.textContent || "").toLowerCase();
    return terms.some(function (term) {
      return text.includes(term.toLowerCase());
    });
  }

  function applySearchHighlight(queryArg, focusArg) {
    const params = !queryArg && !focusArg ? new URLSearchParams(window.location.search) : null;
    const focus = focusArg || (params ? params.get(HIGHLIGHT_FOCUS_KEY) || "" : "");
    const query = queryArg || (params ? params.get(HIGHLIGHT_QUERY_KEY) || "" : "");
    const terms = collectHighlightTerms(query, focus);
    if (!terms.length) {
      return false;
    }

    clearSearchHighlights();

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
    let bestHighlight = null;
    let bestScore = -1;

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
        const candidateScore = scoreHighlightTarget(node.parentElement, focus);
        if (candidateScore > bestScore) {
          bestScore = candidateScore;
          bestHighlight = highlight;
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
      return false;
    }

    const scrollTarget = bestHighlight || firstHighlight;
    scrollTarget.scrollIntoView({ block: "center", behavior: "smooth" });
    window.setTimeout(function () {
      highlights.forEach(function (highlight) {
        highlight.classList.add("is-visible");
      });
    }, 20);
    return true;
  }

  function updateHighlightUrl(query, focus) {
    const nextUrl = new URL(window.location.href);
    if (query) {
      nextUrl.searchParams.set(HIGHLIGHT_QUERY_KEY, query);
    } else {
      nextUrl.searchParams.delete(HIGHLIGHT_QUERY_KEY);
    }
    if (focus) {
      nextUrl.searchParams.set(HIGHLIGHT_FOCUS_KEY, focus);
    } else {
      nextUrl.searchParams.delete(HIGHLIGHT_FOCUS_KEY);
    }
    window.history.replaceState({}, "", nextUrl.pathname + nextUrl.search + nextUrl.hash);
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
      '<div class="vs-locale-wrap">',
      '  <button class="vs-locale-trigger" type="button" aria-haspopup="menu" aria-expanded="false">',
      '    <span class="vs-locale-trigger-code"></span>',
      '    <span class="vs-locale-trigger-name"></span>',
      '    <span class="vs-locale-trigger-chevron" aria-hidden="true">\u25be</span>',
      "  </button>",
      '  <div class="vs-locale-panel" hidden>',
      '    <div class="vs-locale-list" role="menu"></div>',
      "  </div>",
      "</div>",
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

    const localeTrigger = anchor.querySelector(".vs-locale-trigger");
    const localeCode = anchor.querySelector(".vs-locale-trigger-code");
    const localeName = anchor.querySelector(".vs-locale-trigger-name");
    const localePanel = anchor.querySelector(".vs-locale-panel");
    const localeList = anchor.querySelector(".vs-locale-list");
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

    function isLocaleOpen() {
      return !!localePanel && !localePanel.hidden;
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

    function closeLocalePanel() {
      if (!localePanel) return;
      localePanel.hidden = true;
      localeTrigger.setAttribute("aria-expanded", "false");
    }

    function openLocalePanel() {
      if (!localePanel) return;
      closePanel();
      localePanel.hidden = false;
      localeTrigger.setAttribute("aria-expanded", "true");
    }

    function openPanel() {
      closeLocalePanel();
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
      const query = input.value.trim();
      if (pageContainsSearchTerm(query, "")) {
        closePanel();
        updateHighlightUrl(query, "");
        applySearchHighlight(query, "");
        return;
      }
      if (!currentResults.length) {
        return;
      }
      const targetIndex = activeResultIndex >= 0 ? activeResultIndex : 0;
      const target = currentResults[targetIndex];
      if (target && target.url) {
        window.location.href = buildNavigationUrl(target, query);
      }
    }

    function updateLocaleTrigger() {
      const preference = getSavedPreference();
      const option = localeOptionFor(preference);
      localeCode.textContent = option.code;
      localeName.textContent = option.label;
      localeTrigger.setAttribute("aria-label", getUi().languageLabel + ": " + option.label);
      document.documentElement.lang = resolveUiLocale(preference);
    }

    function renderLocaleOptions() {
      if (!localeList) return;
      const preference = getSavedPreference();
      localeList.innerHTML = "";

      LOCALE_OPTIONS.forEach(function (option) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "vs-locale-option";
        if (option.value === preference) {
          button.classList.add("is-active");
          button.setAttribute("aria-current", "true");
        }
        button.innerHTML = [
          '<span class="vs-locale-option-code">', option.code, "</span>",
          '<span class="vs-locale-option-label">', option.label, "</span>",
          '<span class="vs-locale-option-check" aria-hidden="true">\u2713</span>'
        ].join("");
        button.addEventListener("click", function () {
          window.localStorage.setItem(STORAGE_KEY, option.value);
          updateLocaleTrigger();
          updateCopy();
          applyPageTranslations();
          renderLocaleOptions();

          const alternateUrl = findAlternateLocaleUrl(option.value);
          if (alternateUrl && alternateUrl !== window.location.href) {
            window.location.href = alternateUrl;
            return;
          }

          if (isOpen()) {
            runSearch(input.value.trim());
          }
          closeLocalePanel();
        });
        localeList.appendChild(button);
      });
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

    localeTrigger.addEventListener("click", function () {
      if (isLocaleOpen()) {
        closeLocalePanel();
      } else {
        openLocalePanel();
      }
    });

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
      } else if (event.key === "Escape") {
        if (isOpen()) {
          closePanel();
        }
        if (isLocaleOpen()) {
          closeLocalePanel();
        }
      }
    });

    document.addEventListener("click", function (event) {
      if (isOpen() && !anchor.contains(event.target) && !panel.contains(event.target)) {
        closePanel();
      }
      if (isLocaleOpen() && !anchor.contains(event.target)) {
        closeLocalePanel();
      }
    });

    window.addEventListener("resize", function () {
      if (isOpen()) {
        positionPanel();
      }
    });

    updateLocaleTrigger();
    updateCopy();
    applyPageTranslations();
    renderLocaleOptions();
    closePanel();
    closeLocalePanel();
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
