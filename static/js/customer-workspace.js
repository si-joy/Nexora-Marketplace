/* Account dashboard: persistent left navigation and server-rendered right panels.
   Progressive enhancement: normal links/forms remain functional without JS. */
(() => {
  "use strict";
  const root = document.querySelector("[data-customer-workspace]");
  if (!root) return;

  const panel = root.querySelector("[data-customer-panel]");
  const navigation = root.querySelector("[data-customer-navigation]");
  const feedback = root.querySelector("[data-customer-feedback]");
  const api = document.getElementById("real-cart-api");
  const dashboardPath = new URL(root.dataset.dashboardUrl, window.location.href).pathname;
  const allowed = new Set(["overview", "orders", "wishlist", "bag", "password"]);
  if (!panel || !navigation || !feedback || !api) return;

  let navigationRequest = 0;
  let aborter = null;
  let mutating = false;

  function validUrl(href) {
    const url = new URL(href, window.location.href);
    if (url.origin !== window.location.origin || url.pathname !== dashboardPath) return null;
    if (!allowed.has(url.searchParams.get("tab") || "overview")) return null;
    return url;
  }

  function selectTab(tab) {
    navigation.querySelectorAll("[data-customer-tab]").forEach((anchor) => {
      const active = anchor.dataset.customerTab === tab;
      anchor.classList.toggle("bg-surface-soft", active);
      anchor.classList.toggle("text-primary", active);
      anchor.classList.toggle("text-muted", !active);
      anchor.classList.toggle("hover:bg-surface-soft", !active);
      anchor.classList.toggle("hover:text-primary", !active);
      if (active) anchor.setAttribute("aria-current", "page");
      else anchor.removeAttribute("aria-current");
    });
  }

  function install(html, tab, focus = true) {
    const fragment = document.createElement("template");
    fragment.innerHTML = html.trim();
    const view = fragment.content.querySelector("[data-customer-panel-view]");
    if (!view || view.dataset.customerPanelView !== tab) return false;
    panel.replaceChildren(fragment.content);
    if (focus) panel.querySelector("[data-customer-panel-heading]")?.focus({ preventScroll: true });
    return true;
  }

  async function navigate(href, { history = "push", focus = true } = {}) {
    const url = validUrl(href);
    if (!url) {
      window.location.assign(href);
      return false;
    }
    aborter?.abort();
    aborter = new AbortController();
    const current = ++navigationRequest;
    panel.setAttribute("aria-busy", "true");
    feedback.textContent = "Loading account section…";

    try {
      const response = await fetch(url.pathname + url.search, {
        credentials: "same-origin", cache: "no-store", redirect: "follow",
        headers: { "X-Customer-Panel": "1", "Accept": "text/html" },
        signal: aborter.signal,
      });
      const finalUrl = new URL(response.url, window.location.href);
      if (!response.ok || finalUrl.pathname !== dashboardPath) {
        window.location.assign(url.pathname + url.search);
        return false;
      }
      const html = await response.text();
      if (current !== navigationRequest) return false;
      const tab = url.searchParams.get("tab") || "overview";
      if (!install(html, tab, focus)) {
        window.location.assign(url.pathname + url.search);
        return false;
      }
      if (history === "push" && url.href !== window.location.href) {
        window.history.pushState({ accountWorkspace: true }, "", url.pathname + url.search);
      }
      selectTab(tab);
      const title = {
        overview: "My dashboard", orders: "My orders", wishlist: "My wishlist",
        bag: "Shopping bag", password: "Change password",
      }[tab];
      document.title = (url.searchParams.has("order") && tab === "orders"
        ? "Order details" : title) + " | Nexora";
      feedback.textContent = "Account section loaded.";
      return true;
    } catch (error) {
      if (error.name !== "AbortError" && current === navigationRequest) {
        window.location.assign(url.pathname + url.search);
      }
      return false;
    } finally {
      if (current === navigationRequest) panel.setAttribute("aria-busy", "false");
    }
  }

  async function jsonWrite(url, payload) {
    const response = await fetch(url, {
      method: "POST", credentials: "same-origin", cache: "no-store",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": api.dataset.csrf || "",
        "Accept": "application/json",
      },
      body: JSON.stringify(payload),
    });
    const result = await response.json().catch(() => ({}));
    if (response.status === 401 || response.status === 403) {
      throw new Error("Your session may have expired. Refresh and sign in again.");
    }
    if (!response.ok || !result.ok) throw new Error(result.error || "Unable to update saved items.");
    return result;
  }

  async function mutate(button, action) {
    if (mutating) return;
    mutating = true;
    button.disabled = true;
    panel.setAttribute("aria-busy", "true");
    try {
      await action();
      // Refresh header badges and the shared cart drawer from the same account API.
      window.dispatchEvent(new Event("nexora:account-items-updated"));
      await navigate(window.location.href, { history: "none", focus: false });
      feedback.textContent = "Your account has been updated.";
    } catch (error) {
      feedback.textContent = error.message || "Unable to save changes.";
      window.alert(feedback.textContent);
    } finally {
      if (button.isConnected) button.disabled = false;
      panel.setAttribute("aria-busy", "false");
      mutating = false;
    }
  }

  root.addEventListener("click", (event) => {
    if (event.defaultPrevented || event.button !== 0 ||
        event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    const link = event.target.closest("a[data-customer-tab], a[data-customer-panel-link]");
    if (link && !link.hasAttribute("download") && link.target !== "_blank" && validUrl(link.href)) {
      event.preventDefault();
      navigate(link.href);
      return;
    }

    const favorite = event.target.closest("[data-account-remove-favorite]");
    if (favorite) {
      event.preventDefault();
      const kind = favorite.dataset.kind;
      if (kind !== "demo" && kind !== "marketplace") return;
      mutate(favorite, () => jsonWrite(api.dataset.savedChange, {
        action: kind === "demo" ? "demo_wishlist_toggle" : "marketplace_wishlist_toggle",
        product_id: kind === "demo" ? favorite.dataset.itemId : Number(favorite.dataset.itemId),
      }));
      return;
    }

    const bagChange = event.target.closest("[data-account-bag-change]");
    if (bagChange) {
      event.preventDefault();
      const quantity = Number(bagChange.dataset.quantity);
      const kind = bagChange.dataset.kind;
      if (!Number.isInteger(quantity) || quantity < 0 || quantity > 99) return;
      if (kind === "demo") {
        mutate(bagChange, () => jsonWrite(api.dataset.savedChange, {
          action: "demo_cart_set", product_id: bagChange.dataset.itemId, quantity,
        }));
      } else if (kind === "real") {
        const variantId = Number(bagChange.dataset.itemId);
        if (!Number.isSafeInteger(variantId) || variantId <= 0) return;
        mutate(bagChange, () => jsonWrite(
          `${api.dataset.update}${variantId}/`, { quantity },
        ));
      }
    }
  });

  root.addEventListener("submit", async (event) => {
    const form = event.target.closest("form[data-customer-order-cancel], form[data-customer-password-form]");
    if (!form || event.defaultPrevented || mutating) return;
    event.preventDefault();

    const cancelling = form.hasAttribute("data-customer-order-cancel");
    if (cancelling && !window.confirm("Cancel this pending item and release reserved stock?")) return;

    const submit = event.submitter || form.querySelector('button[type="submit"]');
    mutating = true;
    if (submit) submit.disabled = true;
    panel.setAttribute("aria-busy", "true");

    try {
      const response = await fetch(form.action, {
        method: "POST", credentials: "same-origin", cache: "no-store",
        redirect: "follow", body: new FormData(form),
        headers: { "X-Customer-Panel": "1", "Accept": cancelling ? "application/json" : "text/html" },
      });
      const finalUrl = new URL(response.url, window.location.href);
      if (response.redirected || finalUrl.pathname !== (cancelling
        ? new URL(form.action, window.location.href).pathname
        : dashboardPath)) {
        window.location.assign(response.url);
        return;
      }
      if (cancelling) {
        const result = await response.json().catch(() => ({}));
        if (!response.ok || !result.ok) throw new Error(result.error || "Cancellation was unsuccessful.");
        await navigate(window.location.href, { history: "none", focus: false });
        feedback.textContent = "Pending order item cancelled.";
      } else {
        const html = await response.text();
        if (!install(html, "password", false)) {
          window.location.assign(form.action);
          return;
        }
        feedback.textContent = panel.querySelector("[role='status']")?.textContent ||
          (response.ok ? "Password form checked." : "Please correct the password form.");
      }
    } catch (error) {
      feedback.textContent = error.message || "Unable to save changes.";
      window.alert(feedback.textContent);
    } finally {
      if (submit?.isConnected) submit.disabled = false;
      panel.setAttribute("aria-busy", "false");
      mutating = false;
    }
  });

  window.addEventListener("popstate", () => {
    const destination = validUrl(window.location.href);
    if (destination) navigate(destination.href, { history: "none", focus: false });
  });
  window.addEventListener("pageshow", (event) => {
    if (event.persisted) window.location.reload();
  });
})();
