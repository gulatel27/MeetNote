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
- 요약은 너무 짧게 쓰지 말고, 실제 보고서로 활용 가능한 수준으로 작성한다.
- 입력 transcript에 없는 내용은 추측해서 만들지 않는다.

반드시 JSON만 출력한다. Markdown 코드블록이나 설명 문장을 포함하지 않는다.
""".strip()


def build_user_prompt(meeting: Meeting, transcript: str) -> str:
    return f"""
다음 회의 정보를 바탕으로 한국어 회의 요약 JSON을 생성해줘.

[회의 기본 정보]
- 회의 제목: {meeting.title}
- 회의 일자: {meeting.meeting_date}
- 고객사/프로젝트: {meeting.project_name or "미정"}
- 회의 유형: {meeting.meeting_type}
- 참석자: {meeting.participants}

[출력 JSON 스키마]
{{
  "overall_summary": "회의 내용을 5~10줄 정도로 요약한 문단",
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
            "overall_summary": cleaned,
            "key_discussions": [],
            "decisions": [],
            "issues_and_risks": ["LLM 응답을 JSON으로 파싱하지 못했습니다. 원문 응답을 회의 요약에 보존했습니다."],
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
    summary.setdefault("overall_summary", "")
    summary.setdefault("key_discussions", [])
    summary.setdefault("decisions", [])
    summary.setdefault("issues_and_risks", [])
    summary.setdefault("customer_requests", [])
    summary.setdefault("internal_actions", [])
    summary.setdefault("action_items", [])
    summary.setdefault(
        "follow_up",
        {
            "next_meeting_required": "미정",
            "additional_checks": [],
            "communications": [],
        },
    )
    summary.setdefault(
        "incident",
        {
            "cause": "미정",
            "impact": "미정",
            "actions_taken": [],
            "prevention": [],
        },
    )

    if not isinstance(summary["action_items"], list):
        summary["action_items"] = []

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
