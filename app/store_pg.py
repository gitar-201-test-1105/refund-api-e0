import psycopg
from psycopg.rows import class_row

from app.models import Charge, Refund
from app.store import RefundPlan


class PostgresStore:
    """Postgres-backed storage. Run scripts/migrate.py first to create the tables."""

    def __init__(self, url: str) -> None:
        self._url = url

    def add_charge(self, charge: Charge) -> None:
        with psycopg.connect(self._url) as conn:
            conn.execute(
                "INSERT INTO charges (id, amount_cents, currency, description, created_at)"
                " VALUES (%s, %s, %s, %s, %s)",
                (
                    charge.id,
                    charge.amount_cents,
                    charge.currency,
                    charge.description,
                    charge.created_at,
                ),
            )

    def get_charge(self, charge_id: str) -> Charge | None:
        with psycopg.connect(self._url, row_factory=class_row(Charge)) as conn:
            return conn.execute(
                "SELECT id, amount_cents, currency, description, created_at"
                " FROM charges WHERE id = %s",
                (charge_id,),
            ).fetchone()

    def record_refund(self, charge_id: str, refund_id: str, plan: RefundPlan, reason: str | None = None) -> Refund:
        # One transaction: the row lock on the charge serializes concurrent refunds.
        with psycopg.connect(self._url) as conn:
            charge_row = conn.cursor(row_factory=class_row(Charge)).execute(
                "SELECT id, amount_cents, currency, description, created_at"
                " FROM charges WHERE id = %s FOR UPDATE",
                (charge_id,),
            ).fetchone()
            if charge_row is None:
                raise KeyError(charge_id)
            existing = conn.cursor(row_factory=class_row(Refund)).execute(
                "SELECT id, charge_id, amount_cents, reason, created_at"
                " FROM refunds WHERE charge_id = %s ORDER BY created_at, id",
                (charge_id,),
            ).fetchall()
            refund = Refund(
                id=refund_id,
                charge_id=charge_id,
                amount_cents=plan(charge_row, existing),
                reason=reason,
            )
            conn.execute(
                "INSERT INTO refunds (id, charge_id, amount_cents, reason, created_at)"
                " VALUES (%s, %s, %s, %s, %s)",
                (refund.id, refund.charge_id, refund.amount_cents, refund.reason, refund.created_at),
            )
            return refund

    def list_refunds(self, charge_id: str) -> list[Refund]:
        with psycopg.connect(self._url, row_factory=class_row(Refund)) as conn:
            return conn.execute(
                "SELECT id, charge_id, amount_cents, reason, created_at"
                " FROM refunds WHERE charge_id = %s ORDER BY created_at, id",
                (charge_id,),
            ).fetchall()

    def refund_totals(self, charge_id: str) -> tuple[int, int]:
        with psycopg.connect(self._url) as conn:
            count, refunded = conn.execute(
                "SELECT COUNT(*), COALESCE(SUM(amount_cents), 0) FROM refunds WHERE charge_id = %s",
                (charge_id,),
            ).fetchone()
            return count, refunded
