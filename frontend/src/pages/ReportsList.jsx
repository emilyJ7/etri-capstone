import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchReports } from "../api";
import { Loading, ErrorMessage } from "../components/State";

export default function ReportsList() {
  const [reports, setReports] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchReports().then(setReports).catch((err) => setError(err.message));
  }, []);

  if (error) return <ErrorMessage message={error} />;
  if (reports === null) return <Loading label="리포트 목록을 불러오는 중" />;
  if (reports.length === 0) return <p className="muted">저장된 리포트가 없습니다.</p>;

  return (
    <ul className="card-list">
      {reports.map((report, i) => (
        <li key={report.id} className="card" style={{ "--i": i }}>
          <Link to={`/reports/${report.id}`} className="card-link">
            <h3>{report.title}</h3>
            <p className="muted">{report.research_question}</p>
            <p className="meta">
              논문 {report.paper_count}편 · {new Date(report.created_at).toLocaleString()}
            </p>
          </Link>
        </li>
      ))}
    </ul>
  );
}
