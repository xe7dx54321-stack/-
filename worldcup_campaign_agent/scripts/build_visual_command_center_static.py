#!/usr/bin/env python3
"""Build static Visual Command Center HTML."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from worldcup_campaign.visual_command_center import build_visual_snapshot, render_static_html

ROOT = Path(__file__).resolve().parent.parent
snap = build_visual_snapshot()
html = render_static_html(snap)
hp = ROOT / "reports" / "generated" / "visual_command_center.html"
hp.parent.mkdir(parents=True, exist_ok=True)
hp.write_text(html, encoding="utf-8")
print("Static HTML: " + str(hp))
