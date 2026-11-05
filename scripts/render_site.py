#!/usr/bin/env python3
"""Assemble static GitHub Pages directory: OSTree repo + .flatpakrepo + index.html + .nojekyll."""
from __future__ import annotations

import html
import json
import os
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parent.parent
PUB_KEY_B64_FILE = ROOT / "config/gpg-public-key.b64"


def render_html(base_url: str, repo_file_url: str, apps: list[dict]) -> str:
    rows = []
    for app in apps:
        pin = app["pin"]
        app_id = html.escape(app["id"])
        rows.append(
            f"""
            <div class="card">
              <div class="card-head">
                <div>
                  <h2>{html.escape(app['name'])}</h2>
                  <code>{app_id}</code>
                </div>
                <span class="badge">v{html.escape(pin['version'])}</span>
              </div>
              <p class="summary">{html.escape(app['summary'])}</p>
              <pre><code>flatpak --user install flatpak-hub {app_id}</code></pre>
              <div class="meta">
                <span>Updated: {html.escape(pin['date'])}</span>
                <span>Payload: {pin['size'] / (1024 * 1024):.1f} MiB · SHA-256: <code>{html.escape(pin['sha256'][:16])}…</code></span>
                <a href="{html.escape(pin['url'])}" target="_blank" rel="noopener">Direct .deb</a>
                <a href="{html.escape(app['homepage'])}" target="_blank" rel="noopener">Upstream</a>
              </div>
            </div>
            """
        )
    cards_html = "\n".join(rows)
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Flatpak Hub — helloshu</title>
  <style>
    :root {{ color-scheme: light dark; --bg: #0f172a; --card: #1e293b; --fg: #f8fafc; --muted: #94a3b8; --accent: #38bdf8; --border: #334155; }}
    @media (prefers-color-scheme: light) {{
      :root {{ --bg: #f8fafc; --card: #ffffff; --fg: #0f172a; --muted: #475569; --accent: #0284c7; --border: #e2e8f0; }}
    }}
    body {{ font-family: system-ui, -apple-system, sans-serif; background: var(--bg); color: var(--fg); max-width: 820px; margin: 0 auto; padding: 2.5rem 1.25rem; line-height: 1.6; }}
    h1 {{ margin-bottom: 0.25rem; font-size: 1.85rem; }}
    .sub {{ color: var(--muted); margin-top: 0; margin-bottom: 1.75rem; }}
    pre {{ background: rgba(15, 23, 42, 0.55); color: #e2e8f0; padding: 0.85rem 1rem; border-radius: 8px; overflow-x: auto; font-size: 0.9rem; }}
    @media (prefers-color-scheme: light) {{ pre {{ background: #0f172a; color: #f8fafc; }} }}
    .card {{ background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 1.25rem 1.5rem; margin-top: 1.25rem; }}
    .card-head {{ display: flex; justify-content: space-between; align-items: flex-start; gap: 1rem; }}
    .card-head h2 {{ margin: 0 0 0.2rem 0; font-size: 1.25rem; }}
    .badge {{ background: var(--accent); color: #fff; font-weight: 600; padding: 0.2rem 0.65rem; border-radius: 999px; font-size: 0.85rem; }}
    .summary {{ margin: 0.65rem 0; color: var(--muted); }}
    .meta {{ display: flex; flex-wrap: wrap; gap: 1rem; font-size: 0.85rem; color: var(--muted); margin-top: 0.75rem; }}
    a {{ color: var(--accent); text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
  </style>
</head>
<body>
  <h1>Flatpak Hub</h1>
  <p class="sub">基于 <code>extra-data</code> 模式的轻量级个人公开 Flatpak OSTree 软件源（自动同步发版、支持 <code>flatpak update</code>）。</p>

  <h3>1. 首次添加软件源</h3>
  <pre><code>flatpak --user remote-add --if-not-exists flatpak-hub {html.escape(repo_file_url)}</code></pre>

  <h3>2. 已收录应用（{len(apps)}）</h3>
  {cards_html}
</body>
</html>
"""


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit(f"usage: {sys.argv[0]} <ostree-repo-dir> <output-site-dir>")
    repo_dir = Path(sys.argv[1]).resolve()
    site_dir = Path(sys.argv[2]).resolve()
    base_url = os.environ.get("HUB_BASE_URL", "https://helloshu.github.io/flatpak-hub").rstrip("/") + "/"
    repo_file_url = f"{base_url}flatpak-hub.flatpakrepo"

    if site_dir.exists():
        shutil.rmtree(site_dir)
    shutil.copytree(repo_dir, site_dir)

    gpg_b64 = PUB_KEY_B64_FILE.read_text(encoding="utf-8").strip().replace("\n", "")
    flatpakrepo_content = (
        "[Flatpak Repo]\n"
        "Title=Flatpak Hub (helloshu)\n"
        f"Url={base_url}\n"
        f"Homepage={base_url}\n"
        "Comment=Automated extra-data Flatpak repository\n"
        "Description=Lightweight Flatpak remote fetching official release packages at install time\n"
        f"GPGKey={gpg_b64}\n"
    )
    (site_dir / "flatpak-hub.flatpakrepo").write_text(flatpakrepo_content, encoding="utf-8")
    (site_dir / ".nojekyll").write_text("", encoding="utf-8")

    apps = []
    for app_json in sorted((ROOT / "registry").glob("*/app.json")):
        apps.append(json.loads(app_json.read_text(encoding="utf-8")))
    (site_dir / "index.html").write_text(render_html(base_url, repo_file_url, apps), encoding="utf-8")

    for dirpath, dirnames, filenames in os.walk(site_dir):
        os.chmod(dirpath, 0o755)
        for fn in filenames:
            os.chmod(os.path.join(dirpath, fn), 0o644)

    print(f"[site] Assembled static Pages bundle at {site_dir} ({len(apps)} app(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
