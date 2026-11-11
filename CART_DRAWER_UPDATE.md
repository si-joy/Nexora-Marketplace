# Nexora V5 — Cart drawer + fly-to-cart animation

This update modifies the **existing Nexora V4** Django project. It does not change models, migrations, authentication, database schema, or the light/dark design tokens.

## User experience

- The top navigation **Cart** button opens a right-side modal drawer on every page.
- Clicking **Add to bag** animates the selected product thumbnail into the header cart control, then opens the drawer automatically.
- The cart drawer includes image thumbnails, item titles, per-item subtotals, quantity +/- controls, Remove, Clear bag, full subtotal and a disabled future Checkout button.
- Click the close button, Continue shopping, backdrop, or press Escape to dismiss. Native `<dialog>` supplies modal focus handling.
- The existing browser-storage keys (`nexora.demo.bag` and `nexora.demo.favorites`) remain unchanged. Existing demo cart and wishlist items are preserved on the same origin.
- `prefers-reduced-motion: reduce` skips the fly animation and lengthy transitions.
- Old `/cart/` links now redirect to `/shop/?cart=open`, which opens the same drawer and removes the temporary query parameter.
- Light/dark colors are defined using the existing semantic `--app-*` CSS variables.
- This is still a **browser-only demo cart**. Checkout, actual inventory, payments and saved account-level carts are not implemented.

## Apply the update to an existing V4 project

1. **Back up the project folder**, including `.env` and `db.sqlite3`.
2. Extract the `nexora-v5-cart-drawer-update.zip` contents **into the folder containing `manage.py`**, replacing matching files. Do **not** overwrite `.env`, `.venv`, `db.sqlite3` or migrations.
3. Old `templates/pages/cart.html` is now unused and can be deleted, if present. The `/cart/` route remains for backward compatibility.
4. Open PowerShell in the project folder and run:

```powershell
npm.cmd install
npm.cmd run build:css
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py runserver
```

No database migration is required for this UI change. Hard refresh the browser with **Ctrl + F5**.

## Fresh project

Use the `nexora-marketplace-v5-full.zip` archive and follow README.md. It includes the V4 account/seller apps and the V5 drawer changes.

## Manual checklist

- Click Add to bag on Home, Shop, Wishlist and Product detail. The correct thumbnail should fly toward the header cart icon (unless reduced motion is enabled), and the drawer should slide open.
- Click header Cart to open the drawer directly.
- Use +/- to adjust quantity, Remove to delete one product and Clear bag to empty the demo cart.
- Press Escape or click outside to close; drawer should not navigate to a separate page.
- Refresh and confirm the browser cart persists. Switch between light and dark modes.
- Open an old `/cart/` URL and confirm it redirects to Shop with the drawer open.

## Validation

- Python code compilation and JavaScript syntax passed.
- A headless Chromium smoke test passed for adding an item, drawer open/close, quantities, subtotal, Escape and absence of JS exceptions.
- Full Django tests and Tailwind CSS compilation could not be run in the artifact environment because its Django package and the Tailwind CLI were not available. Run them locally using the commands above.
