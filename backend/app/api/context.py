from fastapi import HTTPException, Request, status

RETAILER_HEADER = "X-Demo-Retailer"


def retailer_id(request: Request) -> str:
    selected = request.headers.get(RETAILER_HEADER, request.app.state.settings.retailer_id)
    if selected not in request.app.state.catalogs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown demo retailer: {selected}",
        )
    return selected


def catalog(request: Request):  # type: ignore[no-untyped-def]
    return request.app.state.catalogs[retailer_id(request)]


def evaluation(request: Request):  # type: ignore[no-untyped-def]
    return request.app.state.evaluations[retailer_id(request)]


def telemetry(request: Request):  # type: ignore[no-untyped-def]
    return request.app.state.telemetries[retailer_id(request)]
