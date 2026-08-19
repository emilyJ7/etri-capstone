import { useEffect, useState } from "react";
import { fetchPapers } from "../api";

export default function PapersList() {
  const [papers, setPapers] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchPapers().then(setPapers).catch((err) => setError(err.message));
  }, []);

  if (error) return <p className="error">{error}</p>;
  if (papers === null) return <p>불러오는 중...</p>;
  if (papers.length === 0) return <p>저장된 논문이 없습니다.</p>;

  return (
    <ul className="card-list">
      {papers.map((paper) => (
        <li key={paper.id} className="card">
          <h4>{paper.title}</h4>
          <p className="meta">
            {paper.authors?.join(", ")} · {paper.publication_year} · 인용 {paper.cited_by_count ?? "-"}
          </p>
          <p className="muted">출처 리포트: {paper.report_title}</p>
          {paper.landing_page_url && (
            <a href={paper.landing_page_url} target="_blank" rel="noreferrer">
              원문 보기
            </a>
          )}
        </li>
      ))}
    </ul>
  );
}
