# Nexora multi-page storefront — Phase 01.5

The first visual demo was a single homepage with in-page filtering. This update adds **real Django URL routes and separate templates**, while keeping the same reusable navbar, footer, product cards, CSS variables, and light/dark mode.

## Routes

| Page | URL |
| --- | --- |
| Home | `/` |
| Shop (search, sort, category filter, pagination) | `/shop/` |
| Categories index | `/categories/` |
| Category detail | `/category/audio/` (and other categories) |
| Product details | `/product/studio-headphones/` (and other products) |
| Seller directories | `/stores/` |
| Demo store detail | `/store/northstar-audio/` (and others) |
| Shopping cart (browser-only demo) | `/cart/` |
| Wishlist (browser-only demo) | `/wishlist/` |
| Django Admin | `/admin/` |

### What works

- All page links navigate to the real route, with a shared responsive layout.
- Search, sort, category filtering and pagination run in Django views.
- Individual product details and seller store pages have dedicated views and templates.
- Demo add-to-cart and wishlist operate across pages using the existing `localStorage` keys (`nexora.demo.bag`, `nexora.demo.favorites`). Quantity updates, removal and cart summary work entirely in the browser.
- Light/dark palette is still managed exclusively in `static/src/css/app.css` semantic variables.

### What is deliberately not implemented

Sample catalog data still lives in `apps/catalog/demo_data.py`. It is not fetched from database models. Sellers are fictional sample stores. Cart, wishlist and subtotal are **not secure, account-synced, server-side order records**. Real product models, customer authentication, inventory, checkout, taxes, shipping, payment and orders remain future phases. The disabled checkout button is intentional.

## Installation on your existing project (Windows PowerShell)

1. Backup your project folder.
2. Extract `nexora-multipage-update.zip` into the **project folder that contains `manage.py` and `package.json`**. Allow merging/replacement.
3. Keep your existing `.env`, `db.sqlite3`, and `.venv`—none are included in the update.
4. Run:

```powershell
cd "C:\Users\SI Joy\Desktop\multivendor-marketplace-foundation"
.\.venv\Scripts\Activate.ps1
npm.cmd install
npm.cmd run build:css
python manage.py check
python manage.py runserver
```

Change the folder path if yours is different. If PowerShell blocks activation, use `Set-ExecutionPolicy -Scope Process Bypass` in that terminal, or call `.\.venv\Scripts\python.exe` directly.

No new database models or migrations are needed for this multi-page UI update. To run tests use `python -m pytest` after dependencies are installed.

## Code organization

- `apps/core`: homepage
- `apps/catalog`: demo data, selectors, storefront URL/routes/views
- `apps/shopping`: demo cart and wishlist routes/views
- `templates/pages`: distinct Django page templates
- `templates/components`: shared header/footer, product cards and notices
- `static/js/storefront.js`: shared demo cart and wishlist UI on every page
- `static/src/css/app.css`: the same light/dark semantic theme tokens

Production settings explicitly require a PostgreSQL `DATABASE_URL`. Local development defaults to SQLite when no DATABASE_URL is provided; never deploy the demo cart/payment state for real customer orders.
