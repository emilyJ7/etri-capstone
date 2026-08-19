const LABELS = {
  openalex: "OpenAlex",
  arxiv: "arXiv",
  semantic_scholar: "Semantic Scholar",
  google_scholar: "Google Scholar",
};

export default function SourceBadge({ source }) {
  return <span className="badge">{LABELS[source] ?? LABELS.openalex}</span>;
}
