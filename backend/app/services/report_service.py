import re
from typing import Any

from app.models import Meeting


NO_VALUE = "미정"


def generate_report_markdown(meeting: Meeting, summary: dict[str, Any], transcript: str) -> str:
    if getattr(meeting, "report_type", "meeting") == "seminar":
        return generate_seminar_report_markdown(meeting, summary, transcript)

    action_items = summary.get("action_items") or []
    follow_up = summary.get("follow_up") or {}
    incident = summary.get("incident") or {}

    lines = [
        "# 📝 회의 보고서",
        "",
        "## 1. ℹ️ 회의 기본 정보",
        "",
        "| 항목 | 내용 |",
        "| -- | -- |",
        f"| 회의 제목 | {_escape_table(meeting.title)} |",
        f"| 회의 일자 | {_escape_table(meeting.meeting_date)} |",
        f"| 고객사/프로젝트 | {_escape_table(meeting.project_name or NO_VALUE)} |",
        f"| 회의 유형 | {_escape_table(meeting.meeting_type)} |",
        f"| 참석자 | {_escape_table(meeting.participants)} |",
        "",
        "## 2. ✅ 회의 요약",
        "",
        _format_bullets(summary.get("overall_summary"), split_sentences=True),
        "",
        "## 3. 💬 주요 논의사항",
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
        "## 4. 📌 결정사항",
        "",
        _format_bullets(summary.get("decisions")),
        "",
        "## 5. ⚠️ 이슈 및 리스크",
        "",
        _format_bullets(summary.get("issues_and_risks")),
    ]

    if _has_incident_content(incident):
        lines.extend(
            [
                "",
                "### 장애 관련 정리",
                "",
                f"* 원인: {_format_report_sentence(incident.get('cause') or NO_VALUE)}",
                f"* 영향도: {_format_report_sentence(incident.get('impact') or NO_VALUE)}",
                "",
                "### 조치내용",
                "",
                _format_bullets(incident.get("actions_taken")),
                "",
                "### 재발방지",
                "",
                _format_bullets(incident.get("prevention")),
            ]
        )

    lines.extend(
        [
            "",
            "## 6. 🧭 액션아이템",
            "",
            "| No | 액션아이템 | 담당자 | 기한 | 상태 |",
            "| -- | ----- | --- | -- | -- |",
        ]
    )
    lines.extend(_format_action_table(action_items))
    lines.extend(
        [
            "",
            "## 7. 🔁 후속 조치",
            "",
            f"* 다음 회의 필요 여부: {_format_report_sentence(follow_up.get('next_meeting_required') or NO_VALUE)}",
            "",
            "### 추가 확인사항",
            "",
            _format_bullets(follow_up.get("additional_checks")),
            "",
            "### 고객/내부 전달 필요사항",
            "",
            _format_bullets(follow_up.get("communications")),
            "",
            "## 8. 🗒️ 원문 Transcript",
            "",
            transcript.strip() or "Transcript가 없음.",
            "",
        ]
    )
    return "\n".join(lines)


def generate_seminar_report_markdown(meeting: Meeting, summary: dict[str, Any], transcript: str) -> str:
    lines = [
        "# 세미나 요약",
        "",
        "## 1. 세미나 기본 정보",
        "",
        "| 항목 | 내용 |",
        "| -- | -- |",
        f"| 세미나 제목 | {_escape_table(meeting.title)} |",
        f"| 세미나 일자 | {_escape_table(meeting.meeting_date)} |",
        f"| 주제/프로젝트 | {_escape_table(meeting.project_name or NO_VALUE)} |",
        f"| 발표자/진행자/참석자 | {_escape_table(meeting.participants or NO_VALUE)} |",
    ]

    if (meeting.custom_prompt or "").strip():
        lines.extend(
            [
                f"| 추가 요청사항 | {_escape_table(meeting.custom_prompt)} |",
            ]
        )

    lines.extend(
        [
            "",
            "## 2. 세미나 내용 공유용 핵심요약",
            "",
            _format_bullets(summary.get("share_summary"), split_sentences=True),
            "",
            "## 3. 내용 요약",
            "",
            _format_bullets(summary.get("content_summary"), split_sentences=True),
            "",
            "## 4. 청중이 알아야할 핵심 내용정리",
            "",
            _format_bullets(summary.get("audience_key_points"), split_sentences=True),
            "",
            "## 5. 원문 Transcript",
            "",
            transcript.strip() or "Transcript가 없음.",
            "",
        ]
    )
    return "\n".join(lines)


def _format_bullets(items: Any, split_sentences: bool = False) -> str:
    values = _as_list(items, split_sentences=split_sentences)
    if not values:
        return f"* {NO_VALUE}"
    return "\n".join(f"* {_format_report_sentence(item)}" for item in values)


def _format_action_table(action_items: list[dict[str, Any]]) -> list[str]:
    if not action_items:
        return [f"| 1 | {NO_VALUE} | {NO_VALUE} | {NO_VALUE} | {NO_VALUE} |"]

    rows = []
    for index, action in enumerate(action_items, start=1):
        rows.append(
            "| {no} | {item} | {owner} | {due_date} | {status} |".format(
                no=index,
                item=_escape_table(_format_report_sentence(action.get("item") or NO_VALUE)),
                owner=_escape_table(action.get("owner") or NO_VALUE),
                due_date=_escape_table(action.get("due_date") or NO_VALUE),
                status=_escape_table(action.get("status") or NO_VALUE),
            )
        )
    return rows


def _as_list(value: Any, split_sentences: bool = False) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        items: list[str] = []
        for item in value:
            items.extend(_split_text_items(str(item), split_sentences=split_sentences))
        return items
    text = str(value).strip()
    if not text:
        return []

    return _split_text_items(text, split_sentences=split_sentences)


def _split_text_items(text: str, split_sentences: bool = False) -> list[str]:
    lines = [line.strip(" -\t") for line in text.splitlines() if line.strip(" -\t")]
    if len(lines) > 1:
        return lines
    if split_sentences:
        sentences = _split_summary_sentences(text)
        if len(sentences) > 1:
            return sentences
    return [text]


def _split_summary_sentences(text: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", text.strip())
    if not normalized:
        return []

    parts = re.split(r"(?<=[.!?。])\s+", normalized)
    sentences = [part.strip(" -\t") for part in parts if part.strip(" -\t")]
    if len(sentences) > 1:
        return sentences

    semicolon_parts = [part.strip(" -\t") for part in re.split(r"\s*[;；]\s*", normalized) if part.strip(" -\t")]
    return semicolon_parts if len(semicolon_parts) > 1 else sentences


def _format_report_sentence(value: Any) -> str:
    text = re.sub(r"\s+", " ", str(value or NO_VALUE).strip())
    if not text:
        return NO_VALUE

    replacements = [
        (r"논의하였습니다([.。]?)$", "논의함."),
        (r"논의했습니다([.。]?)$", "논의함."),
        (r"확인하였습니다([.。]?)$", "확인함."),
        (r"확인했습니다([.。]?)$", "확인함."),
        (r"공유하였습니다([.。]?)$", "공유함."),
        (r"공유했습니다([.。]?)$", "공유함."),
        (r"요청하였습니다([.。]?)$", "요청함."),
        (r"요청했습니다([.。]?)$", "요청함."),
        (r"언급하였습니다([.。]?)$", "언급함."),
        (r"언급했습니다([.。]?)$", "언급함."),
        (r"언급되었습니다([.。]?)$", "언급됨."),
        (r"언급됩니다([.。]?)$", "언급됨."),
        (r"검토하였습니다([.。]?)$", "검토함."),
        (r"검토했습니다([.。]?)$", "검토함."),
        (r"정리하였습니다([.。]?)$", "정리함."),
        (r"정리했습니다([.。]?)$", "정리함."),
        (r"설명하였습니다([.。]?)$", "설명함."),
        (r"설명했습니다([.。]?)$", "설명함."),
        (r"안내하였습니다([.。]?)$", "안내함."),
        (r"안내했습니다([.。]?)$", "안내함."),
        (r"결정하였습니다([.。]?)$", "결정함."),
        (r"결정했습니다([.。]?)$", "결정함."),
        (r"결정되었습니다([.。]?)$", "결정됨."),
        (r"결정됩니다([.。]?)$", "결정됨."),
        (r"진행하였습니다([.。]?)$", "진행함."),
        (r"진행했습니다([.。]?)$", "진행함."),
        (r"진행됩니다([.。]?)$", "진행됨."),
        (r"필요하였습니다([.。]?)$", "필요함."),
        (r"필요했습니다([.。]?)$", "필요함."),
        (r"필요합니다([.。]?)$", "필요함."),
        (r"예정입니다([.。]?)$", "예정."),
        (r"예정되었습니다([.。]?)$", "예정됨."),
        (r"예정됩니다([.。]?)$", "예정됨."),
        (r"가능합니다([.。]?)$", "가능함."),
        (r"어렵습니다([.。]?)$", "어려움."),
        (r"없습니다([.。]?)$", "없음."),
        (r"있습니다([.。]?)$", "있음."),
        (r"되었습니다([.。]?)$", "됨."),
        (r"됩니다([.。]?)$", "됨."),
        (r"하였습니다([.。]?)$", "함."),
        (r"했습니다([.。]?)$", "함."),
        (r"합니다([.。]?)$", "함."),
        (r"입니다([.。]?)$", "임."),
    ]
    for pattern, replacement in replacements:
        text = re.sub(pattern, replacement, text)

    if text.endswith("다."):
        text = text[:-2] + "."
    elif text.endswith("다"):
        text = text[:-1]

    if text and not text.endswith((".", ")", ")", "!", "?", "임", "함", "됨", "필요", "미정")):
        text += "."
    return text


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
    return any(str(value or "").strip() not in {"", NO_VALUE} for value in values)
