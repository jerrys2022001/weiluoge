(function () {
  const STORAGE_KEY = "velocai-site-locale";
  const SEARCH_ENDPOINT = "/assets/data/site-search-index.json";
  const DEFAULT_UI_LOCALE = "en-US";
  const LOCALE_OPTIONS = [
    { value: "auto", code: "AUTO", label: "English", uiLocale: "en-US" },
    { value: "fr-FR", code: "FR", label: "French", uiLocale: "fr-FR" },
    { value: "ro-RO", code: "RO", label: "Romanian", uiLocale: "ro-RO" },
    { value: "de-DE", code: "DE", label: "German", uiLocale: "de-DE" },
    { value: "es-ES", code: "ES", label: "Spanish", uiLocale: "es-ES" },
    { value: "it-IT", code: "IT", label: "Italian", uiLocale: "it-IT" },
    { value: "pt-BR", code: "BR", label: "Portuguese", uiLocale: "pt-BR" },
    { value: "nl-NL", code: "NL", label: "Dutch", uiLocale: "nl-NL" },
    { value: "sv-SE", code: "SE", label: "Swedish", uiLocale: "sv-SE" },
    { value: "pl-PL", code: "PL", label: "Polish", uiLocale: "pl-PL" },
    { value: "cs-CZ", code: "CZ", label: "Czech", uiLocale: "cs-CZ" },
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

  Object.assign(copy, {
    "fr-FR": {
      languageLabel: "Langue",
      searchLabel: "Rechercher sur le site",
      closeLabel: "Fermer la recherche",
      searchPlaceholder: "Rechercher des apps, articles, documents Bluetooth ou guides",
      searchHint: "Accès rapides",
      resultsHint: "Meilleurs résultats",
      noResults: "Aucune page correspondante pour le moment. Essayez des noms d’apps, des sujets Bluetooth ou des termes de nettoyage.",
      loading: "Chargement de l’index de recherche...",
      ready: "La recherche est prête.",
    },
    "ro-RO": {
      languageLabel: "Limbă",
      searchLabel: "Caută pe site",
      closeLabel: "Închide căutarea",
      searchPlaceholder: "Caută aplicații, articole, documente Bluetooth sau ghiduri",
      searchHint: "Acces rapid",
      resultsHint: "Rezultate principale",
      noResults: "Nu există încă pagini potrivite. Încearcă nume de aplicații, subiecte Bluetooth sau termeni de curățare.",
      loading: "Se încarcă indexul de căutare...",
      ready: "Căutarea este pregătită.",
    },
    "de-DE": {
      languageLabel: "Sprache",
      searchLabel: "Website durchsuchen",
      closeLabel: "Suche schließen",
      searchPlaceholder: "Apps, Beiträge, Bluetooth-Dokumente oder Anleitungen suchen",
      searchHint: "Schnellzugriffe",
      resultsHint: "Top-Treffer",
      noResults: "Noch keine passenden Seiten. Versuche App-Namen, Bluetooth-Themen oder Cleanup-Begriffe.",
      loading: "Suchindex wird geladen...",
      ready: "Suche ist bereit.",
    },
    "es-ES": {
      languageLabel: "Idioma",
      searchLabel: "Buscar en el sitio",
      closeLabel: "Cerrar búsqueda",
      searchPlaceholder: "Buscar apps, artículos, documentos Bluetooth o guías",
      searchHint: "Accesos rápidos",
      resultsHint: "Resultados principales",
      noResults: "Aún no hay páginas coincidentes. Prueba nombres de apps, temas Bluetooth o términos de limpieza.",
      loading: "Cargando índice de búsqueda...",
      ready: "La búsqueda está lista.",
    },
    "it-IT": {
      languageLabel: "Lingua",
      searchLabel: "Cerca nel sito",
      closeLabel: "Chiudi ricerca",
      searchPlaceholder: "Cerca app, articoli, documenti Bluetooth o guide",
      searchHint: "Accessi rapidi",
      resultsHint: "Risultati principali",
      noResults: "Nessuna pagina corrispondente al momento. Prova con nomi di app, temi Bluetooth o termini di pulizia.",
      loading: "Caricamento indice di ricerca...",
      ready: "La ricerca è pronta.",
    },
    "pt-BR": {
      languageLabel: "Idioma",
      searchLabel: "Pesquisar no site",
      closeLabel: "Fechar pesquisa",
      searchPlaceholder: "Pesquise apps, posts, documentos Bluetooth ou guias",
      searchHint: "Acessos rápidos",
      resultsHint: "Principais resultados",
      noResults: "Ainda não há páginas correspondentes. Tente nomes de apps, temas Bluetooth ou termos de limpeza.",
      loading: "Carregando índice de busca...",
      ready: "A pesquisa está pronta.",
    },
    "nl-NL": {
      languageLabel: "Taal",
      searchLabel: "Zoek op de site",
      closeLabel: "Zoeken sluiten",
      searchPlaceholder: "Zoek apps, berichten, Bluetooth-documenten of gidsen",
      searchHint: "Snelle links",
      resultsHint: "Topresultaten",
      noResults: "Nog geen overeenkomende pagina's. Probeer appnamen, Bluetooth-onderwerpen of opschoontermen.",
      loading: "Zoekindex wordt geladen...",
      ready: "Zoeken is klaar.",
    },
    "sv-SE": {
      languageLabel: "Språk",
      searchLabel: "Sök på webbplatsen",
      closeLabel: "Stäng sökningen",
      searchPlaceholder: "Sök appar, inlägg, Bluetooth-dokument eller guider",
      searchHint: "Snabblänkar",
      resultsHint: "Bästa träffar",
      noResults: "Inga matchande sidor ännu. Prova appnamn, Bluetooth-ämnen eller rensningstermer.",
      loading: "Laddar sökindex...",
      ready: "Sökningen är redo.",
    },
    "pl-PL": {
      languageLabel: "Język",
      searchLabel: "Szukaj w witrynie",
      closeLabel: "Zamknij wyszukiwanie",
      searchPlaceholder: "Szukaj aplikacji, wpisów, dokumentów Bluetooth lub poradników",
      searchHint: "Szybkie linki",
      resultsHint: "Najlepsze wyniki",
      noResults: "Brak pasujących stron. Spróbuj nazw aplikacji, tematów Bluetooth lub haseł związanych z czyszczeniem.",
      loading: "Ładowanie indeksu wyszukiwania...",
      ready: "Wyszukiwanie jest gotowe.",
    },
    "cs-CZ": {
      languageLabel: "Jazyk",
      searchLabel: "Hledat na webu",
      closeLabel: "Zavřít hledání",
      searchPlaceholder: "Hledejte aplikace, články, dokumenty Bluetooth nebo průvodce",
      searchHint: "Rychlé odkazy",
      resultsHint: "Nejlepší výsledky",
      noResults: "Zatím žádné odpovídající stránky. Zkuste názvy aplikací, témata Bluetooth nebo výrazy pro čištění.",
      loading: "Načítá se index vyhledávání...",
      ready: "Vyhledávání je připraveno.",
    }
  });

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

  const PAGE_TRANSLATION_OVERRIDES = {
    "/": {
      "fr-FR": {
        pageTitle: "VelocAI | Apps IA pour récupération, nettoyage et diagnostic Bluetooth",
        metaDescription: "VelocAI crée des apps iPhone ciblées pour retrouver des appareils, nettoyer le stockage et diagnostiquer les flux Bluetooth dans une expérience calme et moderne.",
        selectorTexts: {
          ".va-nav-list li:nth-child(1) a": "Apps Hub",
          ".va-nav-list li:nth-child(2) a": "Blog",
          ".va-nav-list li:nth-child(3) a": "Find AI",
          ".va-nav-list li:nth-child(4) a": "AI Cleanup PRO",
          ".va-nav-list li:nth-child(5) a": "Bluetooth Explorer",
          ".va-eyebrow": ["VelocAI Studio", "Flux visuel", "Contact"],
          ".va-hero-title": { html: 'Une façon <span class="is-accent">plus claire</span> d’exécuter vos workflows IA du quotidien.' },
          ".va-hero-subtitle": "De la récupération d’appareils perdus au nettoyage photo et au diagnostic BLE, VelocAI réunit des outils mobiles ciblés dans un système visuel rapide, clair et moderne.",
          ".va-hero-actions .va-btn-primary": "Explorer les apps",
          ".va-hero-actions .va-btn-secondary": "Lire les guides",
          ".va-proof-list li": ["Confidentialité d’abord", "Pensé pour l’usage quotidien sur iPhone", "Des tâches accomplies plus vite avec moins de friction"],
          ".va-showcase .va-app-card:nth-child(1) .va-app-kicker": "Récupération",
          ".va-showcase .va-app-card:nth-child(1) .va-app-body > p:nth-of-type(2)": "Retrouvez vos AirPods et accessoires Bluetooth proches grâce au radar de distance et aux indices de dernière position.",
          ".va-showcase .va-app-card:nth-child(2) .va-app-kicker": "Nettoyage",
          ".va-showcase .va-app-card:nth-child(2) .va-app-body > p:nth-of-type(2)": "Supprimez les photos en double, les grandes vidéos et les anciens contacts avec des flux de nettoyage sûrs et faciles à comprendre.",
          ".va-showcase .va-app-card:nth-child(3) .va-app-kicker": "Diagnostic",
          ".va-showcase .va-app-card:nth-child(3) .va-app-body > p:nth-of-type(2)": "Scannez des appareils, inspectez des services, testez des paquets et déboguez des sessions BLE avec des journaux structurés.",
          ".va-showcase .va-app-links a:nth-child(1)": ["Page produit", "Page produit", "Page produit"],
          ".va-briefing-section-label": "À la une",
          ".va-briefing-heading": { html: 'Pouls <span class="is-accent">produit</span>' },
          ".va-briefing-stamp": { html: 'Mis à jour chaque jour à 08:30 <span aria-hidden="true">|</span> 25 mars 2026 à 08:30 (UTC+08:00)' },
          ".va-brief-label": ["Sorties Apple", "Veille produit du secteur", "Sorties Apple", "Sorties Apple", "Sorties Apple", "Sorties Apple", "Évolutions IA", "Évolutions IA", "Percées semiconducteurs", "Normes et usages Bluetooth"],
          ".va-gallery-head h2": "Chaque écran reste clair, tactile et focalisé.",
          ".va-gallery-head > p:last-of-type": "Le langage d’interface reste cohérent entre découverte, nettoyage et dépannage avancé.",
          ".va-contact-panel h2": "Besoin d’assistance produit ou d’un échange partenariat ?",
          ".va-contact-panel > p:last-of-type": { html: 'Écrivez à <a href="mailto:vp@velocai.net">vp@velocai.net</a>. Nous répondons généralement sous un jour ouvré.' }
        }
      },
      "ro-RO": {
        pageTitle: "VelocAI | Aplicații AI pentru recuperare, curățare și diagnostic Bluetooth",
        metaDescription: "VelocAI creează aplicații iPhone concentrate pentru găsirea dispozitivelor pierdute, curățarea stocării și depanarea fluxurilor Bluetooth.",
        selectorTexts: {
          ".va-eyebrow": ["VelocAI Studio", "Flux vizual", "Contact"],
          ".va-hero-title": { html: 'Un mod <span class="is-accent">mai curat</span> de a rula fluxurile AI de zi cu zi.' },
          ".va-hero-subtitle": "De la recuperarea dispozitivelor pierdute la curățarea fotografiilor și diagnostic BLE, VelocAI adună instrumente mobile clare și rapide într-un singur sistem vizual.",
          ".va-hero-actions .va-btn-primary": "Explorează aplicațiile",
          ".va-hero-actions .va-btn-secondary": "Citește ghidurile",
          ".va-proof-list li": ["Confidențialitate implicită", "Conceput pentru utilizarea zilnică pe iPhone", "Finalizare rapidă a sarcinilor cu mai puțină fricțiune"],
          ".va-showcase .va-app-card:nth-child(1) .va-app-kicker": "Recuperare",
          ".va-showcase .va-app-card:nth-child(2) .va-app-kicker": "Curățare",
          ".va-showcase .va-app-card:nth-child(3) .va-app-kicker": "Diagnostic",
          ".va-showcase .va-app-links a:nth-child(1)": ["Pagina produsului", "Pagina produsului", "Pagina produsului"],
          ".va-briefing-section-label": "Subiecte principale",
          ".va-briefing-heading": { html: 'Puls <span class="is-accent">produs</span>' },
          ".va-gallery-head h2": "Fiecare ecran rămâne clar, tactil și concentrat.",
          ".va-contact-panel h2": "Ai nevoie de suport pentru produs sau de o discuție de parteneriat?"
        }
      },
      "de-DE": {
        pageTitle: "VelocAI | KI-Apps für Wiederfinden, Bereinigung und Bluetooth-Diagnose",
        metaDescription: "VelocAI entwickelt fokussierte iPhone-Apps zum Wiederfinden verlorener Geräte, zum Bereinigen von Speicher und zum Debuggen von Bluetooth-Workflows.",
        selectorTexts: {
          ".va-eyebrow": ["VelocAI Studio", "Visueller Fluss", "Kontakt"],
          ".va-hero-title": { html: 'Ein <span class="is-accent">klarerer</span> Weg für tägliche KI-Workflows.' },
          ".va-hero-subtitle": "Vom Wiederfinden verlorener Geräte über Fotobereinigung bis zur BLE-Diagnose bündelt VelocAI fokussierte Mobile-Tools in einem schnellen, klaren und modernen System.",
          ".va-hero-actions .va-btn-primary": "Apps entdecken",
          ".va-hero-actions .va-btn-secondary": "Guides lesen",
          ".va-proof-list li": ["Datenschutz zuerst", "Für den iPhone-Alltag entwickelt", "Schnellere Aufgabenerledigung mit weniger Reibung"],
          ".va-showcase .va-app-card:nth-child(1) .va-app-kicker": "Wiederfinden",
          ".va-showcase .va-app-card:nth-child(2) .va-app-kicker": "Bereinigung",
          ".va-showcase .va-app-card:nth-child(3) .va-app-kicker": "Diagnose",
          ".va-showcase .va-app-links a:nth-child(1)": ["Produktseite", "Produktseite", "Produktseite"],
          ".va-briefing-section-label": "Top-Stories",
          ".va-briefing-heading": { html: 'Produkt-<span class="is-accent">Pulse</span>' },
          ".va-gallery-head h2": "Jeder Screen bleibt klar, greifbar und fokussiert.",
          ".va-contact-panel h2": "Brauchen Sie Produktsupport oder ein Partnerschaftsgespräch?"
        }
      },
      "es-ES": {
        pageTitle: "VelocAI | Apps de IA para recuperación, limpieza y diagnóstico Bluetooth",
        metaDescription: "VelocAI crea apps de iPhone centradas en encontrar dispositivos perdidos, limpiar almacenamiento y depurar flujos Bluetooth.",
        selectorTexts: {
          ".va-eyebrow": ["VelocAI Studio", "Flujo visual", "Contacto"],
          ".va-hero-title": { html: 'Una forma <span class="is-accent">más limpia</span> de ejecutar flujos de IA cotidianos.' },
          ".va-hero-subtitle": "Desde recuperar dispositivos perdidos hasta limpiar fotos y diagnosticar BLE, VelocAI reúne herramientas móviles rápidas, claras y modernas en un solo sistema visual.",
          ".va-hero-actions .va-btn-primary": "Explorar apps",
          ".va-hero-actions .va-btn-secondary": "Leer guías",
          ".va-proof-list li": ["Privacidad primero", "Diseñado para el uso diario en iPhone", "Tareas más rápidas con menos fricción"],
          ".va-showcase .va-app-card:nth-child(1) .va-app-kicker": "Recuperación",
          ".va-showcase .va-app-card:nth-child(2) .va-app-kicker": "Limpieza",
          ".va-showcase .va-app-card:nth-child(3) .va-app-kicker": "Diagnóstico",
          ".va-showcase .va-app-links a:nth-child(1)": ["Página del producto", "Página del producto", "Página del producto"],
          ".va-briefing-section-label": "Historias destacadas",
          ".va-briefing-heading": { html: 'Pulso de <span class="is-accent">producto</span>' },
          ".va-gallery-head h2": "Cada pantalla se mantiene clara, táctil y enfocada.",
          ".va-contact-panel h2": "¿Necesitas soporte del producto o una conversación de colaboración?"
        }
      },
      "it-IT": {
        pageTitle: "VelocAI | App IA per recupero, pulizia e diagnostica Bluetooth",
        metaDescription: "VelocAI crea app iPhone focalizzate sul ritrovamento dei dispositivi, sulla pulizia dello spazio e sul debug dei flussi Bluetooth.",
        selectorTexts: {
          ".va-eyebrow": ["VelocAI Studio", "Flusso visivo", "Contatto"],
          ".va-hero-title": { html: 'Un modo <span class="is-accent">più pulito</span> per gestire i flussi IA quotidiani.' },
          ".va-hero-subtitle": "Dal recupero dei dispositivi persi alla pulizia delle foto e alla diagnostica BLE, VelocAI riunisce strumenti mobili chiari, veloci e moderni in un unico sistema visivo.",
          ".va-hero-actions .va-btn-primary": "Esplora le app",
          ".va-hero-actions .va-btn-secondary": "Leggi le guide",
          ".va-proof-list li": ["Privacy al primo posto", "Progettato per l’uso quotidiano su iPhone", "Completamento rapido con meno attrito"],
          ".va-showcase .va-app-card:nth-child(1) .va-app-kicker": "Recupero",
          ".va-showcase .va-app-card:nth-child(2) .va-app-kicker": "Pulizia",
          ".va-showcase .va-app-card:nth-child(3) .va-app-kicker": "Diagnostica",
          ".va-showcase .va-app-links a:nth-child(1)": ["Pagina prodotto", "Pagina prodotto", "Pagina prodotto"],
          ".va-briefing-section-label": "In evidenza",
          ".va-briefing-heading": { html: 'Polso del <span class="is-accent">prodotto</span>' },
          ".va-gallery-head h2": "Ogni schermata resta chiara, tattile e focalizzata.",
          ".va-contact-panel h2": "Hai bisogno di supporto prodotto o di parlare di una partnership?"
        }
      },
      "pt-BR": {
        pageTitle: "VelocAI | Apps de IA para recuperação, limpeza e diagnóstico Bluetooth",
        metaDescription: "A VelocAI cria apps para iPhone focados em encontrar dispositivos perdidos, limpar armazenamento e depurar fluxos Bluetooth.",
        selectorTexts: {
          ".va-eyebrow": ["VelocAI Studio", "Fluxo visual", "Contato"],
          ".va-hero-title": { html: 'Uma forma <span class="is-accent">mais limpa</span> de rodar fluxos de IA do dia a dia.' },
          ".va-hero-subtitle": "Da recuperação de dispositivos perdidos à limpeza de fotos e ao diagnóstico BLE, a VelocAI reúne ferramentas móveis rápidas, claras e modernas em um único sistema visual.",
          ".va-hero-actions .va-btn-primary": "Explorar apps",
          ".va-hero-actions .va-btn-secondary": "Ler guias",
          ".va-proof-list li": ["Privacidade em primeiro lugar", "Feito para o uso diário no iPhone", "Tarefas concluídas mais rápido com menos atrito"],
          ".va-showcase .va-app-card:nth-child(1) .va-app-kicker": "Recuperação",
          ".va-showcase .va-app-card:nth-child(2) .va-app-kicker": "Limpeza",
          ".va-showcase .va-app-card:nth-child(3) .va-app-kicker": "Diagnóstico",
          ".va-showcase .va-app-links a:nth-child(1)": ["Página do produto", "Página do produto", "Página do produto"],
          ".va-briefing-section-label": "Principais notícias",
          ".va-briefing-heading": { html: 'Pulso do <span class="is-accent">produto</span>' },
          ".va-gallery-head h2": "Cada tela permanece clara, tátil e focada.",
          ".va-contact-panel h2": "Precisa de suporte do produto ou de uma conversa sobre parceria?"
        }
      },
      "nl-NL": {
        pageTitle: "VelocAI | AI-apps voor terugvinden, opschonen en Bluetooth-diagnose",
        metaDescription: "VelocAI maakt gerichte iPhone-apps voor het terugvinden van verloren apparaten, het opschonen van opslag en het debuggen van Bluetooth-workflows.",
        selectorTexts: {
          ".va-eyebrow": ["VelocAI Studio", "Visuele flow", "Contact"],
          ".va-hero-title": { html: 'Een <span class="is-accent">schonere</span> manier om dagelijkse AI-workflows uit te voeren.' },
          ".va-hero-subtitle": "Van het terugvinden van verloren apparaten tot foto-opruiming en BLE-diagnose: VelocAI brengt snelle, duidelijke en moderne mobiele tools samen in één visueel systeem.",
          ".va-hero-actions .va-btn-primary": "Apps bekijken",
          ".va-hero-actions .va-btn-secondary": "Gidsen lezen",
          ".va-proof-list li": ["Privacy eerst", "Ontworpen voor dagelijks iPhone-gebruik", "Snellere taakafhandeling met minder frictie"],
          ".va-showcase .va-app-card:nth-child(1) .va-app-kicker": "Herstel",
          ".va-showcase .va-app-card:nth-child(2) .va-app-kicker": "Opschonen",
          ".va-showcase .va-app-card:nth-child(3) .va-app-kicker": "Diagnose",
          ".va-showcase .va-app-links a:nth-child(1)": ["Productpagina", "Productpagina", "Productpagina"],
          ".va-briefing-section-label": "Topverhalen",
          ".va-briefing-heading": { html: 'Product-<span class="is-accent">pulse</span>' },
          ".va-gallery-head h2": "Elk scherm blijft helder, tastbaar en gefocust.",
          ".va-contact-panel h2": "Hulp nodig bij een product of een gesprek over samenwerking?"
        }
      },
      "sv-SE": {
        pageTitle: "VelocAI | AI-appar för återställning, rensning och Bluetooth-diagnostik",
        metaDescription: "VelocAI skapar fokuserade iPhone-appar för att hitta borttappade enheter, rensa lagring och felsöka Bluetooth-flöden.",
        selectorTexts: {
          ".va-eyebrow": ["VelocAI Studio", "Visuellt flöde", "Kontakt"],
          ".va-hero-title": { html: 'Ett <span class="is-accent">renare</span> sätt att köra vardagliga AI-flöden.' },
          ".va-hero-subtitle": "Från återställning av borttappade enheter till bildrensning och BLE-diagnostik samlar VelocAI tydliga och snabba mobilverktyg i ett modernt visuellt system.",
          ".va-hero-actions .va-btn-primary": "Utforska appar",
          ".va-hero-actions .va-btn-secondary": "Läs guider",
          ".va-proof-list li": ["Integritet först", "Utformad för daglig iPhone-användning", "Snabbare uppgifter med mindre friktion"],
          ".va-showcase .va-app-card:nth-child(1) .va-app-kicker": "Återställning",
          ".va-showcase .va-app-card:nth-child(2) .va-app-kicker": "Rensning",
          ".va-showcase .va-app-card:nth-child(3) .va-app-kicker": "Diagnostik",
          ".va-showcase .va-app-links a:nth-child(1)": ["Produktsida", "Produktsida", "Produktsida"],
          ".va-briefing-section-label": "Toppnyheter",
          ".va-briefing-heading": { html: 'Produkt-<span class="is-accent">puls</span>' },
          ".va-gallery-head h2": "Varje skärm förblir tydlig, taktil och fokuserad.",
          ".va-contact-panel h2": "Behöver du produktsupport eller ett partnerskapssamtal?"
        }
      },
      "pl-PL": {
        pageTitle: "VelocAI | Aplikacje AI do odzyskiwania, czyszczenia i diagnostyki Bluetooth",
        metaDescription: "VelocAI tworzy aplikacje iPhone do odnajdywania zgubionych urządzeń, czyszczenia pamięci i debugowania przepływów Bluetooth.",
        selectorTexts: {
          ".va-eyebrow": ["VelocAI Studio", "Przepływ wizualny", "Kontakt"],
          ".va-hero-title": { html: '<span class="is-accent">Czystszy</span> sposób na codzienne przepływy AI.' },
          ".va-hero-subtitle": "Od odzyskiwania zgubionych urządzeń po czyszczenie zdjęć i diagnostykę BLE — VelocAI łączy szybkie i przejrzyste narzędzia mobilne w jeden nowoczesny system wizualny.",
          ".va-hero-actions .va-btn-primary": "Przeglądaj aplikacje",
          ".va-hero-actions .va-btn-secondary": "Czytaj poradniki",
          ".va-proof-list li": ["Prywatność przede wszystkim", "Zaprojektowane do codziennego użycia na iPhonie", "Szybsze wykonanie zadań przy mniejszym tarciu"],
          ".va-showcase .va-app-card:nth-child(1) .va-app-kicker": "Odzyskiwanie",
          ".va-showcase .va-app-card:nth-child(2) .va-app-kicker": "Czyszczenie",
          ".va-showcase .va-app-card:nth-child(3) .va-app-kicker": "Diagnostyka",
          ".va-showcase .va-app-links a:nth-child(1)": ["Strona produktu", "Strona produktu", "Strona produktu"],
          ".va-briefing-section-label": "Najważniejsze",
          ".va-briefing-heading": { html: '<span class="is-accent">Puls</span> produktu' },
          ".va-gallery-head h2": "Każdy ekran pozostaje czytelny, namacalny i skupiony.",
          ".va-contact-panel h2": "Potrzebujesz wsparcia produktu lub rozmowy o współpracy?"
        }
      },
      "cs-CZ": {
        pageTitle: "VelocAI | AI aplikace pro hledání, čištění a diagnostiku Bluetooth",
        metaDescription: "VelocAI vytváří zaměřené aplikace pro iPhone na hledání ztracených zařízení, čištění úložiště a ladění Bluetooth pracovních postupů.",
        selectorTexts: {
          ".va-eyebrow": ["VelocAI Studio", "Vizuální tok", "Kontakt"],
          ".va-hero-title": { html: '<span class="is-accent">Čistší</span> způsob, jak spouštět každodenní AI workflow.' },
          ".va-hero-subtitle": "Od hledání ztracených zařízení přes čištění fotek až po BLE diagnostiku spojuje VelocAI rychlé a přehledné mobilní nástroje do jednoho moderního vizuálního systému.",
          ".va-hero-actions .va-btn-primary": "Prozkoumat aplikace",
          ".va-hero-actions .va-btn-secondary": "Číst průvodce",
          ".va-proof-list li": ["Soukromí na prvním místě", "Navrženo pro každodenní používání iPhonu", "Rychlejší dokončení úkolů s menším třením"],
          ".va-showcase .va-app-card:nth-child(1) .va-app-kicker": "Obnova",
          ".va-showcase .va-app-card:nth-child(2) .va-app-kicker": "Čištění",
          ".va-showcase .va-app-card:nth-child(3) .va-app-kicker": "Diagnostika",
          ".va-showcase .va-app-links a:nth-child(1)": ["Produktová stránka", "Produktová stránka", "Produktová stránka"],
          ".va-briefing-section-label": "Hlavní zprávy",
          ".va-briefing-heading": { html: 'Produktový <span class="is-accent">pulz</span>' },
          ".va-gallery-head h2": "Každá obrazovka zůstává jasná, hmatová a soustředěná.",
          ".va-contact-panel h2": "Potřebujete podporu produktu nebo rozhovor o partnerství?"
        }
      }
    },
    "/apps/": {
      "fr-FR": {
        pageTitle: "VelocAI Apps | AI Cleanup PRO, Find AI, Bluetooth Explorer",
        metaDescription: "Comparez les apps iOS VelocAI pour le nettoyage, la recherche d’appareils et le diagnostic Bluetooth.",
        selectorTexts: {
          "header .brand span": "VelocAI Apps",
          "header nav a:nth-child(1)": "Accueil",
          "header nav a:nth-child(2)": "Apps",
          "header nav a:nth-child(3)": "Blog",
          "header nav a:nth-child(4)": "Confidentialité",
          "main > h1": "Choisissez l’app VelocAI adaptée à votre workflow",
          ".lede": "VelocAI crée des apps iOS pratiques pour le nettoyage du stockage, la récupération d’appareils perdus et le dépannage Bluetooth professionnel.",
          ".card:nth-child(1) > p": "Nettoyez les photos en double, supprimez les grandes vidéos et organisez les contacts avec un traitement local respectueux de la vie privée.",
          ".card:nth-child(1) .tags span": ["Nettoyeur photo iPhone", "Nettoyage des doublons", "Optimisation du stockage"],
          ".card:nth-child(1) .update-label": "Dernière version App Store",
          ".card:nth-child(1) .update-source": "Notes de version officielles de l’App Store",
          ".card:nth-child(1) .actions a:nth-child(1)": "Télécharger sur l’App Store",
          ".card:nth-child(1) .actions a:nth-child(2)": "Page produit",
          ".card:nth-child(1) .actions a:nth-child(3)": "Politique de confidentialité",
          ".card:nth-child(2) > p": "Retrouvez des AirPods perdus et des appareils Bluetooth proches grâce au radar de distance et aux indications de dernière position.",
          ".card:nth-child(2) .tags span": ["Recherche Bluetooth", "Retrouver des AirPods", "Récupération d’appareil"],
          ".card:nth-child(2) .update-label": "Dernière version App Store",
          ".card:nth-child(2) .update-source": "Notes de version officielles de l’App Store",
          ".card:nth-child(2) .actions a:nth-child(1)": "Télécharger sur l’App Store",
          ".card:nth-child(2) .actions a:nth-child(2)": "Page produit",
          ".card:nth-child(2) .actions a:nth-child(3)": "Politique de confidentialité",
          ".card:nth-child(3) > p": "Scannez les appareils BLE, inspectez les services GATT, envoyez des paquets et diagnostiquez les problèmes de connexion avec une aide IA.",
          ".card:nth-child(3) .tags span": ["Scanner BLE", "Inspecteur GATT", "Outil de debug Bluetooth"],
          ".card:nth-child(3) .update-label": "Dernière version App Store",
          ".card:nth-child(3) .update-source": "Notes de version officielles de l’App Store",
          ".card:nth-child(3) .actions a:nth-child(1)": "Télécharger sur l’App Store",
          ".card:nth-child(3) .actions a:nth-child(2)": "Page produit",
          ".card:nth-child(3) .actions a:nth-child(3)": "Guide utilisateur",
          ".resources h2": "Ressources liées",
          ".resources p": "Lisez les guides produits et tutoriels de dépannage du blog VelocAI.",
          ".resource-links a:nth-child(1)": "Ouvrir le hub blog"
        }
      },
      "ro-RO": { pageTitle: "VelocAI Apps | AI Cleanup PRO, Find AI, Bluetooth Explorer", metaDescription: "Compară aplicațiile VelocAI pentru curățare, găsirea dispozitivelor și diagnostic Bluetooth.", selectorTexts: { "header nav a:nth-child(1)": "Acasă", "header nav a:nth-child(2)": "Aplicații", "header nav a:nth-child(4)": "Confidențialitate", "main > h1": "Alege aplicația VelocAI potrivită pentru fluxul tău", ".lede": "VelocAI construiește aplicații iOS practice pentru curățarea stocării, recuperarea dispozitivelor pierdute și depanarea profesională Bluetooth.", ".card:nth-child(1) .update-label": "Ultima versiune din App Store", ".card:nth-child(2) .update-label": "Ultima versiune din App Store", ".card:nth-child(3) .update-label": "Ultima versiune din App Store", ".resources h2": "Resurse asociate" } },
      "de-DE": { pageTitle: "VelocAI Apps | AI Cleanup PRO, Find AI, Bluetooth Explorer", metaDescription: "Vergleichen Sie VelocAI-Apps für Bereinigung, Gerätesuche und Bluetooth-Diagnose.", selectorTexts: { "header nav a:nth-child(1)": "Start", "header nav a:nth-child(2)": "Apps", "header nav a:nth-child(4)": "Datenschutz", "main > h1": "Wählen Sie die passende VelocAI-App für Ihren Workflow", ".lede": "VelocAI entwickelt praktische iOS-Apps für Speicherbereinigung, Wiederfinden verlorener Geräte und professionelle Bluetooth-Fehleranalyse.", ".card:nth-child(1) .update-label": "Neueste App-Store-Version", ".card:nth-child(2) .update-label": "Neueste App-Store-Version", ".card:nth-child(3) .update-label": "Neueste App-Store-Version", ".resources h2": "Verwandte Ressourcen" } },
      "es-ES": { pageTitle: "VelocAI Apps | AI Cleanup PRO, Find AI, Bluetooth Explorer", metaDescription: "Compara las apps de VelocAI para limpieza, búsqueda de dispositivos y diagnóstico Bluetooth.", selectorTexts: { "header nav a:nth-child(1)": "Inicio", "header nav a:nth-child(2)": "Apps", "header nav a:nth-child(4)": "Privacidad", "main > h1": "Elige la app de VelocAI adecuada para tu flujo de trabajo", ".lede": "VelocAI crea apps iOS prácticas para limpieza de almacenamiento, recuperación de dispositivos perdidos y solución profesional de problemas Bluetooth.", ".card:nth-child(1) .update-label": "Última versión en App Store", ".card:nth-child(2) .update-label": "Última versión en App Store", ".card:nth-child(3) .update-label": "Última versión en App Store", ".resources h2": "Recursos relacionados" } },
      "it-IT": { pageTitle: "VelocAI Apps | AI Cleanup PRO, Find AI, Bluetooth Explorer", metaDescription: "Confronta le app VelocAI per pulizia, ricerca dispositivi e diagnostica Bluetooth.", selectorTexts: { "header nav a:nth-child(1)": "Home", "header nav a:nth-child(2)": "App", "header nav a:nth-child(4)": "Privacy", "main > h1": "Scegli l’app VelocAI giusta per il tuo flusso di lavoro", ".lede": "VelocAI realizza app iOS pratiche per la pulizia dello spazio, il recupero dei dispositivi smarriti e la risoluzione professionale dei problemi Bluetooth.", ".card:nth-child(1) .update-label": "Ultima versione su App Store", ".card:nth-child(2) .update-label": "Ultima versione su App Store", ".card:nth-child(3) .update-label": "Ultima versione su App Store", ".resources h2": "Risorse correlate" } },
      "pt-BR": { pageTitle: "VelocAI Apps | AI Cleanup PRO, Find AI, Bluetooth Explorer", metaDescription: "Compare os apps da VelocAI para limpeza, busca de dispositivos e diagnóstico Bluetooth.", selectorTexts: { "header nav a:nth-child(1)": "Início", "header nav a:nth-child(2)": "Apps", "header nav a:nth-child(4)": "Privacidade", "main > h1": "Escolha o app VelocAI certo para o seu fluxo de trabalho", ".lede": "A VelocAI cria apps iOS práticos para limpeza de armazenamento, recuperação de dispositivos perdidos e solução profissional de problemas Bluetooth.", ".card:nth-child(1) .update-label": "Última versão na App Store", ".card:nth-child(2) .update-label": "Última versão na App Store", ".card:nth-child(3) .update-label": "Última versão na App Store", ".resources h2": "Recursos relacionados" } },
      "nl-NL": { pageTitle: "VelocAI Apps | AI Cleanup PRO, Find AI, Bluetooth Explorer", metaDescription: "Vergelijk VelocAI-apps voor opschonen, apparaatherstel en Bluetooth-diagnose.", selectorTexts: { "header nav a:nth-child(1)": "Home", "header nav a:nth-child(2)": "Apps", "header nav a:nth-child(4)": "Privacy", "main > h1": "Kies de juiste VelocAI-app voor jouw workflow", ".lede": "VelocAI bouwt praktische iOS-apps voor opslagopschoning, het terugvinden van verloren apparaten en professionele Bluetooth-probleemoplossing.", ".card:nth-child(1) .update-label": "Nieuwste App Store-versie", ".card:nth-child(2) .update-label": "Nieuwste App Store-versie", ".card:nth-child(3) .update-label": "Nieuwste App Store-versie", ".resources h2": "Gerelateerde bronnen" } },
      "sv-SE": { pageTitle: "VelocAI Apps | AI Cleanup PRO, Find AI, Bluetooth Explorer", metaDescription: "Jämför VelocAI-appar för rensning, enhetssökning och Bluetooth-diagnostik.", selectorTexts: { "header nav a:nth-child(1)": "Hem", "header nav a:nth-child(2)": "Appar", "header nav a:nth-child(4)": "Integritet", "main > h1": "Välj rätt VelocAI-app för ditt arbetsflöde", ".lede": "VelocAI bygger praktiska iOS-appar för lagringsrensning, återställning av borttappade enheter och professionell Bluetooth-felsökning.", ".card:nth-child(1) .update-label": "Senaste App Store-versionen", ".card:nth-child(2) .update-label": "Senaste App Store-versionen", ".card:nth-child(3) .update-label": "Senaste App Store-versionen", ".resources h2": "Relaterade resurser" } },
      "pl-PL": { pageTitle: "VelocAI Apps | AI Cleanup PRO, Find AI, Bluetooth Explorer", metaDescription: "Porównaj aplikacje VelocAI do czyszczenia, wyszukiwania urządzeń i diagnostyki Bluetooth.", selectorTexts: { "header nav a:nth-child(1)": "Strona główna", "header nav a:nth-child(2)": "Aplikacje", "header nav a:nth-child(4)": "Prywatność", "main > h1": "Wybierz odpowiednią aplikację VelocAI do swojego workflow", ".lede": "VelocAI tworzy praktyczne aplikacje iOS do czyszczenia pamięci, odzyskiwania zgubionych urządzeń i profesjonalnego rozwiązywania problemów Bluetooth.", ".card:nth-child(1) .update-label": "Najnowsza wersja w App Store", ".card:nth-child(2) .update-label": "Najnowsza wersja w App Store", ".card:nth-child(3) .update-label": "Najnowsza wersja w App Store", ".resources h2": "Powiązane zasoby" } },
      "cs-CZ": { pageTitle: "VelocAI Apps | AI Cleanup PRO, Find AI, Bluetooth Explorer", metaDescription: "Porovnejte aplikace VelocAI pro čištění, hledání zařízení a diagnostiku Bluetooth.", selectorTexts: { "header nav a:nth-child(1)": "Domů", "header nav a:nth-child(2)": "Aplikace", "header nav a:nth-child(4)": "Soukromí", "main > h1": "Vyberte správnou aplikaci VelocAI pro svůj pracovní postup", ".lede": "VelocAI vytváří praktické aplikace pro iOS pro čištění úložiště, hledání ztracených zařízení a profesionální řešení problémů s Bluetooth.", ".card:nth-child(1) .update-label": "Nejnovější verze v App Store", ".card:nth-child(2) .update-label": "Nejnovější verze v App Store", ".card:nth-child(3) .update-label": "Nejnovější verze v App Store", ".resources h2": "Související zdroje" } }
    }
  };

  Object.assign(PAGE_TRANSLATION_OVERRIDES, {
    "/blog/": {
      "fr-FR": { pageTitle: "Blog VelocAI | Guides Bluetooth, nettoyage mobile et optimisation", metaDescription: "Articles VelocAI sur le dépannage Bluetooth, le nettoyage du téléphone et les guides pratiques d’optimisation mobile.", selectorTexts: { "header nav a:nth-child(1)": "Accueil", "header nav a:nth-child(2)": "Apps", "h1": { html: '<span class="is-accent">Bluetooth</span> et guides de <span class="is-accent">nettoyage</span> mobile pour la performance quotidienne' }, ".lede": "Ces articles ciblent des tâches à forte intention : débogage Bluetooth, checklists de nettoyage du stockage, correctifs de stabilité et routines pratiques pour un iPhone ou Android plus fluide.", ".list": { ariaLabel: "Derniers articles du blog" }, ".pagination": { ariaLabel: "Pagination du blog" } } },
      "ro-RO": { pageTitle: "Blog VelocAI | Ghiduri Bluetooth, curatare telefon si optimizare mobila", metaDescription: "Articole VelocAI despre depanare Bluetooth, curatarea telefonului si optimizare mobila.", selectorTexts: { "header nav a:nth-child(1)": "Acasa", "header nav a:nth-child(2)": "Aplicatii", "h1": { html: 'Ghiduri pentru <span class="is-accent">Bluetooth</span> si <span class="is-accent">curatare</span> telefon pentru performanta zilnica' }, ".lede": "Aceste articole acopera sarcini cautate frecvent: depanare Bluetooth, liste de curatare a stocarii, remedieri de stabilitate si rutine practice pentru performanta mobila mai buna.", ".list": { ariaLabel: "Ultimele articole" }, ".pagination": { ariaLabel: "Paginare blog" } } },
      "de-DE": { pageTitle: "VelocAI Blog | Bluetooth-Guides, Handy-Bereinigung und mobile Optimierung", metaDescription: "VelocAI-Artikel zu Bluetooth-Fehlersuche, Handy-Bereinigung und praktischer mobiler Optimierung.", selectorTexts: { "header nav a:nth-child(1)": "Start", "header nav a:nth-child(2)": "Apps", "h1": { html: '<span class="is-accent">Bluetooth</span>-Troubleshooting und Handy-<span class="is-accent">Bereinigung</span> für bessere mobile Leistung' }, ".lede": "Diese Artikel konzentrieren sich auf stark nachgefragte Aufgaben: Bluetooth-Debugging, Speicher-Checklisten, Stabilitätskorrekturen und praktische Routinen für schnellere iPhone- und Android-Leistung.", ".list": { ariaLabel: "Neueste Blogbeiträge" }, ".pagination": { ariaLabel: "Blog-Paginierung" } } },
      "es-ES": { pageTitle: "Blog de VelocAI | Guias Bluetooth, limpieza del telefono y optimizacion", metaDescription: "Articulos de VelocAI sobre solucion de problemas Bluetooth, limpieza del telefono y optimizacion movil.", selectorTexts: { "header nav a:nth-child(1)": "Inicio", "header nav a:nth-child(2)": "Apps", "h1": { html: 'Guias de <span class="is-accent">Bluetooth</span> y <span class="is-accent">limpieza</span> del telefono para el rendimiento diario' }, ".lede": "Estos articulos cubren tareas de alta intencion: depuracion Bluetooth, listas de limpieza de almacenamiento, correcciones de estabilidad y rutinas practicas para un mejor rendimiento en iPhone y Android.", ".list": { ariaLabel: "Entradas recientes del blog" }, ".pagination": { ariaLabel: "Paginacion del blog" } } },
      "it-IT": { pageTitle: "Blog VelocAI | Guide Bluetooth, pulizia telefono e ottimizzazione mobile", metaDescription: "Articoli VelocAI su troubleshooting Bluetooth, pulizia del telefono e ottimizzazione mobile.", selectorTexts: { "header nav a:nth-child(1)": "Home", "header nav a:nth-child(2)": "App", "h1": { html: 'Guide per <span class="is-accent">Bluetooth</span> e <span class="is-accent">pulizia</span> del telefono per le prestazioni quotidiane' }, ".lede": "Questi articoli trattano attivita ad alta intenzione: debug Bluetooth, checklist di pulizia storage, correzioni di stabilita e routine pratiche per prestazioni migliori su iPhone e Android.", ".list": { ariaLabel: "Ultimi articoli del blog" }, ".pagination": { ariaLabel: "Paginazione blog" } } },
      "pt-BR": { pageTitle: "Blog VelocAI | Guias de Bluetooth, limpeza do telefone e otimizacao", metaDescription: "Artigos da VelocAI sobre solucao de problemas Bluetooth, limpeza do telefone e otimizacao movel.", selectorTexts: { "header nav a:nth-child(1)": "Inicio", "header nav a:nth-child(2)": "Apps", "h1": { html: 'Guias de <span class="is-accent">Bluetooth</span> e <span class="is-accent">limpeza</span> do telefone para desempenho movel diario' }, ".lede": "Esses artigos cobrem tarefas de alta intencao: depuracao Bluetooth, checklists de limpeza de armazenamento, correcoes de estabilidade e rotinas praticas para melhor desempenho em iPhone e Android.", ".list": { ariaLabel: "Postagens mais recentes" }, ".pagination": { ariaLabel: "Paginacao do blog" } } },
      "nl-NL": { pageTitle: "VelocAI Blog | Bluetooth-gidsen, telefoonopschoning en optimalisatie", metaDescription: "VelocAI-artikelen over Bluetooth-probleemoplossing, telefoonopschoning en mobiele optimalisatie.", selectorTexts: { "header nav a:nth-child(1)": "Home", "header nav a:nth-child(2)": "Apps", "h1": { html: '<span class="is-accent">Bluetooth</span>-gidsen en <span class="is-accent">opschoon</span>workflows voor dagelijkse mobiele prestaties' }, ".lede": "Deze artikelen richten zich op taken met hoge zoekintentie: Bluetooth-debugging, opslag-checklists, stabiliteitsfixes en praktische routines voor betere iPhone- en Android-prestaties.", ".list": { ariaLabel: "Laatste blogposts" }, ".pagination": { ariaLabel: "Blogpaginering" } } },
      "sv-SE": { pageTitle: "VelocAI Blogg | Bluetooth-guider, telefonrensning och optimering", metaDescription: "VelocAI-artiklar om Bluetooth-felsokning, telefonrensning och mobil optimering.", selectorTexts: { "header nav a:nth-child(1)": "Hem", "header nav a:nth-child(2)": "Appar", "h1": { html: '<span class="is-accent">Bluetooth</span>-guider och <span class="is-accent">rensning</span> for daglig mobil prestanda' }, ".lede": "Dessa artiklar fokuserar pa uppgifter med hog sokintention: Bluetooth-debuggning, lagringschecklistor, stabilitetsfixar och praktiska rutiner for snabbare iPhone- och Android-prestanda.", ".list": { ariaLabel: "Senaste blogginlaggen" }, ".pagination": { ariaLabel: "Bloggpaginering" } } },
      "pl-PL": { pageTitle: "Blog VelocAI | Przewodniki Bluetooth, czyszczenie telefonu i optymalizacja", metaDescription: "Artykuly VelocAI o rozwiazywaniu problemow Bluetooth, czyszczeniu telefonu i optymalizacji mobilnej.", selectorTexts: { "header nav a:nth-child(1)": "Strona glowna", "header nav a:nth-child(2)": "Aplikacje", "h1": { html: 'Przewodniki <span class="is-accent">Bluetooth</span> i <span class="is-accent">czyszczenia</span> telefonu dla codziennej wydajnosci mobilnej' }, ".lede": "Te artykuly obejmuja najczestsze zadania: debugowanie Bluetooth, checklisty czyszczenia pamieci, poprawki stabilnosci i praktyczne rutyny dla szybszego iPhone’a i Androida.", ".list": { ariaLabel: "Najnowsze wpisy" }, ".pagination": { ariaLabel: "Paginacja bloga" } } },
      "cs-CZ": { pageTitle: "Blog VelocAI | Bluetooth pruvodce, cisteni telefonu a optimalizace", metaDescription: "Clanky VelocAI o reseni problemu Bluetooth, cisteni telefonu a mobilni optimalizaci.", selectorTexts: { "header nav a:nth-child(1)": "Domu", "header nav a:nth-child(2)": "Aplikace", "h1": { html: 'Pruvodce pro <span class="is-accent">Bluetooth</span> a <span class="is-accent">cisteni</span> telefonu pro kazdodenni mobilni vykon' }, ".lede": "Tyto clanky se zameruji na ukoly s vysokym zamerem: Bluetooth debugging, checklisty cisteni uloziste, opravy stability a prakticke postupy pro lepsi vykon iPhonu a Androidu.", ".list": { ariaLabel: "Nejnovejsi clanky" }, ".pagination": { ariaLabel: "Strankovani blogu" } } }
    },
    "/aifind/": {
      "fr-FR": { pageTitle: "Find AI | Retrouver AirPods et appareils Bluetooth", metaDescription: "Find AI vous aide a retrouver AirPods et appareils Bluetooth proches avec radar de distance en temps reel.", selectorTexts: { ".nav a:nth-child(1)": "Accueil", ".nav a:nth-child(2)": "Apps", ".nav a:nth-child(4)": "Cas d’usage", ".nav a:nth-child(5)": "Fonctionnalites", ".nav a:nth-child(6)": "Comment ca marche", ".nav a:nth-child(8)": "Confidentialite", "#hero-title": "Retrouvez vos AirPods et appareils Bluetooth, simplement et rapidement.", ".cta-row .btn-primary": "Telecharger sur l’App Store", ".cta-row .btn-secondary:nth-child(2)": "Voir la FAQ", ".cta-row .btn-secondary:nth-child(3)": "Lire la politique de confidentialite", "#use-cases-title": "Scenarios courants d’appareil perdu", "#features-title": "Modules concus pour accelerer la recuperation", "#how-title": "Comment fonctionne Find AI", "#faq-title": "Questions frequentes", ".download h2": "Pret a retrouver vos AirPods ou ecouteurs perdus ?", ".download .btn-primary": "Obtenir Find AI" } },
      "ro-RO": { pageTitle: "Find AI | Gaseste AirPods si dispozitive Bluetooth pierdute", metaDescription: "Find AI te ajuta sa gasesti AirPods si dispozitive Bluetooth din apropiere cu radar de distanta in timp real.", selectorTexts: { ".nav a:nth-child(1)": "Acasa", ".nav a:nth-child(2)": "Aplicatii", ".nav a:nth-child(4)": "Cazuri de utilizare", ".nav a:nth-child(5)": "Functii", ".nav a:nth-child(6)": "Cum functioneaza", ".nav a:nth-child(8)": "Confidentialitate", "#hero-title": "Gaseste AirPods si dispozitive Bluetooth pierdute, simplu si rapid.", ".cta-row .btn-primary": "Descarca din App Store", "#use-cases-title": "Scenarii frecvente de dispozitive pierdute", "#features-title": "Module construite pentru recuperare rapida", "#how-title": "Cum functioneaza Find AI", "#faq-title": "Intrebari frecvente" } },
      "de-DE": { pageTitle: "Find AI | Verlorene AirPods und Bluetooth-Gerate finden", metaDescription: "Find AI hilft beim Wiederfinden verlorener AirPods und Bluetooth-Gerate mit Live-Distanzradar.", selectorTexts: { ".nav a:nth-child(1)": "Start", ".nav a:nth-child(2)": "Apps", ".nav a:nth-child(4)": "Anwendungsfalle", ".nav a:nth-child(5)": "Funktionen", ".nav a:nth-child(6)": "So funktioniert es", ".nav a:nth-child(8)": "Datenschutz", "#hero-title": "Verlorene AirPods und Bluetooth-Gerate einfach und schnell finden.", ".cta-row .btn-primary": "Im App Store laden", ".cta-row .btn-secondary:nth-child(2)": "FAQ ansehen", ".cta-row .btn-secondary:nth-child(3)": "Datenschutz lesen", "#use-cases-title": "Haufige Szenarien fur verlorene Gerate", "#features-title": "Funktionen fur schnellere Wiederfindung", "#how-title": "So funktioniert Find AI", "#faq-title": "Haufige Fragen", ".download h2": "Bereit, verlorene AirPods oder Earbuds zu finden?" } },
      "es-ES": { pageTitle: "Find AI | Encuentra AirPods y dispositivos Bluetooth perdidos", metaDescription: "Find AI te ayuda a encontrar AirPods y dispositivos Bluetooth cercanos con radar de distancia en tiempo real.", selectorTexts: { ".nav a:nth-child(1)": "Inicio", ".nav a:nth-child(2)": "Apps", ".nav a:nth-child(4)": "Casos de uso", ".nav a:nth-child(5)": "Funciones", ".nav a:nth-child(6)": "Como funciona", ".nav a:nth-child(8)": "Privacidad", "#hero-title": "Encuentra AirPods y dispositivos Bluetooth perdidos, simple y rapido.", ".cta-row .btn-primary": "Descargar en App Store", ".cta-row .btn-secondary:nth-child(2)": "Ver FAQ", ".cta-row .btn-secondary:nth-child(3)": "Leer politica de privacidad", "#use-cases-title": "Escenarios comunes de perdida", "#features-title": "Modulos pensados para recuperar mas rapido", "#how-title": "Como funciona Find AI", "#faq-title": "Preguntas frecuentes", ".download h2": "Listo para encontrar tus AirPods o auriculares?" } }
      ,"it-IT": { pageTitle: "Find AI | Trova AirPods e dispositivi Bluetooth smarriti", metaDescription: "Find AI aiuta a trovare AirPods e dispositivi Bluetooth vicini con radar di distanza in tempo reale.", selectorTexts: { ".nav a:nth-child(1)": "Home", ".nav a:nth-child(2)": "App", ".nav a:nth-child(4)": "Casi d’uso", ".nav a:nth-child(5)": "Funzioni", ".nav a:nth-child(6)": "Come funziona", ".nav a:nth-child(8)": "Privacy", "#hero-title": "Trova AirPods e dispositivi Bluetooth smarriti in modo semplice e veloce.", ".cta-row .btn-primary": "Scarica su App Store", "#use-cases-title": "Scenari comuni di dispositivi smarriti", "#features-title": "Moduli pensati per recuperare piu velocemente", "#how-title": "Come funziona Find AI", "#faq-title": "Domande frequenti" } }
      ,"pt-BR": { pageTitle: "Find AI | Encontre AirPods e dispositivos Bluetooth perdidos", metaDescription: "Find AI ajuda voce a encontrar AirPods e dispositivos Bluetooth proximos com radar de distancia em tempo real.", selectorTexts: { ".nav a:nth-child(1)": "Inicio", ".nav a:nth-child(2)": "Apps", ".nav a:nth-child(4)": "Casos de uso", ".nav a:nth-child(5)": "Recursos", ".nav a:nth-child(6)": "Como funciona", ".nav a:nth-child(8)": "Privacidade", "#hero-title": "Encontre AirPods e dispositivos Bluetooth perdidos de forma simples e rapida.", ".cta-row .btn-primary": "Baixar na App Store", "#use-cases-title": "Cenarios comuns de dispositivos perdidos", "#features-title": "Modulos criados para recuperacao rapida", "#how-title": "Como o Find AI funciona", "#faq-title": "Perguntas frequentes" } }
      ,"nl-NL": { pageTitle: "Find AI | Vind verloren AirPods en Bluetooth-apparaten", metaDescription: "Find AI helpt je verloren AirPods en Bluetooth-apparaten in de buurt te vinden met live afstandsradar.", selectorTexts: { ".nav a:nth-child(1)": "Home", ".nav a:nth-child(2)": "Apps", ".nav a:nth-child(4)": "Gebruiksscenario’s", ".nav a:nth-child(5)": "Functies", ".nav a:nth-child(6)": "Hoe het werkt", ".nav a:nth-child(8)": "Privacy", "#hero-title": "Vind verloren AirPods en Bluetooth-apparaten, eenvoudig en snel.", ".cta-row .btn-primary": "Download in de App Store", "#use-cases-title": "Veelvoorkomende scenario’s voor verloren apparaten", "#features-title": "Modules gebouwd voor snelle terugvinding", "#how-title": "Hoe Find AI werkt", "#faq-title": "Veelgestelde vragen" } }
      ,"sv-SE": { pageTitle: "Find AI | Hitta borttappade AirPods och Bluetooth-enheter", metaDescription: "Find AI hjalper dig att hitta borttappade AirPods och Bluetooth-enheter i narheten med live avstandsradar.", selectorTexts: { ".nav a:nth-child(1)": "Hem", ".nav a:nth-child(2)": "Appar", ".nav a:nth-child(4)": "Anvandningsfall", ".nav a:nth-child(5)": "Funktioner", ".nav a:nth-child(6)": "Sa fungerar det", ".nav a:nth-child(8)": "Integritet", "#hero-title": "Hitta borttappade AirPods och Bluetooth-enheter, enkelt och snabbt.", ".cta-row .btn-primary": "Hamta i App Store", "#use-cases-title": "Vanliga scenarier for borttappade enheter", "#features-title": "Moduler byggda for snabb aterhamtning", "#how-title": "Sa fungerar Find AI", "#faq-title": "Vanliga fragor" } }
      ,"pl-PL": { pageTitle: "Find AI | Znajdz zgubione AirPods i urzadzenia Bluetooth", metaDescription: "Find AI pomaga znajdowac zgubione AirPods i pobliskie urzadzenia Bluetooth dzieki radarowi odleglosci w czasie rzeczywistym.", selectorTexts: { ".nav a:nth-child(1)": "Strona glowna", ".nav a:nth-child(2)": "Aplikacje", ".nav a:nth-child(4)": "Przypadki uzycia", ".nav a:nth-child(5)": "Funkcje", ".nav a:nth-child(6)": "Jak to dziala", ".nav a:nth-child(8)": "Prywatnosc", "#hero-title": "Znajdz zgubione AirPods i urzadzenia Bluetooth szybko i prosto.", ".cta-row .btn-primary": "Pobierz z App Store", "#use-cases-title": "Typowe scenariusze zagubienia urzadzen", "#features-title": "Moduly stworzone do szybkiego odzyskiwania", "#how-title": "Jak dziala Find AI", "#faq-title": "Najczesciej zadawane pytania" } }
      ,"cs-CZ": { pageTitle: "Find AI | Najdete ztracene AirPods a Bluetooth zarizeni", metaDescription: "Find AI pomaha najit ztracene AirPods a blizka Bluetooth zarizeni pomoci radaru vzdalenosti v realnem case.", selectorTexts: { ".nav a:nth-child(1)": "Domu", ".nav a:nth-child(2)": "Aplikace", ".nav a:nth-child(4)": "Pripady pouziti", ".nav a:nth-child(5)": "Funkce", ".nav a:nth-child(6)": "Jak to funguje", ".nav a:nth-child(8)": "Soukromi", "#hero-title": "Najdete ztracene AirPods a Bluetooth zarizeni jednoduse a rychle.", ".cta-row .btn-primary": "Stahnout z App Store", "#use-cases-title": "Bezne scenare ztracenych zarizeni", "#features-title": "Moduly pro rychlejsi obnovu", "#how-title": "Jak Find AI funguje", "#faq-title": "Caste dotazy" } }
    },
    "/ai-cleanup-pro/": {
      "fr-FR": { pageTitle: "AI Cleanup PRO | Super Cleaner pour iPhone", metaDescription: "AI Cleanup PRO nettoie photos en double, videos lourdes et contacts sur iPhone avec une approche locale et privee.", selectorTexts: { ".nav a:nth-child(1)": "Accueil", ".nav a:nth-child(2)": "Apps", ".nav a:nth-child(4)": "Fonctionnalites", ".nav a:nth-child(6)": "Confidentialite", "h1": "AI Cleanup PRO - Super Cleaner pour iPhone", ".cta-row .btn-primary": "Telecharger sur l’App Store", ".cta-row .btn-secondary": "Explorer les fonctions", "#features h2": "Des outils puissants pour la vraie pression de stockage iPhone", "#workflow h2": "Trois etapes pour retrouver de l’espace", "#faq h2": "Questions frequentes", ".cta h2": "Pret a nettoyer votre iPhone plus vite ?", ".cta .btn-primary": "Telecharger sur l’App Store", ".cta .btn-secondary": "Lire la politique de confidentialite" } },
      "ro-RO": { pageTitle: "AI Cleanup PRO | Super Cleaner pentru iPhone", metaDescription: "AI Cleanup PRO curata poze duplicate, videoclipuri mari si contacte pe iPhone cu procesare locala si orientata spre confidentialitate.", selectorTexts: { ".nav a:nth-child(1)": "Acasa", ".nav a:nth-child(2)": "Aplicatii", ".nav a:nth-child(4)": "Functii", ".nav a:nth-child(6)": "Confidentialitate", "h1": "AI Cleanup PRO - Super Cleaner pentru iPhone", ".cta-row .btn-primary": "Descarca din App Store", ".cta-row .btn-secondary": "Exploreaza functiile", "#features h2": "Instrumente puternice pentru presiunea reala a stocarii pe iPhone", "#workflow h2": "Trei pasi catre mai mult spatiu", "#faq h2": "Intrebari frecvente", ".cta h2": "Gata sa cureti iPhone-ul mai repede?" } },
      "de-DE": { pageTitle: "AI Cleanup PRO | Super Cleaner fur iPhone", metaDescription: "AI Cleanup PRO bereinigt doppelte Fotos, grosse Videos und Kontakte auf dem iPhone mit lokalem Datenschutzfokus.", selectorTexts: { ".nav a:nth-child(1)": "Start", ".nav a:nth-child(2)": "Apps", ".nav a:nth-child(4)": "Funktionen", ".nav a:nth-child(6)": "Datenschutz", "h1": "AI Cleanup PRO - Super Cleaner fur das iPhone", ".cta-row .btn-primary": "Im App Store laden", ".cta-row .btn-secondary": "Funktionen ansehen", "#features h2": "Leistungsstarke Tools fur echten iPhone-Speicherdruck", "#workflow h2": "Drei Schritte zu mehr freiem Speicher", "#faq h2": "Haufige Fragen", ".cta h2": "Bereit, Ihr iPhone schneller zu bereinigen?" } },
      "es-ES": { pageTitle: "AI Cleanup PRO | Super Cleaner para iPhone", metaDescription: "AI Cleanup PRO limpia fotos duplicadas, videos pesados y contactos en iPhone con procesamiento local y privado.", selectorTexts: { ".nav a:nth-child(1)": "Inicio", ".nav a:nth-child(2)": "Apps", ".nav a:nth-child(4)": "Funciones", ".nav a:nth-child(6)": "Privacidad", "h1": "AI Cleanup PRO - Super Cleaner para iPhone", ".cta-row .btn-primary": "Descargar en App Store", ".cta-row .btn-secondary": "Explorar funciones", "#features h2": "Herramientas potentes para la presion real del almacenamiento del iPhone", "#workflow h2": "Tres pasos para recuperar espacio", "#faq h2": "Preguntas frecuentes", ".cta h2": "Listo para limpiar tu iPhone mas rapido?" } },
      "it-IT": { pageTitle: "AI Cleanup PRO | Super Cleaner per iPhone", metaDescription: "AI Cleanup PRO pulisce foto duplicate, video pesanti e contatti su iPhone con elaborazione locale e privata.", selectorTexts: { ".nav a:nth-child(1)": "Home", ".nav a:nth-child(2)": "App", ".nav a:nth-child(4)": "Funzioni", ".nav a:nth-child(6)": "Privacy", "h1": "AI Cleanup PRO - Super Cleaner per iPhone", ".cta-row .btn-primary": "Scarica su App Store", ".cta-row .btn-secondary": "Esplora le funzioni", "#features h2": "Strumenti potenti per la vera pressione di archiviazione su iPhone", "#workflow h2": "Tre passaggi per recuperare spazio", "#faq h2": "Domande frequenti", ".cta h2": "Pronto a pulire il tuo iPhone piu velocemente?" } },
      "pt-BR": { pageTitle: "AI Cleanup PRO | Super Cleaner para iPhone", metaDescription: "AI Cleanup PRO limpa fotos duplicadas, videos pesados e contatos no iPhone com processamento local e privado.", selectorTexts: { ".nav a:nth-child(1)": "Inicio", ".nav a:nth-child(2)": "Apps", ".nav a:nth-child(4)": "Recursos", ".nav a:nth-child(6)": "Privacidade", "h1": "AI Cleanup PRO - Super Cleaner para iPhone", ".cta-row .btn-primary": "Baixar na App Store", ".cta-row .btn-secondary": "Explorar recursos", "#features h2": "Ferramentas poderosas para a pressao real de armazenamento do iPhone", "#workflow h2": "Tres etapas para recuperar espaco", "#faq h2": "Perguntas frequentes", ".cta h2": "Pronto para limpar seu iPhone mais rapido?" } },
      "nl-NL": { pageTitle: "AI Cleanup PRO | Super Cleaner voor iPhone", metaDescription: "AI Cleanup PRO ruimt dubbele foto’s, zware video’s en contacten op met lokale en privacygerichte verwerking.", selectorTexts: { ".nav a:nth-child(1)": "Home", ".nav a:nth-child(2)": "Apps", ".nav a:nth-child(4)": "Functies", ".nav a:nth-child(6)": "Privacy", "h1": "AI Cleanup PRO - Super Cleaner voor iPhone", ".cta-row .btn-primary": "Download in de App Store", ".cta-row .btn-secondary": "Functies bekijken", "#features h2": "Krachtige tools voor echte iPhone-opslagdruk", "#workflow h2": "Drie stappen naar meer vrije ruimte", "#faq h2": "Veelgestelde vragen", ".cta h2": "Klaar om je iPhone sneller op te schonen?" } },
      "sv-SE": { pageTitle: "AI Cleanup PRO | Super Cleaner for iPhone", metaDescription: "AI Cleanup PRO rensar dubbla bilder, stora videor och kontakter pa iPhone med lokal och integritetsfokuserad bearbetning.", selectorTexts: { ".nav a:nth-child(1)": "Hem", ".nav a:nth-child(2)": "Appar", ".nav a:nth-child(4)": "Funktioner", ".nav a:nth-child(6)": "Integritet", "h1": "AI Cleanup PRO - Super Cleaner for iPhone", ".cta-row .btn-primary": "Hamta i App Store", ".cta-row .btn-secondary": "Utforska funktioner", "#features h2": "Kraftfulla verktyg for verkligt lagringstryck pa iPhone", "#workflow h2": "Tre steg till mer fritt utrymme", "#faq h2": "Vanliga fragor", ".cta h2": "Redo att rensa din iPhone snabbare?" } },
      "pl-PL": { pageTitle: "AI Cleanup PRO | Super Cleaner dla iPhone", metaDescription: "AI Cleanup PRO czyści duplikaty zdjęć, ciężkie filmy i kontakty na iPhonie z lokalnym, prywatnym przetwarzaniem.", selectorTexts: { ".nav a:nth-child(1)": "Strona glowna", ".nav a:nth-child(2)": "Aplikacje", ".nav a:nth-child(4)": "Funkcje", ".nav a:nth-child(6)": "Prywatnosc", "h1": "AI Cleanup PRO - Super Cleaner dla iPhone", ".cta-row .btn-primary": "Pobierz z App Store", ".cta-row .btn-secondary": "Poznaj funkcje", "#features h2": "Zaawansowane narzedzia na realna presje pamieci iPhone’a", "#workflow h2": "Trzy kroki do odzyskania miejsca", "#faq h2": "Najczesciej zadawane pytania", ".cta h2": "Gotowy, aby szybciej wyczyscic iPhone’a?" } },
      "cs-CZ": { pageTitle: "AI Cleanup PRO | Super Cleaner pro iPhone", metaDescription: "AI Cleanup PRO cisti duplicitni fotky, velka videa a kontakty na iPhonu s lokalnim a soukromym zpracovanim.", selectorTexts: { ".nav a:nth-child(1)": "Domu", ".nav a:nth-child(2)": "Aplikace", ".nav a:nth-child(4)": "Funkce", ".nav a:nth-child(6)": "Soukromi", "h1": "AI Cleanup PRO - Super Cleaner pro iPhone", ".cta-row .btn-primary": "Stahnout z App Store", ".cta-row .btn-secondary": "Prozkoumat funkce", "#features h2": "Silne nastroje pro skutecny tlak na uloziste iPhonu", "#workflow h2": "Tri kroky k vice volnemu mistu", "#faq h2": "Caste dotazy", ".cta h2": "Pripraven cistit iPhone rychleji?" } }
    },
    "/bluetoothexplorer/": {
      "fr-FR": { pageTitle: "Bluetooth Explorer | Terminal IA pour iPhone et iPad", metaDescription: "Bluetooth Explorer permet de scanner des appareils BLE, d’inspecter GATT, d’envoyer des commandes et d’analyser les logs sur iPhone et iPad.", selectorTexts: { ".nav a:nth-child(1)": "Accueil", ".nav a:nth-child(2)": "Apps", ".nav a:nth-child(4)": "Documentation", ".nav a:nth-child(5)": "Fonctionnalites", ".nav a:nth-child(6)": "Cas d’usage", ".nav a:nth-child(7)": "Workflow", ".nav a:nth-child(9)": "Telecharger", "h1": "Bluetooth Explorer : terminal IA pour iPhone et iPad", ".cta-row .btn-primary": "Telecharger sur l’App Store", ".cta-row .btn-secondary": "Ouvrir le guide utilisateur", "#features h2": "Fonctions cles pour le developpement BLE et le debug terrain", "#use-cases h2": "Cas d’usage", "#workflow h2": "Workflow en 3 etapes", "#faq h2": "Questions frequentes", ".install h2": "Installer Bluetooth Explorer : terminal IA", ".install .btn-primary": "Telecharger sur l’App Store" } },
      "ro-RO": { pageTitle: "Bluetooth Explorer | Terminal AI pentru iPhone si iPad", metaDescription: "Bluetooth Explorer scaneaza dispozitive BLE, inspecteaza GATT, trimite comenzi si analizeaza loguri pe iPhone si iPad.", selectorTexts: { ".nav a:nth-child(1)": "Acasa", ".nav a:nth-child(2)": "Aplicatii", ".nav a:nth-child(4)": "Documentatie", ".nav a:nth-child(5)": "Functii", ".nav a:nth-child(6)": "Cazuri de utilizare", ".nav a:nth-child(7)": "Flux", ".nav a:nth-child(9)": "Descarca", "h1": "Bluetooth Explorer: terminal AI pentru iPhone si iPad", ".cta-row .btn-primary": "Descarca din App Store", ".cta-row .btn-secondary": "Deschide ghidul utilizatorului", "#features h2": "Functii cheie pentru dezvoltare BLE si depanare in teren", "#use-cases h2": "Cazuri de utilizare", "#workflow h2": "Flux in 3 pasi", "#faq h2": "Intrebari frecvente", ".install h2": "Instaleaza Bluetooth Explorer" } },
      "de-DE": { pageTitle: "Bluetooth Explorer | KI-Terminal fur iPhone und iPad", metaDescription: "Bluetooth Explorer scannt BLE-Gerate, inspiziert GATT, sendet Befehle und analysiert Logs auf iPhone und iPad.", selectorTexts: { ".nav a:nth-child(1)": "Start", ".nav a:nth-child(2)": "Apps", ".nav a:nth-child(4)": "Dokumentation", ".nav a:nth-child(5)": "Funktionen", ".nav a:nth-child(6)": "Anwendungsfalle", ".nav a:nth-child(7)": "Workflow", ".nav a:nth-child(9)": "Download", "h1": "Bluetooth Explorer: KI-Terminal fur iPhone und iPad", ".cta-row .btn-primary": "Im App Store laden", ".cta-row .btn-secondary": "Benutzerhandbuch offnen", "#features h2": "Wichtige Funktionen fur BLE-Entwicklung und Felddiagnose", "#use-cases h2": "Anwendungsfalle", "#workflow h2": "3-Schritte-Workflow", "#faq h2": "Haufige Fragen", ".install h2": "Bluetooth Explorer installieren" } },
      "es-ES": { pageTitle: "Bluetooth Explorer | Terminal IA para iPhone y iPad", metaDescription: "Bluetooth Explorer escanea dispositivos BLE, inspecciona GATT, envia comandos y analiza registros en iPhone y iPad.", selectorTexts: { ".nav a:nth-child(1)": "Inicio", ".nav a:nth-child(2)": "Apps", ".nav a:nth-child(4)": "Documentacion", ".nav a:nth-child(5)": "Funciones", ".nav a:nth-child(6)": "Casos de uso", ".nav a:nth-child(7)": "Flujo", ".nav a:nth-child(9)": "Descargar", "h1": "Bluetooth Explorer: terminal IA para iPhone y iPad", ".cta-row .btn-primary": "Descargar en App Store", ".cta-row .btn-secondary": "Abrir guia de usuario", "#features h2": "Funciones clave para desarrollo BLE y depuracion en campo", "#use-cases h2": "Casos de uso", "#workflow h2": "Flujo de 3 pasos", "#faq h2": "Preguntas frecuentes", ".install h2": "Instalar Bluetooth Explorer" } },
      "it-IT": { pageTitle: "Bluetooth Explorer | Terminale AI per iPhone e iPad", metaDescription: "Bluetooth Explorer scansiona dispositivi BLE, ispeziona GATT, invia comandi e analizza log su iPhone e iPad.", selectorTexts: { ".nav a:nth-child(1)": "Home", ".nav a:nth-child(2)": "App", ".nav a:nth-child(4)": "Documentazione", ".nav a:nth-child(5)": "Funzioni", ".nav a:nth-child(6)": "Casi d’uso", ".nav a:nth-child(7)": "Workflow", ".nav a:nth-child(9)": "Scarica", "h1": "Bluetooth Explorer: terminale AI per iPhone e iPad", ".cta-row .btn-primary": "Scarica su App Store", ".cta-row .btn-secondary": "Apri la guida utente", "#features h2": "Funzioni chiave per sviluppo BLE e debug sul campo", "#use-cases h2": "Casi d’uso", "#workflow h2": "Workflow in 3 passaggi", "#faq h2": "Domande frequenti", ".install h2": "Installa Bluetooth Explorer" } },
      "pt-BR": { pageTitle: "Bluetooth Explorer | Terminal de IA para iPhone e iPad", metaDescription: "Bluetooth Explorer escaneia dispositivos BLE, inspeciona GATT, envia comandos e analisa logs no iPhone e iPad.", selectorTexts: { ".nav a:nth-child(1)": "Inicio", ".nav a:nth-child(2)": "Apps", ".nav a:nth-child(4)": "Documentacao", ".nav a:nth-child(5)": "Recursos", ".nav a:nth-child(6)": "Casos de uso", ".nav a:nth-child(7)": "Fluxo", ".nav a:nth-child(9)": "Baixar", "h1": "Bluetooth Explorer: terminal de IA para iPhone e iPad", ".cta-row .btn-primary": "Baixar na App Store", ".cta-row .btn-secondary": "Abrir guia do usuario", "#features h2": "Recursos principais para desenvolvimento BLE e depuracao em campo", "#use-cases h2": "Casos de uso", "#workflow h2": "Fluxo em 3 etapas", "#faq h2": "Perguntas frequentes", ".install h2": "Instale o Bluetooth Explorer" } },
      "nl-NL": { pageTitle: "Bluetooth Explorer | AI-terminal voor iPhone en iPad", metaDescription: "Bluetooth Explorer scant BLE-apparaten, inspecteert GATT, verstuurt commando’s en analyseert logs op iPhone en iPad.", selectorTexts: { ".nav a:nth-child(1)": "Home", ".nav a:nth-child(2)": "Apps", ".nav a:nth-child(4)": "Documentatie", ".nav a:nth-child(5)": "Functies", ".nav a:nth-child(6)": "Gebruiksscenario’s", ".nav a:nth-child(7)": "Workflow", ".nav a:nth-child(9)": "Download", "h1": "Bluetooth Explorer: AI-terminal voor iPhone en iPad", ".cta-row .btn-primary": "Download in de App Store", ".cta-row .btn-secondary": "Open gebruikershandleiding", "#features h2": "Belangrijkste functies voor BLE-ontwikkeling en velddebugging", "#use-cases h2": "Gebruiksscenario’s", "#workflow h2": "Workflow in 3 stappen", "#faq h2": "Veelgestelde vragen", ".install h2": "Installeer Bluetooth Explorer" } },
      "sv-SE": { pageTitle: "Bluetooth Explorer | AI-terminal for iPhone och iPad", metaDescription: "Bluetooth Explorer skannar BLE-enheter, inspekterar GATT, skickar kommandon och analyserar loggar pa iPhone och iPad.", selectorTexts: { ".nav a:nth-child(1)": "Hem", ".nav a:nth-child(2)": "Appar", ".nav a:nth-child(4)": "Dokumentation", ".nav a:nth-child(5)": "Funktioner", ".nav a:nth-child(6)": "Anvandningsfall", ".nav a:nth-child(7)": "Workflow", ".nav a:nth-child(9)": "Ladda ner", "h1": "Bluetooth Explorer: AI-terminal for iPhone och iPad", ".cta-row .btn-primary": "Hamta i App Store", ".cta-row .btn-secondary": "Oppna användarguide", "#features h2": "Nyckelfunktioner for BLE-utveckling och felsokning i falt", "#use-cases h2": "Anvandningsfall", "#workflow h2": "Workflow i 3 steg", "#faq h2": "Vanliga fragor", ".install h2": "Installera Bluetooth Explorer" } },
      "pl-PL": { pageTitle: "Bluetooth Explorer | Terminal AI dla iPhone i iPad", metaDescription: "Bluetooth Explorer skanuje urzadzenia BLE, sprawdza GATT, wysyla komendy i analizuje logi na iPhonie i iPadzie.", selectorTexts: { ".nav a:nth-child(1)": "Strona glowna", ".nav a:nth-child(2)": "Aplikacje", ".nav a:nth-child(4)": "Dokumentacja", ".nav a:nth-child(5)": "Funkcje", ".nav a:nth-child(6)": "Przypadki uzycia", ".nav a:nth-child(7)": "Workflow", ".nav a:nth-child(9)": "Pobierz", "h1": "Bluetooth Explorer: terminal AI dla iPhone i iPad", ".cta-row .btn-primary": "Pobierz z App Store", ".cta-row .btn-secondary": "Otworz przewodnik uzytkownika", "#features h2": "Kluczowe funkcje dla rozwoju BLE i debugowania w terenie", "#use-cases h2": "Przypadki uzycia", "#workflow h2": "Workflow w 3 krokach", "#faq h2": "Najczesciej zadawane pytania", ".install h2": "Zainstaluj Bluetooth Explorer" } },
      "cs-CZ": { pageTitle: "Bluetooth Explorer | AI terminal pro iPhone a iPad", metaDescription: "Bluetooth Explorer skenuje BLE zarizeni, kontroluje GATT, posila prikazy a analyzuje logy na iPhonu a iPadu.", selectorTexts: { ".nav a:nth-child(1)": "Domu", ".nav a:nth-child(2)": "Aplikace", ".nav a:nth-child(4)": "Dokumentace", ".nav a:nth-child(5)": "Funkce", ".nav a:nth-child(6)": "Pripady pouziti", ".nav a:nth-child(7)": "Workflow", ".nav a:nth-child(9)": "Stahnout", "h1": "Bluetooth Explorer: AI terminal pro iPhone a iPad", ".cta-row .btn-primary": "Stahnout z App Store", ".cta-row .btn-secondary": "Otevrit uzivatelskou prirucku", "#features h2": "Klicove funkce pro BLE vyvoj a terénni debug", "#use-cases h2": "Pripady pouziti", "#workflow h2": "Workflow ve 3 krocich", "#faq h2": "Caste dotazy", ".install h2": "Nainstalujte Bluetooth Explorer" } }
    }
  });

  const DEEP_PAGE_TRANSLATION_OVERRIDES = {
    "/aifind/": {
      "fr-FR": {
        selectorTexts: {
          ".proof-list li": ["Retrouvez plus vite AirPods, écouteurs et Beats.", "Radar de distance en temps réel pour les scans Bluetooth à proximité.", "Dernière position connue pour les appareils hors de portée.", "Traitement local des données pour une utilisation centrée sur la confidentialité."],
          ".card-note": "Le retour radar en temps réel vous aide à passer d’un signal faible à une proximité réelle sans tâtonner.",
          "#use-cases .section-head p": "Nous optimisons ici les scénarios de récupération les plus fréquents : AirPods perdus à la maison, écouteurs oubliés au bureau et casques manquants pendant les déplacements.",
          "#use-cases .panel h3": ["AirPods à la maison", "Écouteurs dans des espaces partagés", "Récupération hors de portée"],
          "#use-cases .panel p": ["Utilisez le scanner pour isoler le signal de vos AirPods et avancez vers la lecture de distance la plus forte.", "Filtrez le bruit des appareils voisins et épinglez vos appareils connus pour les retrouver plus vite dans les zones encombrées.", "Ouvrez l’indice de dernière position enregistré sur l’appareil, revenez à ce point et relancez le scan quand l’appareil est de nouveau proche."],
          "#features .section-head p": "Le flux de l’app suit une séquence pratique : détecter, trier, se déplacer et confirmer. Chaque écran réduit le temps de recherche sans exposer vos données à des traceurs tiers.",
          "#features .panel h3": ["Radar de distance en temps réel", "Regroupement intelligent des appareils", "Épingler et prioriser", "Mémoire de dernière position"],
          "#features .panel p": ["Convertit la puissance du signal RSSI en indications pratiques proche/loin pour réduire rapidement la distance.", "Sépare les appareils connus des signaux inconnus pour rester concentré sur votre cible au lieu de faire défiler du bruit.", "Gardez vos écouteurs et casques les plus importants épinglés pour un accès immédiat lors des prochains scans.", "Enregistre localement la dernière position et l’horodatage pour soutenir les flux de récupération hors ligne."],
          ".steps li h3": ["Scanner les appareils Bluetooth proches", "Sélectionner et verrouiller votre cible", "Utiliser les données de dernière position si nécessaire"],
          ".steps li p": ["Ouvrez Find AI et lancez un scan en direct pour repérer les AirPods, écouteurs, Beats et autres cibles Bluetooth à proximité.", "Choisissez l’appareil visé et utilisez la force du signal et les indices de distance pour avancer dans la bonne direction.", "Si l’appareil est hors de portée, revenez au dernier emplacement détecté et reprenez le scan pour terminer la récupération."],
          ".faq-list summary": ["Find AI peut-il m’aider à retrouver des AirPods perdus ?", "Find AI fonctionne-t-il avec des écouteurs ou casques non Apple ?", "Que se passe-t-il si mon appareil est hors de portée ?", "Find AI est-il privé et sécurisé ?"],
          ".faq-list details p": ["Oui. Find AI scanne les signaux Bluetooth proches et affiche un radar de distance en direct pour vous guider vers vos AirPods ou écouteurs perdus.", "Oui. Find AI fonctionne avec de nombreux appareils Bluetooth comme des écouteurs, casques et accessoires compatibles Beats lorsqu’ils sont proches et détectables.", "Find AI stocke la dernière heure et le dernier emplacement vus sur l’appareil, afin que vous puissiez revenir dans cette zone et continuer le scan.", "Find AI traite les données de recherche Bluetooth sur l’appareil. Selon la politique de confidentialité, ces données ne sont pas envoyées pour de l’analytics ou l’entraînement de modèles."] ,
          ".final-cta p": "Installez Find AI et lancez votre récupération Bluetooth en moins d’une minute.",
          "footer .footer-links a:nth-child(1)": "Accueil VelocAI",
          "footer .footer-links a:nth-child(2)": "Toutes les apps VelocAI",
          "footer .footer-links a:nth-child(3)": "Blog VelocAI",
          "footer .footer-links a:nth-child(6)": "Politique de confidentialité Find AI",
          "footer .footer-links a:nth-child(7)": "Contact : vp@velocai.net"
        }
      },
      "de-DE": {
        selectorTexts: {
          ".proof-list li": ["AirPods, Earbuds und Beats schneller finden.", "Live-Distanzradar für Bluetooth-Scans in der Nähe.", "Zuletzt gesehener Standort für Geräte außerhalb der Reichweite.", "Lokale Datenverarbeitung für datenschutzorientierte Nutzung."],
          ".card-note": "Das Live-Radar hilft Ihnen dabei, ohne Rätselraten von einem schwachen Signal zur tatsächlichen Nähe zu gelangen.",
          "#use-cases .panel h3": ["AirPods zu Hause", "Earbuds in gemeinsam genutzten Räumen", "Wiederfinden außerhalb der Reichweite"],
          "#features .panel h3": ["Live-Distanzradar", "Intelligente Geräte-Gruppierung", "Anheften und priorisieren", "Zuletzt-gesehen-Speicher"],
          ".steps li h3": ["Bluetooth-Geräte in der Nähe scannen", "Ziel auswählen und fixieren", "Bei Bedarf zuletzt gesehene Daten nutzen"],
          ".faq-list summary": ["Kann Find AI mir helfen, verlorene AirPods zu finden?", "Funktioniert Find AI auch mit Nicht-Apple-Earbuds oder Kopfhörern?", "Was passiert, wenn mein Gerät außer Reichweite ist?", "Ist Find AI privat und sicher?"],
          ".final-cta p": "Installieren Sie Find AI und starten Sie Ihren Bluetooth-Findefluss in weniger als einer Minute."
        }
      },
      "es-ES": {
        selectorTexts: {
          ".proof-list li": ["Encuentra AirPods, auriculares y Beats más rápido.", "Radar de distancia en tiempo real para escaneos Bluetooth cercanos.", "Última ubicación vista para dispositivos fuera de alcance.", "Procesamiento local de datos para un uso centrado en la privacidad."],
          ".card-note": "La respuesta del radar en tiempo real te ayuda a pasar de una señal débil a la proximidad sin adivinar.",
          "#use-cases .panel h3": ["AirPods en casa", "Auriculares en espacios compartidos", "Recuperación fuera de alcance"],
          "#features .panel h3": ["Radar de distancia en tiempo real", "Agrupación inteligente de dispositivos", "Fijar y priorizar", "Memoria de última ubicación"],
          ".steps li h3": ["Escanea dispositivos Bluetooth cercanos", "Selecciona y fija tu objetivo", "Usa los datos de última ubicación cuando sea necesario"],
          ".faq-list summary": ["¿Find AI puede ayudarme a encontrar AirPods perdidos?", "¿Find AI funciona con auriculares o cascos que no sean Apple?", "¿Qué ocurre cuando mi dispositivo está fuera de alcance?", "¿Find AI es privado y seguro?"],
          ".final-cta p": "Instala Find AI y comienza tu flujo de recuperación Bluetooth en menos de un minuto."
        }
      }
    },
    "/ai-cleanup-pro/": {
      "fr-FR": {
        selectorTexts: {
          ".lede": "AI Cleanup PRO est conçu pour les personnes qui ont besoin d’un flux fiable de nettoyage photo sur iPhone, sans tri manuel interminable. De l’automatisation des doublons à la gestion intelligente des vidéos et des contacts, l’app aide à récupérer de l’espace chaque semaine avant que cela ne devienne urgent.",
          ".hero-points li": ["App de nettoyage IA pour iPhone et iPad", "Nettoyeur de photos en double avec revue rapide", "Réduire la pression de stockage vidéo sur iPhone", "Organiser les contacts et supprimer les doublons"],
          ".hero-card-note span": ["Examinez des photos similaires, réduisez les vidéos trop lourdes et supprimez les contacts en double dans un seul flux clair.", "AI Cleanup PRO garde chaque étape visible afin que vous puissiez prendre des décisions fiables sans supprimer à l’aveugle."],
          ".feature-card h3": ["Nettoyeur de photos en double avec regroupement intelligent", "Nettoyer les vidéos iPhone avec des parcours de compression", "Organiser les contacts et fusionner les entrées répétées", "Conception de nettoyage IA axée confidentialité"],
          ".workflow .step h3": ["Scanner les catégories", "Examiner les suggestions", "Libérer de l’espace"],
          ".faq details summary": ["Que peut nettoyer AI Cleanup PRO sur iPhone ?", "Est-ce un nettoyeur de doublons adapté à un usage quotidien ?", "Comment fonctionne le nettoyage vidéo sur iPhone ?", "L’app peut-elle aussi organiser les contacts ?", "Où lire la politique de données ?"],
          ".faq details p": ["L’app aide pour les photos identiques ou similaires, les grandes vidéos et les contacts répétés afin de récupérer du stockage avec moins d’actions manuelles.", "Oui. Elle est pensée pour un nettoyage continu, afin de traiter les nouveaux doublons en sessions courtes au lieu d’attendre une urgence de stockage.", "L’app met d’abord en avant les grandes vidéos puis vous laisse décider quoi supprimer ou compresser selon vos priorités de qualité et d’espace.", "Oui. Vous pouvez examiner les fiches en double et fusionner les entrées répétées dans des profils plus propres et fiables.", "Vous pouvez consulter les détails sur la page de politique de confidentialité d’AI Cleanup PRO."],
          ".cta-panel p": "Commencez à utiliser AI Cleanup PRO pour supprimer les doublons, alléger les vidéos lourdes et garder vos contacts organisés avec des flux respectueux de la confidentialité.",
          ".footer-links a:nth-child(2)": "Toutes les apps VelocAI",
          ".footer-links a:nth-child(3)": "Blog VelocAI"
        }
      },
      "de-DE": {
        selectorTexts: {
          ".hero-points li": ["KI-Cleanup-App für iPhone und iPad", "Doppel-Foto-Bereiniger mit schneller Prüfung", "Videospeicherdruck auf dem iPhone reduzieren", "Kontakte organisieren und Duplikate entfernen"],
          ".workflow .step h3": ["Kategorien scannen", "Vorschläge prüfen", "Speicher freigeben"],
          ".faq details summary": ["Was kann AI Cleanup PRO auf dem iPhone bereinigen?", "Ist dies ein Duplikat-Fotobereiniger für den täglichen Einsatz?", "Wie funktioniert der iPhone-Video-Cleanup-Workflow?", "Kann die App auch Kontakte organisieren?", "Wo kann ich die Datenrichtlinie lesen?"]
        }
      },
      "es-ES": {
        selectorTexts: {
          ".hero-points li": ["App de limpieza con IA para iPhone y iPad", "Limpieza de fotos duplicadas con revisión rápida", "Reducir la presión del almacenamiento de vídeos en iPhone", "Organizar contactos y eliminar duplicados"],
          ".workflow .step h3": ["Escanear categorías", "Revisar sugerencias", "Liberar espacio"],
          ".faq details summary": ["¿Qué puede limpiar AI Cleanup PRO en iPhone?", "¿Es un limpiador de fotos duplicadas para uso diario?", "¿Cómo funciona el flujo para limpiar vídeos en iPhone?", "¿La app también puede organizar contactos?", "¿Dónde puedo leer la política de datos?"]
        }
      }
    },
    "/bluetoothexplorer/": {
      "fr-FR": {
        selectorTexts: {
          ".hero-points li": ["Scannez rapidement les périphériques BLE proches.", "Inspectez services et caractéristiques GATT avec état de connexion en direct.", "Envoyez des paquets hex/text/binary/decimal depuis un seul terminal Bluetooth.", "Exportez des journaux chronologiques pour le debug firmware et l’assurance qualité.", "Utilisez le diagnostic IA pour prioriser les causes probables.", "Retrouvez le matériel sur le terrain avec une navigation assistée par carte."],
          ".hero-card-note span": ["Vue d’ensemble de connexion, arbre des services GATT et accès instantané aux logs, à la navigation et au diagnostic IA."],
          "#features .panel h3": ["Scanner BLE", "Inspecteur GATT", "Terminal Bluetooth", "Bibliothèque de paquets", "Chronologie des logs", "Diagnostic IA"],
          "#use-cases .panel h3": ["Initialisation firmware", "Dépannage terrain", "Runs de régression QA"],
          "#workflow .step h3": ["Scanner et connecter", "Lancer les tests de commandes", "Analyser et exporter"],
          "#faq .faq-item h3": ["À quoi sert Bluetooth Explorer ?", "Bluetooth Explorer prend-il en charge les commandes hex ?", "Puis-je inspecter les services et caractéristiques GATT ?", "Comment l’app aide-t-elle au dépannage BLE ?", "Bluetooth Explorer traite-t-il les données de debug dans le cloud ?", "Où trouver le guide utilisateur et la politique de confidentialité ?"],
          ".changelog li": ["Flux de scan BLE amélioré pour une sélection plus rapide de la cible en environnement dense.", "Guidage de workflow paquet étendu pour des vérifications QA et régression plus répétables.", "Recommandations de debug IA affinées pour prioriser les actions suivantes les plus utiles."],
          ".helper-links a:nth-child(1)": "Guide utilisateur anglais",
          ".helper-links a:nth-child(2)": "Guide utilisateur chinois",
          ".helper-links a:nth-child(3)": "Index de documentation",
          ".helper-links a:nth-child(4)": "Politique de confidentialité"
        }
      },
      "de-DE": {
        selectorTexts: {
          ".hero-points li": ["BLE-Peripheriegeräte in der Nähe schnell scannen und filtern.", "GATT-Services und -Merkmale mit Live-Verbindungsstatus prüfen.", "Hex-/Text-/Binary-/Decimal-Pakete aus einer Terminalansicht senden.", "Zeitachsen-Logs für Firmware-Debugging und QA exportieren.", "KI-Diagnostik nutzen, um wahrscheinliche Ursachen zu priorisieren.", "Hardware vor Ort mit kartenunterstützter Navigation finden."],
          "#features .panel h3": ["BLE-Scanner", "GATT-Inspektor", "Bluetooth-Terminal", "Paketbibliothek", "Log-Zeitleiste", "KI-Diagnostik"],
          "#use-cases .panel h3": ["Firmware-Inbetriebnahme", "Fehlersuche im Feld", "QA-Regressionsläufe"],
          "#workflow .step h3": ["Scannen und verbinden", "Befehlstests ausführen", "Analysieren und exportieren"],
          "#faq .faq-item h3": ["Wofür wird Bluetooth Explorer verwendet?", "Unterstützt Bluetooth Explorer Hex-Terminalbefehle?", "Kann ich GATT-Services und -Merkmale inspizieren?", "Wie hilft die App bei BLE-Fehlersuche?", "Verarbeitet Bluetooth Explorer Debug-Daten in der Cloud?", "Wo finde ich Benutzerhandbuch und Datenschutzrichtlinie?"]
        }
      },
      "es-ES": {
        selectorTexts: {
          ".hero-points li": ["Escanea periféricos BLE cercanos y filtra resultados rápidamente.", "Inspecciona servicios y características GATT con estado de conexión en vivo.", "Envía paquetes en modo hex/text/binary/decimal desde una sola vista de terminal Bluetooth.", "Exporta registros temporales para depuración de firmware y evidencia de QA.", "Usa diagnóstico con IA para priorizar causas probables.", "Encuentra hardware en campo con navegación asistida por mapa."],
          "#features .panel h3": ["Escáner BLE", "Inspector GATT", "Terminal Bluetooth", "Biblioteca de paquetes", "Línea temporal de registros", "Diagnóstico IA"],
          "#use-cases .panel h3": ["Puesta en marcha de firmware", "Resolución de problemas en campo", "Ejecuciones de regresión QA"],
          "#workflow .step h3": ["Escanear y conectar", "Ejecutar pruebas de comandos", "Analizar y exportar"],
          "#faq .faq-item h3": ["¿Para qué se utiliza Bluetooth Explorer?", "¿Bluetooth Explorer admite comandos de terminal hex?", "¿Puedo inspeccionar servicios y características GATT?", "¿Cómo ayuda la app con la resolución de problemas BLE?", "¿Bluetooth Explorer procesa datos de depuración en la nube?", "¿Dónde puedo encontrar la guía de usuario y la política de privacidad?"]
        }
      }
    }
  };

  let searchData = null;
  let loadPromise = null;
  const HIGHLIGHT_QUERY_KEY = "stq";
  const HIGHLIGHT_FOCUS_KEY = "stfocus";
  const BLOG_TOPIC_TRANSLATIONS = {
    "fr-FR": {
      published: "Publié",
      topic: "Sujet",
      readArticle: "Lire l’article",
      topics: {
        "Apple Product Commentary": "Commentaire produit Apple",
        "AI Technology Outlook": "Perspectives technologiques IA",
        "Bluetooth Industry Update": "Actualité de l’industrie Bluetooth",
      },
    },
    "ro-RO": {
      published: "Publicat",
      topic: "Subiect",
      readArticle: "Citește articolul",
      topics: {
        "Apple Product Commentary": "Comentariu despre produsele Apple",
        "AI Technology Outlook": "Perspective tehnologice AI",
        "Bluetooth Industry Update": "Actualizare din industria Bluetooth",
      },
    },
    "de-DE": {
      published: "Veröffentlicht",
      topic: "Thema",
      readArticle: "Artikel lesen",
      topics: {
        "Apple Product Commentary": "Apple-Produktkommentar",
        "AI Technology Outlook": "Ausblick KI-Technologie",
        "Bluetooth Industry Update": "Bluetooth-Branchenupdate",
      },
    },
    "es-ES": {
      published: "Publicado",
      topic: "Tema",
      readArticle: "Leer artículo",
      topics: {
        "Apple Product Commentary": "Comentario de producto Apple",
        "AI Technology Outlook": "Panorama tecnológico de IA",
        "Bluetooth Industry Update": "Actualización de la industria Bluetooth",
      },
    },
    "it-IT": {
      published: "Pubblicato",
      topic: "Argomento",
      readArticle: "Leggi l’articolo",
      topics: {
        "Apple Product Commentary": "Commento prodotto Apple",
        "AI Technology Outlook": "Scenario tecnologico IA",
        "Bluetooth Industry Update": "Aggiornamento industria Bluetooth",
      },
    },
    "pt-BR": {
      published: "Publicado",
      topic: "Tema",
      readArticle: "Ler artigo",
      topics: {
        "Apple Product Commentary": "Comentário de produto Apple",
        "AI Technology Outlook": "Panorama de tecnologia de IA",
        "Bluetooth Industry Update": "Atualização da indústria Bluetooth",
      },
    },
    "nl-NL": {
      published: "Gepubliceerd",
      topic: "Onderwerp",
      readArticle: "Artikel lezen",
      topics: {
        "Apple Product Commentary": "Apple-productcommentaar",
        "AI Technology Outlook": "AI-technologievooruitblik",
        "Bluetooth Industry Update": "Bluetooth-industrie-update",
      },
    },
    "sv-SE": {
      published: "Publicerad",
      topic: "Ämne",
      readArticle: "Läs artikel",
      topics: {
        "Apple Product Commentary": "Apple-produktkommentar",
        "AI Technology Outlook": "AI-tekniköversikt",
        "Bluetooth Industry Update": "Bluetooth-branschuppdatering",
      },
    },
    "pl-PL": {
      published: "Opublikowano",
      topic: "Temat",
      readArticle: "Czytaj artykuł",
      topics: {
        "Apple Product Commentary": "Komentarz o produktach Apple",
        "AI Technology Outlook": "Przegląd technologii AI",
        "Bluetooth Industry Update": "Aktualizacja branży Bluetooth",
      },
    },
    "cs-CZ": {
      published: "Publikováno",
      topic: "Téma",
      readArticle: "Číst článek",
      topics: {
        "Apple Product Commentary": "Komentář k produktům Apple",
        "AI Technology Outlook": "Přehled AI technologií",
        "Bluetooth Industry Update": "Aktualizace Bluetooth průmyslu",
      },
    },
  };

  function normalizePath(pathname) {
    if (!pathname) return "/";
    if (pathname === "/index.html") return "/";
    return pathname.endsWith("/index.html") ? pathname.slice(0, -10) || "/" : pathname;
  }

  function isChineseLocale(locale) {
    return typeof locale === "string" && locale.toLowerCase().startsWith("zh");
  }

  function detectDocumentLocale() {
    return DEFAULT_UI_LOCALE;
  }

  function detectInitialLocale() {
    const saved = window.localStorage.getItem(STORAGE_KEY);
    if (saved === "en-US") {
      return "auto";
    }
    if (LOCALES.includes(saved)) {
      return saved;
    }
    return "auto";
  }

  function resolveUiLocale(preference) {
    if (preference === "auto") {
      return DEFAULT_UI_LOCALE;
    }
    const option = LOCALE_OPTIONS.find(function (entry) {
      return entry.value === preference;
    });
    return option && option.uiLocale ? option.uiLocale : DEFAULT_UI_LOCALE;
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

  function localizeBlogSummary(text, uiLocale) {
    const trimmed = (text || "").trim();
    if (!trimmed || uiLocale === DEFAULT_UI_LOCALE) {
      return trimmed;
    }

    const templates = {
      "fr-FR": {
        apple: "Ce commentaire sur les produits Apple analyse {subject} sous l’angle de {lens}",
        ai: "Cette perspective technologique IA analyse {subject} sous l’angle de {lens}",
        bt: "Ce commentaire sur les standards et applications Bluetooth analyse {subject} sous l’angle de {lens}",
      },
      "ro-RO": {
        apple: "Acest comentariu despre produsele Apple analizează {subject} din perspectiva {lens}",
        ai: "Această perspectivă tehnologică AI analizează {subject} din perspectiva {lens}",
        bt: "Acest comentariu despre standardele și aplicațiile Bluetooth analizează {subject} din perspectiva {lens}",
      },
      "de-DE": {
        apple: "Dieser Apple-Produktkommentar analysiert {subject} unter dem Blickwinkel von {lens}",
        ai: "Dieser Ausblick auf KI-Technologie analysiert {subject} unter dem Blickwinkel von {lens}",
        bt: "Dieser Kommentar zu Bluetooth-Standards und -Anwendungen analysiert {subject} unter dem Blickwinkel von {lens}",
      },
      "es-ES": {
        apple: "Este comentario sobre productos Apple examina {subject} desde la perspectiva de {lens}",
        ai: "Este panorama de tecnología de IA examina {subject} desde la perspectiva de {lens}",
        bt: "Este comentario sobre estándares y aplicaciones Bluetooth examina {subject} desde la perspectiva de {lens}",
      },
      "it-IT": {
        apple: "Questo commento sui prodotti Apple analizza {subject} dal punto di vista di {lens}",
        ai: "Questa panoramica sulla tecnologia IA analizza {subject} dal punto di vista di {lens}",
        bt: "Questo commento su standard e applicazioni Bluetooth analizza {subject} dal punto di vista di {lens}",
      },
      "pt-BR": {
        apple: "Este comentário sobre produtos Apple analisa {subject} pela ótica de {lens}",
        ai: "Este panorama de tecnologia de IA analisa {subject} pela ótica de {lens}",
        bt: "Este comentário sobre padrões e aplicações Bluetooth analisa {subject} pela ótica de {lens}",
      },
      "nl-NL": {
        apple: "Dit Apple-productcommentaar bekijkt {subject} vanuit het perspectief van {lens}",
        ai: "Deze AI-technologievooruitblik bekijkt {subject} vanuit het perspectief van {lens}",
        bt: "Dit commentaar over Bluetooth-standaarden en toepassingen bekijkt {subject} vanuit het perspectief van {lens}",
      },
      "sv-SE": {
        apple: "Den här Apple-produktkommentaren granskar {subject} ur perspektivet {lens}",
        ai: "Den här AI-tekniköversikten granskar {subject} ur perspektivet {lens}",
        bt: "Den här kommentaren om Bluetooth-standarder och användningar granskar {subject} ur perspektivet {lens}",
      },
      "pl-PL": {
        apple: "Ten komentarz o produktach Apple analizuje {subject} z perspektywy {lens}",
        ai: "Ten przegląd technologii AI analizuje {subject} z perspektywy {lens}",
        bt: "Ten komentarz o standardach i zastosowaniach Bluetooth analizuje {subject} z perspektywy {lens}",
      },
      "cs-CZ": {
        apple: "Tento komentář k produktům Apple analyzuje {subject} z pohledu {lens}",
        ai: "Tento přehled AI technologií analyzuje {subject} z pohledu {lens}",
        bt: "Tento komentář ke standardům a aplikacím Bluetooth analyzuje {subject} z pohledu {lens}",
      },
    };

    const localeTemplates = templates[uiLocale];
    if (!localeTemplates) {
      return trimmed;
    }

    const patterns = [
      { key: "apple", regex: /^This Apple feature and performance commentary examines (.+?) through the lens of (.+)$/ },
      { key: "ai", regex: /^This AI technology outlook examines (.+?) through the lens of (.+)$/ },
      { key: "bt", regex: /^This Bluetooth standards and application commentary examines (.+?) through the lens of (.+)$/ },
    ];

    for (let index = 0; index < patterns.length; index += 1) {
      const pattern = patterns[index];
      const match = trimmed.match(pattern.regex);
      if (match) {
        return localeTemplates[pattern.key]
          .replace("{subject}", match[1])
          .replace("{lens}", match[2]);
      }
    }

    return trimmed;
  }

  function applyBlogCardLocalization(uiLocale) {
    if (normalizePath(window.location.pathname) !== "/blog/" || uiLocale === DEFAULT_UI_LOCALE) {
      return;
    }

    const localeConfig = BLOG_TOPIC_TRANSLATIONS[uiLocale];
    if (!localeConfig) {
      return;
    }

    const articles = Array.from(document.querySelectorAll(".list article"));
    articles.forEach(function (article) {
      const summary = article.querySelector("p");
      const metaSpans = article.querySelectorAll(".meta span");
      const readLink = article.querySelector(".read");

      if (summary) {
        summary.textContent = localizeBlogSummary(summary.textContent, uiLocale);
      }

      if (metaSpans[0]) {
        metaSpans[0].textContent = (metaSpans[0].textContent || "").replace(/^Published:/, localeConfig.published + ":");
      }

      if (metaSpans[1]) {
        metaSpans[1].textContent = (metaSpans[1].textContent || "").replace(/^Topic:\s*/, localeConfig.topic + ": ");
        Object.keys(localeConfig.topics).forEach(function (topicKey) {
          if (metaSpans[1].textContent.includes(topicKey)) {
            metaSpans[1].textContent = metaSpans[1].textContent.replace(topicKey, localeConfig.topics[topicKey]);
          }
        });
      }

      if (readLink) {
        readLink.textContent = localeConfig.readArticle;
      }
    });
  }

  function getPageTranslation(path, uiLocale) {
    const baseTranslations = PAGE_TRANSLATIONS[path];
    const overrideTranslations = PAGE_TRANSLATION_OVERRIDES[path];
    const deepOverrideTranslations = DEEP_PAGE_TRANSLATION_OVERRIDES[path];
    if (!baseTranslations && !overrideTranslations && !deepOverrideTranslations) {
      return null;
    }

    const base = (baseTranslations && (baseTranslations[uiLocale] || baseTranslations[DEFAULT_UI_LOCALE])) || null;
    const override = (overrideTranslations && (overrideTranslations[uiLocale] || overrideTranslations[DEFAULT_UI_LOCALE])) || null;
    const deepOverride = (deepOverrideTranslations && (deepOverrideTranslations[uiLocale] || deepOverrideTranslations[DEFAULT_UI_LOCALE])) || null;

    if (!base && !override && !deepOverride) {
      return null;
    }

    return {
      pageTitle: (deepOverride && deepOverride.pageTitle) || (override && override.pageTitle) || (base && base.pageTitle) || "",
      metaDescription: (deepOverride && deepOverride.metaDescription) || (override && override.metaDescription) || (base && base.metaDescription) || "",
      selectorTexts: Object.assign(
        {},
        (base && base.selectorTexts) || {},
        (override && override.selectorTexts) || {},
        (deepOverride && deepOverride.selectorTexts) || {}
      ),
    };
  }

  function applyPageTranslations() {
    const path = normalizePath(window.location.pathname);
    const uiLocale = resolveUiLocale(window.localStorage.getItem(STORAGE_KEY) || detectInitialLocale());
    const translation = getPageTranslation(path, uiLocale);
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

    applyBlogCardLocalization(uiLocale);
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
      const saved = window.localStorage.getItem(STORAGE_KEY) || initialPreference;
      return saved === "en-US" ? "auto" : saved;
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
