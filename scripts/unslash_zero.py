"""Body-text font: Atkinson Hyperlegible with a plain zero (no slash), renamed "AlTiempo Text".

    python scripts/unslash_zero.py IN.woff2 OUT.woff2 Regular|Bold

Atkinson Hyperlegible draws "0" with a diagonal slash, so times like 12:00 read as "12:ØØ" to
people who are not used to it. This script keeps every other glyph unchanged and redraws only the
zero: the outer contour stays as it is, and the two counter halves split by the slash are replaced
by one counter (the outer contour scaled to the original counter's bounding box, reversed).
The font is licensed under the SIL OFL 1.1; a modified copy is renamed so it can't be mistaken for
the original. Needs fontTools + brotli (dev only).
"""

from __future__ import annotations

import sys

from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.reverseContourPen import ReverseContourPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont

FAMILY = "AlTiempo Text"


def contours(glyph_set, name: str) -> list[list[tuple]]:
    rec = RecordingPen()
    glyph_set[name].draw(rec)
    out, cur = [], []
    for op, args in rec.value:
        cur.append((op, args))
        if op in ("closePath", "endPath"):
            out.append(cur)
            cur = []
    return out


def bbox(contour: list[tuple]) -> tuple[float, float, float, float]:
    pts = [p for _, args in contour for p in args]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def replay(contour: list[tuple], pen) -> None:
    for op, args in contour:
        getattr(pen, op)(*args)


def unslash(font: TTFont) -> None:
    glyph_set = font.getGlyphSet()
    parts = contours(glyph_set, "zero")
    if len(parts) != 3:
        raise SystemExit(
            f"expected the slashed zero (3 contours), found {len(parts)}: already done?"
        )
    parts.sort(key=lambda c: (bbox(c)[2] - bbox(c)[0]) * (bbox(c)[3] - bbox(c)[1]), reverse=True)
    outer, halves = parts[0], parts[1:]
    ox0, oy0, ox1, oy1 = bbox(outer)
    boxes = [bbox(c) for c in halves]
    ix0, iy0 = min(b[0] for b in boxes), min(b[1] for b in boxes)
    ix1, iy1 = max(b[2] for b in boxes), max(b[3] for b in boxes)
    sx, sy = (ix1 - ix0) / (ox1 - ox0), (iy1 - iy0) / (oy1 - oy0)
    # scale around the outer centre, then move to the counter's centre
    ocx, ocy, icx, icy = (ox0 + ox1) / 2, (oy0 + oy1) / 2, (ix0 + ix1) / 2, (iy0 + iy1) / 2
    matrix = (sx, 0, 0, sy, icx - sx * ocx, icy - sy * ocy)

    pen = TTGlyphPen(glyph_set)
    replay(outer, pen)
    replay(outer, ReverseContourPen(TransformPen(pen, matrix)))
    glyph = pen.glyph()
    glyph.recalcBounds(font["glyf"])
    font["glyf"]["zero"] = glyph


def rename(font: TTFont, style: str) -> None:
    ps = f"{FAMILY.replace(' ', '')}-{style}"
    names = {1: FAMILY, 3: f"{ps};unslashed-zero", 4: f"{FAMILY} {style}", 6: ps, 16: FAMILY}
    table = font["name"]
    for rec in list(table.names):
        if rec.nameID in (1, 3, 4, 6, 16, 17, 21, 22):
            table.removeNames(nameID=rec.nameID)
    for name_id, value in names.items():
        table.setName(value, name_id, 3, 1, 0x409)
    table.setName(style, 2, 3, 1, 0x409)


def main() -> None:
    src, dst, style = sys.argv[1], sys.argv[2], sys.argv[3]
    font = TTFont(src)
    unslash(font)
    rename(font, style)
    font.flavor = "woff2"
    font.save(dst)
    print(f"written {dst}")


if __name__ == "__main__":
    main()
