"""Market definitions — 50 diverse tasks spanning the full price/quality spectrum.

Each market has different economics, creating varied competitive dynamics.
Think of this as the "order book" — the demand side of the exchange.
"""

MARKETS = [
    # ══════════════════════════════════════════════════════════════════
    # PENNY MARKETS ($0.012-0.02, quality 3-5)
    # Only the cheapest model fits. Tests: who can even afford to play?
    # ══════════════════════════════════════════════════════════════════
    {"id": "P01", "prompt": "A red circle on white", "max_price": 0.012, "min_quality": 3,
     "criteria": ["Shows a red circle"], "tier": "penny"},
    {"id": "P02", "prompt": "A green tree", "max_price": 0.013, "min_quality": 4,
     "criteria": ["Shows a tree that is green"], "tier": "penny"},
    {"id": "P03", "prompt": "A yellow sun", "max_price": 0.015, "min_quality": 3,
     "criteria": ["Shows a sun"], "tier": "penny"},
    {"id": "P04", "prompt": "A blue house", "max_price": 0.018, "min_quality": 5,
     "criteria": ["Shows a blue house"], "tier": "penny"},
    {"id": "P05", "prompt": "A cat face", "max_price": 0.014, "min_quality": 4,
     "criteria": ["Shows a cat's face"], "tier": "penny"},
    {"id": "P06", "prompt": "A mountain silhouette", "max_price": 0.012, "min_quality": 3,
     "criteria": ["Shows mountains as silhouettes"], "tier": "penny"},
    {"id": "P07", "prompt": "A single candle flame", "max_price": 0.016, "min_quality": 4,
     "criteria": ["Shows a lit candle"], "tier": "penny"},
    {"id": "P08", "prompt": "A paper airplane", "max_price": 0.015, "min_quality": 4,
     "criteria": ["Shows a paper airplane"], "tier": "penny"},

    # ══════════════════════════════════════════════════════════════════
    # BUDGET MARKETS ($0.025-0.05, quality 5-6)
    # Cheap models dominate. Speed wins at this quality bar.
    # ══════════════════════════════════════════════════════════════════
    {"id": "B01", "prompt": "A golden retriever sitting in grass", "max_price": 0.03, "min_quality": 5,
     "criteria": ["Shows a golden retriever in grass"], "tier": "budget"},
    {"id": "B02", "prompt": "A coffee cup on a wooden table", "max_price": 0.035, "min_quality": 5,
     "criteria": ["Coffee cup on wood surface"], "tier": "budget"},
    {"id": "B03", "prompt": "A sunset over the ocean with orange sky", "max_price": 0.04, "min_quality": 5,
     "criteria": ["Sunset over water, orange tones"], "tier": "budget"},
    {"id": "B04", "prompt": "A red sports car on an empty road", "max_price": 0.05, "min_quality": 6,
     "criteria": ["Red car on a road, car is recognizable"], "tier": "budget"},
    {"id": "B05", "prompt": "A snowman with a top hat and carrot nose", "max_price": 0.04, "min_quality": 5,
     "criteria": ["Snowman with hat and carrot nose"], "tier": "budget"},
    {"id": "B06", "prompt": "A bowl of ramen with chopsticks", "max_price": 0.045, "min_quality": 6,
     "criteria": ["Bowl of ramen, chopsticks visible"], "tier": "budget"},
    {"id": "B07", "prompt": "A lighthouse on a rocky cliff", "max_price": 0.03, "min_quality": 5,
     "criteria": ["Lighthouse on cliff/rocks"], "tier": "budget"},

    # ══════════════════════════════════════════════════════════════════
    # MID MARKETS ($0.08-0.15, quality 7)
    # The contested zone. Speed matters but quality bar filters junk.
    # ══════════════════════════════════════════════════════════════════
    {"id": "M01", "prompt": "A cat wearing a tiny crown on a velvet throne, Renaissance lighting",
     "max_price": 0.10, "min_quality": 7, "tier": "mid",
     "criteria": ["Cat on throne with crown visible", "Renaissance-style dramatic lighting",
                  "Fabric texture looks rich"]},
    {"id": "M02", "prompt": "A Japanese garden in autumn — red bridge, koi pond, falling maple leaves, morning mist",
     "max_price": 0.12, "min_quality": 7, "tier": "mid",
     "criteria": ["All elements: bridge, koi, maple, mist", "Autumn color palette",
                  "Serene composition"]},
    {"id": "M03", "prompt": "A steampunk airship with brass details flying through golden hour clouds",
     "max_price": 0.10, "min_quality": 7, "tier": "mid",
     "criteria": ["Steampunk aesthetic with brass/gears", "Golden hour lighting",
                  "Airship clearly the subject"]},
    {"id": "M04", "prompt": "A cozy bookshop interior on a rainy evening — warm lamps, overflowing shelves, cat on books",
     "max_price": 0.15, "min_quality": 7, "tier": "mid",
     "criteria": ["Warm interior atmosphere", "Rain visible", "Cat sleeping on books"]},
    {"id": "M05", "prompt": "A wolf howling at a full moon on a snowy cliff, northern lights behind",
     "max_price": 0.10, "min_quality": 7, "tier": "mid",
     "criteria": ["Wolf howling at moon", "Snow environment", "Aurora in sky"]},
    {"id": "M06", "prompt": "A medieval market square at dawn — merchant stalls, cobblestones, warm bread steam",
     "max_price": 0.12, "min_quality": 7, "tier": "mid",
     "criteria": ["Medieval setting", "Market stalls/merchants", "Dawn lighting with steam"]},
    {"id": "M07", "prompt": "An astronaut planting a flag on Mars with Earth visible in the sky",
     "max_price": 0.10, "min_quality": 7, "tier": "mid",
     "criteria": ["Astronaut on Mars surface", "Flag planting", "Earth in sky"]},
    {"id": "M08", "prompt": "A dragon sleeping on a pile of gold coins in a torch-lit cave",
     "max_price": 0.14, "min_quality": 7, "tier": "mid",
     "criteria": ["Dragon clearly sleeping", "Gold coins visible", "Torch lighting"]},

    # ══════════════════════════════════════════════════════════════════
    # PREMIUM MARKETS ($0.20-0.50, quality 8-9)
    # High bar. Only excellent images pass. Budget agents will fail.
    # ══════════════════════════════════════════════════════════════════
    {"id": "X01", "prompt": "Photorealistic close-up: elderly fisherman on boat at dawn, weathered face, "
     "salt-and-pepper beard, golden light reflecting in eyes, every pore visible",
     "max_price": 0.30, "min_quality": 8, "tier": "premium",
     "criteria": ["Photorealism: could be a photograph", "Face detail: wrinkles, pores, hairs",
                  "Golden dawn light in eyes", "Emotional depth in expression"]},
    {"id": "X02", "prompt": "Dutch Golden Age still life: silver goblet, ripe peaches, half-peeled lemon "
     "with spiral peel, purple grapes, butterfly on flower, dark marble ledge, dramatic side lighting",
     "max_price": 0.35, "min_quality": 8, "tier": "premium",
     "criteria": ["Period-accurate Dutch style", "All objects present", "Chiaroscuro lighting",
                  "Texture mastery: metal, fruit skin, marble"]},
    {"id": "X03", "prompt": "Fantasy city built into a massive waterfall — bridges between towers, "
     "glowing windows at dusk, flying creatures, rainbow in mist, cinematic widescreen",
     "max_price": 0.40, "min_quality": 8, "tier": "premium",
     "criteria": ["Epic scale", "Waterfall integration", "Atmospheric depth",
                  "Cinematic composition"]},
    {"id": "X04", "prompt": "Hyperrealistic macro: single dewdrop on spider web at sunrise, "
     "entire garden reflected inverted inside droplet, bokeh wildflower background",
     "max_price": 0.25, "min_quality": 9, "tier": "premium",
     "criteria": ["Macro realism", "Reflection inside dewdrop", "Spider web strands",
                  "Bokeh with correct depth of field"]},
    {"id": "X05", "prompt": "Architectural visualization: futuristic museum at night — parametric white facade, "
     "glass galleries glowing inside, reflecting pool, human silhouettes for scale",
     "max_price": 0.50, "min_quality": 8, "tier": "premium",
     "criteria": ["Architectural quality", "Parametric organic forms", "Night lighting",
                  "Reflection pool", "Human scale"]},
    {"id": "X06", "prompt": "Photorealistic aerial view of a coral reef teeming with tropical fish, "
     "sea turtle gliding through, sunbeams penetrating turquoise water, shot from above",
     "max_price": 0.30, "min_quality": 8, "tier": "premium",
     "criteria": ["Photorealistic underwater scene", "Multiple fish species visible",
                  "Sea turtle clearly present", "Sunbeam light rays through water"]},
    {"id": "X07", "prompt": "Renaissance oil painting of a modern-day street food vendor — same technique "
     "as Vermeer, but the subject wears a baseball cap and serves tacos from a cart",
     "max_price": 0.35, "min_quality": 8, "tier": "premium",
     "criteria": ["Vermeer-quality technique: light, texture, composition",
                  "Modern subject matter: baseball cap, tacos, food cart",
                  "Juxtaposition feels intentional, not accidental"]},

    # ══════════════════════════════════════════════════════════════════
    # CREATIVE MARKETS ($0.10-0.25, quality 7-8)
    # Abstract/conceptual prompts. Tests artistic interpretation.
    # ══════════════════════════════════════════════════════════════════
    {"id": "C01", "prompt": "Visualize the feeling of nostalgia", "max_price": 0.15, "min_quality": 7,
     "tier": "creative",
     "criteria": ["Evokes nostalgia emotionally", "Creative, not literal",
                  "Unified mood and palette"]},
    {"id": "C02", "prompt": "What silence looks like in a forest", "max_price": 0.12, "min_quality": 7,
     "tier": "creative",
     "criteria": ["Evokes silence and stillness", "Atmospheric quality",
                  "Beyond literal empty forest"]},
    {"id": "C03", "prompt": "The last page of a story nobody finished", "max_price": 0.20, "min_quality": 8,
     "tier": "creative",
     "criteria": ["Narrative quality", "Emotional weight: incompleteness",
                  "Surprising interpretation rewarded"]},
    {"id": "C04", "prompt": "A color that doesn't exist yet", "max_price": 0.15, "min_quality": 7,
     "tier": "creative",
     "criteria": ["Creative audacity", "Visual impact", "Needs concept, not just gradient"]},
    {"id": "C05", "prompt": "The moment between sleeping and waking", "max_price": 0.18, "min_quality": 7,
     "tier": "creative",
     "criteria": ["Liminal quality", "Dreamlike yet grounded", "Evokes the hypnagogic state"]},
    {"id": "C06", "prompt": "What music tastes like", "max_price": 0.15, "min_quality": 7,
     "tier": "creative",
     "criteria": ["Synesthesia concept", "Sensory cross-wiring visualized",
                  "Not just musical instruments"]},
    {"id": "C07", "prompt": "The weight of an unspoken apology", "max_price": 0.20, "min_quality": 8,
     "tier": "creative",
     "criteria": ["Emotional complexity", "Visual metaphor for regret/heaviness",
                  "Human vulnerability"]},
    {"id": "C08", "prompt": "If gravity worked sideways for one second", "max_price": 0.12, "min_quality": 7,
     "tier": "creative",
     "criteria": ["Physics concept visualized", "Dynamic motion/chaos",
                  "Playful or dramatic interpretation"]},

    # ══════════════════════════════════════════════════════════════════
    # STRESS MARKETS ($0.06-0.08, quality 6-7)
    # Just above budget, just below mid. Maximum competitive tension.
    # ══════════════════════════════════════════════════════════════════
    {"id": "S01", "prompt": "A pirate ship at sunset", "max_price": 0.06, "min_quality": 6,
     "tier": "stress",
     "criteria": ["Pirate ship clearly visible", "Sunset lighting"]},
    {"id": "S02", "prompt": "A robot reading a book in a library", "max_price": 0.07, "min_quality": 6,
     "tier": "stress",
     "criteria": ["Robot identifiable", "Library setting", "Book in hand/view"]},
    {"id": "S03", "prompt": "A fox in an autumn forest", "max_price": 0.065, "min_quality": 7,
     "tier": "stress",
     "criteria": ["Fox clearly visible", "Autumn colors", "Forest setting"]},
    {"id": "S04", "prompt": "A hot air balloon over lavender fields", "max_price": 0.075, "min_quality": 6,
     "tier": "stress",
     "criteria": ["Hot air balloon in sky", "Lavender fields below"]},
    {"id": "S05", "prompt": "A wizard's tower on a floating island", "max_price": 0.08, "min_quality": 7,
     "tier": "stress",
     "criteria": ["Tower on floating island", "Magical/fantasy atmosphere"]},
    {"id": "S06", "prompt": "A polar bear on an ice floe under aurora", "max_price": 0.07, "min_quality": 7,
     "tier": "stress",
     "criteria": ["Polar bear on ice", "Aurora visible in sky", "Arctic atmosphere"]},
]

TIER_INFO = {
    "penny":   {"color": "\033[90m", "label": "PENNY",   "desc": "$0.01-0.02, q≥3-5"},
    "budget":  {"color": "\033[32m", "label": "BUDGET",  "desc": "$0.03-0.05, q≥5-6"},
    "stress":  {"color": "\033[38;5;208m", "label": "STRESS",  "desc": "$0.06-0.08, q≥6-7"},
    "mid":     {"color": "\033[33m", "label": "MID",     "desc": "$0.08-0.15, q≥7"},
    "premium": {"color": "\033[35m", "label": "PREMIUM", "desc": "$0.20-0.50, q≥8-9"},
    "creative":{"color": "\033[36m", "label": "CREATIVE","desc": "$0.10-0.25, q≥7-8"},
}
RESET = "\033[0m"
