/* Nexora shared storefront: account-backed demo/marketplace saved items,
   cart drawer and thumbnail animation. No real checkout. */
(() => {
  "use strict";

  const catalogScript = document.getElementById("demo-catalog-json");
  let products = [];
  try {
    const parsed = JSON.parse(catalogScript?.textContent || "[]");
    if (Array.isArray(parsed)) products = parsed;
  } catch { /* The site remains navigable if demo JSON is missing. */ }
  const catalog = new Map(products.map((product) => [product.id, product]));
  const MAX_CART_ITEMS = 200;
  const MAX_PER_PRODUCT = 99;
  const cards = [...document.querySelectorAll("[data-product]")];
  const filters = [...document.querySelectorAll("[data-filter]")];
  const drawer = document.getElementById("cart-drawer");
  const bagTrigger = document.querySelector("[data-open-bag]");
  const prefersReducedMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)");
  let category = "all";
  let toastTimeout;
  let closeTimeout;

  // Old browser-only demo keys must never show a previous customer's items.
  try {
    localStorage.removeItem("nexora.demo.favorites");
    localStorage.removeItem("nexora.demo.bag");
  } catch { /* Browser storage might be disabled. */ }
  // No account data is read from localStorage. All saved items are account-owned.
  let favorites = new Set();
  let marketplaceFavorites = new Set();
  let cart = [];
  let realCart = { authenticated: false, items: [], item_count: 0, subtotal: "0.00" };
  const realConfig = document.getElementById("real-cart-api");
  const realApi = {
    get: realConfig?.dataset.get,
    add: realConfig?.dataset.add,
    update: realConfig?.dataset.update,
    clear: realConfig?.dataset.clear,
    token: realConfig?.dataset.csrf,
    authenticated: realConfig?.dataset.authenticated === "true",
    login: realConfig?.dataset.login || "/account/login/",
    savedGet: realConfig?.dataset.savedGet,
    savedChange: realConfig?.dataset.savedChange,
  };

  function loginForSavedItems() {
    const next = encodeURIComponent(window.location.pathname + window.location.search);
    window.location.href = `${realApi.login}?next=${next}`;
  }
  function applySavedState(state) {
    realApi.authenticated = !!state?.authenticated;
    if (!state?.authenticated) {
      favorites = new Set();
      marketplaceFavorites = new Set();
      cart = [];
    } else {
      favorites = new Set((state.demo_favorites || []).filter((id) => catalog.has(id)));
      marketplaceFavorites = new Set(state.marketplace_favorites || []);
      cart = [];
      for (const line of state.demo_cart || []) {
        if (!catalog.has(line.product_id)) continue;
        const count = Number(line.quantity);
        if (!Number.isInteger(count) || count < 1 || count > MAX_PER_PRODUCT) continue;
        for (let i = 0; i < count && cart.length < MAX_CART_ITEMS; i++) cart.push(line.product_id);
      }
    }
    updateBadges();
    updateHearts();
    refreshWishlist();
    renderCart();
  }
  async function refreshSavedItems() {
    if (!realApi.authenticated) {
      applySavedState({ authenticated: false });
      return;
    }
    try {
      const response = await fetch(realApi.savedGet, { credentials: "same-origin", cache: "no-store" });
      if (!response.ok) throw new Error("Could not load saved items");
      const result = await response.json();
      applySavedState(result);
    } catch (error) {
      applySavedState({ authenticated: false });
      notify("Unable to load your saved items. Please refresh.");
    }
  }
  async function changeSavedItems(action, payload = {}) {
    if (!realApi.authenticated) {
      loginForSavedItems();
      return null;
    }
    const response = await fetch(realApi.savedChange, {
      method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-CSRFToken": realApi.token || "" },
      body: JSON.stringify({ action, ...payload }),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok || !data.ok) throw new Error(data.error || "Unable to save your items.");
    applySavedState(data);
    return data;
  }
  function money(value) { return `৳${Number(value).toLocaleString("en-BD")}`; }
  function el(tag, className, content) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (content !== undefined) element.textContent = content;
    return element;
  }
  function notify(message) {
    const toast = document.getElementById("storefront-toast");
    if (!toast) return;
    clearTimeout(toastTimeout);
    toast.textContent = message;
    toast.classList.add("is-visible");
    toastTimeout = setTimeout(() => toast.classList.remove("is-visible"), 2300);
  }
  function updateBadges() {
    document.querySelectorAll("[data-favorites-count]").forEach((badge) => {
      badge.textContent = String(favorites.size + marketplaceFavorites.size);
      badge.hidden = !(favorites.size + marketplaceFavorites.size);
    });
    document.querySelectorAll("[data-bag-count]").forEach((badge) => {
      badge.textContent = String(cart.length + realCart.item_count);
    });
    document.querySelectorAll("[data-drawer-count]").forEach((label) => {
      label.textContent = `(${cart.length + realCart.item_count})`;
    });
  }
  function bumpBadge() {
    const badge = bagTrigger?.querySelector("[data-bag-count]");
    if (!badge) return;
    badge.classList.remove("cart-badge-pop");
    // Reflow restarts this short celebratory animation when consecutive items land.
    void badge.offsetWidth;
    badge.classList.add("cart-badge-pop");
    badge.addEventListener("animationend", () => badge.classList.remove("cart-badge-pop"), { once: true });
  }
  function updateHearts() {
    document.querySelectorAll("[data-favorite-toggle]").forEach((button) => {
      const active = favorites.has(button.dataset.itemId);
      button.setAttribute("aria-pressed", String(active));
      button.setAttribute("aria-label", `${active ? "Remove" : "Save"} ${button.dataset.itemName || "item"} ${active ? "from" : "to"} wishlist`);
      if (!button.closest("[data-product]")) button.textContent = active ? "♥ Saved" : "♡ Save";
    });
    document.querySelectorAll("[data-marketplace-favorite]").forEach((button) => {
      const id = Number(button.dataset.productId);
      const active = marketplaceFavorites.has(id);
      button.setAttribute("aria-pressed", String(active));
      button.setAttribute("aria-label", `${active ? "Remove" : "Save"} ${button.dataset.productName || "item"} ${active ? "from" : "to"} wishlist`);
      const icon = button.querySelector("[data-heart-icon]");
      if (icon) icon.textContent = active ? "♥" : "♡";
    });
  }
  function refreshWishlist() {
    const grid = document.getElementById("wishlist-grid");
    if (!grid) return;
    let demoCount = 0;
    grid.querySelectorAll("[data-product]").forEach((card) => {
      const visible = favorites.has(card.dataset.productId);
      card.hidden = !visible;
      if (visible) demoCount++;
    });
    grid.hidden = demoCount === 0;
    let realCount = 0;
    document.querySelectorAll("[data-saved-marketplace-item]").forEach((item) => {
      const active = marketplaceFavorites.has(Number(item.dataset.productId));
      item.hidden = !active;
      if (active) realCount++;
    });
    const realGrid = document.getElementById("marketplace-wishlist-grid");
    if (realGrid) realGrid.hidden = realCount === 0;
    const empty = document.getElementById("wishlist-empty");
    if (empty) empty.hidden = demoCount + realCount !== 0;
  }
  function refreshHomeFilters() {
    if (!filters.length) return;
    let visibleCount = 0;
    cards.forEach((card) => {
      const visible = category === "all" || card.dataset.productCategory === category;
      card.hidden = !visible;
      if (visible) visibleCount += 1;
    });
    const results = document.getElementById("product-results");
    if (results) results.textContent = `${visibleCount} product${visibleCount === 1 ? "" : "s"}`;
    const empty = document.getElementById("products-empty");
    if (empty) empty.hidden = visibleCount > 0;
    filters.forEach((button) => {
      const active = button.dataset.filter === category;
      button.classList.toggle("is-active", active);
      button.setAttribute("aria-pressed", String(active));
    });
  }
  filters.forEach((button) => button.addEventListener("click", () => {
    category = button.dataset.filter || "all";
    refreshHomeFilters();
  }));
  document.querySelector("[data-clear-filters]")?.addEventListener("click", () => {
    category = "all";
    refreshHomeFilters();
  });
  document.querySelectorAll("[data-favorite-toggle]").forEach((button) => {
    button.addEventListener("click", async () => {
      const id = button.dataset.itemId;
      if (!catalog.has(id)) return;
      button.disabled = true;
      try {
        const result = await changeSavedItems("demo_wishlist_toggle", { product_id: id });
        if (result) notify(favorites.has(id) ? "Saved to your wishlist" : "Removed from wishlist");
      } catch (error) { notify(error.message); }
      finally { button.disabled = false; }
    });
  });
  document.querySelectorAll("[data-marketplace-favorite]").forEach((button) => {
    button.addEventListener("click", async () => {
      const id = Number(button.dataset.productId);
      button.disabled = true;
      try {
        const result = await changeSavedItems("marketplace_wishlist_toggle", { product_id: id });
        if (result) notify(marketplaceFavorites.has(id) ? "Saved to your wishlist" : "Removed from wishlist");
      } catch (error) { notify(error.message); }
      finally { button.disabled = false; }
    });
  });

  function openCart() {
    if (!drawer || typeof drawer.showModal !== "function") return;
    clearTimeout(closeTimeout);
    renderCart();
    if (!drawer.open) drawer.showModal();
    document.body.classList.add("cart-is-open");
    bagTrigger?.setAttribute("aria-expanded", "true");
    // The first animation frame is off-screen so the panel visibly slides in.
    requestAnimationFrame(() => drawer.classList.add("is-open"));
  }
  function closeCart() {
    if (!drawer?.open) return;
    drawer.classList.remove("is-open");
    document.body.classList.remove("cart-is-open");
    bagTrigger?.setAttribute("aria-expanded", "false");
    clearTimeout(closeTimeout);
    if (prefersReducedMotion?.matches) drawer.close();
    else closeTimeout = setTimeout(() => {
      if (drawer.open && !drawer.classList.contains("is-open")) drawer.close();
    }, 340);
  }
  bagTrigger?.addEventListener("click", openCart);
  drawer?.querySelectorAll("[data-close-cart]").forEach((button) => button.addEventListener("click", closeCart));
  drawer?.addEventListener("cancel", (event) => {
    event.preventDefault();
    closeCart();
  });
  drawer?.addEventListener("click", (event) => {
    if (event.target === drawer) closeCart();
  });

  function flyProductThumbnail(button) {
    if (!bagTrigger || prefersReducedMotion?.matches || !Element.prototype.animate) return Promise.resolve();
    const sourceImage = button.closest("[data-product], [data-real-product]")?.querySelector("[data-gallery-main-image], img")
      || document.querySelector("main [data-gallery-main-image], main .product-art img");
    if (!sourceImage) return Promise.resolve();
    const from = sourceImage.getBoundingClientRect();
    const to = bagTrigger.getBoundingClientRect();
    if (!from.width || !from.height || !to.width || !to.height) return Promise.resolve();

    const size = 88;
    const x1 = from.left + from.width / 2 - size / 2;
    const y1 = from.top + from.height / 2 - size / 2;
    const x2 = to.left + to.width / 2 - size / 2;
    const y2 = to.top + to.height / 2 - size / 2;
    const midX = (x1 + x2) / 2;
    const midY = Math.min(y1, y2) - Math.min(130, window.innerHeight * 0.16);

    const ghost = el("div", "cart-flying-thumbnail");
    ghost.setAttribute("aria-hidden", "true");
    const image = document.createElement("img");
    image.src = sourceImage.currentSrc || sourceImage.src;
    image.alt = "";
    ghost.append(image);
    document.body.append(ghost);
    try {
      const animation = ghost.animate([
        { transform: `translate3d(${x1}px, ${y1}px, 0) scale(1) rotate(0deg)`, opacity: 1, offset: 0 },
        { transform: `translate3d(${midX}px, ${midY}px, 0) scale(.78) rotate(-9deg)`, opacity: 1, offset: .48 },
        { transform: `translate3d(${x2}px, ${y2}px, 0) scale(.15) rotate(10deg)`, opacity: .25, offset: 1 },
      ], { duration: 690, easing: "cubic-bezier(.25,.8,.2,1)", fill: "forwards" });
      return animation.finished.catch(() => {}).finally(() => ghost.remove());
    } catch {
      ghost.remove();
      return Promise.resolve();
    }
  }

  document.querySelectorAll("[data-add-bag]").forEach((button) => {
    button.addEventListener("click", async () => {
      const id = button.dataset.itemId;
      if (!catalog.has(id)) return;
      const selected = button.hasAttribute("data-detail-quantity")
        ? Number(document.querySelector("[data-demo-qty-value]")?.textContent || 1)
        : 1;
      const desired = cart.filter((itemId) => itemId === id).length + selected;
      button.disabled = true;
      try {
        const result = await changeSavedItems("demo_cart_set", { product_id: id, quantity: desired });
        if (!result) return;
        await flyProductThumbnail(button);
        bumpBadge();
        openCart();
        notify(`${catalog.get(id).name} saved to your bag`);
      } catch (error) { notify(error.message); }
      finally { button.disabled = false; }
    });
  });

  async function adjustItem(id, delta) {
    const current = cart.filter((itemId) => itemId === id).length;
    try {
      await changeSavedItems("demo_cart_set", {
        product_id: id, quantity: Math.max(0, current + delta),
      });
    } catch (error) { notify(error.message); }
  }

  function renderCart() {
    const list = document.getElementById("cart-list");
    if (!list) return;
    list.replaceChildren();
    const quantities = new Map();
    cart.forEach((id) => quantities.set(id, (quantities.get(id) || 0) + 1));
    let subtotal = 0;
    if (!quantities.size && !realCart.items.length) {
      const empty = el("div", "cart-drawer-empty");
      const symbol = el("div", "cart-drawer-empty-icon", "♡");
      symbol.setAttribute("aria-hidden", "true");
      empty.append(symbol, el("h3", "mt-4 text-lg font-extrabold text-foreground", "Your bag is empty"),
        el("p", "mt-2 max-w-[270px] text-center text-sm leading-6 text-muted", "Find something you love and add it to your bag."));
      const link = el("a", "mt-5 rounded-xl bg-primary px-5 py-3 text-xs font-bold text-on-primary", "Browse products");
      link.href = "/shop/";
      empty.append(link);
      list.append(empty);
    }

    // Server-backed marketplace items are separate from local demo items.
    if (realCart.items.length) {
      list.append(el("div", "cart-section-title", "Marketplace products · Saved to your account"));
    }
    for (const item of realCart.items) {
      if (item.is_available) subtotal += Number(item.line_total);
      const row = el("article", "cart-item-row");
      const visual = el("a", "cart-item-visual bg-surface-soft");
      visual.href = item.url;
      if (item.image_url) {
        const image = document.createElement("img");
        image.src = item.image_url;
        image.alt = item.name;
        image.loading = "lazy";
        visual.append(image);
      }
      const content = el("div", "cart-item-content");
      const name = el("a", "cart-item-name", item.name);
      name.href = item.url;
      content.append(name, el("p", "mt-1 text-xs text-muted", item.store),
        el("p", "mt-2 text-sm font-extrabold text-foreground", item.is_available ? money(item.line_total) : "Unavailable"));
      if (!item.is_available) content.append(el("p", "mt-1 text-xs text-danger", "Stock or listing changed. Please remove or adjust this item."));
      const footer = el("div", "mt-3 flex flex-wrap items-center justify-between gap-2");
      const quantityControls = el("div", "cart-qty-controls");
      const minus = el("button", "cart-qty-button", "−");
      minus.type = "button";
      minus.setAttribute("aria-label", `Decrease quantity of ${item.name}`);
      minus.addEventListener("click", () => changeRealQuantity(item.variant_id, item.quantity - 1));
      const count = el("span", "min-w-6 text-center text-xs font-bold", String(item.quantity));
      const plus = el("button", "cart-qty-button", "+");
      plus.type = "button";
      plus.disabled = !item.is_available || item.quantity >= item.available_quantity || item.quantity >= 99;
      plus.setAttribute("aria-label", `Increase quantity of ${item.name}`);
      plus.addEventListener("click", () => changeRealQuantity(item.variant_id, item.quantity + 1));
      quantityControls.append(minus, count, plus);
      const remove = el("button", "text-xs font-semibold text-muted hover:text-danger", "Remove");
      remove.type = "button";
      remove.addEventListener("click", () => changeRealQuantity(item.variant_id, 0));
      footer.append(quantityControls, remove);
      content.append(footer);
      row.append(visual, content);
      list.append(row);
    }
    if (quantities.size && realCart.items.length) list.append(el("div", "cart-section-title", "Demo products · Saved to your account"));
    for (const [id, quantity] of quantities) {
      const item = catalog.get(id);
      if (!item) continue;
      subtotal += item.price_value * quantity;
      const row = el("article", "cart-item-row");
      const visual = el("a", `product-art product-art--${item.visual} cart-item-visual`);
      visual.href = `/product/${encodeURIComponent(item.id)}/`;
      const image = document.createElement("img");
      image.src = `/static/${item.image}`;
      image.alt = item.name;
      image.loading = "lazy";
      visual.append(image);
      const content = el("div", "cart-item-content");
      const name = el("a", "cart-item-name", item.name);
      name.href = visual.href;
      content.append(name, el("p", "mt-1 text-xs text-muted", item.category),
        el("p", "mt-2 text-sm font-extrabold text-foreground", money(item.price_value * quantity)));

      const footer = el("div", "mt-3 flex flex-wrap items-center justify-between gap-2");
      const quantityControls = el("div", "cart-qty-controls");
      const minus = el("button", "cart-qty-button", "−");
      minus.type = "button";
      minus.setAttribute("aria-label", `Decrease quantity of ${item.name}`);
      minus.addEventListener("click", () => adjustItem(id, -1));
      const count = el("span", "min-w-6 text-center text-xs font-bold", String(quantity));
      count.setAttribute("aria-label", `Quantity ${quantity}`);
      const plus = el("button", "cart-qty-button", "+");
      plus.type = "button";
      plus.setAttribute("aria-label", `Increase quantity of ${item.name}`);
      plus.disabled = quantity >= MAX_PER_PRODUCT || cart.length >= MAX_CART_ITEMS;
      plus.addEventListener("click", () => adjustItem(id, 1));
      quantityControls.append(minus, count, plus);
      const remove = el("button", "text-xs font-semibold text-muted hover:text-danger", "Remove");
      remove.type = "button";
      remove.setAttribute("aria-label", `Remove ${item.name} from bag`);
      remove.addEventListener("click", () => {
        adjustItem(id, -quantity);
      });
      footer.append(quantityControls, remove);
      content.append(footer);
      row.append(visual, content);
      list.append(row);
    }
    document.querySelectorAll("[data-cart-subtotal]").forEach((subtotalNode) => {
      subtotalNode.textContent = money(subtotal);
    });
    drawer?.querySelectorAll("[data-clear-cart]").forEach((button) => {
      button.disabled = cart.length === 0 && realCart.item_count === 0;
    });
  }
  drawer?.querySelector("[data-clear-cart]")?.addEventListener("click", async () => {
    if (!realApi.authenticated) return;
    try {
      // Clear the account-owned demo bag and marketplace bag independently.
      await changeSavedItems("demo_cart_clear");
      if (realCart.item_count) await writeReal(realApi.clear, {});
    } catch (error) {
      notify(error.message);
      await refreshSavedItems();
      await refreshRealCart();
    }
  });

  // Real product cart: CSRF-protected JSON requests, never localStorage.
  async function refreshRealCart() {
    if (!realApi.get) return;
    try {
      const response = await fetch(realApi.get, { credentials: "same-origin" });
      if (!response.ok) throw new Error("Unable to load account cart");
      const data = await response.json();
      if (data.ok) {
        realCart = data;
        updateBadges();
        renderCart();
      }
    } catch { /* Existing saved-item state remains unchanged on API failure. */ }
  }

  async function writeReal(url, payload) {
    const response = await fetch(url, {
      method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-CSRFToken": realApi.token || "" },
      body: JSON.stringify(payload),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok || !data.ok) throw new Error(data.error || "Couldn't update the bag. Please try again.");
    realCart = data;
    updateBadges();
    renderCart();
    return data;
  }

  async function changeRealQuantity(variantId, quantity) {
    if (!realApi.update) return;
    try {
      await writeReal(`${realApi.update}${variantId}/`, { quantity });
    } catch (error) { notify(error.message); }
  }

  document.querySelectorAll("[data-add-real-bag]").forEach((button) => {
    button.addEventListener("click", async () => {
      if (!realApi.authenticated) {
        notify("Sign in to save real marketplace items");
        const next = encodeURIComponent(window.location.pathname + window.location.search);
        window.location.href = `${realApi.login}?next=${next}`;
        return;
      }
      if (button.disabled) return;
      button.disabled = true;
      try {
        const variantId = Number(button.dataset.variantId);
        await writeReal(realApi.add, { variant_id: variantId, quantity: 1 });
        await flyProductThumbnail(button);
        bumpBadge();
        openCart();
        notify("Marketplace product added to your bag");
      } catch (error) { notify(error.message); }
      finally { button.disabled = false; }
    });
  });

  // Old /cart/ links redirect here. Open the same drawer, then clean the URL.
  const locationUrl = new URL(window.location.href);
  if (locationUrl.searchParams.get("cart") === "open") {
    locationUrl.searchParams.delete("cart");
    window.history.replaceState(window.history.state, "", locationUrl.pathname + locationUrl.search + locationUrl.hash);
    openCart();
  }
  updateBadges();
  updateHearts();
  refreshHomeFilters();
  refreshWishlist();
  renderCart();
  refreshSavedItems();
  refreshRealCart();

  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") {
      // An account may have signed out in a different tab.
      refreshSavedItems();
      refreshRealCart();
    }
  });

  window.addEventListener("pageshow", (event) => {
    if (event.persisted) {
      // A restored back/forward page must never expose a previous account.
      realCart = { authenticated: false, items: [], item_count: 0, subtotal: "0.00" };
      applySavedState({ authenticated: false });
      refreshSavedItems();
      refreshRealCart();
    }
  });

  // Detail page quantity selector. Server still validates the 99-unit cap.
  document.querySelectorAll("[data-demo-qty]").forEach((picker) => {
    const output = picker.querySelector("[data-demo-qty-value]");
    const minus = picker.querySelector("[data-demo-qty-minus]");
    const plus = picker.querySelector("[data-demo-qty-plus]");
    if (!output || !minus || !plus) return;
    const set = (value) => {
      const quantity = Math.max(1, Math.min(99, value));
      output.textContent = String(quantity);
      minus.disabled = quantity <= 1;
      plus.disabled = quantity >= 99;
    };
    minus.addEventListener("click", () => set(Number(output.textContent) - 1));
    plus.addEventListener("click", () => set(Number(output.textContent) + 1));
    set(1);
  });

  function initProductGalleries() {
    document.querySelectorAll("[data-product-gallery]").forEach((gallery) => {
      const thumbs = [...gallery.querySelectorAll("[data-gallery-thumb]")];
      if (!thumbs.length) return;

      const mainImage = gallery.querySelector("[data-gallery-main-image]");
      const stage = gallery.querySelector("[data-gallery-stage]");
      const position = gallery.querySelector("[data-gallery-position]");
      const title = gallery.querySelector("[data-gallery-title]");
      const description = gallery.querySelector("[data-gallery-description]");
      let current = Math.max(0, thumbs.findIndex((thumb) => thumb.classList.contains("is-active")));
      let touchX = null;

      const display = (index, { focus = false } = {}) => {
        current = (index + thumbs.length) % thumbs.length;
        const active = thumbs[current];
        thumbs.forEach((thumb, i) => {
          const selected = i === current;
          thumb.classList.toggle("is-active", selected);
          if (selected) thumb.setAttribute("aria-current", "true");
          else thumb.removeAttribute("aria-current");
        });
        if (stage) {
          stage.dataset.galleryIndex = String(current);
          [...stage.classList]
            .filter((name) => name.startsWith("product-art--"))
            .forEach((name) => stage.classList.remove(name));
          if (active.dataset.artClass) stage.classList.add(active.dataset.artClass);
        }
        if (mainImage) {
          if (active.dataset.src) mainImage.src = active.dataset.src;
          if (active.dataset.alt) mainImage.alt = active.dataset.alt;
        }
        if (position) position.textContent = `${String(current + 1).padStart(2, "0")} / ${String(thumbs.length).padStart(2, "0")}`;
        if (title) title.textContent = active.dataset.label || "";
        if (description) description.textContent = active.dataset.description || "";
        if (focus) active.focus();
      };

      thumbs.forEach((thumb, index) => thumb.addEventListener("click", () => display(index)));
      gallery.querySelector('[data-gallery-nav="prev"]')?.addEventListener("click", () => display(current - 1));
      gallery.querySelector('[data-gallery-nav="next"]')?.addEventListener("click", () => display(current + 1));

      stage?.addEventListener("keydown", (event) => {
        if (event.key !== "ArrowRight" && event.key !== "ArrowLeft") return;
        event.preventDefault();
        display(current + (event.key === "ArrowRight" ? 1 : -1));
      });
      stage?.addEventListener("touchstart", (event) => {
        if (event.touches.length === 1) touchX = event.touches[0].clientX;
      }, { passive: true });
      stage?.addEventListener("touchend", (event) => {
        if (touchX === null || !event.changedTouches.length) return;
        const delta = event.changedTouches[0].clientX - touchX;
        touchX = null;
        if (Math.abs(delta) >= 45) display(current + (delta < 0 ? 1 : -1));
      }, { passive: true });
      display(current);
    });
  }

  initProductGalleries();
})();
