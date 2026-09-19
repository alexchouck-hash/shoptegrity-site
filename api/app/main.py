from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from api.app.db.session import init_db
from api.app.routers import brands, food_chain, swaps, flows, local, methodology, web_views, parent_feed


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

# Mount REST API routers
app.include_router(brands.router)
app.include_router(food_chain.router)
app.include_router(swaps.router)
app.include_router(flows.router)
app.include_router(local.router)
app.include_router(methodology.router)
app.include_router(parent_feed.router)

# Mount interactive HTML web portal views
app.include_router(web_views.router)


@app.get("/health")
def health_check():
    return {"status": "healthy", "platform": "Shoptegrity", "version": "1.0.0"}
