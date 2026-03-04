/**
 * Dynamic content width control with drag handle.
 * Adds a draggable handle to the right edge of the content area.
 * Saves preference to localStorage.
 */
(function () {
  "use strict";

  var STORAGE_KEY = "vr-content-width";
  var MIN_WIDTH = 800;
  var HANDLE_WIDTH = 6;

  function getMaxWidth() {
    return window.innerWidth - 40;
  }

  function init() {
    // Wait for the content container to exist
    var grid = document.querySelector(".md-grid");
    if (!grid) return;

    // Create the drag handle
    var handle = document.createElement("div");
    handle.className = "width-handle";
    handle.title = "Потяните для изменения ширины";

    // Create the reset button (double-click hint)
    var tooltip = document.createElement("div");
    tooltip.className = "width-handle-tooltip";
    tooltip.textContent = "Ширина";

    // Create the wrapper that positions the handle relative to the content
    var wrapper = document.createElement("div");
    wrapper.className = "width-handle-wrapper";
    wrapper.appendChild(handle);
    wrapper.appendChild(tooltip);

    // Insert after the main content grid
    var mainContent = document.querySelector(".md-content");
    if (mainContent) {
      mainContent.style.position = "relative";
      mainContent.appendChild(wrapper);
    } else {
      return;
    }

    // Restore saved width
    var saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      var savedPx = parseInt(saved, 10);
      if (savedPx >= MIN_WIDTH && savedPx <= getMaxWidth()) {
        applyWidth(savedPx);
      }
    }

    // Drag state
    var isDragging = false;
    var startX = 0;
    var startWidth = 0;

    handle.addEventListener("mousedown", function (e) {
      e.preventDefault();
      isDragging = true;
      startX = e.clientX;
      var gridRect = grid.getBoundingClientRect();
      startWidth = gridRect.width;
      document.body.style.cursor = "col-resize";
      document.body.style.userSelect = "none";
      handle.classList.add("active");
      tooltip.classList.add("visible");
    });

    document.addEventListener("mousemove", function (e) {
      if (!isDragging) return;
      e.preventDefault();
      // Calculate new width: dragging right = wider, left = narrower
      // The handle is on the right side, so we use 2x delta (symmetric expansion)
      var delta = e.clientX - startX;
      var newWidth = Math.round(startWidth + delta * 2);
      newWidth = Math.max(MIN_WIDTH, Math.min(newWidth, getMaxWidth()));
      applyWidth(newWidth);
      tooltip.textContent = newWidth + "px";
    });

    document.addEventListener("mouseup", function () {
      if (!isDragging) return;
      isDragging = false;
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
      handle.classList.remove("active");

      // Save current width
      var gridRect = grid.getBoundingClientRect();
      localStorage.setItem(STORAGE_KEY, Math.round(gridRect.width));

      setTimeout(function () {
        tooltip.classList.remove("visible");
      }, 1200);
    });

    // Double-click to reset to default
    handle.addEventListener("dblclick", function () {
      localStorage.removeItem(STORAGE_KEY);
      grid.style.maxWidth = "";
      tooltip.textContent = "Сброс";
      tooltip.classList.add("visible");
      setTimeout(function () {
        tooltip.classList.remove("visible");
      }, 1200);
    });

    // Show tooltip on hover
    handle.addEventListener("mouseenter", function () {
      if (!isDragging) {
        var gridRect = grid.getBoundingClientRect();
        tooltip.textContent = Math.round(gridRect.width) + "px";
        tooltip.classList.add("visible");
      }
    });

    handle.addEventListener("mouseleave", function () {
      if (!isDragging) {
        tooltip.classList.remove("visible");
      }
    });
  }

  function applyWidth(px) {
    var grids = document.querySelectorAll(".md-grid");
    for (var i = 0; i < grids.length; i++) {
      grids[i].style.maxWidth = px + "px";
    }
  }

  // Init on DOMContentLoaded
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
