from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import GateKey
from app.common.schemas import ApiResponse, GateReview
from app.common.errors import ErrorCode
from app.core.exceptions import AppException
from app.modules.gates.service import review_gate
from app.modules.systems import repository as systems_repo
from app.persistence import get_db_session

router = APIRouter(tags=["gates"])


@router.post(
    "/systems/{system_id}/gates/{gate_key}/review",
    response_model=ApiResponse[GateReview],
)
async def review_gate_endpoint(
    system_id: str,
    gate_key: GateKey,
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[GateReview]:
    system = await systems_repo.get_system_by_id(session, system_id)
    if system is None:
        raise AppException(
            code=ErrorCode.NOT_FOUND.value,
            message="System not found",
            status_code=404,
            details={"system_id": system_id},
        )

    gate_review = await session.run_sync(
        lambda sync_session: review_gate(sync_session, system, gate_key)
    )
    return ApiResponse(data=gate_review)
