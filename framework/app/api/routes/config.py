"""
Config Route
"""
import os
import time
from typing import Dict, Any
from fastapi import APIRouter, HTTPException

from ..models import ConfigUpdate
from ...utils.logging import get_logger

router = APIRouter()
logger = get_logger("config")

# In-memory config store
_config: Dict[str, Any] = {
    "model": "claude-sonnet-4-20250514",
    "max_turns": 30,
    "temperature": 0.7,
    "timeout": 120
}

# Provider configs (simulated) - default providers with models
_provider_configs: Dict[str, Any] = {
    "minimax": {
        "api_key": None,
        "group_id": None,
        "model": "MiniMax-M2.7",
        "has_api_key": False
    },
    "deepseek": {
        "api_key": None,
        "group_id": None,
        "model": "deepseek-chat",
        "has_api_key": False
    },
    "qwen": {
        "api_key": None,
        "group_id": None,
        "model": "qwen-turbo",
        "has_api_key": False
    },
    "openai": {
        "api_key": None,
        "group_id": None,
        "model": "gpt-4o",
        "has_api_key": False
    },
    "anthropic": {
        "api_key": None,
        "group_id": None,
        "model": "claude-3-5-sonnet-20241022",
        "has_api_key": False
    },
    "zhipu": {
        "api_key": None,
        "group_id": None,
        "model": "glm-4",
        "has_api_key": False
    },
    "moonshot": {
        "api_key": None,
        "group_id": None,
        "model": "moonshot-v1-8k",
        "has_api_key": False
    },
}
_current_provider = "minimax"

# Storage paths
_storage_paths: Dict[str, str] = {
    "local_storage_path": "./wolf_data",
    "knowledge_base_path": "./wolf_data/knowledge",
    "sessions_path": "./wolf_data/sessions",
    "upload_path": "./wolf_data/uploads"
}

# Work directory
_work_directory: str = ""


@router.get("/config/config")
async def get_full_config() -> dict:
    """Get full configuration including providers"""
    logger.info("GET /config/config")
    return {
        "current_provider": _current_provider,
        "config": {
            "current_provider": _current_provider,
            "providers": _provider_configs
        }
    }


@router.get("/config")
async def get_config() -> dict:
    """Get current configuration"""
    logger.debug("GET /config")
    return {"config": _config}


@router.patch("/config")
async def update_config(request: ConfigUpdate) -> dict:
    """Update configuration"""
    logger.info(f"PATCH /config: {request.config}")
    _config.update(request.config)
    return {"status": "ok", "config": _config}


# IMPORTANT: Specific routes must come BEFORE generic /config/{key}
@router.get("/config/storage-paths")
async def get_storage_paths() -> dict:
    """Get storage paths configuration"""
    return {"paths": _storage_paths}


@router.post("/config/storage-path")
async def set_storage_path(request: dict) -> dict:
    """Set a storage path"""
    from ...core.runtime_config import runtime_config, save_config

    path_type = request.get("path_type")
    path = request.get("path")

    if not path_type or not path:
        raise HTTPException(status_code=400, detail="path_type and path are required")

    _storage_paths[path_type] = path

    # Sync to runtime_config and persist
    runtime_config.set_storage_path(path_type, path)
    save_config()

    # When local_storage changes, rebuild memory directory
    if path_type == "local_storage":
        try:
            from ...memory.directory import reset_memory_directory_with_config
            new_dir = reset_memory_directory_with_config()
            logger.info(f"Memory directory rebuilt at: {new_dir.path}")
        except Exception as e:
            logger.warning(f"Failed to rebuild memory directory: {e}")

    return {"status": "ok"}


@router.get("/config/storage-paths/status")
async def get_storage_paths_status() -> dict:
    """Get status of storage paths"""
    status = {}
    for path_type, path in _storage_paths.items():
        exists = os.path.exists(path) if path else False
        is_writable = os.access(path, os.W_OK) if exists else False
        status[path_type] = {
            "exists": exists,
            "is_writable": is_writable
        }
    return {"status": status}


@router.get("/config/work-directory")
async def get_work_directory() -> dict:
    """Get work directory"""
    return {"work_directory": _work_directory}


@router.post("/config/work-directory")
async def set_work_directory(request: dict) -> dict:
    """Set work directory"""
    path = request.get("path")
    if not path:
        raise HTTPException(status_code=400, detail="path is required")

    global _work_directory
    _work_directory = path

    exists = os.path.exists(path)
    is_writable = os.access(path, os.W_OK) if exists else False

    return {
        "success": True,
        "work_directory": path,
        "status": {
            "set": True,
            "exists": exists,
            "is_writable": is_writable
        }
    }


@router.get("/config/work-directory/status")
async def get_work_directory_status() -> dict:
    """Get work directory status"""
    exists = os.path.exists(_work_directory) if _work_directory else False
    is_writable = os.access(_work_directory, os.W_OK) if exists else False

    return {
        "status": {
            "set": bool(_work_directory),
            "exists": exists,
            "is_writable": is_writable
        }
    }


@router.post("/config/provider")
async def set_provider(request: dict) -> dict:
    """Set current provider"""
    from ...core.runtime_config import runtime_config, save_config

    provider = request.get("provider")
    if provider not in _provider_configs and provider != "minimax":
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")
    global _current_provider
    _current_provider = provider
    # Also update runtime_config so LLMService uses the correct provider
    runtime_config.current_provider = provider
    save_config()
    return {"status": "ok", "current_provider": _current_provider}


@router.post("/config/api-key")
async def save_api_key(request: dict) -> dict:
    """Save API key for a provider"""
    from ...core.runtime_config import runtime_config, save_config

    provider = request.get("provider")
    api_key = request.get("api_key")
    group_id = request.get("group_id")

    if not provider or not api_key:
        raise HTTPException(status_code=400, detail="Provider and api_key are required")

    # Update runtime_config
    runtime_config.set_provider_api_key(provider, api_key)
    if group_id:
        runtime_config.set_provider_group_id(provider, group_id)
    else:
        # Clear group_id when not provided (e.g., user left it empty)
        runtime_config.set_provider_group_id(provider, None)

    # Update local provider configs for frontend sync
    if provider not in _provider_configs:
        _provider_configs[provider] = {"api_key": None, "group_id": None, "model": None, "has_api_key": False}

    _provider_configs[provider]["api_key"] = api_key
    _provider_configs[provider]["group_id"] = group_id if group_id else None
    _provider_configs[provider]["has_api_key"] = bool(api_key)

    # Persist to config.json
    save_config()

    return {"status": "ok"}


@router.post("/config/model")
async def set_model(request: dict) -> dict:
    """Set model for a provider"""
    from ...core.runtime_config import runtime_config

    provider = request.get("provider")
    model = request.get("model")

    if not provider or not model:
        raise HTTPException(status_code=400, detail="Provider and model are required")

    # Update runtime_config
    runtime_config.set_provider_model(provider, model)

    # Update local provider configs for frontend sync
    if provider in _provider_configs:
        _provider_configs[provider]["model"] = model
    else:
        _provider_configs[provider] = {
            "api_key": None,
            "group_id": None,
            "model": model,
            "has_api_key": False
        }

    return {"status": "ok", "model": model}


@router.post("/config/test")
async def test_api_key(request: dict) -> dict:
    """Test API key for a provider"""
    provider = request.get("provider")
    api_key = request.get("api_key")
    model = request.get("model")

    # Simulate API test
    if api_key and len(api_key) > 10:
        return {"success": True, "message": f"API key for {provider} is valid"}
    return {"success": False, "message": "Invalid API key"}


# ============== NEW ENHANCED CONFIG ENDPOINTS ==============

# Query Engine Configuration
_query_engine_config: dict = {
    "max_turns": 30,
    "max_tokens": 8000,
    "temperature": 0.7,
    "timeout": 120.0,
    "stream": True,
    "max_parallel_tools": 5,
    "max_context_tokens": 100000,
    "context_overflow_threshold": 0.9
}

@router.get("/config/query-engine")
async def get_query_engine_config() -> dict:
    """Get Query Engine configuration"""
    return {"config": _query_engine_config}


@router.post("/config/query-engine")
async def update_query_engine_config(request: dict) -> dict:
    """Update Query Engine configuration"""
    global _query_engine_config
    allowed_keys = set(_query_engine_config.keys())

    for key, value in request.items():
        if key in allowed_keys:
            _query_engine_config[key] = value

    return {"status": "ok", "config": _query_engine_config}


# MCP Servers Configuration
_mcp_servers: list = []

@router.get("/config/mcp-servers")
async def get_mcp_servers() -> dict:
    """Get MCP servers configuration"""
    return {"servers": _mcp_servers}


@router.post("/config/mcp-servers")
async def update_mcp_servers(request: dict) -> dict:
    """Update MCP servers configuration"""
    global _mcp_servers
    action = request.get("action", "set")

    if action == "add":
        server = request.get("server", {})
        if server.get("name"):
            _mcp_servers.append(server)
    elif action == "remove":
        name = request.get("name")
        _mcp_servers = [s for s in _mcp_servers if s.get("name") != name]
    elif action == "set":
        _mcp_servers = request.get("servers", [])

    return {"status": "ok", "servers": _mcp_servers}


# Tool Configuration
_tool_config: dict = {
    "max_concurrent_reads": 10,
    "bash_enabled": True,
    "edit_enabled": True,
    "write_enabled": True,
    "glob_enabled": True,
    "grep_enabled": True,
    "agent_enabled": True
}

@router.get("/config/tools")
async def get_tool_config() -> dict:
    """Get Tool configuration"""
    return {"config": _tool_config}


@router.post("/config/tools")
async def update_tool_config(request: dict) -> dict:
    """Update Tool configuration"""
    global _tool_config

    for key, value in request.items():
        if key in _tool_config:
            _tool_config[key] = value

    return {"status": "ok", "config": _tool_config}


# Skills Configuration
def _get_skills_list() -> list:
    """Get all loaded skills as dicts"""
    try:
        from ...skills import skill_registry
        return [s.to_dict() for s in skill_registry.list_skills()]
    except Exception:
        return []


@router.get("/config/skills")
async def get_skills() -> dict:
    """Get all loaded skills"""
    return {"skills": _get_skills_list()}


@router.post("/config/skills/reload")
async def reload_skills_endpoint() -> dict:
    """Reload skills from disk"""
    try:
        from ....skills import reload_skills
        count = reload_skills()
        return {"status": "ok", "count": count, "skills": _get_skills_list()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Complete Config (for frontend initial load)
@router.get("/config/all")
async def get_all_config() -> dict:
    """Get all configuration in one call"""
    return {
        "config": _config,
        "query_engine": _query_engine_config,
        "tools": _tool_config,
        "providers": _provider_configs,
        "current_provider": _current_provider,
        "storage_paths": _storage_paths,
        "mcp_servers": _mcp_servers,
        "skills": _get_skills_list()
    }


# ============== .env FILE MANAGEMENT ==============

def _get_env_path() -> str:
    """Get absolute path to .env file"""
    import os as _os
    # .env is at the project root (wolf_b2/.env)
    return _os.path.join(_os.path.dirname(__file__), "..", "..", "..", ".env")


def _parse_env_for_llm_config() -> dict:
    """Parse .env file and return LLM-related configuration"""
    import os as _os

    env_path = _get_env_path()
    result = {
        "current_provider": "minimax",
        "providers": {},
        "env_path": _os.path.abspath(env_path),
    }

    # Define known providers and their env var patterns
    provider_env_map = {
        "minimax": {"api_key": "MINIMAX_API_KEY", "group_id": "MINIMAX_GROUP_ID", "model": "MINIMAX_MODEL"},
        "deepseek": {"api_key": "DEEPSEEK_API_KEY", "model": "DEEPSEEK_MODEL"},
        "qwen": {"api_key": "QWEN_API_KEY", "model": "QWEN_MODEL"},
        "openai": {"api_key": "OPENAI_API_KEY", "model": "OPENAI_MODEL"},
        "anthropic": {"api_key": "ANTHROPIC_API_KEY", "model": "ANTHROPIC_MODEL"},
        "zhipu": {"api_key": "ZHIPU_API_KEY", "model": "ZHIPU_MODEL"},
        "moonshot": {"api_key": "MOONSHOT_API_KEY", "model": "MOONSHOT_MODEL"},
    }

    current = _os.getenv("LLM_PROVIDER", "minimax")
    result["current_provider"] = current

    for provider_id, env_keys in provider_env_map.items():
        api_key = _os.getenv(env_keys["api_key"], "")
        model = _os.getenv(env_keys.get("model", ""), "")
        group_id = _os.getenv(env_keys.get("group_id", ""), "")

        has_key = bool(api_key and api_key not in ("your-api-key", "your-key", ""))
        masked_key = ""
        if has_key and len(api_key) > 8:
            masked_key = api_key[:4] + "****" + api_key[-4:]

        result["providers"][provider_id] = {
            "api_key_masked": masked_key,
            "has_api_key": has_key,
            "group_id": group_id if group_id else None,
            "model": model or "",
            "api_key_env": env_keys["api_key"],
            "model_env": env_keys.get("model", ""),
            "group_id_env": env_keys.get("group_id", ""),
        }

    return result


@router.get("/config/env")
async def get_env_config() -> dict:
    """Get LLM configuration parsed from .env file"""
    config = _parse_env_for_llm_config()
    # Also return provider model lists for display
    providers_list = [
        {"id": "minimax", "name": "MiniMax", "requires_group_id": True},
        {"id": "deepseek", "name": "DeepSeek", "requires_group_id": False},
        {"id": "qwen", "name": "Qwen (Alibaba)", "requires_group_id": False},
        {"id": "openai", "name": "OpenAI", "requires_group_id": False},
        {"id": "anthropic", "name": "Anthropic", "requires_group_id": False},
        {"id": "zhipu", "name": "Zhipu AI (智谱)", "requires_group_id": False},
        {"id": "moonshot", "name": "Moonshot (月之暗面)", "requires_group_id": False},
    ]
    config["providers_list"] = providers_list
    return config


@router.get("/config/env/raw")
async def get_env_raw() -> dict:
    """Get raw .env file content"""
    import os as _os

    env_path = _get_env_path()
    if not _os.path.exists(env_path):
        return {"content": "", "exists": False, "path": _os.path.abspath(env_path)}

    with open(env_path, "r", encoding="utf-8") as f:
        content = f.read()

    return {
        "content": content,
        "exists": True,
        "path": _os.path.abspath(env_path),
    }


@router.post("/config/env")
async def save_env(request: dict) -> dict:
    """Save .env file content and reload environment"""
    import os as _os

    content = request.get("content", "")
    env_path = _get_env_path()

    # Backup the old file
    if _os.path.exists(env_path):
        backup_path = env_path + ".bak"
        with open(env_path, "r", encoding="utf-8") as f:
            old_content = f.read()
        with open(backup_path, "w", encoding="utf-8") as f:
            f.write(old_content)

    # Write new content
    with open(env_path, "w", encoding="utf-8") as f:
        f.write(content)

    # Reload dotenv
    try:
        from dotenv import load_dotenv
        load_dotenv(override=True)

        # Reload runtime_config from updated env
        from ...core.runtime_config import load_config
        load_config()
    except Exception as e:
        logger.warning(f"Failed to reload config after .env save: {e}")

    # Also sync provider from updated env
    global _current_provider
    _current_provider = _os.getenv("LLM_PROVIDER", "minimax")

    # Refresh provider configs from runtime_config
    _refresh_providers_from_runtime()

    return {"status": "ok", "path": _os.path.abspath(env_path)}


@router.post("/config/env/open")
async def open_env_file() -> dict:
    """Open .env file in system default editor"""
    import os as _os
    import platform
    import subprocess

    env_path = _get_env_path()
    abs_path = _os.path.abspath(env_path)

    if not _os.path.exists(abs_path):
        return {"status": "error", "message": f".env file not found at {abs_path}"}

    try:
        system = platform.system()
        if system == "Windows":
            _os.startfile(abs_path)
        elif system == "Darwin":  # macOS
            subprocess.Popen(["open", abs_path])
        else:  # Linux
            subprocess.Popen(["xdg-open", abs_path])
        return {"status": "ok", "path": abs_path}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/config/env/switch-provider")
async def switch_provider_in_env(request: dict) -> dict:
    """Switch LLM_PROVIDER in .env file"""
    import os as _os

    provider = request.get("provider", "minimax")
    env_path = _get_env_path()

    if not _os.path.exists(env_path):
        return {"status": "error", "message": ".env file not found"}

    with open(env_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    new_lines = []
    found = False
    for line in lines:
        if line.startswith("LLM_PROVIDER="):
            new_lines.append(f"LLM_PROVIDER={provider}\n")
            found = True
        else:
            new_lines.append(line)

    if not found:
        new_lines.append(f"\nLLM_PROVIDER={provider}\n")

    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    # Reload
    try:
        from dotenv import load_dotenv
        load_dotenv(override=True)
        from ...core.runtime_config import load_config
        load_config()
    except Exception as e:
        logger.warning(f"Failed to reload after provider switch: {e}")

    global _current_provider
    _current_provider = provider

    return {"status": "ok", "current_provider": provider}


def _refresh_providers_from_runtime():
    """Sync _provider_configs from runtime_config"""
    from ...core.runtime_config import runtime_config

    global _provider_configs
    for provider_id in _provider_configs:
        if provider_id in runtime_config.providers:
            pc = runtime_config.providers[provider_id]
            _provider_configs[provider_id] = {
                "api_key": pc.api_key,
                "group_id": pc.group_id,
                "model": pc.model,
                "has_api_key": bool(pc.api_key),
            }