"""Static site exporter for GitHub Pages deployment.

Renders all Jinja2 pages and exports static JSON API endpoints so the
entire Shoptegrity platform can run 100% statically on GitHub Pages.
"""

import os
import shutil
import argparse
from pathlib import Path
from fastapi.testclient import TestClient

from api.app.main import app
from pipeline.seed_data import run_seed
from api.app.db.session import SessionLocal
from api.app.models.core import Brand

client = TestClient(app)


def export_site(output_dir: str = "dist", base_url: str = ""):
    print(f"Ensuring database is seeded...")
    run_seed()

    out_path = Path(output_dir)
    if out_path.exists():
        shutil.rmtree(out_path)
    out_path.mkdir(parents=True, exist_ok=True)

    # 1. Copy static assets
    static_src = Path("web/static")
    static_dest = out_path / "static"
    if static_src.exists():
        shutil.copytree(static_src, static_dest)
        print(f"Copied static assets to {static_dest}")

    # Helper to clean and adjust links for base_url
    def process_html(html: str) -> str:
        if not base_url:
            return html
        # Prefix root links with base_url
        clean_base = base_url.rstrip("/")
        html = html.replace('href="/static/', f'href="{clean_base}/static/')
        html = html.replace('src="/static/', f'src="{clean_base}/static/')
        html = html.replace('href="/brands', f'href="{clean_base}/brands.html')
        html = html.replace('href="/food', f'href="{clean_base}/food.html')
        html = html.replace('href="/local', f'href="{clean_base}/local.html')
        html = html.replace('href="/swaps', f'href="{clean_base}/swaps.html')
        html = html.replace('href="/flows', f'href="{clean_base}/flows.html')
        html = html.replace('href="/methodology', f'href="{clean_base}/methodology.html')
        html = html.replace('href="/"', f'href="{clean_base}/index.html"')
        html = html.replace('action="/brands"', f'action="{clean_base}/brands.html"')
        return html

    # 2. Render primary pages
    pages = [
        ("/", "index.html"),
        ("/brands", "brands.html"),
        ("/food", "food.html"),
        ("/local", "local.html"),
        ("/swaps", "swaps.html"),
        ("/flows", "flows.html"),
        ("/methodology", "methodology.html"),
    ]

    for route, filename in pages:
        res = client.get(route)
        if res.status_code == 200:
            content = process_html(res.text)
            (out_path / filename).write_text(content, encoding="utf-8")
            print(f"Rendered {route} -> {filename}")
        else:
            print(f"Failed to render {route}: {res.status_code}")

    # 3. Render dynamic brand detail pages
    db = SessionLocal()
    brands = db.query(Brand).all()
    brands_dir = out_path / "brands"
    brands_dir.mkdir(exist_ok=True)

    for b in brands:
        res = client.get(f"/brands/{b.slug}")
        if res.status_code == 200:
            content = process_html(res.text)
            # Support both /brands/slug.html and /brands/slug/index.html
            (brands_dir / f"{b.slug}.html").write_text(content, encoding="utf-8")
            slug_dir = brands_dir / b.slug
            slug_dir.mkdir(exist_ok=True)
            (slug_dir / "index.html").write_text(content, encoding="utf-8")
            print(f"Rendered brand page -> brands/{b.slug}.html")

    # 4. Export static API JSON endpoints for client-side queries
    api_routes = [
        ("/v1/brands", "api/v1/brands.json"),
        ("/v1/food/sourcing-ladder", "api/v1/food/sourcing-ladder.json"),
        ("/v1/food/dollar-split", "api/v1/food/dollar-split.json"),
        ("/v1/food/makers", "api/v1/food/makers.json"),
        ("/v1/swaps", "api/v1/swaps.json"),
        ("/v1/local/places", "api/v1/local/places.json"),
        ("/v1/methodology", "api/v1/methodology.json"),
    ]

    for api_route, api_file in api_routes:
        res = client.get(api_route)
        if res.status_code == 200:
            dest_file = out_path / api_file
            dest_file.parent.mkdir(parents=True, exist_ok=True)
            dest_file.write_text(res.text, encoding="utf-8")
            print(f"Exported API JSON {api_route} -> {api_file}")

    # Add .nojekyll for GitHub Pages
    (out_path / ".nojekyll").write_text("", encoding="utf-8")
    print(f"Export completed successfully to {out_path.absolute()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="dist", help="Output directory")
    parser.add_argument("--base-url", default="/shoptegrity-site", help="Base URL for GitHub Pages")
    args = parser.parse_args()
    export_site(output_dir=args.out, base_url=args.base_url)
