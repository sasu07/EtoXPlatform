import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000'; // FastAPI default port

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export interface Source {
  id: string;
  name: string;
  type: string;
  year?: number;
  session?: string;
  url_file_path?: string;
  notes?: string;
  created_at: string;
}

export interface Exercise {
  id: string;
  exam_type: string;
  profile?: string;
  subject_part?: string;
  item_type?: string;
  statement_latex: string;
  statement_text?: string;
  answer_latex?: string;
  solution_latex?: string;
  scoring_guide_latex?: string;
  scoring_guide_text?: string;
  difficulty?: number;
  estimated_time_sec?: number;
  points?: number;
  metadata?: any;
  status: 'DRAFT' | 'REVIEW' | 'READY' | 'ARCHIVED';
  created_at: string;
  updated_at: string;
}

export interface Tag {
  id: string;
  namespace: string;
  key: string;
  label?: string;
  parent_id?: string;
  created_at: string;
}

export const getSources = () => api.get<Source[]>('/sources/');
export const getExercises = (params?: { exam_type?: string, status?: string }) => 
  api.get<Exercise[]>('/exercises/', { params });
export const getExercise = (id: string) => api.get<Exercise>(`/exercises/${id}`);
export const updateExercise = (id: string, data: Partial<Exercise>) => api.put<Exercise>(`/exercises/${id}`, data);
export const deleteExercise = (id: string) => api.delete(`/exercises/${id}`);

export const getTags = (namespace?: string) => api.get<Tag[]>('/tags/', { params: { namespace } });
export const tagExercise = (id: string) => api.post(`/exercises/${id}/tag`);

export default api;
