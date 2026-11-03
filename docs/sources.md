# Sources — every number we publish, and where to check it

Checked on **2026-11-03**. "Verbatim" = copied from the page/PDF so anyone can find it with Ctrl+F.
Rule: if a number is not in this file, it does not go in the article, the video or the README.

## A. Food-safety rules used by the engine
All 11 rules live in `rules/food_rules.yaml` with their verbatim text (`verified_text`).

| Rules | Source (official) | Verbatim |
|---|---|---|
| WHO_COOKED_2H, WHO_HOT_HOLD_60C | [WHO — Five keys to safer food (WHO/SDE/PHE/FOS/01.1)](https://www.who.int/docs/librariesprovider2/default-document-library/5keys_en.pdf) | "Do not leave cooked food at room temperature for more than 2 hours" · "Keep cooked food piping hot (more than 60°C) prior to serving" |
| FDA_2H, FDA_HOT_1H | [U.S. FDA — Handling Food Safely While Eating Outdoors](https://www.fda.gov/food/buy-store-serve-safe-food/handling-food-safely-while-eating-outdoors) (content current as of 03/05/2024) | "these foods should not sit out for more than 2 hours, or 1 hour in temperatures above 90 °F. If food is left out longer, throw it away to be safe." |
| FDA_OUTAGE_FRIDGE_4H, FDA_OUTAGE_FREEZER_FULL_48H, FDA_OUTAGE_FREEZER_HALF_24H | [U.S. FDA — Food and Water Safety During Power Outages and Floods](https://www.fda.gov/food/buy-store-serve-safe-food/food-and-water-safety-during-power-outages-and-floods) (content current as of 03/05/2024) | "The refrigerator will keep food cold for about 4 hours if it is unopened." · "A full freezer will keep the temperature for approximately 48 hours (24 hours if it is half full) if the door remains closed." |
| CDC_FORMULA_2H, CDC_FORMULA_FEED_1H | [CDC — Infant Formula Preparation and Storage](https://www.cdc.gov/infant-toddler-nutrition/formula-feeding/preparation-and-storage.html) (May 14, 2026) | "use prepared infant formula within 2 hours of preparation and within one hour from when feeding begins." · "Throw out any infant formula that is left in the bottle after feeding your baby." |
| NHS_RICE_1H (*adapted*) | [NHS — Starchy foods and carbohydrates](https://www.nhs.uk/live-well/eat-well/food-types/starchy-foods-and-carbohydrates/) (last reviewed 15 March 2023) | "If you are not going to eat cooked rice immediately, refrigerate it within 1 hour and eat it within 24 hours." |
| Danger signs (dehydration) | [WHO — Diarrhoeal disease fact sheet](https://www.who.int/news-room/fact-sheets/detail/diarrhoeal-disease) (7 March 2024) | severe dehydration signs: "lethargy/unconsciousness", "sunken eyes", "unable to drink or drink poorly", "skin pinch goes back very slowly ( ≥2 seconds)"; see a health professional "when there is blood in stool" |

Notes:
- USDA FSIS publishes the same 2 h / 1 h and 4 h / 48 h / 24 h rules, but its pages block automated
  readers (HTTP 403), so the engine cites the FDA pages, which we could check word by word.
- 90 °F = 32.2 °C. The engine switches to 1 hour **above 32 °C** (slightly stricter than the source).
- NHS_RICE_1H is *adapted*: the NHS gives 1 hour to refrigerate cooked rice; with no fridge we use
  that hour as the limit to eat it. The engine labels it as adapted.
- POLICY_CHILD_STRICT is **our** policy (stricter than official rules) and is labeled as such.

## B. Numbers for the article (latest available)

| Claim | Number | Source | Status |
|---|---|---|---|
| People who get sick from unsafe food every year | **866 million** (almost 1 in 9 people) | [WHO food safety fact sheet, 4 June 2026](https://www.who.int/news-room/fact-sheets/detail/food-safety) | ✅ Verbatim: "An estimated 866 million – almost 1 in 9 people in the world – fall ill after eating contaminated food and 1.52 million die every year." |
| Deaths per year from unsafe food | **1.52 million** | same | ✅ |
| Children under 5 | **29%** of the health burden; **143 000 deaths in 2021** | same | ✅ Verbatim: "Children under 5 years of age experience 29% of the health burden due to unsafe food, with 143 000 deaths in 2021." |
| People without electricity (2024) | **655 million**; Africa holds **~89% (88.8%)** | [SEforALL — Tracking SDG7: The Energy Progress Report 2026, Deep Dive Perspective (July 2026)](https://www.seforall.org/system/files/2026-07/SEforALL%20Tracking%20SDG7%20-%20The%20Energy%20Progress%20Report%202026_Executive%20Version_22Jul2026-2.pdf) | ✅ Verbatim: "655 million people still lack electricity (almost 92% global access)" · "Africa now holds the majority (88.8%) of the global unelectrified population" |
| People at high risk from lack of cooling (2026) | **339 million rural poor + 746 million urban poor**, in 77 heat-exposed countries | [Chilling Prospects 2026 (SEforALL), as published by the UNEP Cool Coalition](https://coolcoalition.org/news/chilling-prospects-2026-links-rising-heat-mortality-persistent-cooling-access-gaps) | ✅ Verbatim: "Across 77 heat-exposed countries, the analysis estimates that 339 million rural poor and 746 million urban poor are at high risk of lacking adequate cooling". Do not write "1.1 billion" unless you say it is the sum we computed (1,085 million). |
| Heat and food poisoning | Salmonellosis cases rise **linearly with temperature above 6 °C**, in 10 European populations | [Kovats et al., Epidemiol Infect 2004;132(3):443–453](https://pmc.ncbi.nlm.nih.gov/articles/PMC2870124) | ✅ Verbatim: "We found, on average, a linear association between temperature and the number of reported cases of salmonellosis above a threshold of 6 degrees C." |
| India: households with a refrigerator | **37.9%** (rural **25.2%**) | NFHS-5 (2019–21), as reported by [The Tribune, May 2022](https://www.tribuneindia.com/news/mobile-most-owned-item-survey-393691) | ⚠️ Secondary press. The [primary NFHS-5 report](https://rchiips.org/nfhs/NFHS-5Reports/NFHS-5_INDIA_REPORT.pdf) did not load for our tool; open it in a browser to confirm, or cite as "reported by". |
| India: households with a mobile phone | **93.3%** (rural **91.5%**) | same | ⚠️ Same as above. |

### Removed (could not be verified with a primary source — do not use)
- "Less than 30% of African households have a fridge; less than 9% in East Africa" (the only source was a blog).
- "More than 86% of African households have a mobile phone" (no source found).
- The old WHO figures "600 million ill, 420 000 deaths, 125 000 children under 5": WHO updated them on 4 June 2026 (see above).
