import { Routes, Route, Link } from "react-router-dom";
import ReportsList from "./pages/ReportsList";
import ReportDetail from "./pages/ReportDetail";
import PapersList from "./pages/PapersList";
import "./App.css";

export default function App() {
  return (
    <div className="app">
      <header className="nav">
        <h1>OpenAlex 연구 지원 뷰어</h1>
        <nav>
          <Link to="/">리포트</Link>
          <Link to="/papers">논문</Link>
        </nav>
      </header>

      <main>
        <Routes>
          <Route path="/" element={<ReportsList />} />
          <Route path="/reports/:reportId" element={<ReportDetail />} />
          <Route path="/papers" element={<PapersList />} />
        </Routes>
      </main>
    </div>
  );
}
