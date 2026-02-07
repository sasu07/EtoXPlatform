
import React, { useState, useRef } from 'react';
import api from '../api';
import './SourceUpload.css';

interface SourceUploadProps {
  onUploadSuccess: () => void;
}

type MessageType = 'info' | 'success' | 'error';

const SourceUpload: React.FC<SourceUploadProps> = ({ onUploadSuccess }) => {
  const [file, setFile] = useState<File | null>(null);
  const [name, setName] = useState('');
  const [year, setYear] = useState('');
  const [sourceType, setSourceType] = useState('pdf');
  const [session, setSession] = useState('');
  const [notes, setNotes] = useState('');
  const [jsonImport, setJsonImport] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [messageType, setMessageType] = useState<MessageType>('info');
  const [dragActive, setDragActive] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
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
      if (droppedFile.type === 'application/pdf') {
        setFile(droppedFile);
        setName(droppedFile.name.replace(/\.pdf$/i, ''));
      } else {
        setMessage('Doar fișierele PDF sunt acceptate.');
        setMessageType('error');
      }
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setName(e.target.files[0].name.replace(/\.pdf$/i, ''));
      setMessage('');
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setMessage('Vă rugăm să selectați un fișier PDF.');
      setMessageType('error');
      return;
    }

    setLoading(true);
    setMessage('Încărcare și procesare în curs...');
    setMessageType('info');
    setUploadProgress(0);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('source_name', name);
    formData.append('source_type', sourceType);
    if (year) formData.append('source_year', year);
    if (session) formData.append('source_session', session);
    if (notes) formData.append('source_notes', notes);
    if (jsonImport) formData.append('json_data', jsonImport);

    try {
      const endpoint = jsonImport ? '/upload-with-json/' : '/upload-and-process/';
      const response = await api.post(endpoint, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (progressEvent) => {
          const progress = progressEvent.total
            ? Math.round((progressEvent.loaded * 100) / progressEvent.total)
            : 0;
          setUploadProgress(progress);
        },
      });

      setMessage(`✓ Succes! Sursa a fost creată cu ID: ${response.data.source_id.substring(0, 8)}...`);
      setMessageType('success');
      onUploadSuccess();

      setFile(null);
      setName('');
      setYear('');
      setSession('');
      setNotes('');
      setJsonImport('');
      setSourceType('pdf');
      setUploadProgress(0);
      if (fileInputRef.current) fileInputRef.current.value = '';
    } catch (error: unknown) {
      const axiosError = error as { response?: { data?: { detail?: string } } };
      const errorMsg = axiosError.response?.data?.detail || 'Eroare la încărcarea fișierului.';
      setMessage(`✗ ${errorMsg}`);
      setMessageType('error');
    } finally {
      setLoading(false);
    }
  };

  const removeFile = () => {
    setFile(null);
    setName('');
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div className="upload-card">
      <div className="upload-card-header">
        <div className="upload-card-icon">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="17 8 12 3 7 8" />
            <line x1="12" y1="3" x2="12" y2="15" />
          </svg>
        </div>
        <div>
          <h2 className="upload-card-title">Încarcă Sursă Nouă</h2>
          <p className="upload-card-subtitle">Fișiere PDF pentru procesare Mathpix</p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="upload-form">
        <div
          className={`drop-zone ${dragActive ? 'active' : ''} ${file ? 'has-file' : ''}`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          onClick={() => !file && fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf"
            onChange={handleFileChange}
            disabled={loading}
            className="file-input-hidden"
          />

          {file ? (
            <div className="file-preview">
              <div className="file-icon">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                  <line x1="16" y1="13" x2="8" y2="13" />
                  <line x1="16" y1="17" x2="8" y2="17" />
                  <line x1="10" y1="9" x2="8" y2="9" />
                </svg>
              </div>
              <div className="file-info">
                <span className="file-name">{file.name}</span>
                <span className="file-size">{formatFileSize(file.size)}</span>
              </div>
              <button
                type="button"
                className="file-remove"
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
            <div className="drop-zone-content">
              <div className="drop-zone-icon">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                </svg>
              </div>
              <p className="drop-zone-text">
                <span className="drop-zone-highlight">Click pentru a selecta</span> sau trageți fișierul aici
              </p>
              <p className="drop-zone-hint">Doar fișiere PDF, max. 50MB</p>
            </div>
          )}
        </div>

        <div className="form-group">
          <label className="form-label" htmlFor="name">
            Nume Sursă <span className="required">*</span>
          </label>
          <input
            id="name"
            type="text"
            className="form-input"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="ex: Manual Matematică Clasa X"
            required
            disabled={loading}
          />
        </div>

        <div className="form-row">
          <div className="form-group">
            <label className="form-label" htmlFor="type">Tip Sursă</label>
            <select
              id="type"
              className="form-select"
              value={sourceType}
              onChange={(e) => setSourceType(e.target.value)}
              disabled={loading}
            >
              <option value="pdf">PDF Document</option>
              <option value="oficial">Document Oficial</option>
              <option value="culegere">Culegere</option>
            </select>
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="year">An</label>
            <input
              id="year"
              type="number"
              className="form-input"
              value={year}
              onChange={(e) => setYear(e.target.value)}
              placeholder="2024"
              min="1990"
              max="2100"
              disabled={loading}
            />
          </div>
        </div>

        <div className="form-group">
          <label className="form-label" htmlFor="session">Sesiune</label>
          <input
            id="session"
            type="text"
            className="form-input"
            value={session}
            onChange={(e) => setSession(e.target.value)}
            placeholder="ex: Sesiunea Iunie"
            disabled={loading}
          />
        </div>

        <div className="form-group">
          <label className="form-label" htmlFor="notes">Note adiționale</label>
          <textarea
            id="notes"
            className="form-textarea"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Orice informații suplimentare..."
            rows={3}
            disabled={loading}
          />
        </div>

        <div className="form-group">
          <label className="form-label" htmlFor="json_data">Import Structurat (JSON) - Opțional</label>
          <textarea
            id="json_data"
            className="form-textarea json-input"
            value={jsonImport}
            onChange={(e) => setJsonImport(e.target.value)}
            placeholder='{"exercises": [{"statement_latex": "...", "tags": [...]}]}'
            rows={4}
            disabled={loading}
          />
          <p className="form-hint">Dacă introduceți JSON, OCR-ul va fi sărit și datele din JSON vor fi folosite direct.</p>
        </div>

        {loading && uploadProgress > 0 && (
          <div className="progress-container">
            <div className="progress-bar">
              <div className="progress-fill" style={{ width: `${uploadProgress}%` }}></div>
            </div>
            <span className="progress-text">{uploadProgress}%</span>
          </div>
        )}

        <button
          type="submit"
          className={`submit-button ${loading ? 'loading' : ''}`}
          disabled={loading || !file}
        >
          {loading ? (
            <>
              <svg className="spinner" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 12a9 9 0 1 1-6.219-8.56" />
              </svg>
              Procesare...
            </>
          ) : (
            <>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="17 8 12 3 7 8" />
                <line x1="12" y1="3" x2="12" y2="15" />
              </svg>
              Încarcă & Procesează
            </>
          )}
        </button>

        {message && (
          <div className={`message ${messageType}`}>
            {message}
          </div>
        )}
      </form>
    </div>
  );
};

export default SourceUpload;
