"""QR code of the public demo for the printable cards (web/icons/qr-demo.png).

    python scripts/make_qr.py            # URL from build/outputs.json (SiteUrl)
    python scripts/make_qr.py --url https://...

Generated once and committed: the web needs no QR library at runtime. Dev-only dependency: qrcode.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import qrcode

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=None)
    args = ap.parse_args()
    url = (
        args.url
        or json.loads((ROOT / "build" / "outputs.json").read_text())["AlTiempoApp"]["SiteUrl"]
    )
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=8, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    out = ROOT / "web" / "icons" / "qr-demo.png"
    qr.make_image(fill_color="#163B32", back_color="white").save(out)
    print(f"{out.relative_to(ROOT)} -> {url}")


if __name__ == "__main__":
    main()
