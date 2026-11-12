# Nexora Marketplace — Source-Based Page UX Audit

**Scope:** Reviewed the current GitHub `main` source/templates and routes, not a deployed end-to-end browser crawl. The audit covers approximately 36 HTML templates and the related Django URL/view implementations. Individual responsive appearances must still be checked on desktop and mobile.

## Findings fixed in the sitewide UX PR

| Surface | Finding | Improvement |
|---|---|---|
| Navbar (all pages) | Search submit button is hidden on narrow screens | Show the Search control on mobile; label demo catalog search clearly |
| Homepage | Approved seller catalog is discoverable only indirectly | Add a visible Explore seller listings action alongside the demo collection |
| Footer (all pages) | Stale Phase 02 badge and claim that products are only demos | Replace with links and honest current-feature summary |
| Demo notice and bag | Text implied that all products were demos or that real orders were possible | Explain browser-only demo bag and separate approved seller catalog |
| Customer dashboard | Quick actions routed only to demo collection and seller onboarding | Add direct approved listing action |
| Seller dashboard | Stock/fulfillment described as future work with unclear next steps | Direct actions to Add Product and Approved Marketplace; clearly state inventory limitations |
| Seller product management | Long product names can crowd listing controls | Improve title wrapping and link discoverability |
| Product editor | Upload and approval behavior not explained up front | Explain maximum five images, unchanged existing photos, and re-approval after edits |
| Marketplace results | Empty search suggested that no approved products exist | Show query-specific empty message and Clear search action |
| Seller store | Long seller copy and empty storefront states were visually weak | Improve wrapping, spacing, and return action |
| Product tiles | Uneven heights from long titles and narrow columns | Align card content and CTAs; improve mobile padding |
| Wishlist | Browser-only nature was ambiguous | Explain that it stores demo favorites locally |

## Not implemented in this pass — follow-up work, prioritized

1. **Repository drift: essential.** The connected GitHub `main` tree contains demo browser cart and catalog, but **no account-cart API/inventory routes**. Earlier ZIP-based V7 code may exist on other local machines; compare deliberately and port only after database/model review. Do not claim these features are live.
2. **Separate demo and real catalog search:** The shared header currently searches `/shop/` only; real listings require visiting `/market/`. Consider a unified discovery experience after planning query semantics.
3. **Seller stock on product edit:** Add stock initialization and audited adjustment controls only after inventory service/models are on `main`; preserve stock movement history and permissions.
4. **Account-backup wishlist:** The current wishlist uses localStorage only. A persisted wishlist needs authenticated models, privacy decisions, and migration design.
5. **Gallery artwork accuracy:** Demo product pages reuse the same illustration for five thumbnail slots. Use legitimate distinct source images or explicitly mark the gallery as conceptual; do not imply five photographs.
6. **Checkout and payment:** Still not supported in current GitHub version. Requires orders, reservation, seller splitting, payment operations, and security work before enabling.
7. **Accessibility QA:** Test dialog focus behavior, keyboard navigation, color contrast, zoom, mobile tap targets and localized text on supported browsers. Static source inspection cannot replace this.
8. **Product-description structure:** Seller description currently contains unstructured free text, so feature highlights can duplicate description content. Add dedicated specifications later, with data migration/validation.

## Guardrails

- Do not modify existing SQLite migrations, current inventory data or media assets in a purely visual pass.
- Keep semantic theme variables, existing cart/gallery hooks, and all auth/role checks unchanged.
- Test `python manage.py check`, `python -m pytest -q`, and `npm.cmd run build:css` locally. Inspect desktop/mobile in both themes before merging.
- PR #3 (`design/product-detail-spacing-alignment`) is separate. Rebase/merge the final sitewide changes and gallery polish in a controlled order.
