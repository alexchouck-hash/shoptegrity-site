/*
 * Cause picker for the home page.
 *
 * Picks are stored only in this browser (localStorage). Nothing is sent to a server.
 * Every storage call is wrapped in try/catch, so the page still works when storage
 * is blocked, full, or unavailable (private windows, disabled site data).
 */
(function () {
  var STORAGE_KEY = "shoptegrity.causes";

  function readSaved() {
    try {
      var raw = window.localStorage.getItem(STORAGE_KEY);
      var parsed = raw ? JSON.parse(raw) : [];
      return Array.isArray(parsed) ? parsed.filter(function (id) { return typeof id === "string"; }) : [];
    } catch (e) {
      return [];
    }
  }

  function save(ids) {
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(ids));
    } catch (e) {
      /* Storage unavailable: the picks still apply for this page view. */
    }
  }

  function forgetAll() {
    try {
      window.localStorage.removeItem(STORAGE_KEY);
    } catch (e) {
      /* Nothing to clear when storage is unavailable. */
    }
  }

  function selectedIds() {
    var boxes = document.querySelectorAll('input[type="checkbox"][data-cause]');
    var ids = [];
    for (var i = 0; i < boxes.length; i++) {
      if (boxes[i].checked) ids.push(boxes[i].getAttribute("data-cause"));
    }
    return ids;
  }

  function reorderCards(selected) {
    var grid = document.getElementById("gateway-grid");
    if (!grid) return;
    var cards = Array.prototype.slice.call(grid.querySelectorAll(".gateway-card"));

    cards.forEach(function (card, index) {
      if (!card.hasAttribute("data-order")) card.setAttribute("data-order", String(index));
    });

    function matches(card) {
      var causes = (card.getAttribute("data-causes") || "").split(" ");
      return causes.some(function (id) { return selected.indexOf(id) !== -1; });
    }

    cards.sort(function (a, b) {
      var ma = matches(a) ? 0 : 1;
      var mb = matches(b) ? 0 : 1;
      if (ma !== mb) return ma - mb;
      return Number(a.getAttribute("data-order")) - Number(b.getAttribute("data-order"));
    });

    cards.forEach(function (card) {
      card.classList.toggle("is-matched", matches(card) && selected.length > 0);
      grid.appendChild(card);
    });
  }

  function showYourCauses(selected) {
    var panel = document.getElementById("your-causes");
    if (!panel) return;
    var items = panel.querySelectorAll(".your-cause-item");
    for (var i = 0; i < items.length; i++) {
      var id = items[i].getAttribute("data-cause");
      items[i].hidden = selected.indexOf(id) === -1;
    }
    panel.hidden = selected.length === 0;
  }

  function apply(selected) {
    var boxes = document.querySelectorAll('input[type="checkbox"][data-cause]');
    for (var i = 0; i < boxes.length; i++) {
      boxes[i].checked = selected.indexOf(boxes[i].getAttribute("data-cause")) !== -1;
    }
    showYourCauses(selected);
    reorderCards(selected);
  }

  function init() {
    var saved = readSaved();
    apply(saved);

    var boxes = document.querySelectorAll('input[type="checkbox"][data-cause]');
    for (var i = 0; i < boxes.length; i++) {
      boxes[i].addEventListener("change", function () {
        var ids = selectedIds();
        save(ids);
        apply(ids);
      });
    }

    var clear = document.getElementById("clear-causes");
    if (clear) {
      clear.addEventListener("click", function () {
        forgetAll();
        apply([]);
      });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
