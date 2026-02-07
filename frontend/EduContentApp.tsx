import { useState, useEffect } from 'react';
import SourceUpload from './components/SourceUpload';
import SourceList from './components/SourceList';
import './App.css';

function App() {
  const [refreshKey, setRefreshKey] = useState(0);
  const [isOnline, setIsOnline] = useState(true);

  const handleUploadSuccess = () => {
    setRefreshKey(prevKey => prevKey + 1);
  };

  // Check backend connection
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
    <div className="app">
      {/* Navigation */}
      <nav className="navbar">
        <div className="navbar-content">
          <div className="navbar-brand">
            <div className="navbar-logo">E</div>
            <div>
              <div className="navbar-title">EduContent</div>
              <div className="navbar-subtitle">Sistem de Gestiune Conținut Educațional</div>
            </div>
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
            <span className="tech-badge">
              <span className="tech-badge-dot postgres"></span>
              PostgreSQL
            </span>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="main-content">
        <header className="page-header">
          <h1 className="page-title">📚 Gestionare Surse Educaționale</h1>
          <p className="page-description">
            Încărcați și gestionați documentele PDF pentru procesare automată
          </p>
        </header>

        <div className="content-grid">
          <aside>
            <SourceUpload onUploadSuccess={handleUploadSuccess} />
          </aside>

          <section>
            <SourceList refreshKey={refreshKey} />
          </section>
        </div>
      </main>

      {/* Footer */}
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
  );
}

export default App;
