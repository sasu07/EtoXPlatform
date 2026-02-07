import React, { useState, useEffect } from 'react';
import { getExercises, type Exercise, tagExercise } from '../api';
import { Edit2, Tag, BookOpen, ChevronRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import './ExerciseList.css';

interface ExerciseListProps {
  refreshKey?: number;
}

const ExerciseList: React.FC<ExerciseListProps> = ({ refreshKey }) => {
  const [exercises, setExercises] = useState<Exercise[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchExercises = async () => {
    setLoading(true);
    try {
      const response = await getExercises();
      setExercises(Array.isArray(response.data) ? response.data : []);
      setError(null);
    } catch (err) {
      setError('Eroare la încărcarea exercițiilor');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchExercises();
  }, [refreshKey]);

  const handleAutoTag = async (id: string) => {
    try {
      await tagExercise(id);
      fetchExercises();
      alert('Tag-uri AI aplicate cu succes!');
    } catch (err) {
      console.error('Error auto-tagging:', err);
      alert('Eroare la aplicarea tag-urilor AI');
    }
  };

  const getStatusBadgeClass = (status: string) => {
    switch (status) {
      case 'READY': return 'badge-success';
      case 'DRAFT': return 'badge-warning';
      case 'ARCHIVED': return 'badge-danger';
      default: return 'badge-secondary';
    }
  };

  if (loading && exercises.length === 0) return <div className="loading-spinner">Se încarcă exercițiile...</div>;

  return (
    <div className="exercise-list-container">
      <div className="list-header">
        <h2>📝 Listă Exerciții</h2>
        <button onClick={fetchExercises} className="btn-refresh">Actualizează</button>
      </div>

      {error && <div className="error-message">{error}</div>}

      <div className="exercise-grid">
        {!Array.isArray(exercises) || exercises.length === 0 ? (
          <div className="empty-state">Nu s-au găsit exerciții.</div>
        ) : (
          exercises.map((exercise) => (
            <div key={exercise.id} className="exercise-card">
              <div className="exercise-card-header">
                <span className={`status-badge ${getStatusBadgeClass(exercise.status)}`}>
                  {exercise.status}
                </span>
                <span className="exam-type-tag">{exercise.exam_type}</span>
              </div>
              
              <div className="exercise-content-preview">
                <p className="statement-preview">
                  {exercise.statement_text || exercise.statement_latex.substring(0, 150) + '...'}
                </p>
              </div>

              <div className="exercise-meta">
                {exercise.subject_part && (
                  <span className="meta-item">
                    <BookOpen size={14} /> {exercise.subject_part}
                  </span>
                )}
                {exercise.difficulty && (
                  <span className="meta-item">
                    Dificultate: {exercise.difficulty}/10
                  </span>
                )}
              </div>

              <div className="exercise-actions">
                <Link to={`/exercises/${exercise.id}`} className="btn-action btn-edit" title="Editează">
                  <Edit2 size={18} />
                </Link>
                <button 
                  onClick={() => handleAutoTag(exercise.id)} 
                  className="btn-action btn-tag" 
                  title="Tag AI"
                >
                  <Tag size={18} />
                </button>
                <Link to={`/exercises/${exercise.id}`} className="btn-view-more">
                  Detalii <ChevronRight size={16} />
                </Link>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default ExerciseList;
