# 회의 보고서 자동화 MVP

회의 음성파일을 업로드하면 FastAPI 백엔드가 파일을 로컬에 저장하고, OpenAI STT API로 transcript를 생성한 뒤 LLM으로 회의 요약 JSON과 Markdown 회의 보고서를 생성하는 MVP입니다. 처리 이력은 SQLite에 저장됩니다.

## 구현 범위

- 로컬 웹 화면에서 mp3, wav, m4a, mp4 업로드
- 회의 제목, 일자, 참석자, 프로젝트명, 회의 유형 입력
- FastAPI 서버 로컬 파일 저장
- OpenAI STT API 호출 구조와 25MB 초과 파일 chunk 분할
- LLM 기반 한국어 회의 요약 JSON 생성
- Markdown 회의 보고서 생성 및 다운로드
- 결과 화면과 히스토리 화면
- SQLite `meetings` 테이블 저장

## 프로젝트 구조

```text
meeting-report-tool/
  backend/
    app/
      main.py
      config.py
      database.py
      models.py
      schemas.py
      routers/
        meetings.py
      services/
        file_service.py
        stt_service.py
        summary_service.py
        report_service.py
    uploads/
    reports/
    requirements.txt
    .env.example
  frontend/
    src/
      api/
      components/
      pages/
      App.jsx
      main.jsx
      styles.css
    package.json
    .env.example
```

## Backend 실행 방법

```bash
cd meeting-report-tool/backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

macOS/Linux에서는 가상환경 활성화 명령만 아래처럼 바꿉니다.

```bash
source .venv/bin/activate
```

25MB를 초과하는 음성파일을 STT 처리할 때는 백엔드가 `ffmpeg`로 파일을 chunk 분할합니다. 기본적으로 `imageio-ffmpeg` 패키지의 bundled ffmpeg를 사용하며, 별도 ffmpeg를 쓰려면 PATH에 추가하거나 `.env`의 `FFMPEG_PATH`에 `ffmpeg.exe` 절대 경로를 설정하세요.

## `.env` 설정 방법

`backend/.env`에 OpenAI API Key를 설정합니다.

```env
OPENAI_API_KEY=sk-your-openai-api-key
OPENAI_STT_MODEL=whisper-1
OPENAI_SUMMARY_MODEL=gpt-5.5
STT_PROVIDER=openai
OPENAI_STT_MAX_BYTES=25165824
STT_CHUNK_SECONDS=600
FFMPEG_PATH=ffmpeg
DATABASE_URL=sqlite:///./meeting_reports.db
UPLOAD_DIR=./uploads
REPORT_DIR=./reports
MAX_UPLOAD_BYTES=524288000
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

`OPENAI_SUMMARY_MODEL`은 계정에서 사용 가능한 모델명으로 변경할 수 있습니다. `OPENAI_STT_MODEL`도 `whisper-1` 또는 사용 가능한 transcription 모델로 바꿀 수 있습니다.

`OPENAI_STT_MAX_BYTES`는 OpenAI STT 요청 1회에 보낼 안전한 파일 크기입니다. 기본값은 24MiB입니다. 원본 업로드 파일이 이 값을 넘으면 백엔드가 `ffmpeg`로 10분 단위 mp3 chunk를 만든 뒤 chunk별 STT 결과를 합칩니다.

## Frontend 실행 방법

```bash
cd meeting-report-tool/frontend
copy .env.example .env
npm install
npm run dev
```

브라우저에서 `http://localhost:5173`을 엽니다.

## 테스트 방법

1. 백엔드 서버를 `http://127.0.0.1:8000`으로 실행합니다.
2. 프론트엔드 서버를 `http://localhost:5173`으로 실행합니다.
3. 업로드 화면에서 mp3, wav, m4a, mp4 중 하나를 선택합니다.
4. 회의 제목, 회의 일자, 참석자, 프로젝트명, 회의 유형을 입력합니다.
5. `업로드 및 분석 시작` 버튼을 누릅니다.
6. 처리가 완료되면 결과 화면에서 transcript와 Markdown 보고서를 확인합니다.
7. `Markdown 다운로드` 버튼으로 `.md` 파일을 내려받습니다.
8. 히스토리 메뉴에서 기존 처리 이력을 다시 조회합니다.

## API

- `POST /api/meetings/upload`
- `POST /api/meetings/{meeting_id}/process`
- `GET /api/meetings/{meeting_id}`
- `GET /api/meetings`
- `GET /api/meetings/{meeting_id}/download/markdown`
- `GET /api/meetings/{meeting_id}/download/docx` - MVP 이후 TODO, 현재 501 반환

## 현재 TODO

- 로컬 Whisper 실제 연결
- DOCX 보고서 다운로드
- 비동기 큐 기반 백그라운드 처리
- 실시간 진행률 표시
- 화자분리
- 로그인과 권한관리
- 클라우드 스토리지 및 배포

## 오류 확인 위치

- 백엔드 콘솔: `uvicorn` 실행 터미널에 API 오류와 stack trace가 출력됩니다.
- DB 오류 메시지: `backend/meeting_reports.db`의 `meetings.error_message`에 STT/LLM 처리 실패 메시지가 저장됩니다.
- 업로드 파일: `backend/uploads/`
- 생성된 Markdown 파일: `backend/reports/`
