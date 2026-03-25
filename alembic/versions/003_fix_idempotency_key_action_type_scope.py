"""Scope idempotency_keys unique constraint to (workspace_id, key, action_type).

The previous unique index on (workspace_id, key) prevented using the same key
string for different action_types (e.g., 'alert_dispatch' vs 'execution_intent')
within the same workspace, causing spurious IntegrityErrors even though those
are semantically independent operations. The correct scope is the triple
(workspace_id, key, action_type).

Revision ID: 003
Revises: 002_fix_idempotency_key_uniqueness
Create Date: 2026-03-25

"""

from typing import Sequence, Union

from alembic import op

revision: str = "003_fix_idempotency_key_action_type_scope"
down_revision: Union[str, None] = "002_fix_idempotency_key_uniqueness"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the old (workspace_id, key) unique index.
    op.drop_index("uq_idempotency_keys_workspace_key", table_name="idempotency_keys")

    # Create the correct (workspace_id, key, action_type) unique index.
    op.create_index(
        "uq_idempotency_keys_workspace_key_action",
        "idempotency_keys",
        ["workspace_id", "key", "action_type"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_idempotency_keys_workspace_key_action", table_name="idempotency_keys")

    op.create_index(
        "uq_idempotency_keys_workspace_key",
        "idempotency_keys",
        ["workspace_id", "key"],
        unique=True,
    )
