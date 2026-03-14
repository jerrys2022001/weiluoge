"use strict";

(function () {
  var embeds = document.querySelectorAll("iframe[data-video-fallback]");
  if (!embeds.length) return;

  var timeoutMs = 3500;

  function toWatchUrl(embedUrl) {
    if (!embedUrl) return "";
    var match = embedUrl.match(/youtube\.com\/embed\/([^?&/]+)/i);
    if (match && match[1]) {
      return "https://www.youtube.com/watch?v=" + match[1];
    }
    return embedUrl;
  }

  embeds.forEach(function (embed) {
    var shell = embed.closest(".video-shell");
    if (!shell) return;

    var fallbackImage = shell.querySelector(".video-fallback-image");
    if (!fallbackImage) return;

    var fallbackLink = shell.querySelector(".video-fallback-link");
    var loaded = false;
    var fallbackMode = shell.getAttribute("data-video-fallback-mode") || "";
    var sourceUrl = embed.getAttribute("data-video-src") || embed.getAttribute("src") || "";
    shell.classList.add("video-fallback-active");
    embed.setAttribute("aria-hidden", "true");

    if (fallbackLink && !fallbackLink.getAttribute("href")) {
      fallbackLink.setAttribute("href", toWatchUrl(sourceUrl));
    }

    if (fallbackMode === "preview-only") {
      embed.setAttribute("tabindex", "-1");
      return;
    }

    if (!embed.getAttribute("src") && sourceUrl) {
      embed.setAttribute("src", sourceUrl);
    }

    var timer = window.setTimeout(function () {
      if (!loaded) {
        shell.classList.add("video-fallback-active");
        embed.setAttribute("aria-hidden", "true");
      }
    }, timeoutMs);

    embed.addEventListener(
      "load",
      function () {
        loaded = true;
        window.clearTimeout(timer);
        shell.classList.remove("video-fallback-active");
        embed.removeAttribute("aria-hidden");
      },
      { once: true }
    );

    embed.addEventListener(
      "error",
      function () {
        if (loaded) return;
        window.clearTimeout(timer);
        shell.classList.add("video-fallback-active");
        embed.setAttribute("aria-hidden", "true");
      },
      { once: true }
    );
  });
})();
