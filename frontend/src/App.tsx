import { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, NavLink } from 'react-router-dom';
import SourceUpload from './components/SourceUpload';
import SourceList from './components/SourceList';
import ExerciseList from './components/ExerciseList';
import ExerciseEditor from './components/ExerciseEditor';
import JSONImport from './components/JSONImport';
import VariantBuilderAuto from './components/VariantBuilderAuto';
import './App.css';

function Home({ refreshKey, onUploadSuccess }: { refreshKey: number, onUploadSuccess: () => void }) {
  return (
    <>
      <header className="page-header">
        <h1 className="page-title">📚 Gestionare Surse Educaționale</h1>
        <p className="page-description">
          Încărcați și gestionați documentele PDF pentru procesare automată
        </p>
      </header>

      <div className="content-grid">
        <aside>
          <SourceUpload onUploadSuccess={onUploadSuccess} />
        </aside>

        <section>
          <SourceList refreshKey={refreshKey} />
        </section>
      </div>
    </>
  );
}

function ImportPage({ refreshKey, onImportSuccess }: { refreshKey: number, onImportSuccess: () => void }) {
  return (
    <>
      <header className="page-header">
        <h1 className="page-title">📥 Import JSON Pre-procesat</h1>
        <p className="page-description">
          Încărcați fișiere JSON cu exerciții deja procesate (LaTeX + tag-uri)
        </p>
      </header>

      <div className="content-grid single-column">
        <JSONImport onImportSuccess={onImportSuccess} />
      </div>
    </>
  );
}

function App() {
  const [refreshKey, setRefreshKey] = useState(0);
  const [isOnline, setIsOnline] = useState(true);

  const handleUploadSuccess = () => {
    setRefreshKey(prevKey => prevKey + 1);
  };

  useEffect(() => {
    const checkConnection = async () => {
      try {
        const response = await fetch('http://localhost:8000/');
        setIsOnline(response.ok);
      } catch {
        setIsOnline(false);
      }
    };

    checkConnection();
    const interval = setInterval(checkConnection, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <Router>
      <div className="app">
        <nav className="navbar">
          <div className="navbar-content">
            <Link to="/" className="navbar-brand">
              <div className="navbar-logo">E</div>
              <div>
                <div className="navbar-title">EduContent</div>
                <div className="navbar-subtitle">Sistem de Gestiune Conținut Educațional</div>
              </div>
            </Link>

            <div className="navbar-links">
              <NavLink to="/" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
                Surse
              </NavLink>
              <NavLink to="/import" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
                Import JSON
              </NavLink>
              <NavLink to="/exercises" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
                Exerciții
              </NavLink>
              <NavLink to="/variants" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
                Subiecte
              </NavLink>
            </div>

            <div className="navbar-badges">
              <span className="tech-badge">
                <span className="tech-badge-dot fastapi"></span>
                FastAPI
              </span>
              <span className="tech-badge">
                <span className="tech-badge-dot react"></span>
                React
              </span>
            </div>
          </div>
        </nav>

        <main className="main-content">
          <Routes>
            <Route path="/" element={<Home refreshKey={refreshKey} onUploadSuccess={handleUploadSuccess} />} />
            <Route path="/import" element={<ImportPage refreshKey={refreshKey} onImportSuccess={handleUploadSuccess} />} />
            <Route path="/exercises" element={<ExerciseList refreshKey={refreshKey} />} />
            <Route path="/exercises/:id" element={<ExerciseEditor />} />
            <Route path="/variants" element={<VariantBuilderAuto />} />
          </Routes>
        </main>

        <footer className="footer">
          <div className="footer-content">
            <div className="footer-status">
              <span className={`status-indicator ${isOnline ? '' : 'offline'}`}></span>
              <span>
                Server: {isOnline ? 'Conectat' : 'Deconectat'} • localhost:8000
              </span>
            </div>
            <div>
              © 2026 EduContent • Toate drepturile rezervate
            </div>
          </div>
        </footer>
      </div>
    </Router>
  );
}

export default App;
