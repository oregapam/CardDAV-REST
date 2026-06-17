from fastapi import APIRouter, Request

from app.models import ConfigResponse

router = APIRouter(prefix="/api", tags=["config"])


@router.get("/config", response_model=ConfigResponse)
async def get_config(request: Request) -> ConfigResponse:
    return ConfigResponse(
        name_format=request.app.state.name_format,
        default_region=request.app.state.default_region,
        required_fields=list(request.app.state.required_fields),
    )
