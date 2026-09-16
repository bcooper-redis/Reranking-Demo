from fastapi import APIRouter, HTTPException, Request, status

from app.models import (
    ClickEventRequest,
    EvaluationRequest,
    EvaluationRun,
    EventReceipt,
    LoadTestRequest,
    LoadTestRun,
    TelemetrySnapshot,
)
from app.reranking import RerankerError

router = APIRouter()


@router.post("/api/v1/events/click", response_model=EventReceipt, tags=["events"])
async def record_click(request: Request, payload: ClickEventRequest) -> EventReceipt:
    event_id = await request.app.state.telemetry.record_click(payload)
    return EventReceipt(event_id=event_id)


@router.get("/api/v1/telemetry", response_model=TelemetrySnapshot, tags=["telemetry"])
async def telemetry_snapshot(request: Request) -> TelemetrySnapshot:
    return request.app.state.telemetry.snapshot()


@router.post("/api/v1/evaluations/run", response_model=EvaluationRun, tags=["evaluations"])
async def run_evaluation(
    request: Request, payload: EvaluationRequest | None = None
) -> EvaluationRun:
    try:
        return await request.app.state.evaluation.run(
            payload.reranker_id if payload else "minilm_l6"
        )
    except RerankerError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.code
        ) from exc


@router.post("/api/v1/evaluations/load", response_model=LoadTestRun, tags=["evaluations"])
async def run_load_test(request: Request, payload: LoadTestRequest) -> LoadTestRun:
    try:
        return await request.app.state.evaluation.run_load(
            payload.reranker_id, payload.concurrency, payload.rounds
        )
    except RerankerError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.code
        ) from exc


@router.get(
    "/api/v1/evaluations/{evaluation_id}",
    response_model=EvaluationRun,
    tags=["evaluations"],
)
async def get_evaluation(request: Request, evaluation_id: str) -> EvaluationRun:
    evaluation = await request.app.state.evaluation.get(evaluation_id)
    if evaluation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown evaluation: {evaluation_id}",
        )
    return evaluation
