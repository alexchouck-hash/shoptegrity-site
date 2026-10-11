"""Static site exporter for Cloudflare Pages.

Renders all Jinja2 pages and exports static JSON API endpoints so the
Shoptegrity site can be served as plain files from the site root (shopteg.com).

The export fails loudly: a page that does not render, an internal link that
points nowhere, or an image that nothing uses and nobody allow-listed exits
non-zero so Cloudflare does not publish a broken or leaky site.
"""

import os
import sys
import shutil
import argparse
from html.parser import HTMLParser
from pathlib import Path
from fastapi.testclient import TestClient

from api.app.main import app
from api.app.routers.web_views import templates
from pipeline.seed_data import run_seed
from pipeline.top2000_brands import export_top2000_json, seed_top2000_db
from pipeline.healthcare_2000 import export_healthcare_json, seed_healthcare_db, generate_healthcare_2000
from pipeline.top2000_brands import generate_top_2000_brands
from pipeline.provenance import QUEUE_PATH, ROOT, write_verification_queue
from api.app.db.session import SessionLocal
from api.app.models.core import Brand

client = TestClient(app)


class _RefParser(HTMLParser):
    """Collects href and src values from one HTML document."""

    def __init__(self):
        super().__init__()
        self.refs = []

    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            if name in ("href", "src") and value:
                self.refs.append(value)


def _root_ref_resolves(out_path: Path, ref: str) -> bool:
    """True when a root-relative reference matches a file the static host will serve."""
    path = ref.split("#", 1)[0].split("?", 1)[0]
    rel = path.lstrip("/")
    if rel == "":
        candidates = ["index.html"]
    elif path.endswith("/"):
        candidates = [rel + "index.html"]
    else:
        candidates = [rel, rel + ".html", rel + "/index.html"]
    return any((out_path / c).is_file() for c in candidates)


def check_internal_links(out_path: Path) -> list:
    """Returns (page, reference) pairs for every root-relative link that resolves to nothing."""
    broken = []
    for page in sorted(out_path.rglob("*.html")):
        parser = _RefParser()
        parser.feed(page.read_text(encoding="utf-8"))
        for ref in parser.refs:
            if not ref.startswith("/") or ref.startswith("//"):
                continue
            if not _root_ref_resolves(out_path, ref):
                broken.append((str(page.relative_to(out_path)), ref))
    return broken


# Images published at /static/img/ although no page, stylesheet, script or JSON export names them.
# Every file in dist is public whether linked or not, so each entry needs a reason it is safe to serve.
STATIC_IMG_ALLOWLIST = {
    "favicon-32.png": "Shoptegrity's own site icon; makes no claim about any company",
    "icon-192.png": "Shoptegrity's own app icon; makes no claim about any company",
    "icon-512.png": "Shoptegrity's own app icon; makes no claim about any company",
    "logo.png": "Shoptegrity's own logo, kept for press and link previews; makes no claim about any company",
    "logo.svg": "Shoptegrity's own logo, kept for press and link previews; makes no claim about any company",
}

# Files whose text can reference an image.
_REFERENCING_SUFFIXES = {".html", ".css", ".js", ".json", ".webmanifest", ".xml", ".txt"}


def check_static_images(out_path: Path, allowlist=STATIC_IMG_ALLOWLIST) -> list:
    """Returns static/img paths that no exported text file references and the allowlist does not cover."""
    img_dir = out_path / "static" / "img"
    if not img_dir.is_dir():
        return []
    texts = [
        p.read_text(encoding="utf-8", errors="ignore")
        for p in out_path.rglob("*")
        if p.is_file() and p.suffix in _REFERENCING_SUFFIXES
    ]
    unreferenced = []
    for img in sorted(img_dir.rglob("*")):
        if not img.is_file():
            continue
        rel = img.relative_to(img_dir).as_posix()
        if rel in allowlist:
            continue
        ref = f"static/img/{rel}"
        if not any(ref in text for text in texts):
            unreferenced.append(ref)
    return unreferenced


def export_site(output_dir: str = "dist", base_url: str = ""):
    failures = []
    print(f"Ensuring database is seeded...")
    run_seed()
    with SessionLocal() as db:
        seed_top2000_db(db)
        seed_healthcare_db(db)
    export_top2000_json()
    export_healthcare_json()
    queued = write_verification_queue({
        "brands": generate_top_2000_brands(),
        "healthcare": generate_healthcare_2000(),
    })
    print(f"Verification queue: {queued} unsourced claims withheld ({QUEUE_PATH.relative_to(ROOT).as_posix()}, gitignored)")

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
        # Root-level favicon: requested at /favicon.ico by browsers and crawlers
        shutil.copy2(static_src / "favicon.ico", out_path / "favicon.ico")

    # Helper to clean and adjust links for base_url
    def process_html(html: str) -> str:
        if not base_url:
            return html
        # Prefix root links with base_url
        clean_base = base_url.rstrip("/")
        html = html.replace('href="/static/', f'href="{clean_base}/static/')
        html = html.replace('src="/static/', f'src="{clean_base}/static/')
        html = html.replace('href="/housing', f'href="{clean_base}/housing.html')
        html = html.replace('href="/healthcare', f'href="{clean_base}/healthcare.html')
        html = html.replace('href="/brands', f'href="{clean_base}/brands.html')
        html = html.replace('href="/food', f'href="{clean_base}/food.html')
        html = html.replace('href="/local', f'href="{clean_base}/local.html')
        html = html.replace('href="/swaps', f'href="{clean_base}/swaps.html')
        html = html.replace('href="/flows', f'href="{clean_base}/flows.html')
        html = html.replace('href="/parents', f'href="{clean_base}/parents.html')
        html = html.replace('href="/community', f'href="{clean_base}/community.html')
        html = html.replace('href="/methodology', f'href="{clean_base}/methodology.html')
        html = html.replace('href="/corrections', f'href="{clean_base}/corrections.html')
        html = html.replace('href="/sell-direct', f'href="{clean_base}/sell-direct.html')
        html = html.replace('href="/disclosures', f'href="{clean_base}/disclosures.html')
        html = html.replace('href="/"', f'href="{clean_base}/index.html"')
        html = html.replace('action="/brands"', f'action="{clean_base}/brands.html"')
        html = html.replace('action="/flows"', f'action="{clean_base}/flows.html"')
        html = html.replace('action="/healthcare"', f'action="{clean_base}/healthcare.html"')
        return html

    # 2. Render primary pages
    pages = [
        ("/", "index.html"),
        ("/housing", "housing.html"),
        ("/healthcare", "healthcare.html"),
        ("/brands", "brands.html"),
        ("/parents", "parents.html"),
        ("/food", "food.html"),
        ("/local", "local.html"),
        ("/swaps", "swaps.html"),
        ("/flows", "flows.html"),
        ("/community", "community.html"),
        ("/methodology", "methodology.html"),
        ("/corrections", "corrections.html"),
        ("/sell-direct", "sell-direct.html"),
        ("/disclosures", "disclosures.html"),
    ]

    for route, filename in pages:
        res = client.get(route)
        if res.status_code == 200:
            content = process_html(res.text)
            (out_path / filename).write_text(content, encoding="utf-8")
            print(f"Rendered {route} -> {filename}")
        else:
            failures.append(f"page {route} returned {res.status_code}")
            print(f"Failed to render {route}: {res.status_code}")

    # Ensure clean directory index copies for /healthcare and /housing
    for clean_sec in ["healthcare", "housing", "food", "local", "swaps", "flows", "community", "methodology", "parents", "corrections", "sell-direct", "disclosures"]:
        sec_file = out_path / f"{clean_sec}.html"
        if sec_file.exists():
            sec_dir = out_path / clean_sec
            sec_dir.mkdir(exist_ok=True)
            shutil.copy2(sec_file, sec_dir / "index.html")

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
        else:
            failures.append(f"brand page /brands/{b.slug} returned {res.status_code}")
    db.close()

    # 4. Export static API JSON endpoints for client-side queries
    api_routes = [
        ("/v1/brands", "api/v1/brands.json"),
        ("/v1/brands/database?limit=1000", "api/v1/brands/database.json"),
        ("/v1/brands/retailers", "api/v1/brands/retailers.json"),
        ("/v1/food/sourcing-ladder", "api/v1/food/sourcing-ladder.json"),
        ("/v1/food/dollar-split", "api/v1/food/dollar-split.json"),
        ("/v1/food/makers", "api/v1/food/makers.json"),
        ("/v1/food/farmland-ownership", "api/v1/food/farmland-ownership.json"),
        ("/v1/food/farm-budgets", "api/v1/food/farm-budgets.json"),
        ("/v1/swaps", "api/v1/swaps.json"),
        ("/v1/local/places", "api/v1/local/places.json"),
        ("/v1/methodology", "api/v1/methodology.json"),
        ("/v1/housing/overview", "api/v1/housing/overview.json"),
        ("/v1/housing/landlords", "api/v1/housing/landlords.json"),
        ("/v1/healthcare/database?limit=1000", "api/v1/healthcare/database.json"),
        ("/v1/healthcare/stats", "api/v1/healthcare/stats.json"),
    ]

    for api_route, api_file in api_routes:
        res = client.get(api_route)
        if res.status_code == 200:
            dest_file = out_path / api_file
            dest_file.parent.mkdir(parents=True, exist_ok=True)
            dest_file.write_text(res.text, encoding="utf-8")
            print(f"Exported API JSON {api_route} -> {api_file}")
        else:
            failures.append(f"API {api_route} returned {res.status_code}")

    # Also ensure the raw static json bundles are copied
    for raw_f in ["brands_top2000.json", "retailers.json", "healthcare_2000.json"]:
        raw_src = Path(f"api/v1/{raw_f}")
        if raw_src.exists():
            raw_dest = out_path / f"api/v1/{raw_f}"
            raw_dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(raw_src, raw_dest)
            print(f"Copied {raw_src} -> {raw_dest}")

    # Not-found page: Cloudflare Pages serves 404.html for any path that has no file
    not_found_html = process_html(templates.get_template("not_found.html").render(active_page=""))
    (out_path / "404.html").write_text(not_found_html, encoding="utf-8")
    print("Wrote 404.html")

    # Refuse to publish a site with broken internal links
    broken = check_internal_links(out_path)
    for page, ref in broken:
        failures.append(f"broken link in {page}: {ref}")

    # Refuse to publish an image nothing uses unless it is allow-listed with a reason
    for ref in check_static_images(out_path):
        failures.append(f"unreferenced image {ref}: link it from a page or add it to STATIC_IMG_ALLOWLIST")

    if failures:
        print(f"Export FAILED with {len(failures)} problem(s):")
        for item in failures:
            print(f"  - {item}")
        sys.exit(1)

    # Crawl files: sitemap of every exported page, robots.txt pointing to it
    site = "https://shopteg.com"
    urls = []
    for html_file in sorted(out_path.rglob("*.html")):
        rel = html_file.relative_to(out_path).as_posix()
        if rel == "404.html" or rel.endswith("/index.html"):
            continue
        path = "/" if rel == "index.html" else "/" + rel[:-5]
        urls.append(f"  <url><loc>{site}{path}</loc></url>")
    sitemap = ['<?xml version="1.0" encoding="UTF-8"?>',
               '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">', *urls, "</urlset>", ""]
    (out_path / "sitemap.xml").write_text("\n".join(sitemap), encoding="utf-8")
    (out_path / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\n\nSitemap: {site}/sitemap.xml\n", encoding="utf-8")
    print(f"Wrote sitemap.xml ({len(urls)} URLs) and robots.txt")

    # Retained for compatibility with the older GitHub Pages layout; harmless on Cloudflare
    (out_path / ".nojekyll").write_text("", encoding="utf-8")
    print(f"Export completed successfully to {out_path.absolute()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="dist", help="Output directory")
    parser.add_argument(
        "--base-url",
        default="",
        help='URL prefix for links. Leave empty for a site served from the root (shopteg.com).',
    )
    args = parser.parse_args()
    export_site(output_dir=args.out, base_url=args.base_url)
