"""Preview-only sample products. Replace with Product/Store database models in Catalog phase."""

DEMO_CATEGORIES = (
    {"name": "Audio", "slug": "audio", "image": "images/products/headphones.svg", "caption": "Sound & music"},
    {"name": "Wearables", "slug": "wearables", "image": "images/products/watch.svg", "caption": "Everyday smart"},
    {"name": "Computing", "slug": "computing", "image": "images/products/laptop.svg", "caption": "Work & create"},
    {"name": "Gaming", "slug": "gaming", "image": "images/products/controller.svg", "caption": "Play your way"},
    {"name": "Photography", "slug": "photography", "image": "images/products/camera.svg", "caption": "Capture more"},
    {"name": "Lifestyle", "slug": "lifestyle", "image": "images/products/backpack.svg", "caption": "On the move"},
)

DEMO_PRODUCTS = (
    {"id": "studio-headphones", "name": "Studio Wireless Headphones", "subtitle": "Immersive audio · 40h battery", "category": "Audio", "category_slug": "audio", "price": "4,990", "price_value": 4990, "old_price": "6,490", "badge": "Popular", "image": "images/products/headphones.svg", "visual": "audio"},
    {"id": "orbit-watch", "name": "Orbit Smartwatch Series 5", "subtitle": "Stay connected in style", "category": "Wearables", "category_slug": "wearables", "price": "7,890", "price_value": 7890, "old_price": "9,490", "badge": "New", "image": "images/products/watch.svg", "visual": "wearables"},
    {"id": "airbook-laptop", "name": "Airbook Pro 14-inch", "subtitle": "Powerful. Light. Ready to go.", "category": "Computing", "category_slug": "computing", "price": "68,900", "price_value": 68900, "old_price": "", "badge": "", "image": "images/products/laptop.svg", "visual": "computing"},
    {"id": "pulse-controller", "name": "Pulse Wireless Controller", "subtitle": "Precision for every move", "category": "Gaming", "category_slug": "gaming", "price": "3,290", "price_value": 3290, "old_price": "4,190", "badge": "Deal", "image": "images/products/controller.svg", "visual": "gaming"},
    {"id": "pods-lite", "name": "Nova True Wireless Earbuds", "subtitle": "Pocket-size immersive sound", "category": "Audio", "category_slug": "audio", "price": "2,490", "price_value": 2490, "old_price": "3,190", "badge": "", "image": "images/products/earbuds.svg", "visual": "audio"},
    {"id": "zoom-camera", "name": "Focus Mirrorless Camera", "subtitle": "Bring every detail to life", "category": "Photography", "category_slug": "photography", "price": "42,500", "price_value": 42500, "old_price": "", "badge": "New", "image": "images/products/camera.svg", "visual": "photography"},
    {"id": "metro-backpack", "name": "Metro Everyday Backpack", "subtitle": "Designed for daily adventure", "category": "Lifestyle", "category_slug": "lifestyle", "price": "1,890", "price_value": 1890, "old_price": "2,490", "badge": "Deal", "image": "images/products/backpack.svg", "visual": "lifestyle"},
    {"id": "boom-speaker", "name": "Boom Portable Speaker", "subtitle": "Big sound, anywhere", "category": "Audio", "category_slug": "audio", "price": "3,790", "price_value": 3790, "old_price": "", "badge": "", "image": "images/products/speaker.svg", "visual": "audio"},
)


DEMO_STORES = (
    {"name": "Northstar Audio", "slug": "northstar-audio", "tagline": "Sound that moves with you.", "category": "Audio", "initial": "N"},
    {"name": "Orbit Devices", "slug": "orbit-devices", "tagline": "Thoughtful technology for daily life.", "category": "Tech", "initial": "O"},
    {"name": "Everyday Supply", "slug": "everyday-supply", "tagline": "Smart essentials, simply selected.", "category": "Lifestyle", "initial": "E"},
)

PRODUCT_STORES = {
    "studio-headphones": "northstar-audio",
    "pods-lite": "northstar-audio",
    "boom-speaker": "northstar-audio",
    "orbit-watch": "orbit-devices",
    "airbook-laptop": "orbit-devices",
    "pulse-controller": "orbit-devices",
    "zoom-camera": "everyday-supply",
    "metro-backpack": "everyday-supply",
}

PRODUCT_FEATURES = {
    "studio-headphones": ("Comfortable around-ear design", "Wireless everyday listening", "Up to 40 hours (sample specification)"),
    "orbit-watch": ("Bright wearable display", "Everyday activity dashboard", "Designed for comfortable daily wear"),
    "airbook-laptop": ("14-inch portable form factor", "Slim modern silhouette", "Made for work and creativity"),
    "pulse-controller": ("Comfortable ergonomic grip", "Wireless gaming concept", "Responsive directional controls"),
    "pods-lite": ("Pocket-friendly charging case", "Wireless listening", "Minimal lightweight design"),
    "zoom-camera": ("Compact camera silhouette", "Made for on-the-go photography", "Easy-to-carry design"),
    "metro-backpack": ("Everyday travel styling", "Multiple storage compartments", "Comfortable shoulder straps"),
    "boom-speaker": ("Compact portable form", "Wireless audio demo", "Easy-to-carry design"),
}

# Decorated copies keep the original demo catalog immutable and allow one source of truth.
DEMO_PRODUCTS = tuple({
    **product,
    "store_slug": PRODUCT_STORES[product["id"]],
    "store_name": next(store["name"] for store in DEMO_STORES if store["slug"] == PRODUCT_STORES[product["id"]]),
    "features": PRODUCT_FEATURES[product["id"]],
} for product in DEMO_PRODUCTS)
