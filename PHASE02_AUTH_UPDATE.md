# Phase 02 — Authentication & Seller Onboarding

This is a **multi-page Django upgrade**, not a standalone new website. It preserves the Nexora storefront, Tailwind semantic light/dark color variables and SQLite development workflow.

## Implemented

| Feature | Route | Status |
|---|---|---|
| Customer registration | `/account/register/` | Django user created with password hashing |
| Login | `/account/login/` | Session authentication, email sign-in |
| Logout | `POST /account/logout/` | CSRF-protected form; no logout via GET |
| Customer dashboard | `/account/dashboard/` | Login required |
| Password change | `/account/password/change/` | Login required |
| Password reset | `/account/password/reset/` | Local console email backend |
| Seller application | `/seller/apply/` | Login required; open to customers |
| Seller dashboard or approval status | `/seller/dashboard/` | Only approved sellers with an active store can see management dashboard |
| Admin approval | `/admin/vendors/sellerprofile/` | Django admin bulk actions: Approve, Reject, Suspend |

A seller application **does not** confer seller privileges. Seller status can move from pending to under review, approved, rejected or suspended only by authorized staff with `vendors.change_sellerprofile` permission; a `Store` is created on approval. A seller can also shop as a customer. Rejected applications may be resubmitted; suspended sellers cannot reapply automatically.

## How to upgrade an existing V3 project

1. **Back up** the entire project directory, including `db.sqlite3` and `.env`.
2. Extract the **V4 UPDATE ZIP** into the existing project folder, preserving the directory structure. It does not contain `.env`, `db.sqlite3`, `.venv`, `node_modules` or an accounts initial migration.
3. Make sure your **project's** virtual environment is activated and your working directory contains `manage.py` and `package.json`.
4. Run these PowerShell commands:

```powershell
cd "C:\Users\SI Joy\Desktop\multivendor-marketplace-foundation"
.\.venv\Scripts\Activate.ps1
python manage.py migrate
python manage.py check
python -m pytest
npm.cmd install
npm.cmd run build:css
python manage.py runserver
```

If your previous project **does not have** `apps/accounts/migrations/0001_initial.py`, generate the existing user migration **before extracting** V4, or use the **V4 FULL ZIP** as a new project; do **not** overwrite a migration that was previously applied. For a new V4 FULL ZIP project, `python manage.py migrate` is sufficient (both initial migrations are included).

If you never created a superuser:

```powershell
python manage.py createsuperuser
```

Create a customer via `/account/register/`, submit a seller application via `/seller/apply/`, then use the superuser at `/admin/` → **Seller profiles** → select pending application → **Approve selected pending sellers**. After approval, sign in as the seller and visit `/seller/dashboard/`.

## Database additions

- `vendors_sellerprofile` — exactly one application profile per user; application status and approval metadata.
- `vendors_store` — exactly one store per approved seller; store status and unique slug.

The existing custom `accounts.User` model is **unchanged**. Seller data lives in a new `vendors` app. The application review service runs inside a database transaction and checks staff permissions before state transitions.

## Not implemented / important production steps

This is a **development MVP**. The catalog is still fixture-backed demo data; seller product management, real customer orders, shipping, marketplace financials, payouts, checkout and payment processing are **not yet implemented**.

Before launching publicly: enable email verification, login/registration/password-reset rate limiting and abuse protection, replace console email with a verified provider, add seller identity/KYC verification, review privacy requirements, use PostgreSQL and robust backups, configure HTTPS and secure secrets, and thoroughly audit permissions and financial flows. Do not accept real customer orders or payments with this starter.

## Quality checks

`python -m pytest` includes existing storefront tests and new customer auth, seller workflow, permission, rejection and suspension tests. Run these on your local machine with dependencies installed. The ZIP was statically checked but was not fully run against Django in the build environment.
