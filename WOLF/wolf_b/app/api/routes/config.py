"""
Config API - Runtime configuration for LLM providers
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

from app.core.runtime_config import runtime_config, LLM_PROVIDERS, save_config, load_config

router = APIRouter()


class SetProviderRequest(BaseModel):
    provider: str


class SetApiKeyRequest(BaseModel):
    provider: str
    api_key: str
    group_id: Optional[str] = None


class SetModelRequest(BaseModel):
    provider: str
    model: str


class TestApiKeyRequest(BaseModel):
    provider: str
    api_key: str
    group_id: Optional[str] = None
    model: Optional[str] = None


class SetStoragePathRequest(BaseModel):
    path_type: str  # local_storage, knowledge_base, sessions, upload
    path: str


@router.get("/providers")
async def get_providers():
    """Get list of available LLM providers"""
    return {
        "providers": [
            {
                "id": provider_id,
                "name": info["name"],
                "models": info["models"],
                "requires_group_id": info["requires_group_id"],
                "api_key_label": info["api_key_label"],
                "group_id_label": info["group_id_label"]
            }
            for provider_id, info in LLM_PROVIDERS.items()
        ]
    }


@router.get("/config")
async def get_config():
    """Get current runtime configuration (masks API keys)"""
    return {
        "current_provider": runtime_config.current_provider,
        "config": runtime_config.to_dict()
    }


@router.get("/status")
async def get_provider_status():
    """Get status of all LLM providers including circuit breaker state"""
    from app.services.llm_service import llm_service
    return {
        "providers": llm_service.get_provider_status()
    }


@router.post("/reset")
async def reset_provider(provider: str = None):
    """Reset circuit breaker for a provider or all providers"""
    from app.services.llm_service import llm_service
    if provider:
        if provider not in LLM_PROVIDERS:
            raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")
        llm_service.reset_provider(provider)
        return {"success": True, "message": f"Provider {provider} has been reset"}
    else:
        # Reset all providers
        for provider_id in LLM_PROVIDERS.keys():
            llm_service.reset_provider(provider_id)
        return {"success": True, "message": "All providers have been reset"}


@router.post("/provider")
async def set_provider(request: SetProviderRequest):
    """Set the current LLM provider"""
    if request.provider not in LLM_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {request.provider}")

    runtime_config.current_provider = request.provider
    save_config()

    return {
        "success": True,
        "current_provider": runtime_config.current_provider,
        "model": runtime_config.get_current_config().model
    }


@router.post("/api-key")
async def set_api_key(request: SetApiKeyRequest):
    """Set API key for a provider"""
    if request.provider not in LLM_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {request.provider}")

    runtime_config.set_provider_api_key(request.provider, request.api_key)

    if request.group_id:
        runtime_config.set_provider_group_id(request.provider, request.group_id)

    save_config()

    return {
        "success": True,
        "provider": request.provider,
        "has_api_key": bool(runtime_config.providers[request.provider].api_key)
    }


@router.post("/model")
async def set_model(request: SetModelRequest):
    """Set model for a provider"""
    if request.provider not in LLM_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {request.provider}")

    provider_info = LLM_PROVIDERS.get(request.provider, {})
    if request.model not in provider_info.get("models", []):
        raise HTTPException(
            status_code=400,
            detail=f"Model {request.model} not available for {request.provider}"
        )

    runtime_config.set_provider_model(request.provider, request.model)
    save_config()

    return {
        "success": True,
        "provider": request.provider,
        "model": request.model
    }


@router.post("/test")
async def test_api_key(request: TestApiKeyRequest):
    """Test if an API key works by making a simple request"""
    import httpx

    if request.provider == "minimax":
        if not request.api_key:
            return {"success": False, "error": "API key required"}

        model = request.model or "abab6.5s-chat"
        group_id = request.group_id

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.minimaxi.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {request.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": "Hi, respond with 'OK' if you receive this."}],
                        "stream": False
                    }
                )
                if response.status_code == 200:
                    return {"success": True, "message": "API key is valid"}
                else:
                    return {"success": False, "error": f"API returned status {response.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    elif request.provider == "deepseek":
        if not request.api_key:
            return {"success": False, "error": "API key required"}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.deepseek.com/chat/completions",
                    headers={
                        "Authorization": f"Bearer {request.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "deepseek-chat",
                        "messages": [{"role": "user", "content": "Hi, respond with 'OK' if you receive this."}],
                        "stream": False
                    }
                )
                if response.status_code == 200:
                    return {"success": True, "message": "API key is valid"}
                else:
                    return {"success": False, "error": f"API returned status {response.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    elif request.provider == "openai":
        if not request.api_key:
            return {"success": False, "error": "API key required"}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {request.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "gpt-4o-mini",
                        "messages": [{"role": "user", "content": "Hi, respond with 'OK' if you receive this."}],
                        "stream": False
                    }
                )
                if response.status_code == 200:
                    return {"success": True, "message": "API key is valid"}
                else:
                    return {"success": False, "error": f"API returned status {response.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    elif request.provider == "qwen":
        if not request.api_key:
            return {"success": False, "error": "API key required"}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {request.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "qwen-turbo",
                        "messages": [{"role": "user", "content": "Hi, respond with 'OK' if you receive this."}],
                        "stream": False
                    }
                )
                if response.status_code == 200:
                    return {"success": True, "message": "API key is valid"}
                else:
                    return {"success": False, "error": f"API returned status {response.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    elif request.provider == "zhipu":
        if not request.api_key:
            return {"success": False, "error": "API key required"}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://open.bigmodel.cn/api/paas/v4/chat/completions",
                    headers={
                        "Authorization": f"Bearer {request.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "glm-4",
                        "messages": [{"role": "user", "content": "Hi, respond with 'OK' if you receive this."}],
                        "stream": False
                    }
                )
                if response.status_code == 200:
                    return {"success": True, "message": "API key is valid"}
                else:
                    return {"success": False, "error": f"API returned status {response.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    elif request.provider == "moonshot":
        if not request.api_key:
            return {"success": False, "error": "API key required"}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.moonshot.cn/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {request.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "moonshot-v1-8k",
                        "messages": [{"role": "user", "content": "Hi, respond with 'OK' if you receive this."}],
                        "stream": False
                    }
                )
                if response.status_code == 200:
                    return {"success": True, "message": "API key is valid"}
                else:
                    return {"success": False, "error": f"API returned status {response.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    else:
        return {"success": False, "error": f"Provider {request.provider} test not implemented"}


@router.get("/storage-paths")
async def get_storage_paths():
    """Get all configured storage paths"""
    return {
        "success": True,
        "paths": runtime_config.get_storage_paths()
    }


@router.post("/storage-path")
async def set_storage_path(request: SetStoragePathRequest):
    """Set a storage path"""
    valid_types = ["local_storage", "knowledge_base", "sessions", "upload"]
    if request.path_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid path type. Must be one of: {', '.join(valid_types)}"
        )

    runtime_config.set_storage_path(request.path_type, request.path)
    save_config()

    # Ensure the directory exists
    try:
        import os
        os.makedirs(request.path, exist_ok=True)
    except Exception as e:
        return {
            "success": True,
            "warning": f"Path set but could not create directory: {str(e)}",
            "paths": runtime_config.get_storage_paths()
        }

    return {
        "success": True,
        "paths": runtime_config.get_storage_paths()
    }


@router.get("/storage-paths/status")
async def get_storage_paths_status():
    """Get status of all storage paths (exists, writable, etc.)"""
    import os

    paths = runtime_config.get_storage_paths()
    status = {}

    for path_type, path in paths.items():
        exists = os.path.exists(path)
        is_dir = os.path.isdir(path) if exists else False
        is_writable = os.access(path, os.W_OK) if exists else False

        status[path_type] = {
            "path": path,
            "exists": exists,
            "is_directory": is_dir,
            "is_writable": is_writable
        }

    return {
        "success": True,
        "status": status
    }


@router.get("/work-directory")
async def get_work_directory():
    """Get the configured work directory (backward compatibility)"""
    return {
        "success": True,
        "work_directory": runtime_config.get_work_directory()
    }


class SetWorkDirectoryRequest(BaseModel):
    path: str


@router.post("/work-directory")
async def set_work_directory(request: SetWorkDirectoryRequest):
    """Set the work directory for agent file operations (backward compatibility)"""
    import os

    work_dir = request.path.strip()

    # Validate the path exists
    if work_dir and not os.path.exists(work_dir):
        return {
            "success": False,
            "error": f"Path does not exist: {work_dir}"
        }

    # Validate it's a directory
    if work_dir and not os.path.isdir(work_dir):
        return {
            "success": False,
            "error": f"Path is not a directory: {work_dir}"
        }

    runtime_config.set_work_directory(work_dir)
    save_config()

    return {
        "success": True,
        "work_directory": work_dir
    }


@router.get("/work-directories")
async def get_working_directories():
    """Get all configured working directories - 参照 cc 的 additionalWorkingDirectories"""
    return {
        "success": True,
        "working_directories": runtime_config.get_additional_working_directories()
    }


class AddWorkingDirectoryRequest(BaseModel):
    path: str
    source: str = "userSettings"  # 来源：originalCwd, cliArg, userSettings, session, mainAgent


@router.post("/work-directories")
async def add_working_directory(request: AddWorkingDirectoryRequest):
    """Add a working directory"""
    import os

    path = request.path.strip()

    # Validate the path exists
    if not path or not os.path.exists(path):
        return {
            "success": False,
            "error": f"Path does not exist: {path}"
        }

    # Validate it's a directory
    if not os.path.isdir(path):
        return {
            "success": False,
            "error": f"Path is not a directory: {path}"
        }

    runtime_config.add_working_directory(path, request.source)
    save_config()

    return {
        "success": True,
        "working_directories": runtime_config.get_additional_working_directories()
    }


@router.delete("/work-directories/{path_encoded}")
async def remove_working_directory(path_encoded: str):
    """Remove a working directory"""
    import urllib.parse

    path = urllib.parse.unquote(path_encoded)
    success = runtime_config.remove_working_directory(path)
    save_config()

    return {
        "success": success,
        "working_directories": runtime_config.get_additional_working_directories()
    }


@router.get("/work-directory/status")
async def get_work_directory_status():
    """Get status of the work directory"""
    import os

    work_dir = runtime_config.get_work_directory()
    if not work_dir:
        return {
            "success": True,
            "status": {
                "path": "",
                "exists": False,
                "is_directory": False,
                "is_writable": False,
                "set": False
            }
        }

    exists = os.path.exists(work_dir)
    is_dir = os.path.isdir(work_dir) if exists else False
    is_writable = os.access(work_dir, os.W_OK) if exists else False

    return {
        "success": True,
        "status": {
            "path": work_dir,
            "exists": exists,
            "is_directory": is_dir,
            "is_writable": is_writable,
            "set": bool(work_dir)
        }
    }


@router.get("/tools")
async def get_available_tools():
    """Get list of available built-in tools"""
    from app.services.tools_service import tools_service
    return {
        "success": True,
        "tools": tools_service.get_available_tools()
    }


@router.post("/tools/execute")
async def execute_tool(tool_name: str, tool_args: dict):
    """Execute a built-in tool with given arguments"""
    from app.services.tools_service import tools_service
    result = await tools_service.execute_tool(tool_name, tool_args)
    return result
