from typing import Any

from app.models import Meeting


def generate_report_markdown(meeting: Meeting, summary: dict[str, Any], transcript: str) -> str:
    action_items = summary.get("action_items") or []
    follow_up = summary.get("follow_up") or {}
    incident = summary.get("incident") or {}

    lines = [
        "# 회의 보고서",
        "",
        "## 1. 회의 기본 정보",
        "",
        f"* 회의 제목: {meeting.title}",
        f"* 회의 일자: {meeting.meeting_date}",
        f"* 고객사/프로젝트: {meeting.project_name or '미정'}",
        f"* 회의 유형: {meeting.meeting_type}",
        f"* 참석자: {meeting.participants}",
        "",
        "## 2. 회의 요약",
        "",
        _format_summary(summary.get("overall_summary")),
        "",
        "## 3. 주요 논의사항",
        "",
        _format_bullets(summary.get("key_discussions")),
        "",
        "### 고객 요청사항",
        "",
        _format_bullets(summary.get("customer_requests")),
        "",
        "### 내부 조치사항",
        "",
        _format_bullets(summary.get("internal_actions")),
        "",
        "## 4. 결정사항",
        "",
        _format_bullets(summary.get("decisions")),
        "",
        "## 5. 이슈 및 리스크",
        "",
        _format_bullets(summary.get("issues_and_risks")),
    ]

    if _has_incident_content(incident):
        lines.extend(
            [
                "",
                "### 장애 관련 정리",
                "",
                f"* 원인: {incident.get('cause') or '미정'}",
                f"* 영향도: {incident.get('impact') or '미정'}",
                "* 조치내용:",
                _format_bullets(incident.get("actions_taken")),
                "* 재발방지:",
                _format_bullets(incident.get("prevention")),
            ]
        )

    lines.extend(
        [
            "",
            "## 6. 액션아이템",
            "",
            "| No | 액션아이템 | 담당자 | 기한 | 상태 |",
            "| -- | ----- | --- | -- | -- |",
        ]
    )
    lines.extend(_format_action_table(action_items))
    lines.extend(
        [
            "",
            "## 7. 후속 조치",
            "",
            f"* 다음 회의 필요 여부: {follow_up.get('next_meeting_required') or '미정'}",
            "* 추가 확인사항:",
            _format_bullets(follow_up.get("additional_checks")),
            "* 고객/내부 전달 필요사항:",
            _format_bullets(follow_up.get("communications")),
            "",
            "## 8. 원문 Transcript",
            "",
            transcript.strip() or "Transcript가 없습니다.",
            "",
        ]
    )
    return "\n".join(lines)


def _format_summary(value: Any) -> str:
    if isinstance(value, list):
        return "\n".join(str(item).strip() for item in value if str(item).strip()) or "요약 내용이 없습니다."
    text = str(value or "").strip()
    return text or "요약 내용이 없습니다."


def _format_bullets(items: Any) -> str:
    if not items:
        return "* 미정"
    if isinstance(items, str):
        items = [items]
    if not isinstance(items, list):
        return f"* {items}"
    bullets = [f"* {str(item).strip()}" for item in items if str(item).strip()]
    return "\n".join(bullets) if bullets else "* 미정"


def _format_action_table(action_items: list[dict[str, Any]]) -> list[str]:
    if not action_items:
        return ["| 1 | 미정 | 미정 | 미정 | 미정 |"]

    rows = []
    for index, action in enumerate(action_items, start=1):
        rows.append(
            "| {no} | {item} | {owner} | {due_date} | {status} |".format(
                no=index,
                item=_escape_table(action.get("item") or "미정"),
                owner=_escape_table(action.get("owner") or "미정"),
                due_date=_escape_table(action.get("due_date") or "미정"),
                status=_escape_table(action.get("status") or "미정"),
            )
        )
    return rows


def _escape_table(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ").strip()


def _has_incident_content(incident: dict[str, Any]) -> bool:
    if not incident:
        return False
    values = [
        incident.get("cause"),
        incident.get("impact"),
        *(incident.get("actions_taken") or []),
        *(incident.get("prevention") or []),
    ]
    return any(str(value or "").strip() not in {"", "미정"} for value in values)
