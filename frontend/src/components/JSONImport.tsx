import React, { useState, useRef } from 'react';
import api from '../api';
import './JSONImport.css';

interface JSONImportProps {
  onImportSuccess: () => void;
}

type MessageType = 'info' | 'success' | 'error';

interface ImportStatistics {
  sources: number;
  segments: number;
  tags: number;
  exercises: number;
  exercise_tags: number;
  exercise_source_segments: number;
}

const JSONImport: React.FC<JSONImportProps> = ({ onImportSuccess }) => {
  const [jsonFile, setJsonFile] = useState<File | null>(null);
  const [includeContainers, setIncludeContainers] = useState(false);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [messageType, setMessageType] = useState<MessageType>('info');
  const [dragActive, setDragActive] = useState(false);
  const [statistics, setStatistics] = useState<ImportStatistics | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile.type === 'application/json' || droppedFile.name.endsWith('.json')) {
        setJsonFile(droppedFile);
        setMessage('');
        setStatistics(null);
      } else {
        setMessage('Doar fișiere JSON sunt acceptate.');
        setMessageType('error');
      }
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setJsonFile(e.target.files[0]);
      setMessage('');
      setStatistics(null);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!jsonFile) {
      setMessage('Vă rugăm să selectați un fișier JSON.');
      setMessageType('error');
      return;
    }

    setLoading(true);
    setMessage('Import în curs...');
    setMessageType('info');
    setStatistics(null);

    const formData = new FormData();
    formData.append('json_file', jsonFile);
    formData.append('include_containers', includeContainers.toString());

    try {
      const response = await api.post('/import-json/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      setMessage(`✓ ${response.data.message}`);
      setMessageType('success');
      setStatistics(response.data.statistics);
      onImportSuccess();

      // Clear form
      setJsonFile(null);
      setIncludeContainers(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    } catch (error: unknown) {
      const axiosError = error as { response?: { data?: { detail?: string } } };
      const errorMsg = axiosError.response?.data?.detail || 'Eroare la importul JSON.';
      setMessage(`✗ ${errorMsg}`);
      setMessageType('error');
    } finally {
      setLoading(false);
    }
  };

  const removeFile = () => {
    setJsonFile(null);
    setStatistics(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div className="json-import-card">
      <div className="json-import-header">
        <div className="json-import-icon">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
            <path d="M10 9h4M10 13h4M10 17h2" />
          </svg>
        </div>
        <div>
          <h2 className="json-import-title">Import JSON Pre-procesat</h2>
          <p className="json-import-subtitle">
            Încarcă direct exerciții procesate (bypass OCR & AI)
          </p>
        </div>
      </div>

      <div className="json-import-info">
        <h3>Când să folosești acest import?</h3>
        <ul>
          <li>✓ Ai deja exercițiile convertite în LaTeX</li>
          <li>✓ Tag-urile sunt deja aplicate</li>
          <li>✓ Vrei să skipezi procesarea automată (OCR + AI)</li>
          <li>✓ Ai exportat și modificat un JSON existent</li>
        </ul>
      </div>

      <form onSubmit={handleSubmit} className="json-import-form">
        <div
          className={`json-drop-zone ${dragActive ? 'active' : ''} ${jsonFile ? 'has-file' : ''}`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          onClick={() => !jsonFile && fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".json,application/json"
            onChange={handleFileChange}
            disabled={loading}
            className="file-input-hidden"
          />

          {jsonFile ? (
            <div className="json-file-preview">
              <div className="json-file-icon">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                  <text x="8" y="16" fontSize="8" fill="currentColor">JSON</text>
                </svg>
              </div>
              <div className="json-file-info">
                <span className="json-file-name">{jsonFile.name}</span>
                <span className="json-file-size">{formatFileSize(jsonFile.size)}</span>
              </div>
              <button
                type="button"
                className="json-file-remove"
                onClick={(e) => {
                  e.stopPropagation();
                  removeFile();
                }}
                disabled={loading}
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </div>
          ) : (
            <div className="json-drop-content">
              <div className="json-drop-icon">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                  <path d="M10 12h4M12 10v4" />
                </svg>
              </div>
              <p className="json-drop-text">
                <span className="json-drop-highlight">Click pentru a selecta JSON</span> sau trageți fișierul
              </p>
              <p className="json-drop-hint">
                Format: <code>{'{ "source": {...}, "tag_catalog": [...], "exercises": [...] }'}</code>
              </p>
            </div>
          )}
        </div>

        <div className="json-options">
          <label className="json-checkbox-label">
            <input
              type="checkbox"
              checked={includeContainers}
              onChange={(e) => setIncludeContainers(e.target.checked)}
              disabled={loading}
              className="json-checkbox"
            />
            <span className="json-checkbox-text">
              Include exerciții container (points = 0)
            </span>
            <span className="json-checkbox-hint">
              Problemele mari care conțin subprobleme
            </span>
          </label>
        </div>

        <button
          type="submit"
          className={`json-submit-button ${loading ? 'loading' : ''}`}
          disabled={loading || !jsonFile}
        >
          {loading ? (
            <>
              <svg className="json-spinner" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 12a9 9 0 1 1-6.219-8.56" />
              </svg>
              Importare în curs...
            </>
          ) : (
            <>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="7 10 12 15 17 10" />
                <line x1="12" y1="15" x2="12" y2="3" />
              </svg>
              Importă JSON
            </>
          )}
        </button>

        {message && (
          <div className={`json-message ${messageType}`}>
            {messageType === 'success' && (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                <polyline points="22 4 12 14.01 9 11.01" />
              </svg>
            )}
            {messageType === 'error' && (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <line x1="15" y1="9" x2="9" y2="15" />
                <line x1="9" y1="9" x2="15" y2="15" />
              </svg>
            )}
            {message}
          </div>
        )}

        {statistics && (
          <div className="json-statistics">
            <h3>Statistici Import</h3>
            <div className="json-stats-grid">
              <div className="json-stat-item">
                <span className="json-stat-value">{statistics.sources}</span>
                <span className="json-stat-label">Surse</span>
              </div>
              <div className="json-stat-item">
                <span className="json-stat-value">{statistics.exercises}</span>
                <span className="json-stat-label">Exerciții</span>
              </div>
              <div className="json-stat-item">
                <span className="json-stat-value">{statistics.tags}</span>
                <span className="json-stat-label">Tag-uri Noi</span>
              </div>
              <div className="json-stat-item">
                <span className="json-stat-value">{statistics.segments}</span>
                <span className="json-stat-label">Segmente</span>
              </div>
              <div className="json-stat-item">
                <span className="json-stat-value">{statistics.exercise_tags}</span>
                <span className="json-stat-label">Legături Tag-uri</span>
              </div>
              <div className="json-stat-item">
                <span className="json-stat-value">{statistics.exercise_source_segments}</span>
                <span className="json-stat-label">Legături Segmente</span>
              </div>
            </div>
          </div>
        )}
      </form>

      <div className="json-import-help">
        <h4>Format JSON așteptat:</h4>
        <pre className="json-code-example">
{`{
  "source": {
    "external_id": "bac-2025-mate-info-var-09",
    "name": "Bacalaureat 2025 – Matematică",
    "type": "BAC",
    "year": 2025,
    "profile": "M_mate-info",
    "page_count": 2
  },
  "tag_catalog": [
    { "namespace": "exam", "key": "bacalaureat", "label": "Bacalaureat" }
  ],
  "exercises": [
    {
      "external_id": "B2025-MI-V09-S1-1",
      "points": 5,
      "difficulty": 1,
      "statement_latex": "...",
      "source_ref": { "page_start": 1, "page_end": 1 },
      "tags": [...]
    }
  ]
}`}
        </pre>
      </div>
    </div>
  );
};

export default JSONImport;
