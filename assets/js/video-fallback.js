"use strict";

(function () {
  var embeds = document.querySelectorAll("iframe[data-video-fallback]");
  if (!embeds.length) return;

  function toWatchUrl(embedUrl) {
    if (!embedUrl) return "";
    var match = embedUrl.match(/youtube\.com\/embed\/([^?&/]+)/i);
    if (match && match[1]) {
      return "https://www.youtube.com/watch?v=" + match[1];
    }
    return embedUrl;
  }

  function toAutoplayUrl(embedUrl) {
    if (!embedUrl) return "";
    var separator = embedUrl.indexOf("?") === -1 ? "?" : "&";
    if (/([?&])autoplay=1(&|$)/i.test(embedUrl)) {
      return embedUrl;
    }
    return embedUrl + separator + "autoplay=1";
  }

  embeds.forEach(function (embed) {
    var shell = embed.closest(".video-shell");
    if (!shell) return;

    var fallbackImage = shell.querySelector(".video-fallback-image");
    if (!fallbackImage) return;

    var fallbackLink = shell.querySelector(".video-fallback-link");
    var sourceUrl = embed.getAttribute("data-video-src") || embed.getAttribute("src") || "";
    var activateUrl = toAutoplayUrl(sourceUrl);
    var hasActivated = false;

    if (!embed.getAttribute("data-video-src") && sourceUrl) {
      embed.setAttribute("data-video-src", sourceUrl);
    }

    shell.classList.add("video-fallback-active");
    embed.setAttribute("aria-hidden", "true");
    embed.setAttribute("tabindex", "-1");

    if (embed.getAttribute("src")) {
      embed.removeAttribute("src");
    }

    if (fallbackLink && !fallbackLink.getAttribute("href")) {
      fallbackLink.setAttribute("href", toWatchUrl(sourceUrl));
    }

    function activatePlayback(event) {
      if (event) {
        event.preventDefault();
      }
      if (hasActivated || !activateUrl) {
        return;
      }
      hasActivated = true;
      shell.classList.remove("video-fallback-active");
      embed.removeAttribute("aria-hidden");
      embed.removeAttribute("tabindex");
      embed.setAttribute("src", activateUrl);
    }

    if (fallbackLink) {
      fallbackLink.addEventListener("click", activatePlayback);
    }

    embed.addEventListener(
      "load",
      function () {
        shell.classList.remove("video-fallback-active");
        embed.removeAttribute("aria-hidden");
        embed.removeAttribute("tabindex");
      },
      { once: false }
    );

    embed.addEventListener(
      "error",
      function () {
        hasActivated = false;
        shell.classList.add("video-fallback-active");
        embed.setAttribute("aria-hidden", "true");
        embed.setAttribute("tabindex", "-1");
        embed.removeAttribute("src");
      },
      { once: false }
    );
  });
})();
