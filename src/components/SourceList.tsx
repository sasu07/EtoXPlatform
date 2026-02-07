
import React, { useEffect, useState } from 'react';
import api from '../api';
import './SourceList.css';

interface Source {
  id: string;
  name: string;
  type: string;
  year: number | null;
  session: string | null;
  created_at: string;
  notes?: string | null;
}

interface SourceListProps {
  refreshKey: number;
}

type SortField = 'name' | 'type' | 'year' | 'created_at';
type SortOrder = 'asc' | 'desc';

const SourceList: React.FC<SourceListProps> = ({ refreshKey }) => {
  const [sources, setSources] = useState<Source[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [sortField, setSortField] = useState<SortField>('created_at');
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc');
  const [selectedType, setSelectedType] = useState<string>('all');

  useEffect(() => {
    const fetchSources = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await api.get<Source[]>('/sources/');
        setSources(Array.isArray(response.data) ? response.data : []);
      } catch (err) {
        setError('Eroare la preluarea surselor. Verificați conexiunea la server.');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchSources();
  }, [refreshKey]);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortOrder('asc');
    }
  };

  const filteredAndSortedSources = Array.isArray(sources) 
    ? sources
      .filter((source) => {
        const matchesSearch = source.name.toLowerCase().includes(searchTerm.toLowerCase());
        const matchesType = selectedType === 'all' || source.type === selectedType;
        return matchesSearch && matchesType;
      })
      .sort((a, b) => {
        let comparison = 0;
        switch (sortField) {
          case 'name':
            comparison = a.name.localeCompare(b.name);
            break;
          case 'type':
            comparison = a.type.localeCompare(b.type);
            break;
          case 'year':
            comparison = (a.year || 0) - (b.year || 0);
            break;
          case 'created_at':
            comparison = new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
            break;
        }
        return sortOrder === 'asc' ? comparison : -comparison;
      })
    : [];

  const uniqueTypes = Array.isArray(sources) ? [...new Set(sources.map((s) => s.type))] : [];

  const getTypeColor = (type: string) => {
    switch (type.toLowerCase()) {
      case 'pdf': return 'type-pdf';
      case 'oficial': return 'type-oficial';
      case 'culegere': return 'type-culegere';
      default: return 'type-default';
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));

    if (days === 0) return 'Azi';
    if (days === 1) return 'Ieri';
    if (days < 7) return `Acum ${days} zile`;

    return date.toLocaleDateString('ro-RO', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    });
  };

  if (loading) {
    return (
      <div className="source-list-card">
        <div className="loading-state">
          <div className="loading-spinner">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 12a9 9 0 1 1-6.219-8.56" />
            </svg>
          </div>
          <p>Se încarcă sursele...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="source-list-card">
        <div className="error-state">
          <div className="error-icon">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
          </div>
          <h3>Eroare de conexiune</h3>
          <p>{error}</p>
          <button className="retry-button" onClick={() => window.location.reload()}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="23 4 23 10 17 10" />
              <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
            </svg>
            Reîncearcă
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="source-list-card">
      <div className="source-list-header">
        <div className="header-title">
          <h2>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
            </svg>
            Surse Existente
          </h2>
          <span className="source-count">{sources.length} total</span>
        </div>

        <div className="filters">
          <div className="search-box">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="11" cy="11" r="8" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
            <input
              type="text"
              placeholder="Caută surse..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>

          <select
            className="type-filter"
            value={selectedType}
            onChange={(e) => setSelectedType(e.target.value)}
          >
            <option value="all">Toate tipurile</option>
            {uniqueTypes.map((type) => (
              <option key={type} value={type}>
                {type.charAt(0).toUpperCase() + type.slice(1)}
              </option>
            ))}
          </select>
        </div>
      </div>

      {filteredAndSortedSources.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">
            <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1">
              <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z" />
              <polyline points="13 2 13 9 20 9" />
            </svg>
          </div>
          <h3>
            {searchTerm || selectedType !== 'all'
              ? 'Niciun rezultat găsit'
              : 'Nu există surse încă'}
          </h3>
          <p>
            {searchTerm || selectedType !== 'all'
              ? 'Încercați să modificați criteriile de căutare'
              : 'Încărcați primul document PDF pentru a începe'}
          </p>
        </div>
      ) : (
        <div className="table-container">
          <table className="source-table">
            <thead>
              <tr>
                <th onClick={() => handleSort('name')} className="sortable">
                  <span>Nume</span>
                  {sortField === 'name' && (
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      {sortOrder === 'asc' ? <polyline points="18 15 12 9 6 15" /> : <polyline points="6 9 12 15 18 9" />}
                    </svg>
                  )}
                </th>
                <th onClick={() => handleSort('type')} className="sortable">
                  <span>Tip</span>
                </th>
                <th onClick={() => handleSort('year')} className="sortable">
                  <span>An</span>
                </th>
                <th onClick={() => handleSort('created_at')} className="sortable">
                  <span>Creat</span>
                </th>
                <th>Acțiuni</th>
              </tr>
            </thead>
            <tbody>
              {filteredAndSortedSources.map((source, index) => (
                <tr key={source.id} style={{ animationDelay: `${index * 50}ms` }}>
                  <td>
                    <div className="source-name">
                      <div className="source-avatar">
                        {source.name.charAt(0).toUpperCase()}
                      </div>
                      <div className="source-name-text">
                        <span className="name-primary">{source.name}</span>
                        <span className="name-secondary">ID: {source.id.substring(0, 8)}...</span>
                      </div>
                    </div>
                  </td>
                  <td>
                    <span className={`type-badge ${getTypeColor(source.type)}`}>
                      {source.type}
                    </span>
                  </td>
                  <td>
                    <span className="year-text">{source.year || '—'}</span>
                  </td>
                  <td>
                    <span className="date-text">{formatDate(source.created_at)}</span>
                  </td>
                  <td>
                    <div className="action-buttons">
                      <button className="action-btn view" title="Vizualizare">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                          <circle cx="12" cy="12" r="3" />
                        </svg>
                      </button>
                      <button className="action-btn edit" title="Editare">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                          <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
                        </svg>
                      </button>
                      <button className="action-btn delete" title="Ștergere">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <polyline points="3 6 5 6 21 6" />
                          <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                        </svg>
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {filteredAndSortedSources.length > 0 && (
        <div className="table-footer">
          <span>
            Afișate {filteredAndSortedSources.length} din {sources.length} surse
          </span>
        </div>
      )}
    </div>
  );
};

export default SourceList;
