# Nexora V6 — Phase 03A: Database-backed Catalog

This release builds on **Nexora V5** (cart drawer + V4 authentication). It does not overwrite your `.env`, local SQLite database, virtual environment, Node packages or uploaded media.

## Included

- Relational `Category`, `Brand`, `Currency`, `Product`, `ProductVariant`, `ProductVariantPrice`, `ProductImage` models and versioned migrations.
- One default SKU and BDT price per seller product for this first management screen; data model is ready for multiple variants and currencies later.
- Approved seller-only product list, create/edit, image upload and submit for admin review.
- Admin moderation through Django Admin > Products > Actions.
- Public, database-backed marketplace listings and product/store detail pages **separate from** existing demo products and demo cart.
- Reusable templates, read selectors, transactional write services, validation, permission tests.
- Local media configuration; development-only media serving. **Before public deployment, configure proper object storage (such as Cloudflare R2)**.

## Apply V6 Update to an existing V5 folder

Back up `db.sqlite3`, `.env`, and `media/` first. Extract the **update ZIP** over your existing V5 project root (next to `manage.py`) and allow code files to be replaced. Do **not** delete your existing database or migrations.

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements/development.txt
python manage.py migrate
python manage.py seed_catalog
python manage.py check
python -m pytest
npm.cmd run build:css
python manage.py runserver
```

If your PowerShell execution policy blocks activation, use the virtual environment's `python.exe` directly or the session-only execution policy already used in V5.

## Pages / workflow

- `/seller/dashboard/` — approved seller overview.
- `/seller/products/` — seller product list.
- `/seller/products/new/` — add draft, SKU, BDT price, photo.
- `/seller/products/<id>/edit/` — edit product and submit for review.
- `/admin/` → Catalog → Products → **Approve selected pending products**.
- `/market/` — real approved database-backed listings (not the demo shop).
- `/market/product/<slug>/` and `/market/store/<slug>/` — product/store pages.

Categories are initialized by `python manage.py seed_catalog`, or edited in Django Admin. Brands can be created in Django Admin.

### Safety and feature boundaries

- Product submissions require a valid photo, an active category, and a BDT price.
- The seller cannot access another seller's products. Editing published products returns them to Draft, requiring reapproval.
- Public listings include only published products of active stores belonging to approved sellers.
- Demo products remain on Home / Shop and continue using the existing browser-based Wishlist / Cart Drawer / fly-to-cart animation. **Actual seller products cannot be purchased yet.**
- This phase intentionally doesn't implement inventory locks, multi-variant management UI, checkout, payments or shipping. Those must be added and tested before accepting real orders.

## Pre-flight verification

Python bytecode compilation, JavaScript syntax check, static URL name checks and archive integrity tests were run on the code. Full Django migrations and pytest are **not run in this environment** because Django could not be installed due to the environment's unavailable package network. Your local `python manage.py migrate` and `python -m pytest` are required acceptance tests.
