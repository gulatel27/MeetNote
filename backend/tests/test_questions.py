import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import Meeting
from app.schemas import QuestionAnswer
from app.services.question_service import answer_question


class QuestionTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.meeting = Meeting(title="테스트", meeting_date="2026-11-06", participants="민수",
                               meeting_type="내부회의", audio_file_path="unused.wav",
                               transcript="민수가 금요일까지 검토한다.", status="completed")
        self.db.add(self.meeting)
        self.db.commit()
        self.mid = self.meeting.id
        app.dependency_overrides[get_db] = lambda: self.db
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()
        self.db.close()
        self.engine.dispose()

    def ask(self, question, meeting_id=None):
        return self.client.post(f"/api/meetings/{meeting_id or self.mid}/questions", json={"question": question})

    def test_answer_uses_original_transcript_without_mutating_meeting(self):
        with patch("app.routers.meetings.answer_question", return_value=QuestionAnswer(
            answer="민수가 금요일까지 검토합니다.", evidence=[self.meeting.transcript], insufficient_evidence=False,
        )) as mocked:
            response = self.ask("  담당자와 기한은?  ")
            self.assertEqual(response.status_code, 200)
            mocked.assert_called_once_with("민수가 금요일까지 검토한다.", "담당자와 기한은?")
            self.assertEqual(response.json()["evidence"], [self.meeting.transcript])
            self.assertEqual(self.meeting.status, "completed")

    def test_rejects_empty_long_missing_recording_and_missing_transcript(self):
        with patch("app.routers.meetings.answer_question") as mocked:
            for text in ("  ", "x" * 2001):
                self.assertEqual(self.ask(text).status_code, 422)
            self.assertEqual(self.ask("질문", 999).status_code, 404)
            self.meeting.transcript = None
            self.db.commit()
            self.assertEqual(self.ask("질문").status_code, 409)
            mocked.assert_not_called()

    def test_provider_failure_does_not_change_recording_status(self):
        with patch("app.routers.meetings.answer_question", side_effect=RuntimeError("private details")):
            response = self.ask("질문")
            self.assertEqual(response.status_code, 502)
            self.assertNotIn("private details", response.text)
            self.assertEqual(self.meeting.status, "completed")

    def test_missing_api_key_returns_actionable_error(self):
        with patch("app.services.question_service.get_settings", return_value=SimpleNamespace(openai_api_key=None)):
            self.assertEqual(self.ask("질문").status_code, 503)

    def test_fabricated_quotes_are_removed_and_unsupported_answer_is_rejected(self):
        with patch("app.services.question_service.get_settings", return_value=SimpleNamespace(
            openai_api_key="test", openai_summary_model="test",
        )), patch("app.services.question_service.OpenAI") as mocked:
            parse = mocked.return_value.__enter__.return_value.responses.parse
            parse.return_value = SimpleNamespace(output_parsed=QuestionAnswer(
                answer="예산은 1억입니다.", evidence=["예산 1억"], insufficient_evidence=False,
            ))
            result = answer_question(self.meeting.transcript, "예산은?")
            self.assertTrue(result.insufficient_evidence)
            self.assertEqual(result.evidence, [])
            self.assertEqual(result.answer, "녹음 내용에서 확인할 수 없습니다.")
            parse.return_value = SimpleNamespace(output_parsed=QuestionAnswer(
                answer="민수가 검토합니다.", evidence=["가짜 인용", "민수가 금요일까지 검토한다."], insufficient_evidence=False,
            ))
            self.assertEqual(answer_question(self.meeting.transcript, "누가?").evidence, [self.meeting.transcript])


if __name__ == "__main__":
    unittest.main()
