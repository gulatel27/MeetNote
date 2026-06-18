const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, options);
  if (!response.ok) {
    let message = `요청 실패 (${response.status})`;
    try {
      const payload = await response.json();
      message = payload.detail || message;
    } catch {
      message = await response.text();
    }
    throw new Error(typeof message === "string" ? message : JSON.stringify(message));
  }
  return response.json();
}

export async function uploadMeeting(formValues) {
  const body = new FormData();
  body.append("audio_file", formValues.audioFile);
  body.append("title", formValues.title);
  body.append("meeting_date", formValues.meetingDate);
  body.append("participants", formValues.participants);
  body.append("project_name", formValues.projectName);
  body.append("meeting_type", formValues.meetingType);

  return request("/api/meetings/upload", {
    method: "POST",
    body,
  });
}

export async function processMeeting(meetingId) {
  return request(`/api/meetings/${meetingId}/process`, {
    method: "POST",
  });
}

export async function getMeeting(meetingId) {
  return request(`/api/meetings/${meetingId}`);
}

export async function getMeetings() {
  return request("/api/meetings");
}

export function markdownDownloadUrl(meetingId) {
  return `${API_BASE_URL}/api/meetings/${meetingId}/download/markdown`;
}
