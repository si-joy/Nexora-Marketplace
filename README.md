# Nexora · Multi-Vendor Marketplace (V6 · Phase 03A Catalog)

Django 5.2 modular monolith + Tailwind v4 + semantic light/dark mode. V3 provided multi-page shopping demo. **V4 adds real account registration, secure session login, password change/reset, customer dashboard, seller applications, admin approval and a permission-gated seller dashboard.**

See [CATALOG_PHASE03_UPDATE.md](CATALOG_PHASE03_UPDATE.md) for the database-backed catalog, seller product creation, moderation and update instructions.

See [CART_DRAWER_UPDATE.md](CART_DRAWER_UPDATE.md) for the right-side cart drawer, thumbnail animation and legacy-cart redirect.

See [PHASE02_AUTH_UPDATE.md](PHASE02_AUTH_UPDATE.md) for all routes, Windows setup, upgrade precautions and production limitations.

## New project (Windows PowerShell)

```powershell
py -3.14 -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements/development.txt
Copy-Item .env.example .env
# Local development: DATABASE_URL=sqlite:///db.sqlite3
python manage.py migrate
python manage.py seed_catalog
python manage.py createsuperuser
npm.cmd install
npm.cmd run build:css
python manage.py check
python -m pytest
python manage.py runserver
```

**Upgrading V5?** Use the V6 Catalog UPDATE ZIP. Back up `.env`, `db.sqlite3` and `media/`. Preserve all existing accounts/vendor migrations and SQLite data. Do not run migration reset commands.

## Code organization

- `apps/accounts/` — custom email-based user, forms, views, auth URLs and tests.
- `apps/vendors/` — seller profile and store, application form, transactional services, admin approval actions, dashboard and tests.
- `apps/catalog/` — separate demo catalog plus relational category/product/variant/image models, seller product services, admin review and live marketplace pages.
- `apps/shopping/` — shared animated cart drawer and browser-only wishlist (not a backend checkout).
- `templates/components/` — reusable navigation, drawer, form fields, error boxes, product card and footer.
- `static/src/css/app.css` — centralized semantic theme tokens for both light/dark mode.

## Production status

This is **not** ready for real commerce. Before public launch: implement verified emails, abuse/rate limiting, security hardening, PostgreSQL backups and inventory/payment/order workflows. For local testing SQLite is supported; production settings require PostgreSQL.
