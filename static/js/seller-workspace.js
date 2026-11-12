/* Seller workspace: progressive enhancement for same-page panel navigation.
   Normal links and POST forms continue working without JavaScript. */
(() => {
  "use strict";

  const workspace = document.querySelector("[data-seller-workspace]");
  if (!workspace) return;

  const panel = workspace.querySelector("[data-seller-panel]");
  const navigation = workspace.querySelector("[data-seller-navigation]");
  const feedback = workspace.querySelector("[data-seller-feedback]");
  const dashboardPath = new URL(workspace.dataset.dashboardUrl, window.location.href).pathname;
  const validTabs = new Set(["overview", "products", "stock", "orders"]);
  if (!panel || !navigation || !feedback) return;

  let controller = null;
  let requestNumber = 0;

  function validatedUrl(href) {
    const url = new URL(href, window.location.href);
    if (url.origin !== window.location.origin || url.pathname !== dashboardPath) return null;
    if (!validTabs.has(url.searchParams.get("tab") || "overview")) return null;
    return url;
  }

  function activeTab(url) {
    return url.searchParams.get("tab") || "overview";
  }

  function highlightNavigation(tab) {
    navigation.querySelectorAll("[data-seller-tab]").forEach((link) => {
      const selected = link.dataset.sellerTab === tab;
      link.classList.toggle("bg-surface-soft", selected);
      link.classList.toggle("text-primary", selected);
      link.classList.toggle("text-muted", !selected);
      link.classList.toggle("hover:bg-surface-soft", !selected);
      link.classList.toggle("hover:text-primary", !selected);
      if (selected) link.setAttribute("aria-current", "page");
      else link.removeAttribute("aria-current");
    });
  }

  async function navigate(href, { history = "push", focusHeading = true } = {}) {
    const url = validatedUrl(href);
    if (!url) {
      window.location.assign(href);
      return false;
    }

    if (controller) controller.abort();
    controller = new AbortController();
    const currentRequest = ++requestNumber;
    panel.setAttribute("aria-busy", "true");
    feedback.textContent = "Loading seller workspace section…";

    try {
      const response = await fetch(url.pathname + url.search, {
        credentials: "same-origin",
        cache: "no-store",
        redirect: "follow",
        headers: { "X-Seller-Panel": "1", "Accept": "text/html" },
        signal: controller.signal,
      });

      // Login / permission redirects must never be injected into this panel.
      const returned = new URL(response.url, window.location.href);
      if (!response.ok || returned.pathname !== dashboardPath) {
        window.location.assign(url.pathname + url.search);
        return false;
      }
      const markup = await response.text();
      if (currentRequest !== requestNumber) return false;

      const candidate = document.createElement("template");
      candidate.innerHTML = markup.trim();
      const view = candidate.content.querySelector("[data-seller-panel-view]");
      const tab = activeTab(url);
      if (!view || view.dataset.sellerPanelView !== tab) {
        window.location.assign(url.pathname + url.search);
        return false;
      }

      panel.replaceChildren(candidate.content);
      if (history === "push" && url.href !== window.location.href) {
        window.history.pushState({ sellerWorkspace: true }, "", url.pathname + url.search);
      }
      highlightNavigation(tab);
      document.title = ({
        overview: "Seller dashboard",
        products: "Manage products",
        stock: "Stock overview",
        orders: "Store orders",
      })[tab] + " | Nexora";
      if (focusHeading) {
        panel.querySelector("[data-seller-panel-heading]")?.focus({ preventScroll: true });
      }
      feedback.textContent = "Section loaded.";
      return true;
    } catch (error) {
      if (error.name === "AbortError" || currentRequest !== requestNumber) return false;
      // Full-page navigation is the reliable fallback for network failure.
      window.location.assign(url.pathname + url.search);
      return false;
    } finally {
      if (currentRequest === requestNumber) panel.setAttribute("aria-busy", "false");
    }
  }

  workspace.addEventListener("click", (event) => {
    if (event.defaultPrevented || event.button !== 0 || event.metaKey ||
        event.ctrlKey || event.shiftKey || event.altKey) return;
    const anchor = event.target.closest("a[data-seller-tab], a[data-seller-panel-link]");
    if (!anchor || anchor.target === "_blank" || anchor.hasAttribute("download")) return;
    if (!validatedUrl(anchor.href)) return;
    event.preventDefault();
    navigate(anchor.href);
  });

  // Existing order status service remains authoritative; only its response
  // format changes when explicitly requested by this workspace.
  workspace.addEventListener("submit", async (event) => {
    const form = event.target.closest("form[data-seller-order-form]");
    if (!form || event.defaultPrevented) return;
    event.preventDefault();

    const newStatus = new FormData(form).get("status");
    if ((newStatus === "cancelled" || newStatus === "delivered") &&
        !window.confirm(newStatus === "delivered"
          ? "Confirm delivery? This deducts reserved stock."
          : "Cancel this item and release its reserved stock?")) return;

    const button = event.submitter || form.querySelector('button[type="submit"]');
    if (button) button.disabled = true;
    feedback.textContent = "Updating order status…";
    try {
      const response = await fetch(form.action, {
        method: "POST",
        body: new FormData(form),
        credentials: "same-origin",
        cache: "no-store",
        headers: { "X-Seller-Panel": "1", "Accept": "application/json" },
      });
      if (response.redirected) {
        window.location.assign(response.url);
        return;
      }
      const result = await response.json();
      if (!response.ok || !result.ok) {
        throw new Error(result.error || "Could not update the order. Please try again.");
      }
      await navigate(window.location.href, { history: "none", focusHeading: false });
      feedback.textContent = "Order status updated.";
    } catch (error) {
      feedback.textContent = error.message || "Unable to update order status.";
      window.alert(feedback.textContent);
    } finally {
      if (button) button.disabled = false;
    }
  });

  window.addEventListener("popstate", () => {
    const destination = validatedUrl(window.location.href);
    if (destination) navigate(destination.href, { history: "none", focusHeading: false });
  });
})();
