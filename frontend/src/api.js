const BASE_URL = "http://localhost:8000/api";

async function getJson(path) {
  const response = await fetch(`${BASE_URL}${path}`);
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `요청이 실패했습니다 (HTTP ${response.status})`);
  }
  return response.json();
}

export function fetchReports() {
  return getJson("/reports");
}

export function fetchReport(reportId) {
  return getJson(`/reports/${reportId}`);
}

export function fetchPapers(reportId) {
  return getJson(reportId ? `/papers?report_id=${reportId}` : "/papers");
}
