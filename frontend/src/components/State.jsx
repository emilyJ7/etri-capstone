export function Loading({ label = "불러오는 중" }) {
  return (
    <div className="state">
      <span className="spinner" />
      <span>{label}...</span>
    </div>
  );
}

export function ErrorMessage({ message }) {
  return <p className="error">⚠ {message}</p>;
}
