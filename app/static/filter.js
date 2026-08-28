(function () {
  "use strict";

  var TOPIC_KEY = "meridian_topics";
  var followed = null; // null/[] = no preference saved = show everything

  try {
    var raw = localStorage.getItem(TOPIC_KEY);
    if (raw) followed = JSON.parse(raw);
  } catch (e) {}

  var biasFilter = "";

  function allTopicSlugs() {
    return Array.prototype.map.call(document.querySelectorAll(".topic-toggle"), function (b) {
      return b.dataset.topic;
    });
  }

  function isTopicVisible(el) {
    if (!followed || followed.length === 0) return true;
    var topics = (el.dataset.topics || "").split(",").filter(Boolean);
    return topics.some(function (t) { return followed.indexOf(t) !== -1; });
  }

  function isBiasVisible(el) {
    if (!biasFilter) return true;
    var biases = (el.dataset.biases || "").split(",").filter(Boolean);
    return biases.indexOf(biasFilter) !== -1;
  }

  function applyFilters() {
    var cards = document.querySelectorAll("[data-topics]");
    var visibleCount = 0;
    var anyClusterVisible = false;

    cards.forEach ? cards.forEach(applyOne) : Array.prototype.forEach.call(cards, applyOne);

    function applyOne(el) {
      var visible = isTopicVisible(el) && isBiasVisible(el);
      el.style.display = visible ? "" : "none";
      if (visible && (el.classList.contains("cluster-card") || el.classList.contains("river-item"))) {
        visibleCount++;
      }
      if (visible && el.classList.contains("cluster-card")) anyClusterVisible = true;
    }

    var countEl = document.querySelector(".story-count .num");
    if (countEl) countEl.textContent = visibleCount;

    var hint = document.getElementById("noClustersHint");
    if (hint) hint.style.display = anyClusterVisible ? "none" : "";
  }

  function renderTopicChips() {
    var chips = document.querySelectorAll(".topic-toggle");
    Array.prototype.forEach.call(chips, function (btn) {
      var slug = btn.dataset.topic;
      var isFollowed = !followed || followed.length === 0 || followed.indexOf(slug) !== -1;
      btn.classList.toggle("off", !isFollowed);
      btn.textContent = (isFollowed ? "✓ " : "") + btn.dataset.label;
    });
  }

  Array.prototype.forEach.call(document.querySelectorAll(".topic-toggle"), function (btn) {
    btn.addEventListener("click", function () {
      var slug = btn.dataset.topic;
      var all = allTopicSlugs();
      if (!followed || followed.length === 0) {
        followed = all.filter(function (t) { return t !== slug; });
      } else if (followed.indexOf(slug) !== -1) {
        followed = followed.filter(function (t) { return t !== slug; });
      } else {
        followed = followed.concat([slug]);
        if (followed.length === all.length) followed = [];
      }
      try { localStorage.setItem(TOPIC_KEY, JSON.stringify(followed)); } catch (e) {}
      renderTopicChips();
      applyFilters();
    });
  });

  Array.prototype.forEach.call(document.querySelectorAll(".bias-chip, .all-leans"), function (btn) {
    btn.addEventListener("click", function () {
      biasFilter = btn.dataset.bias || "";
      Array.prototype.forEach.call(document.querySelectorAll(".bias-chip, .all-leans"), function (b) {
        b.classList.toggle("active", b === btn);
      });
      applyFilters();
    });
  });

  renderTopicChips();
  applyFilters();
})();
