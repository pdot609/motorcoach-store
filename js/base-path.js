(function () {
  var base = window.__SITE_BASE__ || "/";
  window.sitePath = function (path) {
    if (path == null || path === "") return base;
    if (/^(https?:|mailto:|tel:|data:|#|\/\/)/i.test(path)) return path;
    var normalized = String(path).charAt(0) === "/" ? path : "/" + path;
    return base.replace(/\/$/, "") + normalized;
  };
})();
