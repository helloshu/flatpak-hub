#!/usr/bin/env python3
"""Update extra-data pins in registry/<app_id>/ from direct payload or GitHub Releases API."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import urllib.request
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
REGISTRY_DIR = ROOT / "registry"

MANAGED_RE = re.compile(
    r"(# BEGIN MANAGED EXTRA-DATA\n)(.*?)( +?# END MANAGED EXTRA-DATA)",
    re.DOTALL,
)


def gh_get_json(url: str, token: str):
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "flatpak-hub-pin-updater",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def gh_get_text(url: str, token: str) -> str:
    headers = {"User-Agent": "flatpak-hub-pin-updater"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def apply_pin_to_files(app_dir: Path, meta: dict, version: str, date_str: str, url: str, sha256: str, size: int) -> bool:
    sha256 = sha256.lower().removeprefix("sha256:").strip()
    if not re.fullmatch(r"[0-9a-f]{64}", sha256):
        raise SystemExit(f"ERROR: invalid sha256 '{sha256}' for {meta['id']}")
    if size <= 0:
        raise SystemExit(f"ERROR: invalid size {size} for {meta['id']}")
    if not url.startswith("https://"):
        raise SystemExit(f"ERROR: invalid url '{url}' for {meta['id']}")

    changed = False
    old_pin = meta.get("pin", {})
    new_pin = {
        "version": version,
        "date": date_str,
        "url": url,
        "sha256": sha256,
        "size": int(size),
    }
    if old_pin != new_pin:
        meta["pin"] = new_pin
        (app_dir / "app.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        changed = True

    manifest_path = app_dir / f"{meta['id']}.yml"
    manifest_text = manifest_path.read_text(encoding="utf-8")
    replacement_block = (
        "      - type: extra-data\n"
        "        filename: app.deb\n"
        "        only-arches:\n"
        "          - x86_64\n"
        f"        url: {url}\n"
        f"        sha256: {sha256}\n"
        f"        size: {int(size)}\n"
    )
    new_manifest, count = MANAGED_RE.subn(rf"\1{replacement_block}\3", manifest_text, count=1)
    if count != 1:
        raise SystemExit(f"ERROR: missing MANAGED EXTRA-DATA markers in {manifest_path}")
    if new_manifest != manifest_text:
        manifest_path.write_text(new_manifest, encoding="utf-8")
        changed = True

    metainfo_path = app_dir / f"{meta['id']}.metainfo.xml"
    metainfo_text = metainfo_path.read_text(encoding="utf-8")
    ET.fromstring(metainfo_text)
    rel_tag = f'<release version="{version}" date="{date_str}"/>'
    if f'version="{version}"' not in metainfo_text:
        new_metainfo = metainfo_text.replace("<releases>\n", f"<releases>\n    {rel_tag}\n", 1)
        ET.fromstring(new_metainfo)
        metainfo_path.write_text(new_metainfo, encoding="utf-8")
        changed = True

    status = "UPDATED" if changed else "UNCHANGED"
    print(f"[pin] {meta['id']} -> v{version} ({status}, size={size}, sha256={sha256[:12]}...)")
    return changed


def resolve_from_github(app_dir: Path, meta: dict, token: str) -> bool:
    repo = meta["source_repo"]
    tag_prefix = meta["tag_prefix"]
    asset_rx = re.compile(meta["asset_regex"])
    rels = gh_get_json(f"https://api.github.com/repos/{repo}/releases?per_page=25", token)
    for rel in rels:
        if rel.get("draft") or rel.get("prerelease"):
            continue
        tag = rel.get("tag_name", "")
        if not tag.startswith(tag_prefix):
            continue
        raw_ver = tag[len(tag_prefix):].lstrip("v")
        pub_at = rel.get("published_at") or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        date_str = pub_at[:10]
        assets = rel.get("assets", [])
        matched = next((a for a in assets if asset_rx.search(a["name"])), None)
        if not matched:
            raise SystemExit(f"ERROR: release {tag} on {repo} has no asset matching {meta['asset_regex']}")
        digest = (matched.get("digest") or "").removeprefix("sha256:")
        if not digest:
            sums_asset = next((a for a in assets if a["name"] == "SHA256SUMS"), None)
            if not sums_asset:
                raise SystemExit(f"ERROR: asset {matched['name']} has no API digest and no SHA256SUMS")
            sums_txt = gh_get_text(sums_asset["browser_download_url"], token)
            for line in sums_txt.splitlines():
                parts = line.strip().split()
                if len(parts) >= 2 and parts[-1].lstrip("*") == matched["name"]:
                    digest = parts[0]
                    break
        return apply_pin_to_files(
            app_dir,
            meta,
            version=raw_ver,
            date_str=date_str,
            url=matched["browser_download_url"],
            sha256=digest,
            size=int(matched["size"]),
        )
    raise SystemExit(f"ERROR: no published release matching '{tag_prefix}*' found on {repo}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sync-all", action="store_true", help="Sync all registered apps from source_repo releases")
    parser.add_argument("--app-id", default="")
    parser.add_argument("--version", default="")
    parser.add_argument("--url", default="")
    parser.add_argument("--sha256", default="")
    parser.add_argument("--size", type=int, default=0)
    parser.add_argument("--date", default="")
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN", "").strip()

    if args.app_id and args.version and args.url and args.sha256 and args.size > 0:
        app_dir = REGISTRY_DIR / args.app_id
        if not app_dir.is_dir():
            raise SystemExit(f"ERROR: unknown app_id '{args.app_id}' in registry/")
        meta = json.loads((app_dir / "app.json").read_text(encoding="utf-8"))
        date_str = args.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        apply_pin_to_files(
            app_dir,
            meta,
            version=args.version.lstrip("v"),
            date_str=date_str,
            url=args.url,
            sha256=args.sha256,
            size=args.size,
        )
        return 0

    targets = sorted(p for p in REGISTRY_DIR.iterdir() if p.is_dir() and (p / "app.json").is_file())
    if args.app_id:
        targets = [p for p in targets if p.name == args.app_id]
        if not targets:
            raise SystemExit(f"ERROR: unknown app_id '{args.app_id}'")

    if args.sync_all or args.app_id:
        for app_dir in targets:
            meta = json.loads((app_dir / "app.json").read_text(encoding="utf-8"))
            resolve_from_github(app_dir, meta, token)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
