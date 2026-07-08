import json
import re
from typing import Any

from openai import OpenAI

from app.config import get_settings
from app.models import Meeting


SYSTEM_PROMPT = """
너는 한국어 회의록과 업무 보고서를 작성하는 전문 AI 어시스턴트다.
회의 transcript를 근거로 보고서에 바로 사용할 수 있는 구조화 JSON을 생성한다.

작성 원칙:
- 불확실한 내용은 단정하지 말고 "확인 필요" 또는 "미정"으로 표시한다.
- 담당자와 기한이 명확하지 않으면 반드시 "미정"으로 표시한다.
- 고객 요청사항과 내부 조치사항을 구분한다.
- 장애회의인 경우 원인, 영향도, 조치내용, 재발방지 항목을 강조한다.
- 기술회의인 경우 시스템명, DB명, 서버명, 작업명, 버전, 오류 메시지 등 고유명사를 최대한 보존한다.
- 요약은 너무 짧게 쓰지 말고, 실제 보고서로 사용할 수 있는 수준으로 작성한다.
- 입력 transcript에 없는 내용은 추측해서 만들지 않는다.
- 보고서 문체는 간결한 명사형 또는 업무 보고체로 작성한다.
- "했습니다", "합니다", "입니다", "됩니다" 같은 다나까체를 피하고 "확인함", "논의함", "필요", "미정"처럼 끝낸다.
- overall_summary는 문단 문자열이 아니라 5~10개의 bullet 항목 배열로 작성한다.
- overall_summary의 각 bullet은 하나의 핵심 사실, 논의, 결정, 이슈만 담고 여러 문장을 한 항목에 이어 붙이지 않는다.

반드시 JSON만 출력한다. Markdown 코드블록이나 설명 문장을 포함하지 않는다.
""".strip()


def build_user_prompt(meeting: Meeting, transcript: str) -> str:
    custom_prompt = (meeting.custom_prompt or "").strip()
    extra_instruction = f"\n[사용자 추가 요청사항]\n{custom_prompt}\n" if custom_prompt else ""
    return f"""
다음 회의 정보를 바탕으로 한국어 회의 요약 JSON을 생성해줘.

[회의 기본 정보]
- 회의 제목: {meeting.title}
- 회의 일자: {meeting.meeting_date}
- 고객사/프로젝트: {meeting.project_name or "미정"}
- 회의 유형: {meeting.meeting_type}
- 참석자: {meeting.participants}
{extra_instruction}

[출력 JSON 스키마]
{{
  "overall_summary": [
    "회의 핵심 내용을 5~10개 항목으로 분리. 각 항목은 하나의 내용만 담고 '확인함', '논의함', '언급됨', '필요', '미정' 형태로 작성"
  ],
  "key_discussions": ["주요 논의사항 bullet"],
  "decisions": ["결정사항"],
  "issues_and_risks": ["이슈 및 리스크"],
  "customer_requests": ["고객 요청사항"],
  "internal_actions": ["내부 조치사항"],
  "action_items": [
    {{
      "item": "액션아이템",
      "owner": "담당자 또는 미정",
      "due_date": "기한 또는 미정",
      "status": "예정/진행중/완료/미정"
    }}
  ],
  "follow_up": {{
    "next_meeting_required": "예/아니오/미정",
    "additional_checks": ["추가 확인사항"],
    "communications": ["고객 또는 내부 전달 필요사항"]
  }},
  "incident": {{
    "cause": "장애회의가 아니거나 원인이 불명확하면 미정",
    "impact": "장애회의가 아니거나 영향도가 불명확하면 미정",
    "actions_taken": ["조치내용"],
    "prevention": ["재발방지 항목"]
  }}
}}

[Transcript]
{transcript}
""".strip()


def generate_meeting_summary(meeting: Meeting, transcript: str) -> dict[str, Any]:
    settings = get_settings()
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY가 설정되지 않았습니다.")
    if not transcript.strip():
        raise ValueError("요약할 transcript가 비어 있습니다.")

    client = OpenAI(api_key=settings.openai_api_key)
    response = client.responses.create(
        model=settings.openai_summary_model,
        instructions=SYSTEM_PROMPT,
        input=build_user_prompt(meeting, transcript),
    )
    output_text = getattr(response, "output_text", None)
    if not output_text:
        output_text = str(response)

    return parse_summary_json(output_text)


def parse_summary_json(raw_text: str) -> dict[str, Any]:
    cleaned = raw_text.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", cleaned, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        cleaned = fenced.group(1).strip()

    try:
        return normalize_summary(json.loads(cleaned))
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end > start:
            try:
                return normalize_summary(json.loads(cleaned[start : end + 1]))
            except json.JSONDecodeError:
                pass

    return normalize_summary(
        {
            "overall_summary": [cleaned],
            "key_discussions": [],
            "decisions": [],
            "issues_and_risks": ["LLM 응답을 JSON으로 파싱하지 못했습니다. 원문 응답을 회의 요약에 보존함."],
            "customer_requests": [],
            "internal_actions": [],
            "action_items": [],
            "follow_up": {
                "next_meeting_required": "미정",
                "additional_checks": ["LLM 응답 형식 확인 필요"],
                "communications": [],
            },
            "incident": {
                "cause": "미정",
                "impact": "미정",
                "actions_taken": [],
                "prevention": [],
            },
        }
    )


def normalize_summary(summary: dict[str, Any]) -> dict[str, Any]:
    list_fields = [
        "overall_summary",
        "key_discussions",
        "decisions",
        "issues_and_risks",
        "customer_requests",
        "internal_actions",
    ]
    for field in list_fields:
        summary[field] = _normalize_list(summary.get(field), split_sentences=field == "overall_summary")

    if not isinstance(summary.get("action_items"), list):
        summary["action_items"] = []

    follow_up = summary.get("follow_up")
    if not isinstance(follow_up, dict):
        follow_up = {}
    summary["follow_up"] = {
        "next_meeting_required": str(follow_up.get("next_meeting_required") or "미정"),
        "additional_checks": _normalize_list(follow_up.get("additional_checks")),
        "communications": _normalize_list(follow_up.get("communications")),
    }

    incident = summary.get("incident")
    if not isinstance(incident, dict):
        incident = {}
    summary["incident"] = {
        "cause": str(incident.get("cause") or "미정"),
        "impact": str(incident.get("impact") or "미정"),
        "actions_taken": _normalize_list(incident.get("actions_taken")),
        "prevention": _normalize_list(incident.get("prevention")),
    }

    normalized_actions = []
    for action in summary["action_items"]:
        if isinstance(action, str):
            normalized_actions.append(
                {
                    "item": action,
                    "owner": "미정",
                    "due_date": "미정",
                    "status": "미정",
                }
            )
        elif isinstance(action, dict):
            normalized_actions.append(
                {
                    "item": str(action.get("item") or action.get("action") or "미정"),
                    "owner": str(action.get("owner") or action.get("assignee") or "미정"),
                    "due_date": str(action.get("due_date") or action.get("deadline") or "미정"),
                    "status": str(action.get("status") or "미정"),
                }
            )
    summary["action_items"] = normalized_actions
    return summary


def _normalize_list(value: Any, split_sentences: bool = False) -> list[str]:
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


SEMINAR_SYSTEM_PROMPT = """
너는 한국어 세미나, 강연, 교육 녹취를 읽고 공유용 요약문을 작성하는 전문 AI 어시스턴트다.
transcript에 근거해서 세미나 참석자와 미참석자 모두 이해할 수 있는 구조화 JSON을 생성한다.

작성 원칙:
- transcript에 없는 내용은 추측하지 않는다.
- 불확실한 내용은 "확인 필요"로 표시한다.
- 발표 주제, 핵심 개념, 사례, 수치, 제품명, 기술명, 인물명, 조직명을 최대한 보존한다.
- 공유용 핵심요약은 메일이나 메신저에 바로 붙여넣을 수 있게 짧고 선명한 bullet로 작성한다.
- 내용 요약은 세미나 흐름에 따라 충분히 자세히 정리한다.
- 청중이 알아야 할 핵심 내용은 실무 적용점, 주의사항, 기억해야 할 메시지 중심으로 정리한다.
- 문체는 "했습니다/합니다/입니다" 대신 "소개함", "강조함", "필요", "확인 필요" 같은 보고체로 끝낸다.
- 반드시 JSON만 출력하고 Markdown 코드블록이나 설명 문장을 포함하지 않는다.
""".strip()


def build_seminar_prompt(meeting: Meeting, transcript: str) -> str:
    custom_prompt = (meeting.custom_prompt or "").strip()
    extra_instruction = f"\n[사용자 추가 요청사항]\n{custom_prompt}\n" if custom_prompt else ""
    image_context = (getattr(meeting, "image_context", None) or "").strip()
    image_section = ""
    if image_context:
        image_section = f"""

[이미지 참고 내용]
아래 내용은 사용자가 세미나와 함께 업로드한 이미지에서 추출한 참고자료다.
transcript와 함께 검토하되, 둘 사이에 충돌이 있으면 단정하지 말고 "확인 필요"로 표시한다.
{image_context}
"""
    return f"""
다음 세미나 정보를 바탕으로 한국어 세미나 요약 JSON을 생성해줘.

[세미나 기본 정보]
- 세미나 제목: {meeting.title}
- 세미나 일자: {meeting.meeting_date}
- 주제/프로젝트: {meeting.project_name or "미정"}
- 발표자/진행자/참석자: {meeting.participants or "미정"}
{image_section}
{extra_instruction}
[출력 JSON 스키마]
{{
  "share_summary": [
    "세미나 내용 공유용 핵심요약. 5~8개 bullet. 메일/메신저 공유에 적합하게 작성"
  ],
  "content_summary": [
    "세미나 내용 요약. 주요 흐름과 설명 내용을 8~15개 bullet로 충분히 정리"
  ],
  "audience_key_points": [
    "청중이 알아야 할 핵심 내용정리. 실무 적용점, 주의사항, 기억해야 할 메시지 중심"
  ]
}}

[Transcript]
{transcript}
""".strip()


def generate_seminar_summary(meeting: Meeting, transcript: str) -> dict[str, Any]:
    settings = get_settings()
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY가 설정되지 않았습니다.")
    if not transcript.strip():
        raise ValueError("요약할 transcript가 비어 있습니다.")

    client = OpenAI(api_key=settings.openai_api_key)
    response = client.responses.create(
        model=settings.openai_summary_model,
        instructions=SEMINAR_SYSTEM_PROMPT,
        input=build_seminar_prompt(meeting, transcript),
    )
    output_text = getattr(response, "output_text", None)
    if not output_text:
        output_text = str(response)

    return parse_seminar_json(output_text)


def parse_seminar_json(raw_text: str) -> dict[str, Any]:
    cleaned = raw_text.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", cleaned, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        cleaned = fenced.group(1).strip()

    try:
        return normalize_seminar_summary(json.loads(cleaned))
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end > start:
            try:
                return normalize_seminar_summary(json.loads(cleaned[start : end + 1]))
            except json.JSONDecodeError:
                pass

    return normalize_seminar_summary(
        {
            "share_summary": [cleaned],
            "content_summary": [],
            "audience_key_points": ["LLM 응답 형식 확인 필요"],
        }
    )


def normalize_seminar_summary(summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "share_summary": _normalize_list(summary.get("share_summary"), split_sentences=True),
        "content_summary": _normalize_list(summary.get("content_summary"), split_sentences=True),
        "audience_key_points": _normalize_list(summary.get("audience_key_points"), split_sentences=True),
    }
