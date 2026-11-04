# Guion del video (< 3 min) — Al Tiempo

Reglas: menos de 3:00 (los jueces no ven más), público en YouTube, **subtítulos en inglés**, sin música con
copyright y **sin logos ni marcas de terceros** (OMS, FDA, CDC, NHS, USDA, FoodKeeper…): las fuentes se dicen o se escriben en texto, nunca con su logo. Si grabas la consola de AWS o GitHub, que no sea el foco de la toma. Graba la pantalla del celular (o el navegador en modo celular con F12 → 📱)
y la terminal. La voz puede ser tuya en inglés o en español con subtítulos en inglés.

Todas las cifras de abajo están medidas o tienen fuente (`docs/metrics.md`, `docs/sources.md`).

| Tiempo | En pantalla | Voz / subtítulo (inglés) |
|---|---|---|
| 0:00–0:15 | Texto sobre fondo: "38 °C. No fridge. Rice cooked at 9:00." → `docs/img/cover.png` | "A mother cooked rice at nine. It's 38 degrees and she has no fridge. At two, her child is hungry. Is the rice still OK? Every year, 866 million people get sick from unsafe food, according to the WHO." |
| 0:15–0:35 | Abre la demo en el celular; toca **Safe window** | "Al Tiempo answers with a clock time, not a guess: eat the beans before 13:00 or throw them away — and it cites the rule: the U.S. FDA one-hour rule above 32 °C." |
| 0:35–0:55 | Responde "Yes, please schedule the reminder" → espera → aparece el ⏰ recordatorio | "It can remind you at the exact minute with Amazon EventBridge Scheduler, even if you close the app. In the demo the clock is accelerated, so it arrives in about a minute." |
| 0:55–1:10 | **Power outage** | "Lost power? It starts the clock when the power went out: the fridge's 4-hour limit ended at 10:00; the full freezer is fine until Friday." |
| 1:10–1:30 | **Shelter (120 people)** | "For shelters after a disaster, it plans staggered cooking batches so nothing is served outside the safe window, with a discard time for each batch." |
| 1:30–1:40 | **Baby + rice** y **Danger signs** (rápido) | "Stricter rules for babies. And if a child shows danger signs, it says: call 911 now. No diagnosis, no doses." |
| 1:40–2:15 | `docs/img/verifier.png`, luego `docs/img/architecture.png` | "The model talks; the rules decide. The language model never calculates a time. A tested rules engine does, with 11 official rules verified word by word. A verifier hook blocks any time the engine didn't produce. It runs on Strands Agents and Amazon Bedrock AgentCore, deployed with CDK and GitHub Actions." |
| 2:15–2:45 | `docs/img/model-evals.png`, luego la terminal con `make smoke` → RESULT: PASS | "We measured it. 99 of 100 evaluation conversations follow the rules, and none was unsafe. 8 of 8 invented times are blocked. 9 of 9 live reminders arrived on time. About a quarter of a cent per message." |
| 2:45–3:00 | La demo + link | "Next: a pilot with a community kitchen, WhatsApp and more languages. Try it in one minute, no login, at the link below." |

## Antes de grabar
- Usa una ventana de incógnito (sesión nueva) y espera ~5 s antes del primer clic: el primer mensaje tarda ~2 s.
- Graba cada escena por separado y júntalas; recorta las esperas (deja ver que el recordatorio llega).
- Subtítulos: pega la columna de voz en YouTube Studio → Subtítulos → inglés.
- Descripción de YouTube: link de la demo, link del repo, y "Built with Strands Agents on AWS. Code written with the help of Claude Code."
- Al terminar, pásame el link y lo pongo en el artículo y en el README.
