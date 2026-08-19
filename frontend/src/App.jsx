import { Routes, Route, NavLink, useLocation } from "react-router-dom";
import ReportsList from "./pages/ReportsList";
import ReportDetail from "./pages/ReportDetail";
import PapersList from "./pages/PapersList";
import "./App.css";

export default function App() {
  const location = useLocation();

  return (
    <div className="app">
      <header className="nav">
        <NavLink to="/" className="brand">
          <span className="brand-mark" />
          <h1>OpenAlex 연구 지원 뷰어</h1>
        </NavLink>
        <nav className="nav-links">
          <NavLink to="/" end className={({ isActive }) => (isActive ? "active" : "")}>
            리포트
          </NavLink>
          <NavLink to="/papers" className={({ isActive }) => (isActive ? "active" : "")}>
            논문
          </NavLink>
        </nav>
      </header>

      <main className="page" key={location.pathname}>
        <Routes>
          <Route path="/" element={<ReportsList />} />
          <Route path="/reports/:reportId" element={<ReportDetail />} />
          <Route path="/papers" element={<PapersList />} />
        </Routes>
      </main>
    </div>
  );
}
