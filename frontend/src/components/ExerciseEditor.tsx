import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getExercise, updateExercise, tagExercise, type Exercise } from '../api';
import 'katex/dist/katex.min.css';
import { BlockMath, InlineMath } from 'react-katex';
import { Save, ArrowLeft, Tag as TagIcon, Check, AlertCircle, CheckCircle } from 'lucide-react';
import './ExerciseEditor.css';

const ExerciseEditor: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [exercise, setExercise] = useState<Exercise | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Form state
  const [statement, setStatement] = useState('');
  const [solution, setSolution] = useState('');
  const [scoringGuide, setScoringGuide] = useState('');
  const [status, setStatus] = useState<Exercise['status']>('DRAFT');

  useEffect(() => {
    const fetchExercise = async () => {
      if (!id) return;
      try {
        const response = await getExercise(id);
        const data = response.data;
        setExercise(data);
        setStatement(data.statement_latex);
        setSolution(data.solution_latex || '');
        setScoringGuide(data.scoring_guide_latex || '');
        setStatus(data.status);
      } catch (err) {
        setError('Eroare la încărcarea exercițiului');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchExercise();
  }, [id]);

  const handleSave = async () => {
    if (!id) return;
    setSaving(true);
    try {
      await updateExercise(id, {
        statement_latex: statement,
        solution_latex: solution,
        scoring_guide_latex: scoringGuide,
        status: status
      });
      alert('Modificări salvate cu succes!');
    } catch (err) {
      console.error('Error saving exercise:', err);
      alert('Eroare la salvarea exercițiului');
    } finally {
      setSaving(false);
    }
  };

  const handleAutoTag = async () => {
    if (!id) return;
    try {
      await tagExercise(id);
      // Refresh exercise data to see new tags (if we were displaying them)
      const response = await getExercise(id);
      setExercise(response.data);
      alert('Tag-uri AI regenerate!');
    } catch (err) {
      console.error('Error tagging:', err);
      alert('Eroare la generarea tag-urilor');
    }
  };

  const handleWorkflowTransition = async (newStatus: Exercise['status']) => {
    if (!id) return;
    setSaving(true);
    try {
      await updateExercise(id, {
        statement_latex: statement,
        solution_latex: solution,
        scoring_guide_latex: scoringGuide,
        status: newStatus
      });
      setStatus(newStatus);
      alert(`Status actualizat la ${newStatus}`);
    } catch (err) {
      console.error('Error during workflow transition:', err);
      alert('Eroare la actualizarea statusului');
    } finally {
      setSaving(false);
    }
  };

  const handleStatusChange = (newStatus: Exercise['status']) => {
    setStatus(newStatus);
  };

  const renderContent = (text: string) => {
    if (!text) return null;
    
    // Split by block math first $$ ... $$
    const blockParts = text.split(/(\$\$.*?\$\$)/gs);
    
    return blockParts.map((blockPart, index) => {
      if (blockPart.startsWith('$$') && blockPart.endsWith('$$')) {
        const math = blockPart.slice(2, -2).trim();
        return <BlockMath key={`block-${index}`} math={math || '\\text{?}'} />;
      }
      
      // Then split by inline math $ ... $
      const inlineParts = blockPart.split(/(\$.*?\$)/gs);
      return inlineParts.map((inlinePart, i) => {
        if (inlinePart.startsWith('$') && inlinePart.endsWith('$')) {
          const math = inlinePart.slice(1, -1).trim();
          return <InlineMath key={`inline-${index}-${i}`} math={math || '\\text{?}'} />;
        }
        // Handle newlines by splitting and adding <br />
        const textParts = inlinePart.split('\n');
        return textParts.map((t, j) => (
          <React.Fragment key={`text-${index}-${i}-${j}`}>
            {t}
            {j < textParts.length - 1 && <br />}
          </React.Fragment>
        ));
      });
    });
  };

  if (loading) return <div className="loading-spinner">Se încarcă editorul...</div>;
  if (error || !exercise) return <div className="error-message">{error || 'Exercițiul nu a fost găsit'}</div>;

  return (
    <div className="editor-container">
      <div className="editor-header">
        <button onClick={() => navigate(-1)} className="btn-back">
          <ArrowLeft size={20} /> Înapoi
        </button>
        <div className="header-actions">
          {status === 'DRAFT' && (
            <button onClick={() => handleWorkflowTransition('REVIEW')} className="btn-workflow review">
              <CheckCircle size={18} /> Trimite la Revizuire
            </button>
          )}
          {status === 'REVIEW' && (
            <button onClick={() => handleWorkflowTransition('READY')} className="btn-workflow ready">
              <Check size={18} /> Aprobă (READY)
            </button>
          )}
          <button onClick={handleAutoTag} className="btn-secondary">
            <TagIcon size={18} /> Tag AI
          </button>
          <button onClick={handleSave} className="btn-primary" disabled={saving}>
            <Save size={18} /> {saving ? 'Se salvează...' : 'Salvează'}
          </button>
        </div>
      </div>

      <div className="editor-layout">
        <div className="editor-form">
          <section className="form-section">
            <label>Enunț (LaTeX)</label>
            <textarea 
              value={statement} 
              onChange={(e) => setStatement(e.target.value)}
              rows={6}
            />
          </section>

          <section className="form-section">
            <label>Soluție (LaTeX)</label>
            <textarea 
              value={solution} 
              onChange={(e) => setSolution(e.target.value)}
              rows={8}
            />
          </section>

          <section className="form-section">
            <label>Barem / Ghid de punctare (LaTeX)</label>
            <textarea 
              value={scoringGuide} 
              onChange={(e) => setScoringGuide(e.target.value)}
              rows={4}
            />
          </section>

          <section className="form-section">
            <label>Status</label>
            <div className="status-selector">
              {(['DRAFT', 'REVIEW', 'READY', 'ARCHIVED'] as const).map((s) => (
                <button
                  key={s}
                  onClick={() => handleStatusChange(s)}
                  className={`status-btn ${status === s ? 'active' : ''} ${s.toLowerCase()}`}
                >
                  {status === s && <Check size={14} />} {s}
                </button>
              ))}
            </div>
          </section>
        </div>

        <div className="editor-preview">
          <div className="preview-sticky">
            <h3>👁️ Previzualizare Live</h3>
            <div className="preview-content">
              <h4>Enunț:</h4>
              <div className="rendered-math">
                {renderContent(statement || '\\text{Enunț gol}')}
              </div>

              {solution && (
                <>
                  <h4>Soluție:</h4>
                  <div className="rendered-math">
                    {renderContent(solution)}
                  </div>
                </>
              )}

              {scoringGuide && (
                <>
                  <h4>Barem:</h4>
                  <div className="rendered-math">
                    {renderContent(scoringGuide)}
                  </div>
                </>
              )}
            </div>
            
            <div className="help-box">
              <AlertCircle size={16} />
              <p>Folosiți sintaxa standard LaTeX. Formulele vor fi randate automat în panoul din dreapta.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ExerciseEditor;
