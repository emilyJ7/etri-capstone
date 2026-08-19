import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchReports } from "../api";

export default function ReportsList() {
  const [reports, setReports] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchReports().then(setReports).catch((err) => setError(err.message));
  }, []);

  if (error) return <p className="error">{error}</p>;
  if (reports === null) return <p>불러오는 중...</p>;
  if (reports.length === 0) return <p>저장된 리포트가 없습니다.</p>;

  return (
    <ul className="card-list">
      {reports.map((report) => (
        <li key={report.id} className="card">
          <Link to={`/reports/${report.id}`}>
            <h3>{report.title}</h3>
          </Link>
          <p className="muted">{report.research_question}</p>
          <p className="meta">
            논문 {report.paper_count}편 · {new Date(report.created_at).toLocaleString()}
          </p>
        </li>
      ))}
    </ul>
  );
}
