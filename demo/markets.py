"""Market definitions — 44 demanding tasks with high quality standards.

Every buyer is specific about what they want. Every market has multiple
criteria that the judge evaluates independently. Quality bars are set
high enough to filter mediocre work — even at low price points.

The exchange only produces value if the quality bar forces real competition
on quality, not just speed.
"""

MARKETS = [
    # ══════════════════════════════════════════════════════════════════
    # PENNY MARKETS ($0.012-0.02, quality 7)
    # Cheap but demanding. Simple subjects, high execution standards.
    # Budget agents must produce GOOD images to qualify.
    # ══════════════════════════════════════════════════════════════════
    {"id": "P01", "max_price": 0.012, "min_quality": 7, "tier": "penny",
     "prompt": "A single red apple on a white marble countertop, soft natural "
               "window light from the left, subtle shadow, photographic style",
     "criteria": ["Apple looks real — skin texture, highlight, stem detail",
                  "Marble surface has visible veining",
                  "Lighting is soft and directional, not flat"]},

    {"id": "P02", "max_price": 0.013, "min_quality": 7, "tier": "penny",
     "prompt": "A lone oak tree in a golden wheat field at magic hour, "
               "long dramatic shadow stretching toward camera",
     "criteria": ["Tree is clearly an oak with proper canopy shape",
                  "Golden hour light with warm/cool contrast",
                  "Shadow extends correctly toward viewer"]},

    {"id": "P03", "max_price": 0.015, "min_quality": 7, "tier": "penny",
     "prompt": "A lit match in complete darkness, the flame illuminating "
               "only the match head and fingertips holding it",
     "criteria": ["Flame is realistic with proper glow falloff",
                  "Darkness is truly dark — not gray",
                  "Fingertips lit by warm light, everything else black"]},

    {"id": "P04", "max_price": 0.018, "min_quality": 7, "tier": "penny",
     "prompt": "A glass of water on a windowsill with afternoon sun creating "
               "a caustic light pattern on the wall behind it",
     "criteria": ["Glass refracts light realistically",
                  "Caustic rainbow/pattern visible on wall",
                  "Water is transparent with meniscus visible"]},

    {"id": "P05", "max_price": 0.014, "min_quality": 7, "tier": "penny",
     "prompt": "A closed leather-bound book on a dark wood desk, "
               "a single reading lamp illuminating it from above",
     "criteria": ["Leather texture visible on book cover",
                  "Wood grain on desk surface",
                  "Pool of lamplight with realistic falloff"]},

    {"id": "P06", "max_price": 0.012, "min_quality": 7, "tier": "penny",
     "prompt": "A hummingbird frozen mid-flight next to a red flower, "
               "wings blurred with motion, sharp eye detail",
     "criteria": ["Wing motion blur looks natural",
                  "Eye is sharp and detailed",
                  "Iridescent feather colors visible"]},

    {"id": "P07", "max_price": 0.016, "min_quality": 7, "tier": "penny",
     "prompt": "Rain hitting a puddle on asphalt — concentric ripples, "
               "city lights reflected and distorted in the water",
     "criteria": ["Ripple physics look correct",
                  "Reflected lights are distorted by ripples",
                  "Asphalt texture visible around puddle"]},

    {"id": "P08", "max_price": 0.015, "min_quality": 7, "tier": "penny",
     "prompt": "A monarch butterfly perched on a child's outstretched finger, "
               "backlit by golden sun, wing veins visible",
     "criteria": ["Wing pattern is accurate for monarch species",
                  "Backlighting creates translucency in wings",
                  "Finger proportions correct for a child"]},

    # ══════════════════════════════════════════════════════════════════
    # BUDGET MARKETS ($0.025-0.05, quality 8)
    # Affordable but the bar is 8/10. Needs strong execution.
    # ══════════════════════════════════════════════════════════════════
    {"id": "B01", "max_price": 0.03, "min_quality": 8, "tier": "budget",
     "prompt": "A golden retriever mid-leap catching a frisbee in a park, "
               "ears flying, all four paws off ground, joyful expression, "
               "shallow depth of field with blurred trees behind",
     "criteria": ["Dog anatomy correct — no extra legs or merged limbs",
                  "Genuine motion and energy in the pose",
                  "Bokeh background with proper depth separation",
                  "Frisbee in mouth or about to be caught"]},

    {"id": "B02", "max_price": 0.035, "min_quality": 8, "tier": "budget",
     "prompt": "Latte art in the shape of a fern leaf in a ceramic cup, "
               "steam rising, coffee beans scattered on the saucer, "
               "morning light from a nearby window",
     "criteria": ["Latte art pattern is a recognizable fern/rosetta",
                  "Steam looks natural, not painted on",
                  "Coffee beans look individual and real",
                  "Ceramic cup has realistic glaze and rim"]},

    {"id": "B03", "max_price": 0.04, "min_quality": 8, "tier": "budget",
     "prompt": "Sunset at Santorini — white-washed buildings with blue domes, "
               "the caldera below, orange-pink sky gradient, a single "
               "bougainvillea vine in the foreground",
     "criteria": ["Architecture is recognizably Santorini",
                  "Sky gradient transitions smoothly from warm to cool",
                  "Bougainvillea flowers are detailed, not blobs",
                  "Caldera/sea visible in background"]},

    {"id": "B04", "max_price": 0.05, "min_quality": 8, "tier": "budget",
     "prompt": "A 1967 Ford Mustang in cherry red, parked on a desert highway "
               "at dusk, headlights on, Route 66 sign visible, "
               "long exposure streaks from passing traffic in background",
     "criteria": ["Car model recognizable as 1960s Mustang",
                  "Chrome and paint reflections look real",
                  "Light streaks from long exposure in background",
                  "Desert landscape with dusk sky colors"]},

    {"id": "B05", "max_price": 0.04, "min_quality": 8, "tier": "budget",
     "prompt": "A snowman in a quiet backyard at twilight — coal eyes, "
               "carrot nose, plaid scarf, a child's mittens left on "
               "a nearby fence post, warm light from a kitchen window",
     "criteria": ["Snowman has character — not generic",
                  "Twilight blue-hour lighting with warm window glow",
                  "Small narrative details: mittens, scarf texture",
                  "Snow has realistic surface texture"]},

    {"id": "B06", "max_price": 0.045, "min_quality": 8, "tier": "budget",
     "prompt": "A steaming bowl of tonkotsu ramen — rich milky broth, "
               "chashu pork slices, soft-boiled egg cut in half showing "
               "jammy yolk, green onions, nori, on a dark wood counter",
     "criteria": ["Broth looks milky and rich, not watery",
                  "Egg yolk is jammy orange, not fully cooked",
                  "Each topping is individually identifiable",
                  "Food photography quality — appetizing"]},

    {"id": "B07", "max_price": 0.03, "min_quality": 8, "tier": "budget",
     "prompt": "Portland Head Light in Maine during a nor'easter — massive "
               "waves crashing against rocks, lighthouse beam cutting "
               "through spray, dramatic overcast sky",
     "criteria": ["Lighthouse architecture is detailed and realistic",
                  "Wave dynamics look powerful and realistic",
                  "Spray and mist create atmospheric depth",
                  "Dramatic lighting through storm clouds"]},

    # ══════════════════════════════════════════════════════════════════
    # MID MARKETS ($0.08-0.15, quality 8)
    # Complex multi-element scenes. Every detail matters.
    # ══════════════════════════════════════════════════════════════════
    {"id": "M01", "max_price": 0.10, "min_quality": 8, "tier": "mid",
     "prompt": "A Persian cat wearing a tiny gold crown, sitting regally on a "
               "crimson velvet throne in a baroque palace room — oil painting "
               "style with visible brushstrokes, gold-leaf frame implied by "
               "the composition, chiaroscuro lighting from a single candelabra",
     "criteria": ["Cat anatomy perfect — no deformities, correct proportions",
                  "Crown is small, gold, sits properly on head",
                  "Velvet texture on throne is convincing",
                  "Chiaroscuro lighting from a single source",
                  "Oil painting technique with visible brushwork"]},

    {"id": "M02", "top_n": 2, "max_price": 0.12, "min_quality": 8, "tier": "mid",
     "prompt": "A Japanese garden in peak autumn — vermillion bridge arching "
               "over a koi pond with visible fish, maple trees with leaves "
               "mid-fall, a stone lantern covered in moss, morning mist "
               "hovering over the water surface",
     "criteria": ["Bridge is the correct torii/arch style",
                  "Koi fish individually visible in clear water",
                  "Maple leaves both on trees and floating on water",
                  "Stone lantern with moss — aged and authentic",
                  "Mist sits low on water surface, not everywhere"]},

    {"id": "M03", "max_price": 0.10, "min_quality": 8, "tier": "mid",
     "prompt": "A Victorian-era steampunk airship — polished brass hull, "
               "spinning propellers, canvas gas envelope, crew members "
               "visible on the observation deck, flying through cumulus "
               "clouds at golden hour with the sun behind it",
     "criteria": ["Brass metalwork with reflections and patina",
                  "Propellers show motion blur",
                  "Crew members are small but identifiable as people",
                  "Cloud lighting is consistent with sun position",
                  "Overall design is mechanically plausible"]},

    {"id": "M04", "top_n": 2, "max_price": 0.15, "min_quality": 8, "tier": "mid",
     "prompt": "An antiquarian bookshop at closing time — floor-to-ceiling "
               "mahogany shelves, a green banker's lamp on a cluttered desk, "
               "rain streaking the window, a marmalade cat asleep on an open "
               "atlas, leather-bound spines with gilt lettering visible",
     "criteria": ["Interior feels warm, intimate, and lived-in",
                  "Cat anatomy correct, clearly sleeping on a book",
                  "Rain on window glass with exterior darkness",
                  "Individual book spines distinguishable",
                  "Green lamp casts a localized warm pool of light"]},

    {"id": "M05", "max_price": 0.10, "min_quality": 8, "tier": "mid",
     "prompt": "A timber wolf mid-howl on a granite cliff edge, silhouetted "
               "against an enormous full moon, fresh snow on the rocks, "
               "aurora borealis rippling green and purple across the sky, "
               "pine forest visible far below",
     "criteria": ["Wolf pose is anatomically correct mid-howl",
                  "Moon is large with visible surface features",
                  "Aurora has correct curtain/ribbon structure",
                  "Snow texture on rocks is realistic",
                  "Sense of height and scale from cliff to forest"]},

    {"id": "M06", "top_n": 2, "max_price": 0.12, "min_quality": 8, "tier": "mid",
     "prompt": "A bustling medieval European market square at first light — "
               "half-timbered buildings, merchant stalls with hanging meats "
               "and bread, cobblestone square wet from overnight rain, "
               "a blacksmith's forge glowing orange in a side alley, "
               "chickens and a dog in the foreground",
     "criteria": ["Architecture period-correct for medieval Europe",
                  "Multiple types of market goods identifiable",
                  "Wet cobblestones reflect the dawn light",
                  "Forge glow provides secondary warm light source",
                  "Animals look natural, not AI-deformed"]},

    {"id": "M07", "max_price": 0.10, "min_quality": 8, "tier": "mid",
     "prompt": "An astronaut in a modern EVA suit planting a flag on red "
               "Martian soil, Earth visible as a small blue dot in the "
               "butterscotch sky, bootprints in the dust leading from "
               "a landed spacecraft in the background",
     "criteria": ["Spacesuit has realistic detail and reflections",
                  "Martian landscape color and terrain correct",
                  "Earth is a small dot, not a large globe",
                  "Bootprints in dust are realistic",
                  "Spacecraft in background provides scale"]},

    {"id": "M08", "top_n": 2, "max_price": 0.14, "min_quality": 8, "tier": "mid",
     "prompt": "A European dragon curled around its treasure hoard in a "
               "vast underground cavern — individual gold coins, jeweled "
               "chalices, one open eye watching the viewer, scales "
               "reflecting firelight from torches mounted on cave walls, "
               "stalactites dripping from the ceiling",
     "criteria": ["Dragon anatomy is coherent — wings, tail, scales",
                  "Treasure has individual items, not a gold blob",
                  "One eye open creates tension and narrative",
                  "Scale reflections show multiple light sources",
                  "Cave environment has geological accuracy"]},

    # ══════════════════════════════════════════════════════════════════
    # PREMIUM MARKETS ($0.20-0.50, quality 9)
    # Near-perfection required. Detailed, specific, unforgiving criteria.
    # ══════════════════════════════════════════════════════════════════
    {"id": "X01", "top_n": 3, "max_price": 0.30, "min_quality": 9, "tier": "premium",
     "prompt": "Photorealistic portrait: an elderly Icelandic fisherman on "
               "his weathered wooden boat at dawn — deep wrinkles mapping "
               "decades of North Atlantic wind, salt-and-pepper beard with "
               "individual strands visible, steel-blue eyes reflecting the "
               "golden sunrise off the water, wool sweater with visible knit "
               "pattern, coiled rope in the background",
     "criteria": ["Could be mistaken for an actual photograph",
                  "Facial detail: wrinkles, pores, individual hairs all visible",
                  "Eyes reflect the sunrise with correct specular highlights",
                  "Wool sweater texture and knit pattern convincing",
                  "Boat wood grain and rope fibers are detailed",
                  "Overall tells a life story through visual details"]},

    {"id": "X02", "max_price": 0.35, "min_quality": 9, "tier": "premium",
     "prompt": "Dutch Golden Age vanitas still life: a silver goblet with "
               "engraved scrollwork, three ripe peaches (one split showing "
               "flesh), a lemon half-peeled with the spiral hanging off the "
               "table edge, purple grapes with visible bloom, a Painted Lady "
               "butterfly resting on a wilting rose, a partially burned "
               "candle with wax drips, all on a dark marble ledge with "
               "dramatic side lighting casting deep shadows",
     "criteria": ["Period-accurate painting technique — glazing, sfumato",
                  "Every object identifiable and distinct from prompt",
                  "Metal has correct reflections for silver",
                  "Fruit textures differ: fuzzy peach, waxy lemon, bloomy grape",
                  "Butterfly wing pattern correct for species",
                  "Vanitas symbolism present: decay, time, mortality"]},

    {"id": "X03", "top_n": 3, "max_price": 0.40, "min_quality": 9, "tier": "premium",
     "prompt": "Cinematic widescreen establishing shot: a fantasy city built "
               "into and around a 500-meter waterfall — stone bridges span "
               "between carved cliff towers, thousands of glowing windows "
               "at dusk, flying creatures (dragons or birds) silhouetted "
               "against the fading sky, a rainbow arcs through the mist "
               "at the base of the falls, a winding river below leads "
               "to farmland in the far distance",
     "criteria": ["City feels massive — sense of scale through detail layers",
                  "Architecture is integrated with the waterfall, not stuck on",
                  "Thousands of windows individually lit, not a blur",
                  "Flying creatures have correct silhouette at distance",
                  "Rainbow placement physically correct relative to mist/sun",
                  "Multiple depth layers: foreground, mid, far distance"]},

    {"id": "X04", "max_price": 0.25, "min_quality": 9, "tier": "premium",
     "prompt": "Hyperrealistic macro photograph: a single perfect dewdrop "
               "suspended on a spider's web strand at sunrise — the entire "
               "garden is reflected upside-down inside the droplet, the web "
               "strands catch prismatic light, wildflowers are soft bokeh "
               "circles in the background, a tiny spider is visible at the "
               "edge of frame",
     "criteria": ["Dewdrop optics correct — inverted reflection inside",
                  "Web strands catch light with prismatic diffraction",
                  "Depth of field is macro-correct: razor thin focus plane",
                  "Bokeh circles are proper hexagonal/circular from lens",
                  "Spider is small but anatomically correct",
                  "Overall achievable with real macro photography"]},

    {"id": "X05", "top_n": 3, "max_price": 0.50, "min_quality": 9, "tier": "premium",
     "prompt": "Architectural visualization: Zaha Hadid-inspired museum at "
               "night — flowing parametric white concrete facade with "
               "integrated LED strip lighting, floor-to-ceiling glass "
               "revealing illuminated gallery spaces with people inside, "
               "a perfectly still reflecting pool in the foreground "
               "mirroring the entire building, three human silhouettes "
               "on the entrance ramp for scale, a crescent moon above",
     "criteria": ["Architecture is world-class parametric design quality",
                  "Facade flows organically — no boxy geometry",
                  "Interior visible through glass with people and art",
                  "Reflecting pool mirrors building with correct physics",
                  "Human silhouettes provide scale reference",
                  "Night lighting is cinematic — not overexposed",
                  "Could appear in an architecture magazine"]},

    {"id": "X06", "max_price": 0.30, "min_quality": 9, "tier": "premium",
     "prompt": "Aerial photograph looking straight down into crystal-clear "
               "tropical water: a coral reef forms a natural circle, "
               "a sea turtle glides over the reef center, schools of "
               "yellow tang and blue chromis move in formation, "
               "white sand channels between coral heads, sunbeams "
               "penetrate from above creating dappled light on the seabed",
     "criteria": ["Overhead perspective is correct — looking straight down",
                  "Water clarity allows seeing the seabed clearly",
                  "Turtle anatomy correct from above (shell pattern)",
                  "Fish schools have correct formation behavior",
                  "Coral has varied species and realistic shapes",
                  "Sunbeam caustics on sand are physically accurate"]},

    {"id": "X07", "max_price": 0.35, "min_quality": 9, "tier": "premium",
     "prompt": "Renaissance oil painting of a modern food truck vendor — "
               "executed with Vermeer's technique: pearl-like skin tones, "
               "a single north-facing window light source, but the subject "
               "wears a backwards baseball cap and vinyl gloves, serving "
               "al pastor tacos from a stainless steel truck with a "
               "hand-painted menu board, a customer checks their phone",
     "criteria": ["Vermeer's lighting technique: soft, directional, luminous",
                  "Skin tones have the characteristic pearl quality",
                  "Modern objects (phone, truck, cap) rendered in Old Master style",
                  "Anachronism is deliberate and thought-provoking",
                  "Composition follows Renaissance rules (golden ratio)",
                  "Brush technique visible — this is a painting, not a photo"]},

    # ══════════════════════════════════════════════════════════════════
    # CREATIVE MARKETS ($0.10-0.25, quality 8)
    # Abstract concepts. High bar for interpretation quality.
    # ══════════════════════════════════════════════════════════════════
    {"id": "C01", "top_n": 2, "max_price": 0.15, "min_quality": 8, "tier": "creative",
     "prompt": "Visualize the feeling of nostalgia — not a literal scene "
               "from the past, but the emotional texture of remembering: "
               "warmth, loss, golden light, the soft edges of a memory "
               "that's already fading",
     "criteria": ["Evokes genuine emotional response, not just 'old things'",
                  "Color palette communicates warmth and gentle melancholy",
                  "Has a dream-like quality — soft focus, bleeding edges",
                  "Goes beyond cliché (not just sepia photos or old houses)"]},

    {"id": "C02", "max_price": 0.12, "min_quality": 8, "tier": "creative",
     "prompt": "What silence sounds like in a forest — not an empty forest, "
               "but a forest so quiet you can hear the moss growing, the "
               "mist breathing, the light landing on leaves",
     "criteria": ["Stillness is the dominant emotion, not emptiness",
                  "Atmospheric density — mist, filtered light, humidity",
                  "Viewer feels they could hear their own heartbeat",
                  "Technical quality is high — not just a blurry forest"]},

    {"id": "C03", "top_n": 2, "max_price": 0.20, "min_quality": 8, "tier": "creative",
     "prompt": "The last page of a story nobody will ever finish — "
               "visualize the moment a narrative dissolves into nothing, "
               "characters mid-gesture, a world half-rendered, the edge "
               "where story meets void",
     "criteria": ["Narrative incompleteness is visible and intentional",
                  "Has both structure (the story) and dissolution (the void)",
                  "Emotionally resonant — melancholy, not just abstract",
                  "Creative risk rewarded — surprising interpretation"]},

    {"id": "C04", "max_price": 0.15, "min_quality": 8, "tier": "creative",
     "prompt": "A color that doesn't exist in nature — not a gradient or "
               "a rainbow, but a single impossible hue that sits between "
               "dimensions, that your brain tries to parse but can't quite "
               "categorize, rendered as a physical phenomenon or object",
     "criteria": ["Genuinely attempts the impossible, not just 'weird colors'",
                  "The 'color' has physical presence — it exists in space",
                  "Viewer's eye is drawn to it and can't look away",
                  "Technically proficient execution around the concept"]},

    {"id": "C05", "max_price": 0.18, "min_quality": 8, "tier": "creative",
     "prompt": "The hypnagogic moment between waking and sleep — that "
               "instant when reality softens, shapes breathe, familiar "
               "objects become strange, and you can't tell if your eyes "
               "are open or closed",
     "criteria": ["Liminal state is palpable — neither awake nor asleep",
                  "Familiar objects are present but subtly wrong",
                  "Lighting suggests ambiguity between real and dream",
                  "Viewer feels the drowsy dissolve of consciousness"]},

    {"id": "C06", "max_price": 0.15, "min_quality": 8, "tier": "creative",
     "prompt": "What music tastes like — not musical instruments, not "
               "sound waves, but the actual flavor-texture of a jazz "
               "saxophone solo translated into a visual/gustatory hybrid",
     "criteria": ["Synesthesia is the operating principle, not metaphor",
                  "Both sensory domains (taste and sound) are present",
                  "Jazz specifically — not generic music",
                  "No musical instruments depicted literally"]},

    {"id": "C07", "top_n": 2, "max_price": 0.20, "min_quality": 8, "tier": "creative",
     "prompt": "The weight of an unspoken apology — the physical mass of "
               "words you should have said but didn't, carried in your "
               "chest for years, visualized as a tangible burden",
     "criteria": ["Emotional gravity is the dominant visual force",
                  "The 'weight' has physical presence — not just sadness",
                  "Human vulnerability without sentimentality",
                  "Compositionally strong — not just conceptually interesting"]},

    {"id": "C08", "max_price": 0.12, "min_quality": 8, "tier": "creative",
     "prompt": "The exact instant gravity reverses for one second inside "
               "a crowded kitchen — coffee rises from mugs, a cat floats "
               "with spread legs, flour hovers, a child laughs upside down, "
               "but outside the window everything is normal",
     "criteria": ["Physics are consistent — everything indoor rises",
                  "Outside window is normal — creating contrast",
                  "Multiple objects mid-float with correct trajectories",
                  "Human/animal reactions are realistic, not posed",
                  "Playful energy, not horror"]},

    # ══════════════════════════════════════════════════════════════════
    # STRESS MARKETS ($0.06-0.08, quality 8)
    # Tight margins, high bar. The hardest economic zone.
    # ══════════════════════════════════════════════════════════════════
    {"id": "S01", "top_n": 2, "max_price": 0.06, "min_quality": 8, "tier": "stress",
     "prompt": "A weathered pirate galleon sailing through a violent storm "
               "at sunset — lightning illuminating the sails, crew scrambling "
               "on deck, enormous waves, the sky split between storm and "
               "golden light on the horizon",
     "criteria": ["Ship rigging and structure are detailed and plausible",
                  "Wave dynamics show power and scale",
                  "Lightning illumination is physically correct",
                  "Crew members visible and active on deck"]},

    {"id": "S02", "max_price": 0.07, "min_quality": 8, "tier": "stress",
     "prompt": "A humanoid robot sitting in an old leather armchair in a "
               "dimly lit library, reading a physical book through glowing "
               "blue optical sensors, dust motes floating in a shaft of "
               "light from a high window",
     "criteria": ["Robot design is detailed and mechanically interesting",
                  "Book is open and robot is clearly reading it",
                  "Library atmosphere is warm despite the robot's cold metal",
                  "Dust motes in light shaft add atmosphere"]},

    {"id": "S03", "max_price": 0.065, "min_quality": 8, "tier": "stress",
     "prompt": "A red fox in sharp focus standing in an autumn beech forest, "
               "golden leaves falling around it, one paw raised mid-step, "
               "morning fog between the trees, eye contact with the viewer",
     "criteria": ["Fox anatomy is perfect — correct proportions, fur texture",
                  "Direct eye contact creates connection with viewer",
                  "Autumn colors are rich but natural, not oversaturated",
                  "Fog creates depth layers between trees"]},

    {"id": "S04", "max_price": 0.075, "min_quality": 8, "tier": "stress",
     "prompt": "A single hot air balloon floating over endless lavender "
               "fields in Provence at golden hour — the balloon's shadow "
               "stretches across the purple rows, a stone farmhouse with "
               "cypress trees in the middle distance",
     "criteria": ["Balloon envelope has detailed panel patterns",
                  "Shadow on lavender is correct angle for time of day",
                  "Lavender rows recede into proper perspective",
                  "Farmhouse and cypress create Provençal atmosphere"]},

    {"id": "S05", "top_n": 2, "max_price": 0.08, "min_quality": 8, "tier": "stress",
     "prompt": "A wizard's tower perched on a floating island of earth and "
               "rock — roots dangling from the bottom, a waterfall pouring "
               "off one edge into clouds below, a narrow stone bridge "
               "connecting to a second smaller island, stars visible in "
               "a twilight sky",
     "criteria": ["Floating island has geological detail — rock strata, roots",
                  "Waterfall falls into void/clouds convincingly",
                  "Tower architecture is detailed and fantastical",
                  "Stone bridge looks precarious and ancient",
                  "Twilight sky transitions from warm horizon to stars"]},

    {"id": "S06", "max_price": 0.07, "min_quality": 8, "tier": "stress",
     "prompt": "An adult polar bear standing on a fractured ice floe, aurora "
               "borealis rippling green and violet overhead, the dark Arctic "
               "ocean visible between ice gaps, stars reflected in still "
               "water pools",
     "criteria": ["Polar bear proportions and fur texture are correct",
                  "Aurora has correct curtain/ribbon light structure",
                  "Ice has realistic fracture patterns and blue translucency",
                  "Star reflections in dark water between ice"]},
]

TIER_INFO = {
    "penny":   {"color": "\033[90m", "label": "PENNY",   "desc": "$0.01-0.02, q≥7"},
    "budget":  {"color": "\033[32m", "label": "BUDGET",  "desc": "$0.03-0.05, q≥8"},
    "stress":  {"color": "\033[38;5;208m", "label": "STRESS",  "desc": "$0.06-0.08, q≥8"},
    "mid":     {"color": "\033[33m", "label": "MID",     "desc": "$0.08-0.15, q≥8"},
    "premium": {"color": "\033[35m", "label": "PREMIUM", "desc": "$0.20-0.50, q≥9"},
    "creative":{"color": "\033[36m", "label": "CREATIVE","desc": "$0.10-0.25, q≥8"},
}
RESET = "\033[0m"
