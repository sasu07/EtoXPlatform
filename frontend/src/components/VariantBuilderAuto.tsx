import { useState, useEffect } from 'react';
import './VariantBuilder.css';

interface Variant {
  id: string;
  name: string;
  exam_type: string;
  profile: string;
  year: number;
  session: string;
  total_points: number;
  duration_minutes: number;
  instructions: string;
  status: string;
  created_at: string;
}

interface VariantExercise {
  id: string;
  exercise_id: string;
  order_index: number;
  section_name?: string;
  statement_latex: string;
  statement_text: string;
  points: number;
  item_type: string;
  subject_part: string;
  difficulty: number;
}

const API_BASE = 'http://localhost:8000';

function VariantBuilderAuto() {
  const [variants, setVariants] = useState<Variant[]>([]);
  const [selectedVariant, setSelectedVariant] = useState<string | null>(null);
  const [variantExercises, setVariantExercises] = useState<VariantExercise[]>([]);
  const [loading, setLoading] = useState(false);
  const [downloadingPdf, setDownloadingPdf] = useState(false);
  const [showCreateForm, setShowCreateForm] = useState(false);

  // Form state for creating new variant
  const [newVariant, setNewVariant] = useState({
    name: '',
    exam_type: 'bacalaureat',
    profile: 'mate-info',
    year: new Date().getFullYear(),
    session: '',
    duration_minutes: 180,
  });
  const [difficultyRange, setDifficultyRange] = useState<[number, number]>([3, 7]);

  // Load variants
  useEffect(() => {
    fetchVariants();
  }, []);

  // Load variant exercises when a variant is selected
  useEffect(() => {
    if (selectedVariant) {
      fetchVariantExercises(selectedVariant);
    }
  }, [selectedVariant]);

  const fetchVariants = async () => {
    try {
      const response = await fetch(`${API_BASE}/variants/`);
      const data = await response.json();
      setVariants(data);
    } catch (error) {
      console.error('Error fetching variants:', error);
    }
  };

  const fetchVariantExercises = async (variantId: string) => {
    try {
      const response = await fetch(`${API_BASE}/variants/${variantId}/exercises/`);
      const data = await response.json();
      setVariantExercises(data);
    } catch (error) {
      console.error('Error fetching variant exercises:', error);
    }
  };

  const handleGenerateVariant = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      const formData = new FormData();
      formData.append('name', newVariant.name);
      formData.append('exam_type', newVariant.exam_type);
      formData.append('profile', newVariant.profile || '');
      formData.append('year', newVariant.year.toString());
      formData.append('session', newVariant.session || '');
      formData.append('difficulty_min', difficultyRange[0].toString());
      formData.append('difficulty_max', difficultyRange[1].toString());
      formData.append('duration_minutes', newVariant.duration_minutes.toString());

      const response = await fetch(`${API_BASE}/variants/generate`, {
        method: 'POST',
        body: formData,
      });

      if (response.ok) {
        const result = await response.json();
        await fetchVariants();
        setSelectedVariant(result.variant_id);
        setShowCreateForm(false);
        setNewVariant({
          name: '',
          exam_type: 'bacalaureat',
          profile: 'mate-info',
          year: new Date().getFullYear(),
          session: '',
          duration_minutes: 180,
        });
        alert(`✅ Variantă generată automat!\n\n${result.exercise_count} exerciții\n${result.total_points} puncte\n\nStructura:\n${result.structure.map((s: any) => `${s.subject}: ${s.exercises} exerciții`).join('\n')}`);
      } else {
        const error = await response.json();
        alert(`Eroare la generarea variantei: ${error.detail}`);
      }
    } catch (error) {
      console.error('Error generating variant:', error);
      alert('Eroare la generarea variantei');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteVariant = async (variantId: string) => {
    if (!confirm('Ștergi această variantă?')) return;

    try {
      const response = await fetch(`${API_BASE}/variants/${variantId}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        await fetchVariants();
        if (selectedVariant === variantId) {
          setSelectedVariant(null);
          setVariantExercises([]);
        }
        alert('Variantă ștearsă!');
      }
    } catch (error) {
      console.error('Error deleting variant:', error);
    }
  };

  const handleDownloadPdf = async (variantId: string) => {
    setDownloadingPdf(true);
    try {
      const response = await fetch(`${API_BASE}/variants/${variantId}/download-pdf`);

      if (!response.ok) {
        const error = await response.json();
        alert(`Eroare la generarea PDF-ului: ${error.detail}`);
        return;
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;

      // Extrage filename din header sau folosește un default
      const contentDisposition = response.headers.get('Content-Disposition');
      let filename = 'varianta.pdf';
      if (contentDisposition) {
        const match = contentDisposition.match(/filename="?(.+?)"?$/);
        if (match) filename = match[1];
      }

      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Error downloading PDF:', error);
      alert('Eroare la descarcarea PDF-ului');
    } finally {
      setDownloadingPdf(false);
    }
  };

  const totalPoints = variantExercises.reduce((sum, ex) => sum + (ex.points || 0), 0);

  // Group exercises by section
  const exercisesBySection = variantExercises.reduce((acc, ex) => {
    const section = ex.section_name || 'Alte exerciții';
    if (!acc[section]) acc[section] = [];
    acc[section].push(ex);
    return acc;
  }, {} as Record<string, VariantExercise[]>);

  return (
    <div className="variant-builder">
      <div className="builder-header">
        <h2>🎯 Generator Automat de Variante</h2>
        <p>Creează subiecte complete automat pe baza dificultății și profilului</p>
      </div>

      <div className="builder-content-auto">
        {/* Left Panel: Variant Selection/Creation */}
        <div className="builder-panel variants-panel">
          <div className="panel-header">
            <h3>Variante Generate</h3>
            <button
              className="btn-create"
              onClick={() => setShowCreateForm(!showCreateForm)}
            >
              {showCreateForm ? '✕ Anulează' : '✨ Generează Nouă'}
            </button>
          </div>

          {showCreateForm && (
            <form onSubmit={handleGenerateVariant} className="create-form">
              <h4 className="form-title">🤖 Generare Automată</h4>

              <input
                type="text"
                placeholder="Nume variantă (ex: Bac 2025 - Simulare 1)"
                value={newVariant.name}
                onChange={e => setNewVariant({...newVariant, name: e.target.value})}
                required
              />

              <select
                value={newVariant.exam_type}
                onChange={e => setNewVariant({...newVariant, exam_type: e.target.value})}
              >
                <option value="bacalaureat">📘 Bacalaureat (S1: 6ex, S2: 2x3var, S3: 2x3var)</option>
                <option value="evaluare_nationala">📗 Evaluare Națională (S1: 6ex, S2: 3ex)</option>
              </select>

              <input
                type="text"
                placeholder="Profil (ex: mate-info, real)"
                value={newVariant.profile}
                onChange={e => setNewVariant({...newVariant, profile: e.target.value})}
              />

              <div className="input-row">
                <input
                  type="number"
                  placeholder="An"
                  value={newVariant.year}
                  onChange={e => setNewVariant({...newVariant, year: parseInt(e.target.value)})}
                  style={{ width: '48%' }}
                />
                <input
                  type="text"
                  placeholder="Sesiune"
                  value={newVariant.session}
                  onChange={e => setNewVariant({...newVariant, session: e.target.value})}
                  style={{ width: '48%' }}
                />
              </div>

              <div className="difficulty-slider">
                <label>Dificultate: {difficultyRange[0]} - {difficultyRange[1]} / 10</label>
                <div className="slider-row">
                  <input
                    type="range"
                    min="1"
                    max="10"
                    value={difficultyRange[0]}
                    onChange={e => setDifficultyRange([parseInt(e.target.value), difficultyRange[1]])}
                    className="range-slider"
                  />
                  <input
                    type="range"
                    min="1"
                    max="10"
                    value={difficultyRange[1]}
                    onChange={e => setDifficultyRange([difficultyRange[0], parseInt(e.target.value)])}
                    className="range-slider"
                  />
                </div>
              </div>

              <input
                type="number"
                placeholder="Durata (minute)"
                value={newVariant.duration_minutes}
                onChange={e => setNewVariant({...newVariant, duration_minutes: parseInt(e.target.value)})}
              />

              <div className="form-info">
                ℹ️ Varianta va fi generată automat respectând structura oficială a examenului
              </div>

              <button type="submit" className="btn-primary" disabled={loading}>
                {loading ? '⏳ Se generează...' : '✨ Generează Variantă Automată'}
              </button>
            </form>
          )}

          <div className="variants-list">
            {variants.map(variant => (
              <div
                key={variant.id}
                className={`variant-item ${selectedVariant === variant.id ? 'selected' : ''}`}
              >
                <div onClick={() => setSelectedVariant(variant.id)}>
                  <div className="variant-name">{variant.name}</div>
                  <div className="variant-meta">
                    {variant.exam_type} • {variant.year} • {variant.total_points}p
                  </div>
                </div>
                <button
                  className="btn-delete-small"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDeleteVariant(variant.id);
                  }}
                  title="Șterge varianta"
                >
                  🗑️
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* Right Panel: Variant Exercises */}
        <div className="builder-panel variant-exercises-panel-large">
          <div className="panel-header">
            <h3>Exercițiile Variantei</h3>
            <div className="panel-header-actions">
              {selectedVariant && variantExercises.length > 0 && (
                <button
                  className="btn-download-pdf"
                  onClick={() => handleDownloadPdf(selectedVariant)}
                  disabled={downloadingPdf}
                  title="Descarca PDF"
                >
                  {downloadingPdf ? 'Se genereaza...' : 'Descarca PDF'}
                </button>
              )}
              {selectedVariant && (
                <span className="total-points">Total: {totalPoints}p</span>
              )}
            </div>
          </div>

          {!selectedVariant ? (
            <div className="empty-state">
              Selectează o variantă pentru a vedea exercițiile generate
            </div>
          ) : variantExercises.length === 0 ? (
            <div className="empty-state">
              Niciun exercițiu încă. Varianta este goală.
            </div>
          ) : (
            <div className="variant-exercises-list">
              {Object.entries(exercisesBySection).map(([section, exercises]) => (
                <div key={section} className="exercise-section">
                  <h4 className="section-title">{section}</h4>
                  {exercises.map((exercise, index) => (
                    <div key={exercise.id} className="variant-exercise-item">
                      <div className="exercise-order">{exercise.order_index + 1}.</div>
                      <div className="exercise-content">
                        <div className="exercise-text">
                          {exercise.statement_text || exercise.statement_latex.substring(0, 150)}
                        </div>
                        <div className="exercise-meta">
                          {exercise.item_type} • {exercise.subject_part} • {exercise.points || 0}p
                          {exercise.difficulty && ` • Dif: ${exercise.difficulty}/10`}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default VariantBuilderAuto;
