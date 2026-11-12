/* Price preview only. Server-side forms and services validate actual prices. */
(() => {
  const regular = document.querySelector('[name="price_bdt"]');
  const sale = document.querySelector('[name="sale_price_bdt"]');
  const final = document.querySelector("[data-price-preview-final]");
  const original = document.querySelector("[data-price-preview-original]");
  const badge = document.querySelector("[data-price-preview-badge]");
  const note = document.querySelector("[data-price-preview-error]");
  if (!regular || !sale || !final || !original || !badge || !note) return;

  const money = (value) => `৳${value.toLocaleString("en-BD", {
    minimumFractionDigits: 2, maximumFractionDigits: 2,
  })}`;

  const refresh = () => {
    const regularAmount = Number(regular.value);
    const saleAmount = Number(sale.value);
    const validRegular = regular.value.trim() !== "" && Number.isFinite(regularAmount) && regularAmount > 0;
    const saleEntered = sale.value.trim() !== "";
    const validSale = saleEntered && Number.isFinite(saleAmount) && saleAmount > 0 && saleAmount < regularAmount;
    final.textContent = validRegular ? money(validSale ? saleAmount : regularAmount) : "—";
    original.hidden = !validSale;
    badge.hidden = !validSale;
    original.textContent = validSale ? money(regularAmount) : "";
    badge.textContent = validSale ? `${Math.round((1 - saleAmount / regularAmount) * 100)}% off` : "";
    note.textContent = saleEntered && !validSale
      ? "Sale price must be lower than regular price."
      : "The cart always uses the effective selling price.";
    note.classList.toggle("text-danger", saleEntered && !validSale);
    note.classList.toggle("text-muted", !saleEntered || validSale);
  };

  regular.addEventListener("input", refresh);
  sale.addEventListener("input", refresh);
  refresh();
})();
