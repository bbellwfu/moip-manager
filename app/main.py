"""FastAPI MoIP Manager Application."""
import sys
import logging
from pathlib import Path
from contextlib import asynccontextmanager

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from app.routes import devices, switching, storage
from app import sync

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - runs on startup and shutdown."""
    # Startup: sync devices from controller
    logger.info("MoIP Manager starting up...")
    try:
        sync.sync_devices()
        logger.info("Initial device sync completed")
    except Exception as e:
        logger.warning(f"Initial device sync failed: {e}")
    yield
    # Shutdown
    logger.info("MoIP Manager shutting down...")


# Create FastAPI app
app = FastAPI(
    title="MoIP Manager",
    description="Web interface for Binary MoIP video distribution control",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(devices.router, prefix="/api", tags=["devices"])
app.include_router(switching.router, prefix="/api", tags=["switching"])
app.include_router(storage.router, prefix="/api", tags=["storage"])

# Mount static files - handle PyInstaller bundle path
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    # Running as PyInstaller bundle
    static_path = Path(sys._MEIPASS) / "app" / "static"
else:
    # Running from source
    static_path = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")


@app.get("/", include_in_schema=False)
async def root():
    """Serve the main HTML page."""
    return FileResponse(str(static_path / "index.html"))


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}
