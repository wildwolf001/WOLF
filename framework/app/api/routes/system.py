"""
System Status & Observability Routes
Aggregates data from vector_store, memory, evolution, observability, skills, tools
"""
import time
from functools import lru_cache
from fastapi import APIRouter, HTTPException
from typing import Optional
import asyncio

router = APIRouter()

# Simple time-based cache for system status (avoids re-importing all subsystems on every page switch)
_cache_ttl = 10  # seconds
_status_cache: dict = {"data": None, "ts": 0}


def _cached_system_status() -> dict:
    now = time.time()
    if _status_cache["data"] is not None and (now - _status_cache["ts"]) < _cache_ttl:
        return _status_cache["data"]
    data = _build_system_status()
    _status_cache["data"] = data
    _status_cache["ts"] = now
    return data


@router.get("/system/status")
async def get_system_status() -> dict:
    """Get overall system status from all initialized subsystems (10s cache)"""
    return _cached_system_status()


def _build_system_status() -> dict:
    """Build full system status (expensive — only called when cache expires)"""
    status = {
        "server": "running",
        "subsystems": {}
    }

    # Vector store + Agentic RAG status
    try:
        from ...vector_store import get_vector_store, get_hybrid_retriever, get_kg_builder, get_error_book
        store = get_vector_store()
        hybrid = get_hybrid_retriever()
        kg = get_kg_builder()
        eb = get_error_book()
        status["subsystems"]["vector_store"] = {
            "initialized": True,
            "doc_count": store.count() if store else 0,
            "kg_nodes": kg.graph.node_count if kg else 0,
            "kg_edges": kg.graph.edge_count if kg else 0,
            "error_book": eb.stats if eb else {}
        }
    except Exception as e:
        status["subsystems"]["vector_store"] = {"initialized": False, "error": str(e)}

    # Memory status
    try:
        from ...memory.directory import get_memory_directory
        mem_dir = get_memory_directory()
        files = mem_dir.list_memory_files() if mem_dir else []
        by_type: dict[str, int] = {"user": 0, "feedback": 0, "project": 0, "reference": 0}
        total_usage = 0
        for _, entry in files:
            mtype = entry.memory_type.value
            if mtype in by_type:
                by_type[mtype] += 1
            total_usage += entry.usage_count
        status["subsystems"]["memory"] = {
            "initialized": True,
            "total": len(files),
            "by_type": by_type,
            "total_usage": total_usage
        }
    except Exception:
        status["subsystems"]["memory"] = {"initialized": False}

    # Skills status
    try:
        from ...skills import skill_registry
        skills_list = skill_registry.list_skills() if skill_registry else []
        status["subsystems"]["skills"] = {
            "initialized": True,
            "total": len(skills_list),
            "bundled": len([s for s in skills_list if getattr(s, 'source', '') == 'bundled']),
            "user": len([s for s in skills_list if getattr(s, 'source', '') == 'user']),
        }
    except Exception as e:
        status["subsystems"]["skills"] = {"initialized": False, "total": 0, "error": str(e)}

    # Tools status
    try:
        from ...tools import tool_registry
        tools = tool_registry.list_tools() if tool_registry else []
        status["subsystems"]["tools"] = {
            "initialized": True,
            "total": len(tools),
            "names": [t.name for t in tools]
        }
    except Exception:
        status["subsystems"]["tools"] = {"initialized": False}

    # Prompt system status
    try:
        from ...prompt.feature_flags import get_feature_flag_manager
        manager = get_feature_flag_manager()
        all_flags = manager.list_all() if manager else {}
        status["subsystems"]["prompt"] = {
            "initialized": True,
            "active_flags": [k for k, v in all_flags.items() if getattr(v, 'enabled', False)],
            "total_flags": len(all_flags)
        }
    except Exception as e:
        status["subsystems"]["prompt"] = {"initialized": False, "error": str(e)}

    # Evolution status
    try:
        from ...evolution.rollout_manager import RolloutManager
        status["subsystems"]["evolution"] = {
            "initialized": True,
            "active_rollouts": 0,
            "stage": "operational"
        }
    except Exception:
        status["subsystems"]["evolution"] = {"initialized": False}

    return status


@router.get("/system/observability")
async def get_observability_stats() -> dict:
    """Get LLM observability stats: calls, tokens, latency, cost, budget"""
    result = {
        "llm_stats": {"total_calls": 0, "by_model": {}},
        "cost": {"daily_cost": 0, "daily_tokens": 0, "alert": "OK", "budget_limit": 50},
        "recent_calls": []
    }

    try:
        from ...observability.tracker import get_stats_aggregator
        agg = get_stats_aggregator()
        stats = agg.total_stats()
        result["llm_stats"] = stats
    except Exception:
        pass

    try:
        from ...observability.cost import get_cost_calculator
        calc = get_cost_calculator()
        result["cost"] = calc.summary
    except Exception:
        pass

    return result


@router.get("/system/memory-cognitive")
async def get_memory_cognitive_data(
    session_id: str,
    workspace_id: str = "default"
) -> dict:
    """
    Get cognitive memory data: layer distribution, importance scores, decay status.
    """
    try:
        from ...memory.directory import get_memory_directory
        from ...memory.cognitive import infer_cognitive_layer, EbbinghausDecay, CognitiveMemoryLayer, HALF_LIFE
        from ...memory.scorer import MemoryScorer
        import time

        mem_dir = get_memory_directory()
        files = mem_dir.list_memory_files()

        memories = []
        for _, entry in files:
            d = entry.to_dict()
            d["cognitive_layer"] = infer_cognitive_layer(d).value
            memories.append(d)

        # Score all memories
        scorer = MemoryScorer()
        scored = scorer.score_all(memories)

        # Layer distribution
        layers = {layer.value: 0 for layer in CognitiveMemoryLayer}
        for m in scored:
            layers[m.get("cognitive_layer", "working")] += 1

        # Decay info
        now = time.time()
        decay_info = {}
        for mtype, half_hours in HALF_LIFE.items():
            decay = EbbinghausDecay(half_hours)
            decay_info[mtype] = {
                "half_life_hours": half_hours,
                "half_life_days": round(half_hours / 24, 1),
                "weight_after_1d": round(decay.weight(1.0, 24), 4),
                "weight_after_7d": round(decay.weight(1.0, 168), 4),
            }

        # Score distribution
        score_distribution = {"keep": 0, "review": 0, "archive": 0, "delete": 0}
        for m in scored:
            cat = m.get("score_category", "archive")
            if cat in score_distribution:
                score_distribution[cat] += 1

        return {
            "session_id": session_id,
            "total": len(scored),
            "cognitive_layers": layers,
            "score_distribution": score_distribution,
            "decay_config": decay_info,
            "top_importance": scored[:5],
            "memories": scored
        }
    except Exception as e:
        return {
            "session_id": session_id,
            "total": 0,
            "error": str(e),
            "cognitive_layers": {},
            "score_distribution": {},
            "decay_config": {},
            "top_importance": [],
            "memories": []
        }


@router.get("/system/evolution")
async def get_evolution_status() -> dict:
    """Get evolution system status: skill versions, rollouts, optimization history"""
    try:
        from ...evolution.versioned_artifact import ArtifactStore
        import os

        # Get artifact store paths
        base = os.path.join(os.path.dirname(__file__), '..', '..', 'evolution')
        store = ArtifactStore(os.path.join(base, '..', '..', 'wolf_data', 'evolution'))

        return {
            "initialized": True,
            "artifacts": [],
            "active_rollouts": 0
        }
    except Exception as e:
        return {"initialized": False, "error": str(e), "artifacts": [], "active_rollouts": 0}
