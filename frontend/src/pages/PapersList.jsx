import { useEffect, useState } from "react";
import { fetchPapers } from "../api";
import { Loading, ErrorMessage } from "../components/State";
import SourceBadge from "../components/SourceBadge";
import PaperReferenceLinks from "../components/PaperReferenceLinks";

export default function PapersList() {
  const [papers, setPapers] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchPapers().then(setPapers).catch((err) => setError(err.message));
  }, []);

  if (error) return <ErrorMessage message={error} />;
  if (papers === null) return <Loading label="논문 목록을 불러오는 중" />;
  if (papers.length === 0) return <p className="muted">저장된 논문이 없습니다.</p>;

  return (
    <ul className="card-list">
      {papers.map((paper, i) => (
        <li key={paper.id} className="card" style={{ "--i": i }}>
          <h4>
            {paper.title} <SourceBadge source={paper.source} />
          </h4>
          <p className="meta">
            {paper.authors?.join(", ")} · {paper.publication_year} · 인용 {paper.cited_by_count ?? "-"}
          </p>
          <p className="muted">출처 리포트: {paper.report_title}</p>
          <PaperReferenceLinks doi={paper.doi} landingPageUrl={paper.landing_page_url} />
        </li>
      ))}
    </ul>
  );
}
