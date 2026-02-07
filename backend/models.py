from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import uuid


# --- ENUM-like types (for Pydantic validation) ---
class SourceType(str, Enum):
    PDF = "pdf"
    OFICIAL = "oficial"
    CULEGERE = "culegere"


class ExamType(str, Enum):
    BACALAUREAT = "bacalaureat"
    EVALUARE_NATIONALA = "evaluare_nationala"
    SIMULARE = "simulare"
    OLIMPIADA = "olimpiada"
    ALTA = "alta"


class SubjectPart(str, Enum):
    ALGEBRA = "algebra"
    GEOMETRIE = "geometrie"
    ANALIZA = "analiza"
    TRIGONOMETRIE = "trigonometrie"
    PROBABILITATI = "probabilitati"
    COMBINATORICA = "combinatorica"
    TEORIA_NUMERELOR = "teoria_numerelor"


class ItemType(str, Enum):
    SUBIECT_1 = "subiect_1"
    SUBIECT_2 = "subiect_2"
    SUBIECT_3 = "subiect_3"
    PROBLEMA = "problema"
    EXERCITIU = "exercitiu"


class ExerciseStatus(str, Enum):
    DRAFT = "DRAFT"
    REVIEW = "REVIEW"
    READY = "READY"
    ARCHIVED = "ARCHIVED"


class SegmentStatus(str, Enum):
    EXTRACTED = "EXTRACTED"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"


class ExtractionMethod(str, Enum):
    MANUAL = "MANUAL"
    PIX2TEXT = "pix2text"
    MATHPIX = "mathpix"
    OTHER = "other"


class AssetType(str, Enum):
    IMAGE = "image"
    DIAGRAM = "diagram"
    GRAPH = "graph"
    TABLE = "table"


# --- Base Models ---

class SourceBase(BaseModel):
    name: str = Field(..., max_length=255)
    type: SourceType
    year: Optional[int] = None
    session: Optional[str] = Field(None, max_length=50)
    url_file_path: Optional[str] = Field(None, max_length=512)
    notes: Optional[str] = None


class SourceCreate(SourceBase):
    pass


class SourceUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    type: Optional[SourceType] = None
    year: Optional[int] = None
    session: Optional[str] = Field(None, max_length=50)
    url_file_path: Optional[str] = Field(None, max_length=512)
    notes: Optional[str] = None


class SourceDB(SourceBase):
    id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            uuid.UUID: str,
            datetime: lambda dt: dt.isoformat()
        }


# --- Source Segments Models ---

class SourceSegmentBase(BaseModel):
    source_id: uuid.UUID
    page_start: int
    page_end: int
    raw_extraction: Optional[str] = None
    checksum: Optional[str] = Field(None, max_length=64)
    status: SegmentStatus = SegmentStatus.EXTRACTED
    extraction_method: ExtractionMethod


class SourceSegmentCreate(SourceSegmentBase):
    pass


class SourceSegmentUpdate(BaseModel):
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    raw_extraction: Optional[str] = None
    checksum: Optional[str] = None
    status: Optional[SegmentStatus] = None
    extraction_method: Optional[ExtractionMethod] = None


class SourceSegmentDB(SourceSegmentBase):
    id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            uuid.UUID: str,
            datetime: lambda dt: dt.isoformat()
        }


# --- Exercise Models ---

class ExerciseBase(BaseModel):
    exam_type: ExamType
    profile: Optional[str] = Field(None, max_length=50)
    subject_part: Optional[SubjectPart] = None
    item_type: Optional[ItemType] = None
    statement_latex: str
    statement_text: Optional[str] = None
    answer_latex: Optional[str] = None
    solution_latex: Optional[str] = None
    scoring_guide_latex: Optional[str] = None
    scoring_guide_text: Optional[str] = None
    difficulty: Optional[int] = Field(None, ge=1, le=10)
    estimated_time_sec: Optional[int] = None
    points: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
    status: ExerciseStatus = ExerciseStatus.DRAFT
    created_by_user_id: Optional[uuid.UUID] = None


class ExerciseCreate(ExerciseBase):
    pass


class ExerciseUpdate(BaseModel):
    exam_type: Optional[ExamType] = None
    profile: Optional[str] = None
    subject_part: Optional[SubjectPart] = None
    item_type: Optional[ItemType] = None
    statement_latex: Optional[str] = None
    statement_text: Optional[str] = None
    answer_latex: Optional[str] = None
    solution_latex: Optional[str] = None
    scoring_guide_latex: Optional[str] = None
    scoring_guide_text: Optional[str] = None
    difficulty: Optional[int] = Field(None, ge=1, le=10)
    estimated_time_sec: Optional[int] = None
    points: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
    status: Optional[ExerciseStatus] = None


class ExerciseDB(ExerciseBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            uuid.UUID: str,
            datetime: lambda dt: dt.isoformat()
        }


# --- Asset Models ---

class AssetBase(BaseModel):
    exercise_id: uuid.UUID
    type: AssetType
    file_path: str = Field(..., max_length=512)
    caption: Optional[str] = None
    latex_ref: Optional[str] = Field(None, max_length=255)


class AssetCreate(AssetBase):
    pass


class AssetDB(AssetBase):
    id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            uuid.UUID: str,
            datetime: lambda dt: dt.isoformat()
        }


# --- Segment Region Models ---

class SegmentRegionBase(BaseModel):
    source_segment_id: uuid.UUID
    page_number: int
    bbox: Dict[str, Any]  # JSON object with bounding box coordinates


class SegmentRegionCreate(SegmentRegionBase):
    pass


class SegmentRegionDB(SegmentRegionBase):
    id: uuid.UUID

    class Config:
        from_attributes = True
        json_encoders = {
            uuid.UUID: str
        }


# --- Exercise Source Segment (many-to-many) Models ---

class ExerciseSourceSegmentBase(BaseModel):
    exercise_id: uuid.UUID
    source_segment_id: uuid.UUID
    role: Optional[str] = Field(None, max_length=50)


class ExerciseSourceSegmentCreate(ExerciseSourceSegmentBase):
    pass


# --- Tag Models ---

class TagBase(BaseModel):
    namespace: str = Field(..., max_length=255)
    key: str = Field(..., max_length=255)
    label: Optional[str] = Field(None, max_length=255)
    parent_id: Optional[uuid.UUID] = None


class TagCreate(TagBase):
    pass


class TagDB(TagBase):
    id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            uuid.UUID: str,
            datetime: lambda dt: dt.isoformat()
        }


# --- Exercise Tag Models ---

class ExerciseTagBase(BaseModel):
    exercise_id: uuid.UUID
    tag_id: uuid.UUID
    weight: float = 1.0
    confidence: float = 1.0
    created_by: Optional[str] = Field(None, max_length=50)
    created_by_user_id: Optional[uuid.UUID] = None


class ExerciseTagCreate(ExerciseTagBase):
    pass


class ExerciseTagDB(ExerciseTagBase):
    class Config:
        from_attributes = True
        json_encoders = {
            uuid.UUID: str
        }


# --- Processing Result Models (for API responses) ---

class TagImport(BaseModel):
    namespace: str = Field(..., max_length=255)
    key: str = Field(..., max_length=255)
    label: Optional[str] = Field(None, max_length=255)
    weight: float = 1.0

class ExerciseImport(BaseModel):
    exam_type: ExamType
    profile: Optional[str] = Field(None, max_length=50)
    subject_part: Optional[SubjectPart] = None
    item_type: Optional[ItemType] = None
    statement_latex: str
    statement_text: Optional[str] = None
    answer_latex: Optional[str] = None
    solution_latex: Optional[str] = None
    scoring_guide_latex: Optional[str] = None
    scoring_guide_text: Optional[str] = None
    difficulty: Optional[int] = Field(None, ge=1, le=10)
    points: Optional[int] = None
    tags: Optional[List[TagImport]] = None

class StructuredImport(BaseModel):
    exercises: List[ExerciseImport]

class ProcessingPageResult(BaseModel):
    """Result from processing a single page"""
    page_number: int
    raw_text: str
    latex_formulas: List[str]
    width: Optional[int] = None
    height: Optional[int] = None
    error: Optional[str] = None


class ProcessingResult(BaseModel):
    """Complete result from PDF processing"""
    source_id: uuid.UUID
    segment_id: Optional[uuid.UUID] = None
    pages: List[ProcessingPageResult]
    combined_text: str
    total_pages: int
    status: str


# --- Variant Models ---

class VariantStatus(str, Enum):
    DRAFT = "DRAFT"
    READY = "READY"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"


class VariantBase(BaseModel):
    name: str = Field(..., max_length=255)
    exam_type: ExamType
    profile: Optional[str] = Field(None, max_length=50)
    year: Optional[int] = None
    session: Optional[str] = Field(None, max_length=50)
    total_points: Optional[int] = None
    duration_minutes: Optional[int] = None
    instructions: Optional[str] = None
    status: VariantStatus = VariantStatus.DRAFT
    created_by_user_id: Optional[uuid.UUID] = None


class VariantCreate(VariantBase):
    pass


class VariantUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    exam_type: Optional[ExamType] = None
    profile: Optional[str] = None
    year: Optional[int] = None
    session: Optional[str] = None
    total_points: Optional[int] = None
    duration_minutes: Optional[int] = None
    instructions: Optional[str] = None
    status: Optional[VariantStatus] = None


class VariantDB(VariantBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            uuid.UUID: str,
            datetime: lambda dt: dt.isoformat()
        }


# --- Variant Exercise Models ---

class VariantExerciseBase(BaseModel):
    variant_id: uuid.UUID
    exercise_id: uuid.UUID
    order_index: int
    section_name: Optional[str] = Field(None, max_length=100)


class VariantExerciseCreate(VariantExerciseBase):
    pass


class VariantExerciseDB(VariantExerciseBase):
    id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            uuid.UUID: str,
            datetime: lambda dt: dt.isoformat()
        }