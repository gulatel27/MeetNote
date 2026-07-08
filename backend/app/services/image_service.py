import base64
import mimetypes
from pathlib import Path

from openai import OpenAI

from app.config import get_settings


def extract_image_context(image_file_paths: list[str]) -> str:
    paths = [Path(path) for path in image_file_paths if path]
    paths = [path for path in paths if path.exists()]
    if not paths:
        return ""

    settings = get_settings()
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY가 설정되지 않아 이미지 내용을 분석할 수 없습니다.")

    content = [
        {
            "type": "input_text",
            "text": (
                "다음 이미지는 미팅 중 촬영한 화이트보드, 문서, 화면, 메모일 수 있다. "
                "이미지 안의 글자, 표, 도식, 숫자, 결정사항, 업무 항목, 시스템명, 일정 정보를 한국어로 추출하고 "
                "회의 요약에 참고할 수 있게 정리해줘. 보이지 않거나 불확실한 내용은 추측하지 말고 '확인 필요'로 표시해줘."
            ),
        }
    ]
    for path in paths:
        content.append(
            {
                "type": "input_image",
                "image_url": _image_to_data_url(path),
            }
        )

    client = OpenAI(api_key=settings.openai_api_key)
    response = client.responses.create(
        model=settings.openai_vision_model,
        input=[
            {
                "role": "user",
                "content": content,
            }
        ],
    )
    output_text = getattr(response, "output_text", None)
    if not output_text:
        output_text = str(response)
    return output_text.strip()


def _image_to_data_url(path: Path) -> str:
    mime_type, _ = mimetypes.guess_type(path.name)
    if not mime_type:
        mime_type = "image/jpeg"
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{data}"
