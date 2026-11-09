from fastapi import APIRouter, Depends, HTTPException

from app import ledger
from app.deps import get_store
from app.models import Charge, Refund
from app.schemas import RefundOut, RefundSummaryOut
from app.store import Store

router = APIRouter()


def plan_full_refund(charge: Charge, refunds: list[Refund]) -> int:
    if refunds:
        raise HTTPException(409, "Charge has already been refunded")
    return charge.amount_cents


@router.post("/charges/{charge_id}/refund", response_model=RefundOut, status_code=201)
def refund_charge_in_full(charge_id: str, store: Store = Depends(get_store)) -> Refund:
    """Refund the entire charge. A charge can only be refunded in full once."""
    charge = store.get_charge(charge_id)
    if charge is None:
        raise HTTPException(404, "Charge not found")
    return ledger.record_refund(store, charge_id, plan_full_refund, reason="full refund")


@router.get("/charges/{charge_id}/refunds", response_model=list[RefundOut])
def list_refunds(charge_id: str, store: Store = Depends(get_store)) -> list[Refund]:
    if store.get_charge(charge_id) is None:
        raise HTTPException(404, "Charge not found")
    return store.list_refunds(charge_id)


@router.get("/charges/{charge_id}/refund-summary", response_model=RefundSummaryOut)
def refund_summary(charge_id: str, store: Store = Depends(get_store)) -> RefundSummaryOut:
    """How much of a charge has been refunded, and how much is left."""
    charge = store.get_charge(charge_id)
    if charge is None:
        raise HTTPException(404, "Charge not found")
    count, refunded = store.refund_totals(charge_id)
    return RefundSummaryOut(
        charge_id=charge_id,
        refund_count=count,
        refunded_cents=refunded,
        remaining_cents=charge.amount_cents - refunded,
    )
