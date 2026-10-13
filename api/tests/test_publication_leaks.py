"""Leaks around the publication gate: files, fields and keys that reach the public site or the
public repository without passing through pipeline/provenance.py.

The repository and the site (built from main) are both public, so a file in either one is
published whether or not a page links to it.
"""

import ast
import re
import shutil
import subprocess

import pytest
from fastapi.testclient import TestClient

from api.app.db.session import SessionLocal
from api.app.main import app
from api.app.models.core import Brand, Entity, Maker, Place
from build_static import STATIC_IMG_ALLOWLIST, check_static_images
from pipeline.healthcare_2000 import generate_healthcare_2000
from pipeline.provenance import QUEUE_PATH, ROOT
from pipeline.top2000_brands import generate_top_2000_brands

client = TestClient(app)


def _write(path, text=""):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


# --- Images: every file the site serves from static/img is used or allow-listed -----------------

def test_build_check_flags_unreferenced_image(tmp_path):
    img = tmp_path / "static" / "img"
    for name in ("used.png", "orphan.gif", "listed.png"):
        _write(img / name)
    _write(tmp_path / "index.html", '<img src="/static/img/used.png">')
    assert check_static_images(tmp_path, allowlist={"listed.png": "test"}) == ["static/img/orphan.gif"]


def test_build_check_counts_css_and_json_references(tmp_path):
    img = tmp_path / "static" / "img"
    _write(img / "bg.png")
    _write(img / "logo.png")
    _write(tmp_path / "static" / "css" / "styles.css", "body { background: url(/static/img/bg.png); }")
    _write(tmp_path / "api" / "v1" / "x.json", '{"logo_url": "/static/img/logo.png"}')
    assert check_static_images(tmp_path, allowlist={}) == []


def test_every_site_image_is_referenced_or_allowlisted(tmp_path):
    """web/static/img checked against the templates, stylesheets and scripts that ship with it."""
    site = tmp_path / "site"
    shutil.copytree(ROOT / "web" / "static", site / "static")
    shutil.copytree(ROOT / "web" / "templates", site / "templates")
    assert check_static_images(site) == []


def test_image_allowlist_entries_exist_and_give_a_reason():
    """A stale entry would let a new file with the same name skip the check."""
    for name, reason in STATIC_IMG_ALLOWLIST.items():
        assert reason.strip(), name
        assert (ROOT / "web" / "static" / "img" / name).is_file(), f"stale allowlist entry: {name}"


def test_gif_generator_never_writes_into_the_site():
    """scripts/generate_gif.py once wrote its GIFs straight into web/static/img."""
    tree = ast.parse((ROOT / "scripts" / "generate_gif.py").read_text(encoding="utf-8"))
    output_dirs = [
        ast.literal_eval(node.value)
        for node in tree.body
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "DEFAULT_OUTPUT_DIR" for t in node.targets)
    ]
    assert output_dirs == ["build/gifs"]
    docstring = ast.get_docstring(tree, clean=False)
    literals = [
        node.value for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value != docstring
    ]
    assert not [s for s in literals if "static" in s.replace("\\", "/")]


# --- Verification queue: withheld values never reach a tracked file ----------------------------

def _git(*args):
    try:
        res = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    except FileNotFoundError:
        pytest.skip("git is not installed")
    if res.returncode == 128:
        pytest.skip("not a git checkout")
    return res


def test_verification_queue_is_gitignored():
    res = _git("check-ignore", "-q", str(QUEUE_PATH))
    assert res.returncode == 0, (
        f"{QUEUE_PATH.relative_to(ROOT)} must be gitignored: it holds every withheld claim verbatim"
    )


def test_no_tracked_data_file_carries_withheld_values():
    """The site withholds unsourced claims; a tracked copy of their values would publish them anyway."""
    offenders = []
    for rel in _git("ls-files", "-z").stdout.split("\0"):
        path = ROOT / rel
        if not rel or path.suffix.lower() not in (".csv", ".tsv", ".json", ".jsonl") or not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "withheld_value" in text or '"_withheld"' in text:
            offenders.append(rel)
    assert offenders == []


# --- Swap categories: no uncited spend figures --------------------------------------------------

def test_swap_categories_withhold_uncited_spend_figures():
    categories = client.get("/v1/swaps").json()
    assert categories
    for cat in categories + [client.get("/v1/swaps/grocery").json()["category"]]:
        assert cat["avg_annual_spend"] is None, f"{cat['slug']}: spend figure has no cited source"
        assert cat["saves_money"] is None, f"{cat['slug']}: savings claim has no cited source"


# --- Machine keys: published keys carry no characterization --------------------------------------

def _keys(obj):
    if isinstance(obj, dict):
        for key, value in obj.items():
            yield key
            yield from _keys(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from _keys(value)


def test_housing_keys_and_page_identifiers_are_neutral():
    data = client.get("/v1/housing/overview").json()
    assert [k for k in _keys(data) if re.search(r"wall_?street|leak", k, re.I)] == []
    for split in data["rent_dollar_splits"].values():
        assert split["local_retention_pct"] + split["outside_share_pct"] == 100
    assert not re.search(r"wallSt|WallSt|wall_street|Leakage", client.get("/housing").text)


# --- README and GIF generator: no named-company claims outside the gate --------------------------

# Removed from README.md and scripts/generate_gif.py; the datasets do not track them, so list them here.
REMOVED_NAMES = ["Burt's Bees", "Clorox", "Annie's"]

_SUFFIX = re.compile(r",?\s+(?:Inc\.?|Incorporated|Corp\.?|Corporation|Co\.?|Company|LLC|L\.P\.|LP|Ltd\.?|plc|Holdings|Group)$")


def _name_variants(name):
    """The name without parenthetical descriptors and legal suffixes, split on " / "."""
    name = re.sub(r"\s*\([^()]*\)", "", name).strip()
    for part in name.split(" / "):
        while part:
            yield part
            shorter = _SUFFIX.sub("", part).strip()
            if shorter == part:
                break
            part = shorter


@pytest.fixture(scope="module")
def tracked_company_names():
    raw = set()
    for rec in generate_top_2000_brands():
        raw |= {rec.get("name"), rec.get("parent_company")}
    for rec in generate_healthcare_2000():
        raw |= {rec.get("name"), rec.get("parent_organization")}
    with SessionLocal() as db:
        for model in (Entity, Brand, Maker, Place):
            raw |= {row.name for row in db.query(model).all()}
    return {v for name in raw if name for v in _name_variants(name) if len(v) >= 3}


@pytest.mark.parametrize("rel", ["README.md", "scripts/generate_gif.py"])
def test_public_text_names_no_tracked_company(rel, tracked_company_names):
    """Claims about a named company belong on the gated site, where they carry a citation."""
    text = (ROOT / rel).read_text(encoding="utf-8")
    found = sorted(n for n in tracked_company_names if re.search(rf"(?<!\w){re.escape(n)}(?!\w)", text))
    found += [n for n in REMOVED_NAMES if n.lower() in text.lower()]
    assert found == [], f"{rel} names {found}"
