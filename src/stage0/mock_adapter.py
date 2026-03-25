"""Mock Stage0 adapter for testing and local development."""

import asyncio
import hashlib
import secrets
import time

from src.schemas.stage0 import (
    Stage0Issue,
    Stage0Meta,
    Stage0Request,
    Stage0Response,
)
from src.stage0.adapter import Stage0Adapter


class MockStage0Adapter(Stage0Adapter):
    def __init__(
        self,
        default_verdict: str = "ALLOW",
        risk_threshold: float = 50.0,
    ):
        self.default_verdict = default_verdict
        self.risk_threshold = risk_threshold

    def _generate_request_id(self, request: Stage0Request) -> str:
        content = f"{request.goal}:{','.join(request.tools)}:{','.join(request.side_effects)}"
        hash_prefix = hashlib.sha256(content.encode()).hexdigest()[:16]
        # Append a random suffix so each call gets a unique request_id even for
        # identical requests — prevents unique constraint violations on stage0_decision_logs.
        unique_suffix = secrets.token_hex(4)
        return f"req_mock_{hash_prefix}_{unique_suffix}"

    def _calculate_risk_score(self, request: Stage0Request) -> float:
        score = 10.0

        high_risk_side_effects = {"data deletion", "payment", "deployment", "webhook"}
        for effect in request.side_effects:
            if effect.lower() in high_risk_side_effects:
                score += 20.0

        if not request.constraints:
            score += 15.0

        ctx = request.context
        if ctx:
            if not ctx.actor_role:
                score += 10.0
            if ctx.approval_status != "approved":
                score += 15.0
            if ctx.environment == "production":
                score += 10.0

        return min(score, 100.0)

    def _determine_verdict(
        self,
        request: Stage0Request,
        risk_score: float,
    ) -> tuple[str, str, list[Stage0Issue]]:
        issues: list[Stage0Issue] = []

        ctx = request.context

        if ctx:
            if ctx.approval_status is None:
                issues.append(Stage0Issue(code="APPROVAL_REQUIRED"))
                return "DEFER", "DEFER", issues

            if ctx.approval_status != "approved":
                issues.append(
                    Stage0Issue(
                        code="APPROVAL_STATUS_INVALID",
                        message=f"Expected 'approved', got '{ctx.approval_status}'",
                    )
                )
                return "NO_GO", "DENY", issues

            if ctx.approval_status == "approved" and not ctx.approved_by:
                issues.append(Stage0Issue(code="APPROVAL_TIMESTAMP_MISSING"))
                return "DEFER", "DEFER", issues

        if risk_score >= self.risk_threshold:
            issues.append(
                Stage0Issue(
                    code="RISK_SCORE_TOO_HIGH",
                    message=f"Risk score {risk_score} exceeds threshold {self.risk_threshold}",
                )
            )
            return "NO_GO", "DENY", issues

        if not ctx:
            issues.append(Stage0Issue(code="CONTEXT_REQUIRED"))
            return "DEFER", "DEFER", issues

        return "GO", "ALLOW", []

    async def check(self, request: Stage0Request) -> Stage0Response:
        await self._simulate_latency()

        request_id = self._generate_request_id(request)
        risk_score = self._calculate_risk_score(request)
        decision, verdict, issues = self._determine_verdict(request, risk_score)

        return Stage0Response(
            decision=decision,
            verdict=verdict,
            risk_score=risk_score,
            high_risk=risk_score >= 50.0,
            issues=issues,
            clarifying_questions=[],
            defer_questions=[],
            guardrails=[],
            guardrail_checks={},
            request_id=request_id,
            policy_version="mock-1.0.0",
            policy_pack_version="mock-2024-01-01",
            timestamp=int(time.time()),
            evaluated_at=int(time.time()),
            decision_trace_summary=f"Mock decision: {decision} (verdict: {verdict})",
            cached=False,
            meta=Stage0Meta(source="mock", test_mode=True),
            raw_response={
                "decision": decision,
                "verdict": verdict,
                "risk_score": risk_score,
                "issues": [i.model_dump() for i in issues],
                "request_id": request_id,
            },
        )

    async def _simulate_latency(self) -> None:
        await asyncio.sleep(0.01)

    def is_mock(self) -> bool:
        return True


def create_mock_adapter_for_test(
    default_verdict: str = "ALLOW",
    risk_threshold: float = 50.0,
) -> MockStage0Adapter:
    return MockStage0Adapter(
        default_verdict=default_verdict,
        risk_threshold=risk_threshold,
    )
