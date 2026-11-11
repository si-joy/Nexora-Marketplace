(() => {
  "use strict";

  const STORAGE_KEY = "marketplace.theme";
  const root = document.documentElement;
  const media = window.matchMedia("(prefers-color-scheme: dark)");

  function storedTheme() {
    try {
      const value = window.localStorage.getItem(STORAGE_KEY);
      return value === "light" || value === "dark" ? value : null;
    } catch {
      return null;
    }
  }

  function saveTheme(theme) {
    try {
      window.localStorage.setItem(STORAGE_KEY, theme);
    } catch {
      // Private browsing/storage restrictions should never break theme switching.
    }
  }

  function effectiveTheme() {
    return storedTheme() || (media.matches ? "dark" : "light");
  }

  function applyTheme(theme) {
    root.dataset.theme = theme;
    root.style.colorScheme = theme;
    document.querySelectorAll("[data-theme-toggle]").forEach((button) => {
      const isDark = theme === "dark";
      button.setAttribute("aria-pressed", String(isDark));
      button.setAttribute("aria-label", `Switch to ${isDark ? "light" : "dark"} mode`);
      button.title = `Switch to ${isDark ? "light" : "dark"} mode`;
    });
  }

  // Runs in <head> before CSS for minimal theme flash.
  applyTheme(effectiveTheme());

  document.addEventListener("DOMContentLoaded", () => {
    applyTheme(effectiveTheme());
    document.querySelectorAll("[data-theme-toggle]").forEach((button) => {
      button.addEventListener("click", () => {
        const next = root.dataset.theme === "dark" ? "light" : "dark";
        saveTheme(next);
        applyTheme(next);
      });
    });
  });

  function syncSystemTheme() {
    if (!storedTheme()) applyTheme(effectiveTheme());
  }
  if (typeof media.addEventListener === "function") {
    media.addEventListener("change", syncSystemTheme);
  } else if (typeof media.addListener === "function") {
    media.addListener(syncSystemTheme);
  }
})();
