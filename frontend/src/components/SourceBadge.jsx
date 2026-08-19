const LABELS = {
  openalex: "OpenAlex",
  arxiv: "arXiv",
  semantic_scholar: "Semantic Scholar",
  google_scholar: "Google Scholar",
};

export default function SourceBadge({ source }) {
  const label = LABELS[source] ?? "출처 미상";
  return <span className={`badge${source in LABELS ? "" : " badge-unknown"}`}>{label}</span>;
}
