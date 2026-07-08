import shutil
import subprocess
import tempfile
from pathlib import Path

from openai import OpenAI

from app.config import get_settings


def split_audio_into_chunks(audio_path: Path, work_dir: Path) -> list[Path]:
    """Normalize every upload to mp3 chunks before sending it to STT.

    Some recorder-produced .m4a files have a valid extension but a container or
    codec layout that OpenAI rejects as "Invalid file format". Transcoding also
    gives every request an ASCII .mp3 filename and keeps large-file chunking in
    the same path.
    """
    settings = get_settings()
    ffmpeg_executable = _resolve_ffmpeg(settings.ffmpeg_path)
    return _create_stt_chunks(audio_path, work_dir, ffmpeg_executable)


def transcribe_audio(audio_file_path: str) -> str:
    settings = get_settings()
    audio_path = Path(audio_file_path)
    if not audio_path.exists():
        raise FileNotFoundError(f"업로드된 음성파일을 찾을 수 없습니다: {audio_path}")

    provider = settings.stt_provider.lower()
    if provider == "openai":
        return transcribe_with_openai(audio_path)
    if provider == "local":
        return transcribe_with_local_whisper(audio_path)

    raise ValueError(f"지원하지 않는 STT_PROVIDER 값입니다: {settings.stt_provider}")


def transcribe_with_openai(audio_path: Path) -> str:
    settings = get_settings()
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY가 설정되지 않았습니다.")

    client = OpenAI(api_key=settings.openai_api_key)
    transcripts: list[str] = []

    with tempfile.TemporaryDirectory(prefix="stt_chunks_", dir=str(settings.upload_path)) as temp_dir:
        chunks = split_audio_into_chunks(audio_path, Path(temp_dir))
        for index, chunk_path in enumerate(chunks, start=1):
            try:
                with chunk_path.open("rb") as audio_file:
                    result = client.audio.transcriptions.create(
                        model=settings.openai_stt_model,
                        file=audio_file,
                        response_format="text",
                        language="ko",
                    )
                transcripts.append(_extract_transcript_text(result))
            except Exception as exc:
                raise RuntimeError(
                    f"STT chunk 처리 실패 ({index}/{len(chunks)}, {chunk_path.name}): {exc}"
                ) from exc

    transcript = "\n\n".join(part.strip() for part in transcripts if part and part.strip()).strip()
    if not transcript:
        raise RuntimeError("STT 결과 transcript가 비어 있습니다.")
    return transcript


def transcribe_with_local_whisper(audio_path: Path) -> str:
    # TODO: Wire faster-whisper/openai-whisper here for offline STT.
    raise NotImplementedError(
        f"로컬 Whisper STT는 아직 연결되지 않았습니다. STT_PROVIDER=openai로 실행하거나 구현을 추가하세요: {audio_path}"
    )


def _extract_transcript_text(result: object) -> str:
    if isinstance(result, str):
        return result
    text = getattr(result, "text", None)
    if isinstance(text, str):
        return text
    return str(result)


def _resolve_ffmpeg(ffmpeg_path: str) -> str:
    configured_path = Path(ffmpeg_path)
    if configured_path.exists():
        return str(configured_path.resolve())

    resolved = shutil.which(ffmpeg_path)
    if resolved:
        return resolved

    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        pass

    raise RuntimeError(
        "STT 전처리를 위해 ffmpeg가 필요합니다. "
        "pip install -r requirements.txt를 다시 실행하거나, ffmpeg를 설치해 PATH에 추가하거나, "
        "backend/.env에 FFMPEG_PATH로 ffmpeg.exe 경로를 설정하세요."
    )


def _create_stt_chunks(audio_path: Path, work_dir: Path, ffmpeg_executable: str) -> list[Path]:
    settings = get_settings()
    work_dir.mkdir(parents=True, exist_ok=True)

    for segment_seconds in _segment_second_candidates(settings.stt_chunk_seconds):
        _clear_chunk_outputs(work_dir)
        output_pattern = work_dir / "chunk_%04d.mp3"
        command = [
            ffmpeg_executable,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(audio_path),
            "-map",
            "0:a:0",
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-b:a",
            "64k",
            "-f",
            "segment",
            "-segment_time",
            str(segment_seconds),
            "-reset_timestamps",
            "1",
            str(output_pattern),
        ]
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if completed.returncode != 0:
            details = (completed.stderr or completed.stdout or "").strip()
            raise RuntimeError(f"ffmpeg 오디오 전처리 실패: {details}")

        chunks = sorted(work_dir.glob("chunk_*.mp3"))
        if chunks and all(chunk.stat().st_size <= settings.openai_stt_max_bytes for chunk in chunks):
            return chunks

    raise RuntimeError(
        "STT chunk 파일이 OpenAI 업로드 제한보다 큽니다. "
        "STT_CHUNK_SECONDS 값을 더 낮추거나 입력 파일을 더 작은 단위로 나누어 업로드하세요."
    )


def _segment_second_candidates(configured_seconds: int) -> list[int]:
    seconds = max(30, int(configured_seconds or 600))
    candidates: list[int] = []
    while seconds >= 30:
        candidates.append(seconds)
        seconds //= 2
    if 30 not in candidates:
        candidates.append(30)
    return candidates


def _clear_chunk_outputs(work_dir: Path) -> None:
    for chunk in work_dir.glob("chunk_*.mp3"):
        chunk.unlink(missing_ok=True)
