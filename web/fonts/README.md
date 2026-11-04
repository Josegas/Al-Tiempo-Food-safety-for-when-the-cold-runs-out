# Fonts (all SIL Open Font License 1.1, self-hosted: no CDN, no tracking)

| File | Family | Source | Use |
|---|---|---|---|
| `fraunces-display.woff2` | Fraunces (static instance: wght 620, opsz 72, SOFT 100) | github.com/google/fonts (ofl/fraunces) | Titles |
| `altiempo-text-regular.woff2`, `altiempo-text-bold.woff2` | Subset of Atkinson Hyperlegible (Braille Institute) with a **zero without the slash**, **renamed "AlTiempo Text"** (`scripts/unslash_zero.py`) | github.com/google/fonts (ofl/atkinsonhyperlegible) | Body text |
| `altiempo-mono-medium.woff2` | Subset of IBM Plex Mono Medium, **renamed "AlTiempo Mono"** | github.com/google/fonts (ofl/ibmplexmono) | Times and data |

All files are subset to Latin + Spanish characters and converted to WOFF2 with fontTools.
IBM Plex declares the Reserved Font Name "Plex", which a modified (subset) copy may not use, so the
subset is renamed. Atkinson Hyperlegible draws 0 with a slash, which read as "12:ØØ" in times; its
zero was redrawn without the slash (every other glyph unchanged) and the modified copy is renamed too. Licenses: `OFL-Fraunces.txt`, `OFL-AtkinsonHyperlegible.txt`, `OFL-IBMPlexMono.txt`.
