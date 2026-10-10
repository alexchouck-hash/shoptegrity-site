from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from api.app.db.session import init_db
from api.app.routers import brands, food_chain, swaps, flows, local, methodology, web_views, parent_feed, healthcare, housing, community


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables on startup
    init_db()
    yield


app = FastAPI(
    title="Shoptegrity Platform API",
    description="Unified API & Web Platform for Brand Integrity, Food Chain Transparency, and Local Services.",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for external callers and frontend applications
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
static_dir = Path(__file__).parent.parent.parent / "web" / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

api_v1_dir = Path(__file__).parent.parent.parent / "api" / "v1"
if api_v1_dir.exists():
    app.mount("/api/v1", StaticFiles(directory=str(api_v1_dir)), name="api_v1")

# Mount REST API routers
app.include_router(brands.router)
app.include_router(food_chain.router)
app.include_router(swaps.router)
app.include_router(flows.router)
app.include_router(local.router)
app.include_router(methodology.router)
app.include_router(parent_feed.router)
app.include_router(healthcare.router)
app.include_router(housing.router)
app.include_router(community.router)

# Mount interactive HTML web portal views
app.include_router(web_views.router)


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    # Browsers, crawlers and feed readers request this at the site root regardless of <link> tags.
    return FileResponse(static_dir / "favicon.ico", media_type="image/x-icon")


@app.get("/health")
def health_check():
    return {"status": "healthy", "platform": "Shoptegrity", "version": "1.0.0"}
