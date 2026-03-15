(function () {
  var toggle = document.querySelector(".va-nav-toggle");
  var navList = document.querySelector(".va-nav-list");

  function setNavOpen(isOpen) {
    if (!toggle || !navList) return;
    navList.classList.toggle("va-nav-open", isOpen);
    toggle.classList.toggle("va-nav-toggle-open", isOpen);
    toggle.setAttribute("aria-expanded", String(isOpen));
  }

  if (!toggle || !navList) {
    return;
  }

  toggle.addEventListener("click", function () {
    var isOpen = navList.classList.contains("va-nav-open");
    setNavOpen(!isOpen);
  });

  navList.addEventListener("click", function (event) {
    var target = event.target;
    if (target && target.tagName === "A") {
      setNavOpen(false);
    }
  });

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") {
      setNavOpen(false);
    }
  });

  document.addEventListener("click", function (event) {
    var target = event.target;
    if (!navList.classList.contains("va-nav-open") || !target) {
      return;
    }
    if (toggle.contains(target) || navList.contains(target)) {
      return;
    }
    setNavOpen(false);
  });

  function applyBriefFallback(image) {
    if (!image) return;
    var fallback = image.getAttribute("data-fallback-src") || "/assets/images/stock-2026-03/stock-10.jpg";
    if (image.getAttribute("src") !== fallback) {
      image.src = fallback;
      image.removeAttribute("srcset");
      return;
    }
    image.alt = "";
  }

  Array.prototype.forEach.call(document.querySelectorAll(".va-brief-thumb img"), function (image) {
    image.addEventListener("error", function () {
      applyBriefFallback(image);
    });

    if (image.complete && image.naturalWidth === 0) {
      applyBriefFallback(image);
    }
  });
})();
