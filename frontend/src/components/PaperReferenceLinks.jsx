export default function PaperReferenceLinks({ doi, landingPageUrl }) {
  const links = [];
  if (landingPageUrl) {
    links.push({ label: "원문 보기", href: landingPageUrl });
  }
  if (doi && doi !== landingPageUrl) {
    links.push({ label: "DOI", href: doi });
  }

  if (links.length === 0) return null;

  return (
    <>
      {links.map((link) => (
        <a key={link.href} className="pill" href={link.href} target="_blank" rel="noreferrer">
          {link.label} ↗
        </a>
      ))}
    </>
  );
}
