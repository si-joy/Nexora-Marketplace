/* Compact progressive enhancement: one brand input mode at a time. */
(() => {
  const editor = document.querySelector("[data-brand-editor]");
  if (!editor) return;

  const toggle = editor.querySelector("[data-brand-mode-toggle]");
  const existingWrap = editor.querySelector("[data-brand-existing]");
  const newWrap = editor.querySelector("[data-brand-new]");
  const existing = existingWrap?.querySelector("select");
  const newInput = newWrap?.querySelector("input");
  if (!toggle || !existingWrap || !newWrap || !existing || !newInput) return;

  const showNew = (enabled, focus = false) => {
    existingWrap.hidden = enabled;
    newWrap.hidden = !enabled;
    if (enabled) existing.value = "";
    else newInput.value = "";
    toggle.textContent = enabled ? "Choose existing" : "+ New brand";
    toggle.setAttribute("aria-expanded", String(enabled));
    if (focus) (enabled ? newInput : existing).focus();
  };

  const initialNew = !newWrap.hidden;
  // On invalid submissions Django preserves the user's selected editor.
  showNew(initialNew);
  toggle.addEventListener("click", () => showNew(newWrap.hidden, true));
})();
