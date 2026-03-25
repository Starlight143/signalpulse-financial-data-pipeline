"""Initial database schema.

Revision ID: 001
Revises:
Create Date: 2024-01-01

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "workspaces",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), unique=True, nullable=False),
        sa.Column("slug", sa.String(100), unique=True, nullable=False),
        sa.Column("is_active", sa.Boolean(), default=True, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_workspaces_slug", "workspaces", ["slug"])

    op.create_table(
        "data_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("exchange", sa.String(50), nullable=False),
        sa.Column("is_active", sa.Boolean(), default=True, nullable=False),
        sa.Column("config", sa.Text(), nullable=True),
        sa.Column("last_fetch_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_message", sa.Text(), nullable=True),
        sa.Column("fetch_count", sa.Integer(), default=0, nullable=False),
        sa.Column("error_count", sa.Integer(), default=0, nullable=False),
        sa.Column("avg_latency_seconds", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_data_sources_workspace_id", "data_sources", ["workspace_id"])

    op.create_table(
        "raw_market_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("data_source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("exchange", sa.String(50), nullable=False),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=False),
        sa.Column("ingestion_job_id", sa.String(100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["data_source_id"], ["data_sources.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_raw_market_events_workspace_id", "raw_market_events", ["workspace_id"])
    op.create_index("ix_raw_market_events_symbol", "raw_market_events", ["symbol"])
    op.create_index(
        "ix_raw_market_events_event_timestamp", "raw_market_events", ["event_timestamp"]
    )
    op.create_index(
        "ix_raw_market_events_lookup",
        "raw_market_events",
        ["workspace_id", "symbol", "event_type", "event_timestamp"],
    )

    op.create_table(
        "normalized_market_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("raw_event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("snapshot_type", sa.String(50), nullable=False),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("open_price", sa.Float(), nullable=True),
        sa.Column("high_price", sa.Float(), nullable=True),
        sa.Column("low_price", sa.Float(), nullable=True),
        sa.Column("close_price", sa.Float(), nullable=True),
        sa.Column("volume", sa.Float(), nullable=True),
        sa.Column("turnover", sa.Float(), nullable=True),
        sa.Column("funding_rate", sa.Float(), nullable=True),
        sa.Column("mark_price", sa.Float(), nullable=True),
        sa.Column("next_funding_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("exchange", sa.String(50), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_normalized_market_snapshots_symbol", "normalized_market_snapshots", ["symbol"]
    )
    op.create_index(
        "ix_normalized_market_snapshots_event_timestamp",
        "normalized_market_snapshots",
        ["event_timestamp"],
    )
    op.create_unique_constraint(
        "uq_normalized_snapshot",
        "normalized_market_snapshots",
        ["workspace_id", "symbol", "snapshot_type", "event_timestamp", "exchange"],
    )
    op.create_index(
        "ix_normalized_market_snapshots_lookup",
        "normalized_market_snapshots",
        ["workspace_id", "symbol", "snapshot_type", "event_timestamp"],
    )

    op.create_table(
        "derived_signals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("signal_type", sa.String(100), nullable=False),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("signal_metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("quality_score", sa.Float(), nullable=True),
        sa.Column("is_anomaly", sa.Boolean(), default=False, nullable=False),
        sa.Column("data_freshness_seconds", sa.Float(), nullable=True),
        sa.Column("computation_window", sa.Integer(), nullable=True),
        sa.Column("source_snapshot_ids", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_derived_signals_symbol", "derived_signals", ["symbol"])
    op.create_index("ix_derived_signals_signal_type", "derived_signals", ["signal_type"])
    op.create_index("ix_derived_signals_event_timestamp", "derived_signals", ["event_timestamp"])
    op.create_index(
        "ix_derived_signals_lookup",
        "derived_signals",
        ["workspace_id", "symbol", "signal_type", "event_timestamp"],
    )

    op.create_table(
        "stage0_decision_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_id", sa.String(100), unique=True, nullable=False),
        sa.Column("decision", sa.String(50), nullable=False),
        sa.Column("verdict", sa.String(50), nullable=False),
        sa.Column("risk_score", sa.Float(), nullable=True),
        sa.Column("high_risk", sa.Boolean(), default=False, nullable=False),
        sa.Column("issues", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("clarifying_questions", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("guardrails", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("policy_version", sa.String(100), nullable=True),
        sa.Column("goal", sa.Text(), nullable=False),
        sa.Column("tools", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("side_effects", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("constraints", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("context", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("raw_response", postgresql.JSONB(), nullable=False),
        sa.Column("action_type", sa.String(100), nullable=True),
        sa.Column("action_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("was_executed", sa.Boolean(), default=False, nullable=False),
        sa.Column("execution_result", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_stage0_decision_logs_request_id", "stage0_decision_logs", ["request_id"])
    op.create_index("ix_stage0_decision_logs_verdict", "stage0_decision_logs", ["verdict"])
    op.create_index(
        "ix_stage0_decision_logs_lookup",
        "stage0_decision_logs",
        ["workspace_id", "verdict", "created_at"],
    )

    op.create_table(
        "execution_intents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("idempotency_key", sa.String(100), unique=True, nullable=False),
        sa.Column("intent_type", sa.String(100), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("stage0_decision_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("stage0_request_id", sa.String(100), nullable=True),
        sa.Column("stage0_verdict", sa.String(50), nullable=True),
        sa.Column("risk_score", sa.Float(), nullable=True),
        sa.Column("actor_role", sa.String(100), nullable=True),
        sa.Column("approval_status", sa.String(50), nullable=True),
        sa.Column("approved_by", sa.String(255), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("execution_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("execution_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("execution_result", postgresql.JSONB(), nullable=True),
        sa.Column("execution_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_execution_intents_idempotency_key", "execution_intents", ["idempotency_key"]
    )
    op.create_index("ix_execution_intents_intent_type", "execution_intents", ["intent_type"])
    op.create_index("ix_execution_intents_status", "execution_intents", ["status"])
    op.create_index(
        "ix_execution_intents_lookup",
        "execution_intents",
        ["workspace_id", "intent_type", "status", "created_at"],
    )

    op.create_table(
        "alert_deliveries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("idempotency_key", sa.String(100), unique=True, nullable=False),
        sa.Column("alert_type", sa.String(100), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("destination", sa.String(255), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("stage0_decision_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("stage0_request_id", sa.String(100), nullable=True),
        sa.Column("stage0_verdict", sa.String(50), nullable=True),
        sa.Column("delivery_attempts", sa.Integer(), default=0, nullable=False),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("response_data", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_alert_deliveries_idempotency_key", "alert_deliveries", ["idempotency_key"])
    op.create_index("ix_alert_deliveries_alert_type", "alert_deliveries", ["alert_type"])
    op.create_index("ix_alert_deliveries_status", "alert_deliveries", ["status"])
    op.create_index(
        "ix_alert_deliveries_lookup",
        "alert_deliveries",
        ["workspace_id", "alert_type", "status", "created_at"],
    )

    op.create_table(
        "idempotency_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("key", sa.String(100), nullable=False),
        sa.Column("action_type", sa.String(100), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="processing"),
        sa.Column("request_payload", postgresql.JSONB(), nullable=False),
        sa.Column("response_payload", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_idempotency_keys_key", "idempotency_keys", ["key"])
    op.create_index("ix_idempotency_keys_status", "idempotency_keys", ["status"])
    op.create_index("ix_idempotency_keys_expires_at", "idempotency_keys", ["expires_at"])
    op.create_index(
        "uq_idempotency_keys_workspace_key",
        "idempotency_keys",
        ["workspace_id", "key"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("idempotency_keys")
    op.drop_table("alert_deliveries")
    op.drop_table("execution_intents")
    op.drop_table("stage0_decision_logs")
    op.drop_table("derived_signals")
    op.drop_table("normalized_market_snapshots")
    op.drop_table("raw_market_events")
    op.drop_table("data_sources")
    op.drop_table("workspaces")
