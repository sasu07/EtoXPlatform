import { useState, useEffect } from 'react';
import './VariantBuilder.css';

interface Exercise {
  id: string;
  statement_latex: string;
  statement_text: string;
  points: number;
  item_type: string;
  subject_part: string;
  difficulty: number;
  exam_type: string;
}

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

interface VariantExercise extends Exercise {
  order_index: number;
  section_name?: string;
}

const API_BASE = 'http://localhost:8000';

function VariantBuilder() {
  const [variants, setVariants] = useState<Variant[]>([]);
  const [exercises, setExercises] = useState<Exercise[]>([]);
  const [selectedVariant, setSelectedVariant] = useState<string | null>(null);
  const [variantExercises, setVariantExercises] = useState<VariantExercise[]>([]);
  const [selectedExercises, setSelectedExercises] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(false);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [filterExamType, setFilterExamType] = useState<string>('');

  // Form state for creating new variant
  const [newVariant, setNewVariant] = useState({
    name: '',
    exam_type: 'bacalaureat',
    profile: '',
    year: new Date().getFullYear(),
    session: '',
    duration_minutes: 180,
    instructions: '',
  });

  // Load variants and exercises
  useEffect(() => {
    fetchVariants();
    fetchExercises();
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

  const fetchExercises = async () => {
    try {
      const response = await fetch(`${API_BASE}/exercises/`);
      const data = await response.json();
      setExercises(data);
    } catch (error) {
      console.error('Error fetching exercises:', error);
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

  const handleCreateVariant = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      const response = await fetch(`${API_BASE}/variants/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newVariant),
      });

      if (response.ok) {
        const created = await response.json();
        setVariants([created, ...variants]);
        setSelectedVariant(created.id);
        setShowCreateForm(false);
        setNewVariant({
          name: '',
          exam_type: 'bacalaureat',
          profile: '',
          year: new Date().getFullYear(),
          session: '',
          duration_minutes: 180,
          instructions: '',
        });
        alert('Variantă creată cu succes!');
      } else {
        alert('Eroare la crearea variantei');
      }
    } catch (error) {
      console.error('Error creating variant:', error);
      alert('Eroare la crearea variantei');
    } finally {
      setLoading(false);
    }
  };

  const handleAddExercises = async () => {
    if (!selectedVariant || selectedExercises.size === 0) {
      alert('Selectează o variantă și cel puțin un exercițiu');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/variants/${selectedVariant}/exercises/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(Array.from(selectedExercises)),
      });

      if (response.ok) {
        await fetchVariantExercises(selectedVariant);
        setSelectedExercises(new Set());
        alert('Exerciții adăugate cu succes!');
      } else {
        alert('Eroare la adăugarea exercițiilor');
      }
    } catch (error) {
      console.error('Error adding exercises:', error);
      alert('Eroare la adăugarea exercițiilor');
    } finally {
      setLoading(false);
    }
  };

  const handleRemoveExercise = async (exerciseId: string) => {
    if (!selectedVariant) return;

    setLoading(true);
    try {
      const response = await fetch(
        `${API_BASE}/variants/${selectedVariant}/exercises/${exerciseId}`,
        { method: 'DELETE' }
      );

      if (response.ok) {
        await fetchVariantExercises(selectedVariant);
        alert('Exercițiu șters!');
      } else {
        alert('Eroare la ștergerea exercițiului');
      }
    } catch (error) {
      console.error('Error removing exercise:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleToggleExercise = (exerciseId: string) => {
    const newSelected = new Set(selectedExercises);
    if (newSelected.has(exerciseId)) {
      newSelected.delete(exerciseId);
    } else {
      newSelected.add(exerciseId);
    }
    setSelectedExercises(newSelected);
  };

  const filteredExercises = exercises.filter(ex =>
    !filterExamType || ex.exam_type === filterExamType
  );

  const totalPoints = variantExercises.reduce((sum, ex) => sum + (ex.points || 0), 0);

  return (
    <div className="variant-builder">
      <div className="builder-header">
        <h2>🎯 Creează Subiecte (Variante)</h2>
        <p>Construiește subiecte de test din exercițiile disponibile</p>
      </div>

      <div className="builder-content">
        {/* Left Panel: Variant Selection/Creation */}
        <div className="builder-panel variants-panel">
          <div className="panel-header">
            <h3>Variante</h3>
            <button
              className="btn-create"
              onClick={() => setShowCreateForm(!showCreateForm)}
            >
              {showCreateForm ? '✕ Anulează' : '+ Variantă Nouă'}
            </button>
          </div>

          {showCreateForm && (
            <form onSubmit={handleCreateVariant} className="create-form">
              <input
                type="text"
                placeholder="Nume variantă"
                value={newVariant.name}
                onChange={e => setNewVariant({...newVariant, name: e.target.value})}
                required
              />

              <select
                value={newVariant.exam_type}
                onChange={e => setNewVariant({...newVariant, exam_type: e.target.value})}
              >
                <option value="bacalaureat">Bacalaureat</option>
                <option value="evaluare_nationala">Evaluare Națională</option>
                <option value="simulare">Simulare</option>
                <option value="olimpiada">Olimpiadă</option>
                <option value="alta">Altă</option>
              </select>

              <input
                type="text"
                placeholder="Profil (ex: mate-info)"
                value={newVariant.profile}
                onChange={e => setNewVariant({...newVariant, profile: e.target.value})}
              />

              <input
                type="number"
                placeholder="An"
                value={newVariant.year}
                onChange={e => setNewVariant({...newVariant, year: parseInt(e.target.value)})}
              />

              <input
                type="text"
                placeholder="Sesiune (ex: iunie)"
                value={newVariant.session}
                onChange={e => setNewVariant({...newVariant, session: e.target.value})}
              />

              <input
                type="number"
                placeholder="Durata (minute)"
                value={newVariant.duration_minutes}
                onChange={e => setNewVariant({...newVariant, duration_minutes: parseInt(e.target.value)})}
              />

              <textarea
                placeholder="Instrucțiuni (opțional)"
                value={newVariant.instructions}
                onChange={e => setNewVariant({...newVariant, instructions: e.target.value})}
                rows={3}
              />

              <button type="submit" className="btn-primary" disabled={loading}>
                {loading ? 'Se creează...' : 'Creează Varianta'}
              </button>
            </form>
          )}

          <div className="variants-list">
            {variants.map(variant => (
              <div
                key={variant.id}
                className={`variant-item ${selectedVariant === variant.id ? 'selected' : ''}`}
                onClick={() => setSelectedVariant(variant.id)}
              >
                <div className="variant-name">{variant.name}</div>
                <div className="variant-meta">
                  {variant.exam_type} • {variant.year} • {variant.status}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Middle Panel: Available Exercises */}
        <div className="builder-panel exercises-panel">
          <div className="panel-header">
            <h3>Exerciții Disponibile ({filteredExercises.length})</h3>
            <select
              value={filterExamType}
              onChange={e => setFilterExamType(e.target.value)}
              className="filter-select"
            >
              <option value="">Toate tipurile</option>
              <option value="bacalaureat">Bacalaureat</option>
              <option value="evaluare_nationala">Evaluare Națională</option>
              <option value="simulare">Simulare</option>
              <option value="olimpiada">Olimpiadă</option>
            </select>
          </div>

          <div className="exercises-list">
            {filteredExercises.map(exercise => (
              <div
                key={exercise.id}
                className={`exercise-item ${selectedExercises.has(exercise.id) ? 'selected' : ''}`}
                onClick={() => handleToggleExercise(exercise.id)}
              >
                <div className="exercise-checkbox">
                  <input
                    type="checkbox"
                    checked={selectedExercises.has(exercise.id)}
                    onChange={() => {}}
                  />
                </div>
                <div className="exercise-content">
                  <div className="exercise-text">
                    {exercise.statement_text || exercise.statement_latex.substring(0, 100)}
                  </div>
                  <div className="exercise-meta">
                    {exercise.item_type} • {exercise.subject_part} • {exercise.points || 0}p
                    {exercise.difficulty && ` • Dif: ${exercise.difficulty}/10`}
                  </div>
                </div>
              </div>
            ))}
          </div>

          {selectedVariant && selectedExercises.size > 0 && (
            <button
              className="btn-add-exercises"
              onClick={handleAddExercises}
              disabled={loading}
            >
              ➕ Adaugă {selectedExercises.size} Exerciții la Variantă
            </button>
          )}
        </div>

        {/* Right Panel: Variant Exercises */}
        <div className="builder-panel variant-exercises-panel">
          <div className="panel-header">
            <h3>Exerciții în Variantă</h3>
            {selectedVariant && (
              <span className="total-points">Total: {totalPoints}p</span>
            )}
          </div>

          {!selectedVariant ? (
            <div className="empty-state">
              Selectează o variantă pentru a vedea exercițiile
            </div>
          ) : variantExercises.length === 0 ? (
            <div className="empty-state">
              Niciun exercițiu încă. Adaugă din lista din stânga.
            </div>
          ) : (
            <div className="variant-exercises-list">
              {variantExercises.map((exercise, index) => (
                <div key={exercise.id} className="variant-exercise-item">
                  <div className="exercise-order">{index + 1}.</div>
                  <div className="exercise-content">
                    <div className="exercise-text">
                      {exercise.statement_text || exercise.statement_latex.substring(0, 100)}
                    </div>
                    <div className="exercise-meta">
                      {exercise.item_type} • {exercise.points || 0}p
                    </div>
                  </div>
                  <button
                    className="btn-remove"
                    onClick={() => handleRemoveExercise(exercise.exercise_id)}
                    disabled={loading}
                  >
                    ✕
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default VariantBuilder;
