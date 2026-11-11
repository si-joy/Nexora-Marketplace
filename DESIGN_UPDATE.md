# Nexora Storefront Refresh · Phase 01

This is a **frontend UI update** for the existing Django multi-vendor marketplace foundation, not a working online store.

## What's new

- Shopping-first storefront instead of a software / architecture landing page
- Announcement bar, responsive search, category navigation, featured hero and promotional tiles
- Six clickable categories, eight sample product cards and local SVG product illustrations
- Working browser-only product search, category filters, favorites and demo bag
- Central light/dark design tokens (including product art backgrounds and promo sections)
- Shared Django template components and unchanged Django backend architecture

No product, account, payment, seller or cart records are saved to the database. Demo favorites and bag are persisted locally in the browser via localStorage.

## Apply to the existing Windows project

**Back up or commit your current project first.**

Extract `nexora-storefront-update.zip` **into your existing** `multivendor-marketplace-foundation` folder, choosing **Replace files**. The update ZIP contains only changed/added source files; it **does not contain `.env`, `db.sqlite3`, `.venv` or `node_modules`**.

From the VS Code PowerShell terminal in your project folder:

```powershell
npm.cmd run build:css
python manage.py runserver
```

Open http://127.0.0.1:8000/ and hard-refresh with `Ctrl+F5` if the old CSS is cached.

If this is a brand-new setup, run `npm.cmd install` first; your existing database setup stays as configured in `.env`.

## Theme source of truth

Edit `static/src/css/app.css` only. All UI semantic colors are defined under `:root[data-theme="light"]` and `:root[data-theme="dark"]`. Tailwind `@theme inline` maps those tokens to semantic utilities used in Django templates. The SVG artwork has its own fixed illustration colors; page/background/button/text colors adapt to the selected theme.

## Included files

- `apps/core/views.py` and `apps/core/tests/test_views.py`
- `templates/base.html`, `templates/pages/home.html`
- `templates/components/navigation/navbar.html`, `templates/components/cards/product_preview.html`
- `templates/components/footer.html`, `templates/components/theme_toggle.html`
- `static/src/css/app.css`, `static/js/storefront.js`
- `static/images/products/` (8 SVGs)

Other project files, including authentication configuration, SQLite database, and environment credentials, remain untouched by the update.
