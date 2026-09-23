from app.retailers.bhn import BHN
from app.retailers.models import RetailerDefinition

RETAILERS: dict[str, RetailerDefinition] = {BHN.id: BHN}


def get_retailer(retailer_id: str) -> RetailerDefinition:
    try:
        return RETAILERS[retailer_id]
    except KeyError as exc:
        available = ", ".join(sorted(RETAILERS))
        raise ValueError(f"Unknown demo retailer: {retailer_id}. Available: {available}") from exc
