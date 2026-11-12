/* Five-slot seller gallery preview. File bytes are saved only on form submit. */
(() => {
  const root = document.querySelector("[data-seller-gallery]");
  if (!root) return;

  const supported = new Set(["image/jpeg", "image/png", "image/webp"]);
  const maxBytes = 5 * 1024 * 1024;
  const blobUrls = new Set();

  root.querySelectorAll("[data-gallery-upload-slot]").forEach((slot) => {
    const input = slot.querySelector('input[type="file"]');
    const image = slot.querySelector("[data-gallery-upload-preview]");
    const placeholder = slot.querySelector("[data-gallery-upload-placeholder]");
    const status = slot.querySelector("[data-gallery-upload-status]");
    if (!input || !image || !placeholder || !status) return;

    const initialSource = image.getAttribute("src");
    const initialText = status.textContent;
    let previewUrl = null;

    const release = () => {
      if (!previewUrl) return;
      URL.revokeObjectURL(previewUrl);
      blobUrls.delete(previewUrl);
      previewUrl = null;
    };
    const restore = () => {
      release();
      if (initialSource) image.src = initialSource;
      else image.removeAttribute("src");
      image.hidden = !initialSource;
      placeholder.hidden = !!initialSource;
      status.textContent = initialText;
      status.classList.remove("text-danger");
    };

    input.addEventListener("change", () => {
      const file = input.files?.[0];
      if (!file) {
        restore();
        return;
      }
      const extension = file.name.toLowerCase().split(".").pop();
      const extensionMatches =
        (file.type === "image/jpeg" && ["jpg", "jpeg"].includes(extension)) ||
        (file.type === "image/png" && extension === "png") ||
        (file.type === "image/webp" && extension === "webp");
      if (!supported.has(file.type) || !extensionMatches || file.size > maxBytes) {
        input.value = "";
        restore();
        status.textContent = file.size > maxBytes
          ? "File too large (max 5 MB)"
          : "Choose JPG, PNG or WebP";
        status.classList.add("text-danger");
        return;
      }
      release();
      previewUrl = URL.createObjectURL(file);
      blobUrls.add(previewUrl);
      image.src = previewUrl;
      image.hidden = false;
      placeholder.hidden = true;
      status.classList.remove("text-danger");
      status.textContent = "New preview · save to apply";
    });
  });

  window.addEventListener("pagehide", () => {
    blobUrls.forEach((url) => URL.revokeObjectURL(url));
    blobUrls.clear();
  }, { once: true });
})();
