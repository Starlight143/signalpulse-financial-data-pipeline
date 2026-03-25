"""Fix idempotency key uniqueness to be scoped per workspace.

The initial schema defined idempotency_key as globally unique on
alert_deliveries and execution_intents, which prevents two different
workspaces from reusing the same key — a cross-workspace collision bug.
The correct uniqueness scope is (workspace_id, idempotency_key).

Revision ID: 002
Revises: 001_initial
Create Date: 2026-03-25

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_fix_idempotency_key_uniqueness"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- alert_deliveries ---
    # Drop the old global unique constraint on idempotency_key alone.
    op.drop_index("ix_alert_deliveries_idempotency_key", table_name="alert_deliveries")
    op.drop_constraint("alert_deliveries_idempotency_key_key", "alert_deliveries", type_="unique")

    # Add the correct composite unique constraint (workspace_id, idempotency_key).
    op.create_unique_constraint(
        "uq_alert_deliveries_workspace_key",
        "alert_deliveries",
        ["workspace_id", "idempotency_key"],
    )
    # Restore a plain index on idempotency_key for fast single-column lookups.
    op.create_index("ix_alert_deliveries_idempotency_key", "alert_deliveries", ["idempotency_key"])

    # --- execution_intents ---
    op.drop_index("ix_execution_intents_idempotency_key", table_name="execution_intents")
    op.drop_constraint(
        "execution_intents_idempotency_key_key", "execution_intents", type_="unique"
    )

    op.create_unique_constraint(
        "uq_execution_intents_workspace_key",
        "execution_intents",
        ["workspace_id", "idempotency_key"],
    )
    op.create_index(
        "ix_execution_intents_idempotency_key", "execution_intents", ["idempotency_key"]
    )


def downgrade() -> None:
    # --- execution_intents ---
    op.drop_index("ix_execution_intents_idempotency_key", table_name="execution_intents")
    op.drop_constraint("uq_execution_intents_workspace_key", "execution_intents", type_="unique")

    op.create_index(
        "ix_execution_intents_idempotency_key", "execution_intents", ["idempotency_key"]
    )
    op.create_unique_constraint(
        "execution_intents_idempotency_key_key",
        "execution_intents",
        ["idempotency_key"],
    )

    # --- alert_deliveries ---
    op.drop_index("ix_alert_deliveries_idempotency_key", table_name="alert_deliveries")
    op.drop_constraint("uq_alert_deliveries_workspace_key", "alert_deliveries", type_="unique")

    op.create_index(
        "ix_alert_deliveries_idempotency_key", "alert_deliveries", ["idempotency_key"]
    )
    op.create_unique_constraint(
        "alert_deliveries_idempotency_key_key",
        "alert_deliveries",
        ["idempotency_key"],
    )
