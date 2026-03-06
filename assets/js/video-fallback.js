"use strict";

(function () {
  var embeds = document.querySelectorAll("iframe[data-video-fallback]");
  if (!embeds.length) return;

  var timeoutMs = 8000;

  embeds.forEach(function (embed) {
    var shell = embed.closest(".video-shell");
    if (!shell) return;

    var fallbackImage = shell.querySelector(".video-fallback-image");
    if (!fallbackImage) return;

    var loaded = false;
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
