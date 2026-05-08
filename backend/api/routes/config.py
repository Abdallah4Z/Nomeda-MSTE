from fastapi import APIRouter, Depends
from ...core.container import Container
from ..deps import get_container

router = APIRouter(prefix="/api", tags=["config"])


@router.get("/config")
async def get_config(container: Container = Depends(get_container)):
    rc = container.runtime_config
    return rc.all()


@router.get("/config/{key}")
async def get_config_key(key: str, container: Container = Depends(get_container)):
    rc = container.runtime_config
    val = rc.get(key)
    if val is None:
        return {"error": f"Unknown config key: {key}"}
    return {key: val}


@router.put("/config")
async def update_config(body: dict, container: Container = Depends(get_container)):
    rc = container.runtime_config
    results = rc.set_many(body)
    failed = [k for k, v in results.items() if not v]
    return {"updated": [k for k, v in results.items() if v], "failed": failed}
