# SignalPulse Financial Data Pipeline

A production-ready financial data pipeline demonstrating **SignalPulse Stage0 runtime authorization** for multi-source market data ingestion, feature engineering, and risk-gated action execution.

> **This repository is a SignalPulse Stage0 use case implementation.** It demonstrates how to integrate Stage0 as a runtime authorization checkpoint for financial workflows. Stage0 is NOT an executor - it's an authorization layer. Final enforcement always happens server-side in this pipeline.

## Overview

### What This Pipeline Does

1. **Multi-source Data Ingestion**: Fetches funding rates and OHLCV data from Binance and Bybit
2. **Normalization**: Converts raw exchange data to a unified schema
3. **Feature Engineering**: Calculates derived signals (funding diff, z-scores, volatility, quality scores)
4. **Runtime Authorization**: All side effects go through Stage0 for risk evaluation
5. **Audit Trail**: Complete logging of all Stage0 decisions

### Stage0 Integration Contract

This pipeline strictly follows the SignalPulse Stage0 integration contract:

| Requirement | Implementation |
|------------|----------------|
| Endpoint | `POST /check` at `STAGE0_BASE_URL` |
| Auth Header | `x-api-key: YOUR_API_KEY` |
| Verdict-Based Logic | Only `verdict == "ALLOW"` permits execution |
| DEFER Handling | Returns structured response requesting more context |
| Fail-Closed | 5xx, timeout, unknown verdict, missing fields = blocked |
| Retry Boundary | Only before side effects begin |
| Idempotency | All side effects use idempotency keys |
| Audit Logging | All request_id, policy_version, verdict, issues persisted |

## Quick Start

### Prerequisites

- Python 3.12+
- Docker and Docker Compose
- (Optional) SignalPulse Stage0 API key from [signalpulse.org/dashboard](https://signalpulse.org/dashboard)

### 1. Clone and Configure

```bash
git clone <repo-url>
cd signalpulse-financial-data-pipeline
cp .env.example .env
# Edit .env with your settings
```

### 2. Start with Docker Compose

```bash
make quickstart
# Or manually:
docker compose up -d --wait
make migrate
make seed
```

### 3. Verify

```bash
curl http://localhost:8000/health
# {"status":"healthy","app_name":"signalpulse-financial-data-pipeline",...}
```

### 4. Explore API Docs

Open [http://localhost:8000/docs](http://localhost:8000/docs) for interactive API documentation.

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `STAGE0_BASE_URL` | SignalPulse API endpoint | `https://api.signalpulse.org` |
| `STAGE0_API_KEY` | Your Stage0 API key | (empty = mock mode) |
| `STAGE0_MOCK_MODE` | Force mock mode | `false` |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://...` |
| `SUPPORTED_SYMBOLS` | Allowed trading pairs | `BTCUSDT,ETHUSDT,SOLUSDT,...` |
| `INTERNAL_API_KEY` | Key for protected endpoints | (generate secure key) |

### Mock vs Live Mode

- **No `STAGE0_API_KEY`**: Automatic mock mode with deterministic responses
- **`STAGE0_API_KEY` set**: Live mode connecting to SignalPulse
- **`STAGE0_MOCK_MODE=true`**: Force mock even with API key (useful for testing)

## API Endpoints

### Health & Readiness

```bash
# Basic health check
curl http://localhost:8000/health

# Readiness with dependency status
curl http://localhost:8000/ready

# Data source health
curl http://localhost:8000/sources/health
```

### Market Data (Read-Only)

```bash
# Get OHLCV/funding snapshots
curl "http://localhost:8000/market/BTCUSDT/snapshot?hours=24"

# Get computed features
curl http://localhost:8000/market/BTCUSDT/features

# Get derived signals
curl http://localhost:8000/market/BTCUSDT/signals
```

### Actions (Require Stage0 Authorization)

```bash
# Dispatch alert - requires X-Internal-Key header
curl -X POST http://localhost:8000/actions/dispatch-alert \
  -H "Content-Type: application/json" \
  -H "X-Internal-Key: your-internal-key" \
  -d '{
    "idempotency_key": "alert-001",
    "alert_type": "price_threshold",
    "symbol": "BTCUSDT",
    "destination": "https://webhook.example.com/alerts",
    "payload": {"message": "BTC crossed $50000"},
    "context": {
      "actor_role": "system",
      "approval_status": "approved",
      "approved_by": "admin@example.com"
    }
  }'

# Create execution intent
curl -X POST http://localhost:8000/actions/create-execution-intent \
  -H "Content-Type: application/json" \
  -H "X-Internal-Key: your-internal-key" \
  -d '{
    "idempotency_key": "intent-001",
    "intent_type": "trade_signal",
    "symbol": "ETHUSDT",
    "payload": {"action": "monitor", "threshold": 2500},
    "actor_role": "trader",
    "approval_status": "approved",
    "approved_by": "manager@example.com",
    "environment": "staging"
  }'
```

### Stage0 Decision Logs

```bash
# Get specific decision by request_id
curl http://localhost:8000/stage0/decisions/req_abc123

# List recent decisions
curl "http://localhost:8000/stage0/decisions?verdict=ALLOW&hours=24"
```

### Manual Ingestion Trigger

```bash
curl -X POST http://localhost:8000/ingest/run \
  -H "X-Internal-Key: your-internal-key"
```

## Curl Examples: All Verdict Scenarios

### 1. Safe Read-Only Query (No Stage0 Required)

```bash
curl http://localhost:8000/market/BTCUSDT/features

# Response: Features data without authorization required
# Read-only endpoints don't need Stage0 check
```

### 2. DEFER - Missing Approval Context

```bash
curl -X POST http://localhost:8000/actions/create-execution-intent \
  -H "Content-Type: application/json" \
  -H "X-Internal-Key: test-internal-key" \
  -d '{
    "idempotency_key": "defer-example-1",
    "intent_type": "trade_execution",
    "symbol": "BTCUSDT",
    "payload": {"side": "buy", "amount": 1.0}
  }'

# Response (mock mode):
# {
#   "id": "...",
#   "status": "deferred",
#   "stage0_verdict": "DEFER",
#   "rejection_reason": "[{\"code\": \"APPROVAL_REQUIRED\"}, ...]"
# }
```

### 3. DENY - High Risk Without Proper Authorization

```bash
curl -X POST http://localhost:8000/actions/dispatch-alert \
  -H "Content-Type: application/json" \
  -H "X-Internal-Key: test-internal-key" \
  -d '{
    "idempotency_key": "deny-example-1",
    "alert_type": "trade_execution",
    "destination": "https://exchange.example.com/api/trade",
    "payload": {"action": "market_buy", "amount": 100000}
  }'

# Response (mock mode with default settings):
# {
#   "success": false,
#   "status": "denied",
#   "stage0_verdict": "DENY",
#   "message": "Stage0 denied alert dispatch: [...]"
# }
```

### 4. ALLOW - Complete Approval Context

```bash
curl -X POST http://localhost:8000/actions/create-execution-intent \
  -H "Content-Type: application/json" \
  -H "X-Internal-Key: test-internal-key" \
  -d '{
    "idempotency_key": "allow-example-1",
    "intent_type": "position_update",
    "symbol": "BTCUSDT",
    "payload": {"action": "update_stop_loss", "price": 45000},
    "actor_role": "trader",
    "approval_status": "approved",
    "approved_by": "risk-manager@example.com",
    "approval_reason": "Within daily risk limits",
    "environment": "staging"
  }'

# Response:
# {
#   "id": "...",
#   "status": "authorized",
#   "stage0_verdict": "ALLOW",
#   "stage0_request_id": "req_mock_...",
#   "risk_score": 15.0
# }
```

## Data Models

### Core Tables

| Table | Purpose |
|-------|---------|
| `workspaces` | Multi-tenant isolation |
| `data_sources` | Exchange connection tracking |
| `raw_market_events` | Original exchange data |
| `normalized_market_snapshots` | Unified data schema |
| `derived_signals` | Feature engineering results |
| `stage0_decision_logs` | Audit trail of all authorizations |
| `execution_intents` | High-risk action records |
| `alert_deliveries` | Notification tracking |
| `idempotency_keys` | Deduplication |

### Multi-Tenancy

The `workspace_id` column provides tenant isolation. All endpoints use the default workspace (`00000000-0000-0000-0000-000000000001`).

## Fail-Closed Design

This pipeline implements **fail-closed** semantics for all side effects:

| Failure Mode | Behavior |
|--------------|----------|
| No API key | Blocked (mock mode for testing) |
| Invalid API key | Blocked |
| Stage0 unreachable | Blocked |
| 5xx response | Blocked |
| Timeout | Blocked |
| Missing `verdict` field | Blocked |
| Unknown `verdict` value | Blocked |
| `verdict == "DENY"` | Blocked |
| `verdict == "DEFER"` | Blocked (await context) |
| `verdict == "ALLOW"` | Proceed (after own checks) |

### Retry Boundary

Retries only happen **before** side effects begin:

```
1. Call Stage0 /check
2. If ALLOW, start side effect
3. If side effect fails → NO RETRY of /check
   (side effect may have partially completed)
```

### Idempotency

All side-effect endpoints require `idempotency_key`:

- Duplicate requests with same key return cached result
- Keys expire after 24 hours (configurable)
- Prevents double-execution on retries

## Development

### Run Tests

```bash
# All tests
make test

# Unit tests only
make test-unit

# Integration tests
make test-integration

# Fail-closed tests
make test-fail-closed

# With coverage
make coverage
```

### Code Quality

```bash
make lint      # Run ruff linter
make format    # Format with ruff
make typecheck # Run mypy
```

### Local Development

```bash
# Install dev dependencies
make dev

# Run with auto-reload
make dev-server

# Database migrations
make migrate
make migrate-create  # Create new migration
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI Application                      │
├─────────────────────────────────────────────────────────────┤
│  Health API    │  Market API    │  Actions API  │ Ingest API│
│  (read-only)   │  (read-only)   │  (protected)  │(protected)│
└────────┬───────┴───────┬────────┴───────┬───────┴─────┬─────┘
         │               │                │             │
         ▼               ▼                ▼             ▼
┌─────────────────────────────────────────────────────────────┐
│                     Service Layer                            │
│  MarketService │ ActionService │ IdempotencyService         │
└─────────────────────────────────────────────────────────────┘
         │                              │
         ▼                              ▼
┌─────────────────────┐    ┌─────────────────────────────────┐
│    PostgreSQL DB    │    │      Stage0 Adapter             │
│  (normalized data)  │    │  ┌───────────┐ ┌──────────────┐ │
└─────────────────────┘    │  │ Mock Mode │ │  Live Mode   │ │
                           │  └───────────┘ └──────────────┘ │
                           └─────────────────────────────────┘
                                        │
                                        ▼
                           ┌─────────────────────────────────┐
                           │     SignalPulse Stage0 API      │
                           │     https://api.signalpulse.org │
                           └─────────────────────────────────┘
```

## SignalPulse Stage0 Integration Details

### Request Schema (Sent to /check)

```json
{
  "goal": "Description of intended action",
  "tools": ["tool1", "tool2"],
  "side_effects": ["effect1", "effect2"],
  "constraints": ["constraint1"],
  "context": {
    "run_id": "run_abc123",
    "current_iteration": 1,
    "elapsed_seconds": 42.5,
    "current_tool": "action_name",
    "recent_tools": ["previous_action"],
    "cumulative_cost_usd": 0.05,
    "actor_role": "trader",
    "approval_status": "approved",
    "approved_by": "manager@example.com",
    "approved_at": "2024-01-15T10:30:00Z",
    "approval_reason": "Within risk limits",
    "environment": "staging"
  }
}
```

### Response Fields (Persisted)

| Field | Description |
|-------|-------------|
| `request_id` | Unique ID for tracing |
| `decision` | GO / NO_GO / DEFER / ERROR |
| `verdict` | ALLOW / DENY / DEFER |
| `risk_score` | 0-100 risk assessment |
| `issues` | List of problem codes |
| `policy_version` | Version of policy applied |
| `clarifying_questions` | Questions for DEFER cases |

### Common Issue Codes

- `APPROVAL_REQUIRED` - Human approval needed
- `ROLE_NOT_AUTHORIZED` - Insufficient role
- `RISK_SCORE_TOO_HIGH` - Exceeds threshold
- `CONTEXT_REQUIRED` - Missing context fields
- `DESTRUCTIVE_ACTION_REQUIRES_APPROVAL` - Dangerous action

## Security Considerations

1. **API Keys**: Never expose `STAGE0_API_KEY` or `INTERNAL_API_KEY` to client-side code
2. **Server-Side Enforcement**: All business rules (symbol allowlist, workspace existence) are enforced server-side
3. **Audit Trail**: Every Stage0 decision is persisted with full context
4. **Fail-Closed**: System blocks on uncertainty, never defaults to allow
5. **Idempotency**: Prevents replay attacks and duplicate execution

## License

MIT License

## Related Projects

- [SignalPulse Stage0](https://signalpulse.org) - Runtime authorization platform
- [stage0-execution-guard-skill](https://github.com/Starlight143/stage0-execution-guard-skill) - Python SDK
- [stage0-agent-runtime-guard](https://github.com/Starlight143/stage0-agent-runtime-guard) - Agent runtime integration