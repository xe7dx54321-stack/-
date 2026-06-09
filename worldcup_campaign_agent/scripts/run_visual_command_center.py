#!/usr/bin/env python3
"""CLI for Visual Command Center."""
import argparse, sys, json as j
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from worldcup_campaign.visual_command_center import (
    VisualCommandCenterRunner, build_visual_snapshot,
    render_visual_json, render_visual_markdown, render_static_html,
    write_visual_outputs, validate_visual_no_forbidden
)

ROOT = Path(__file__).resolve().parent.parent

def main():
    p = argparse.ArgumentParser(description="Visual Command Center")
    p.add_argument("--json", action="store_true")
    p.add_argument("--format", choices=["json","markdown"], default="json")
    p.add_argument("--build-static", action="store_true")
    p.add_argument("--serve", action="store_true")
    p.add_argument("--port", type=int, default=8501)
    p.add_argument("--no-write", action="store_true")
    args = p.parse_args()

    snap = build_visual_snapshot()
    payload = render_visual_json(snap)
    fb = validate_visual_no_forbidden(payload)
    if fb:
        snap.warnings.append("FORBIDDEN: " + str(fb))
        print("WARNING: Forbidden fields: " + str(fb), file=sys.stderr)

    if not args.no_write and not args.serve:
        paths = write_visual_outputs(snap)
        print("VCC: sources=" + str(snap.artifact_source_count) + " candidates=" + str(snap.candidate_summary.candidate_count if snap.candidate_summary else 0), file=sys.stderr)
        for k, vp in paths.items():
            print("  " + k + ": " + vp, file=sys.stderr)

    if args.build_static or args.build_static:
        hp = ROOT / "reports" / "generated" / "visual_command_center.html"
        hp.parent.mkdir(parents=True, exist_ok=True)
        hp.write_text(render_static_html(snap), encoding="utf-8")
        print("Static HTML: " + str(hp), file=sys.stderr)

    if args.serve:
        try:
            import streamlit
            print("Starting Streamlit on port " + str(args.port) + "...", file=sys.stderr)
            import subprocess
            app = ROOT / "apps" / "visual_command_center_app.py"
            subprocess.run([sys.executable, "-m", "streamlit", "run", str(app), "--server.port", str(args.port)])
        except ImportError:
            # Fallback: serve static HTML via http.server
            hp = ROOT / "reports" / "generated" / "visual_command_center.html"
            hp.parent.mkdir(parents=True, exist_ok=True)
            hp.write_text(render_static_html(snap), encoding="utf-8")
            import http.server, socketserver, threading, webbrowser
            os.chdir(str(ROOT / "reports" / "generated"))
            Handler = http.server.SimpleHTTPRequestHandler
            httpd = socketserver.TCPServer(("", args.port), Handler)
            url = "http://localhost:" + str(args.port) + "/visual_command_center.html"
            print("Streamlit not installed. Serving static HTML at " + url, file=sys.stderr)
            print("Install Streamlit: pip install streamlit", file=sys.stderr)
            webbrowser.open(url)
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                httpd.shutdown()

    if args.format == "markdown":
        print(render_visual_markdown(snap))
    elif args.json or args.format == "json":
        print(j.dumps(render_visual_json(snap), indent=2, ensure_ascii=False, default=str))

if __name__ == "__main__":
    main()
