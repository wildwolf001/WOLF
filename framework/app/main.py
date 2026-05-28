"""
WOLF 2.0 Backend
FastAPI Application Entry Point
"""
import asyncio
import os
import sys
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .api.routes import stream, websocket, sessions, files, tools, memory, config, permissions, logs, tasks as task_routes, git_routes, system as system_routes
from .core.runtime_config import runtime_config, load_config
from .utils.logging import setup_logging, get_logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    setup_logging("DEBUG")
    logger = get_logger("wolf")
    logger.info("=" * 50)
    logger.info("WOLF 2.0 starting up...")
    logger.info(f"Python: {sys.version}")
    logger.info("=" * 50)

    # Load configuration (from file and environment)
    load_config()
    logger.info(f"LLM Provider: {runtime_config.current_provider}")
    logger.info(f"MiniMax model: {runtime_config.providers.get('minimax', {}).model}")

    # Initialize memory system (data stored at E:/ai/ARG/WOLF2.0/wolf_b2/wolfdata)
    try:
        from .memory import setup_memory_system
        memory_dir = setup_memory_system()
        logger.info(f"Memory system initialized at: {memory_dir.path}")
    except Exception as e:
        logger.warning(f"Memory system initialization failed: {e}")

    # Create temp directory for agent file operations
    import os as _os
    temp_dir = _os.path.join(_os.path.dirname(_os.path.dirname(__file__)), 'temp')
    _os.makedirs(temp_dir, exist_ok=True)
    logger.info(f"Temp directory: {temp_dir}")

    # Register all tools (Write, Bash, Glob, Read, Edit, Grep)
    try:
        from .tools import register_all_tools
        register_all_tools(temp_dir=temp_dir)
        from .tools import tool_registry
        tools_count = len(tool_registry.list_tools())
        logger.info(f"Registered {tools_count} tools")
    except Exception as e:
        logger.warning(f"Tool registration failed: {e}")

    # Load skills (from bundled, user, and project directories)
    try:
        from .skills import load_skills
        skills_count = load_skills()
        logger.info(f"Loaded {skills_count} skills")
    except Exception as e:
        logger.warning(f"Skill loading failed: {e}")

    # Initialize RAG vector store (semantic code search)
    try:
        from .vector_store import setup_vector_store
        vs_config = getattr(runtime_config, 'vector_store', {}) or {}
        model = vs_config.get("embedding_model")
        setup_vector_store(embedding_model=model)
        from .vector_store import get_vector_store
        store = get_vector_store()
        logger.info(f"Vector store initialized: {store.count()} docs indexed")
    except Exception as e:
        logger.warning(f"Vector store initialization failed: {e}")

    # Initialize Prompt engineering system
    try:
        from .prompt import init_prompt_system
        import json, os as _os
        config_path = _os.path.join(_os.path.dirname(_os.path.dirname(__file__)), 'config.json')
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        result = init_prompt_system(config)
        logger.info(f"Prompt system initialized: {result['feature_flags']} feature flags")
    except Exception as e:
        logger.warning(f"Prompt system init failed: {e}")

    # Initialize LLM observability
    try:
        from .observability import setup_observability
        import json, os as _os
        config_path = _os.path.join(_os.path.dirname(_os.path.dirname(__file__)), 'config.json')
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        result = setup_observability(config.get("observability", {}))
        logger.info(f"Observability initialized: LangFuse={'connected' if result['langfuse_ready'] else 'memory'}")
    except Exception as e:
        logger.warning(f"Observability init failed: {e}")

    # Initialize evolution system
    try:
        from .evolution import setup_evolution_system
        setup_evolution_system()
        logger.info("Evolution system initialized")
    except Exception as e:
        logger.warning(f"Evolution system init failed: {e}")

    yield
    # Shutdown
    logger.info("WOLF 2.0 shutting down...")


# Create FastAPI app
app = FastAPI(
    title="WOLF 2.0",
    description="AI Programming Assistant Backend",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(stream.router, prefix="/api")
app.include_router(websocket.router, prefix="/api")
app.include_router(sessions.router, prefix="/api")
app.include_router(files.router, prefix="/api")
app.include_router(tools.router, prefix="/api")
app.include_router(memory.router, prefix="/api")
app.include_router(config.router, prefix="/api")
app.include_router(permissions.router, prefix="/api")
app.include_router(logs.router, prefix="/api")
app.include_router(task_routes.router, prefix="/api")
app.include_router(git_routes.router, prefix="/api")
app.include_router(system_routes.router, prefix="/api")

# Serve frontend static files
_frontend_dist = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'wolf_f', 'dist')
_frontend_dist = os.path.abspath(_frontend_dist)

if os.path.exists(_frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(_frontend_dist, "assets")), name="assets")


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": time.time()
    }


@app.get("/wolf.svg")
async def favicon():
    """Serve favicon"""
    svg_path = os.path.join(_frontend_dist, "wolf.svg")
    if os.path.exists(svg_path):
        return FileResponse(svg_path)
    return {"status": "not_found"}


@app.get("/{path:path}")
async def spa_fallback(request: Request, path: str):
    """SPA fallback - serve index.html for all non-API routes"""
    # Skip API routes
    if path.startswith("api/"):
        return {"status": "not_found", "detail": f"API route not found: {path}"}

    index_path = os.path.join(_frontend_dist, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"name": "WOLF 2.0", "version": "2.0.0", "status": "running"}


if __name__ == "__main__":
    import uvicorn

    load_config()
    host = getattr(runtime_config, 'host', '127.0.0.1')
    port = getattr(runtime_config, 'port', 8080)
    debug = getattr(runtime_config, 'debug', True)
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=debug
    )