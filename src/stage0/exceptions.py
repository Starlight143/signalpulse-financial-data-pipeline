"""Stage0 exceptions."""

from typing import Any


class Stage0Error(Exception):
    pass


class Stage0AuthorizationError(Stage0Error):
    def __init__(
        self,
        verdict: str,
        issues: list[dict[str, Any]],
        request_id: str | None = None,
    ):
        self.verdict = verdict
        self.issues = issues
        self.request_id = request_id
        issue_codes = [i.get("code", str(i)) for i in issues]
        super().__init__(
            f"Stage0 authorization denied (verdict={verdict}): {', '.join(issue_codes)}"
        )


class Stage0ConnectionError(Stage0Error):
    pass


class Stage0TimeoutError(Stage0Error):
    pass


class Stage0DeferredError(Stage0Error):
    def __init__(
        self,
        issues: list[dict[str, Any]],
        clarifying_questions: list[str],
        request_id: str | None = None,
    ):
        self.issues = issues
        self.clarifying_questions = clarifying_questions
        self.request_id = request_id
        super().__init__(
            f"Stage0 deferred: requires additional context. Questions: {clarifying_questions}"
        )
