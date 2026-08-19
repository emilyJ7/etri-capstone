import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { fetchReport } from "../api";

export default function ReportDetail() {
  const { reportId } = useParams();
  const [report, setReport] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    setReport(null);
    setError(null);
    fetchReport(reportId).then(setReport).catch((err) => setError(err.message));
  }, [reportId]);

  if (error) return <p className="error">{error}</p>;
  if (report === null) return <p>불러오는 중...</p>;

  return (
    <div>
      <Link to="/">← 리포트 목록</Link>
      <h2>{report.title}</h2>
      <p className="muted">{report.research_question}</p>

      <div className="markdown-body">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{report.content}</ReactMarkdown>
      </div>

      <h3>참조 논문 ({report.papers.length}편)</h3>
      <ul className="card-list">
        {report.papers.map((paper) => (
          <li key={paper.openalex_id} className="card">
            <h4>{paper.title}</h4>
            <p className="meta">
              {paper.authors?.join(", ")} · {paper.publication_year} · 인용 {paper.cited_by_count ?? "-"}
            </p>
            {paper.landing_page_url && (
              <a href={paper.landing_page_url} target="_blank" rel="noreferrer">
                원문 보기
              </a>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
