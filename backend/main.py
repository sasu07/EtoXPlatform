
import uuid
import os
import shutil
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from psycopg import Connection
from psycopg.rows import dict_row

from starlette.responses import StreamingResponse
from database import get_db_conn, close_db_pool
from models import (
    SourceCreate, SourceDB, SourceUpdate, SourceType,
    ExerciseCreate, ExerciseDB, ExerciseUpdate,
    SourceSegmentCreate, SourceSegmentDB, SourceSegmentUpdate,
    AssetCreate, AssetDB,
    ProcessingResult, ProcessingPageResult,
    ExtractionMethod, SegmentStatus,
    TagCreate, TagDB, ExerciseTagCreate,
    StructuredImport, ExerciseImport, TagImport, ExamType, ExerciseStatus,
    VariantCreate, VariantDB, VariantUpdate, VariantStatus,
    VariantExerciseCreate, VariantExerciseDB
)
from pix2text_processor import get_pix2text_processor
from ai_tagger import get_ai_tagger
from exercise_extractor import get_exercise_extractor
from import_json import JSONImporter
from variant_generator import get_variant_generator
from pdf_generator import get_pdf_generator

app = FastAPI(
    title="Edu Content API",
    description="Backend API for managing educational exercises and variants.",
    version="0.1.0"
)

# --- CORS Configuration for Frontend Development ---
origins = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:8080",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

# --- File Storage Setup ---
UPLOAD_DIR = "uploaded_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.on_event("shutdown")
def shutdown_event():
    close_db_pool()


# --- Helper functions ---

def _create_source_in_db(source: SourceCreate, conn: Connection) -> dict:
    """Internal function to create source entry in database."""
    query = """
    INSERT INTO sources (name, type, year, session, url_file_path, notes)
    VALUES (%s, %s, %s, %s, %s, %s)
    RETURNING id, name, type, year, session, url_file_path, notes, created_at;
    """
    with conn.cursor(row_factory=dict_row) as cur:
        # Convert SourceType enum to its value for database
        type_value = source.type.value if isinstance(source.type, SourceType) else source.type
        cur.execute(query, (
            source.name, type_value, source.year, source.session,
            source.url_file_path, source.notes
        ))
        new_source = cur.fetchone()
        conn.commit()
        return new_source


def _extract_and_save_exercises(combined_text: str, context: dict, segment_id: uuid.UUID, conn: Connection):
    """Helper to extract exercises from text and save to DB."""
    try:
        extractor = get_exercise_extractor()
        extracted_exercises = extractor.extract_exercises(combined_text, context)
        
        from models import ExerciseCreate, ExamType, ExerciseStatus
        
        for ex_data in extracted_exercises:
            try:
                # Validate exam_type against enum
                try:
                    ex_exam_type = ExamType(ex_data.get('exam_type', 'alta'))
                except ValueError:
                    ex_exam_type = ExamType.ALTA

                exercise_to_create = ExerciseCreate(
                    exam_type=ex_exam_type,
                    statement_latex=ex_data.get('statement_latex', ''),
                    statement_text=ex_data.get('statement_text', ''),
                    solution_latex=ex_data.get('solution_latex', ''),
                    answer_latex=ex_data.get('answer_latex', ''),
                    scoring_guide_latex=ex_data.get('scoring_guide_latex', ''),
                    points=ex_data.get('points'),
                    difficulty=ex_data.get('difficulty'),
                    item_type=ex_data.get('item_type'),
                    subject_part=ex_data.get('subject_part'),
                    status=ExerciseStatus.DRAFT
                )
                
                # Create exercise in DB (reusing the endpoint function)
                new_ex = create_exercise(exercise_to_create, conn)
                
                # Link to source segment
                link_query = "INSERT INTO exercise_source_segments (exercise_id, source_segment_id) VALUES (%s, %s)"
                with conn.cursor() as cur:
                    cur.execute(link_query, (new_ex['id'], segment_id))
                conn.commit()
                
                # Auto-tag
                try:
                    tag_exercise_endpoint(new_ex['id'], conn)
                except Exception:
                    pass # Ignore tagging errors during bulk extraction
                    
            except Exception as ex_err:
                print(f"Error creating extracted exercise: {ex_err}")
                conn.rollback()
    except Exception as extractor_err:
        print(f"Error during exercise extraction: {extractor_err}")


def _save_structured_exercises(exercises: List[ExerciseImport], segment_id: uuid.UUID, conn: Connection):
    """Helper to save structured exercises and their tags to DB."""
    from models import ExerciseCreate, ExerciseStatus
    
    for ex_data in exercises:
        try:
            exercise_to_create = ExerciseCreate(
                exam_type=ex_data.exam_type,
                profile=ex_data.profile,
                subject_part=ex_data.subject_part,
                item_type=ex_data.item_type,
                statement_latex=ex_data.statement_latex,
                statement_text=ex_data.statement_text,
                solution_latex=ex_data.solution_latex,
                answer_latex=ex_data.answer_latex,
                scoring_guide_latex=ex_data.scoring_guide_latex,
                scoring_guide_text=ex_data.scoring_guide_text,
                points=ex_data.points,
                difficulty=ex_data.difficulty,
                status=ExerciseStatus.DRAFT
            )
            
            # Create exercise in DB
            new_ex = create_exercise(exercise_to_create, conn)
            ex_id = new_ex['id']
            
            # Link to source segment
            link_query = "INSERT INTO exercise_source_segments (exercise_id, source_segment_id) VALUES (%s, %s)"
            with conn.cursor() as cur:
                cur.execute(link_query, (ex_id, segment_id))
            
            # Save tags
            if ex_data.tags:
                for t in ex_data.tags:
                    # Create/Get tag
                    tag_query = """
                    INSERT INTO tags (namespace, key, label)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (namespace, key) DO UPDATE SET label = EXCLUDED.label
                    RETURNING id;
                    """
                    with conn.cursor(row_factory=dict_row) as cur:
                        cur.execute(tag_query, (t.namespace, t.key, t.label))
                        res = cur.fetchone()
                        tag_id = res['id'] if isinstance(res, dict) else res[0]

                        # Link to exercise
                        link_tag_query = """
                        INSERT INTO exercise_tags (exercise_id, tag_id, weight, confidence, created_by)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (exercise_id, tag_id) DO UPDATE SET weight = EXCLUDED.weight
                        RETURNING tag_id;
                        """
                        cur.execute(link_tag_query, (ex_id, tag_id, t.weight, 1.0, 'manual_import'))
                        cur.fetchone() # consume result
            
            conn.commit()
        except Exception as ex_err:
            print(f"Error saving imported exercise: {ex_err}")
            conn.rollback()


# --- CRUD Operations for SOURCES ---

@app.post("/sources/", response_model=SourceDB, status_code=status.HTTP_201_CREATED)
def create_source(source: SourceCreate, conn: Connection = Depends(get_db_conn)):
    """Create a new source entry."""
    try:
        return _create_source_in_db(source, conn)
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {e}")


@app.get("/sources/", response_model=List[SourceDB])
def read_sources(conn: Connection = Depends(get_db_conn)):
    """Retrieve a list of all sources."""
    query = "SELECT id, name, type, year, session, url_file_path, notes, created_at FROM sources ORDER BY created_at DESC;"
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(query)
        sources = cur.fetchall()
        return sources


@app.get("/sources/{source_id}", response_model=SourceDB)
def read_source(source_id: uuid.UUID, conn: Connection = Depends(get_db_conn)):
    """Retrieve a single source by ID."""
    query = "SELECT id, name, type, year, session, url_file_path, notes, created_at FROM sources WHERE id = %s;"
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(query, (source_id,))
        source = cur.fetchone()
        if source is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
        return source


@app.put("/sources/{source_id}", response_model=SourceDB)
def update_source(source_id: uuid.UUID, source: SourceUpdate, conn: Connection = Depends(get_db_conn)):
    """Update an existing source."""
    updates = []
    values = []

    update_data = source.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields provided for update")

    for key, value in update_data.items():
        updates.append(f"{key} = %s")
        # Convert enum to value if needed
        if isinstance(value, SourceType):
            value = value.value
        values.append(value)

    values.append(source_id)

    query = f"""
    UPDATE sources SET {', '.join(updates)}
    WHERE id = %s
    RETURNING id, name, type, year, session, url_file_path, notes, created_at;
    """

    try:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, values)
            updated_source = cur.fetchone()
            conn.commit()
            if updated_source is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
            return updated_source
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {e}")


@app.delete("/sources/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_source(source_id: uuid.UUID, conn: Connection = Depends(get_db_conn)):
    """Delete a source by ID."""
    query = "DELETE FROM sources WHERE id = %s RETURNING id;"
    try:
        with conn.cursor() as cur:
            cur.execute(query, (source_id,))
            deleted_count = cur.rowcount
            conn.commit()
            if deleted_count == 0:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {e}")


# --- File Upload and Mathpix Logic ---

@app.post("/upload-and-process/")
async def upload_and_process(
    file: UploadFile = File(...),
    source_name: str = Form("Uploaded Document"),
    source_type: str = Form("pdf"),
    source_year: Optional[int] = Form(None),
    source_session: Optional[str] = Form(None),
    source_notes: Optional[str] = Form(None),
    conn: Connection = Depends(get_db_conn)
):
    """
    Uploads a PDF file, saves it locally, creates a Source entry,
    and initiates the Mathpix processing (placeholder for now).
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

    # 1. Save the file locally
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not save file: {e}")

    # 2. Convert source_type string to SourceType enum
    try:
        type_enum = SourceType(source_type)
    except ValueError:
        type_enum = SourceType.PDF  # Default to PDF if invalid

    # 3. Create Source entry in DB with all fields
    source_data = SourceCreate(
        name=source_name,
        type=type_enum,
        year=source_year,
        session=source_session,
        notes=source_notes,
        url_file_path=file_path
    )

    try:
        source_entry = _create_source_in_db(source_data, conn)
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

    # 4. Process PDF with pix2text
    try:
        processor = get_pix2text_processor()

        # Process the entire PDF
        print(f"Starting pix2text processing for: {file_path}")
        page_results = processor.process_pdf(file_path)

        # Combine all pages into a single segment
        combined_text = processor.combine_segment_text(page_results)

        # Create a source segment for the entire document
        segment_data = SourceSegmentCreate(
            source_id=source_entry["id"] if isinstance(source_entry["id"], uuid.UUID) else uuid.UUID(source_entry["id"]),
            page_start=1,
            page_end=len(page_results),
            raw_extraction=combined_text,
            status=SegmentStatus.PROCESSED,
            extraction_method=ExtractionMethod.PIX2TEXT
        )

        # Save segment to database
        segment_query = """
        INSERT INTO source_segments (source_id, page_start, page_end, raw_extraction, status, extraction_method)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id, source_id, page_start, page_end, raw_extraction, status, extraction_method, created_at;
        """

        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(segment_query, (
                segment_data.source_id,
                segment_data.page_start,
                segment_data.page_end,
                segment_data.raw_extraction,
                segment_data.status.value,
                segment_data.extraction_method.value
            ))
            segment_entry = cur.fetchone()
            conn.commit()

        # 5. Extract individual exercises using AI
        _extract_and_save_exercises(
            combined_text=combined_text,
            context={
                "year": source_data.year,
                "session": source_data.session,
                "notes": source_data.notes
            },
            segment_id=segment_entry["id"] if isinstance(segment_entry["id"], uuid.UUID) else uuid.UUID(segment_entry["id"]),
            conn=conn
        )

        # Prepare response with processing results
        processing_pages = [
            ProcessingPageResult(
                page_number=page['page_number'],
                raw_text=page.get('raw_text', ''),
                latex_formulas=page.get('latex_formulas', []),
                width=page.get('width'),
                height=page.get('height'),
                error=page.get('error')
            )
            for page in page_results
        ]

        # Convert to UUID if they're strings, otherwise use as-is
        source_uuid = source_entry["id"] if isinstance(source_entry["id"], uuid.UUID) else uuid.UUID(source_entry["id"])
        segment_uuid = segment_entry["id"] if isinstance(segment_entry["id"], uuid.UUID) else uuid.UUID(segment_entry["id"])

        return ProcessingResult(
            source_id=source_uuid,
            segment_id=segment_uuid,
            pages=processing_pages,
            combined_text=combined_text,
            total_pages=len(page_results),
            status="success"
        )

    except Exception as e:
        print(f"Error processing PDF with pix2text: {e}")
        # Return partial success with error info
        return {
            "message": "File uploaded and source entry created, but processing failed.",
            "source_id": source_entry["id"],
            "file_path": file_path,
            "error": str(e),
            "status": "partial_success"
        }


@app.post("/upload-with-json/")
async def upload_with_json(
    file: UploadFile = File(...),
    json_data: str = Form(...),
    source_name: str = Form("Uploaded Document"),
    source_type: str = Form("pdf"),
    source_year: Optional[int] = Form(None),
    source_session: Optional[str] = Form(None),
    source_notes: Optional[str] = Form(None),
    conn: Connection = Depends(get_db_conn)
):
    """
    Uploads a file and a JSON string containing structured exercise data.
    """
    import json
    try:
        data = json.loads(json_data)
        structured_data = StructuredImport(**data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON data: {e}")

    # 1. Save the file locally
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not save file: {e}")

    # 2. Create Source entry
    try:
        type_enum = SourceType(source_type)
    except ValueError:
        type_enum = SourceType.PDF

    source_data = SourceCreate(
        name=source_name,
        type=type_enum,
        year=source_year,
        session=source_session,
        notes=source_notes,
        url_file_path=file_path
    )

    try:
        source_entry = _create_source_in_db(source_data, conn)
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

    # 3. Create a source segment (as a container for exercises)
    segment_query = """
    INSERT INTO source_segments (source_id, page_start, page_end, raw_extraction, status, extraction_method)
    VALUES (%s, %s, %s, %s, %s, %s)
    RETURNING id;
    """
    try:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(segment_query, (
                source_entry["id"], 1, 1, "Manual JSON Import", 
                SegmentStatus.PROCESSED.value, ExtractionMethod.MANUAL.value
            ))
            segment_id = cur.fetchone()["id"]
            conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error creating segment: {e}")

    # 4. Save exercises and tags
    _save_structured_exercises(structured_data.exercises, segment_id, conn)

    return {
        "status": "success",
        "source_id": source_entry["id"],
        "exercises_imported": len(structured_data.exercises)
    }


# --- CRUD Operations for SOURCE SEGMENTS ---

@app.post("/source-segments/", response_model=SourceSegmentDB, status_code=status.HTTP_201_CREATED)
def create_source_segment(segment: SourceSegmentCreate, conn: Connection = Depends(get_db_conn)):
    """Create a new source segment entry."""
    query = """
    INSERT INTO source_segments (source_id, page_start, page_end, raw_extraction, checksum, status, extraction_method)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    RETURNING id, source_id, page_start, page_end, raw_extraction, checksum, status, extraction_method, created_at;
    """
    try:
        with conn.cursor(row_factory=dict_row) as cur:
            status_value = segment.status.value if hasattr(segment.status, 'value') else segment.status
            method_value = segment.extraction_method.value if hasattr(segment.extraction_method, 'value') else segment.extraction_method

            cur.execute(query, (
                segment.source_id, segment.page_start, segment.page_end,
                segment.raw_extraction, segment.checksum, status_value, method_value
            ))
            new_segment = cur.fetchone()
            conn.commit()
            return new_segment
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {e}")


@app.get("/source-segments/", response_model=List[SourceSegmentDB])
def read_source_segments(
    source_id: Optional[uuid.UUID] = None,
    conn: Connection = Depends(get_db_conn)
):
    """Retrieve source segments, optionally filtered by source_id."""
    if source_id:
        query = """
        SELECT id, source_id, page_start, page_end, raw_extraction, checksum, status, extraction_method, created_at
        FROM source_segments WHERE source_id = %s ORDER BY page_start;
        """
        params = (source_id,)
    else:
        query = """
        SELECT id, source_id, page_start, page_end, raw_extraction, checksum, status, extraction_method, created_at
        FROM source_segments ORDER BY created_at DESC;
        """
        params = ()

    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(query, params)
        segments = cur.fetchall()
        return segments


@app.get("/source-segments/{segment_id}", response_model=SourceSegmentDB)
def read_source_segment(segment_id: uuid.UUID, conn: Connection = Depends(get_db_conn)):
    """Retrieve a single source segment by ID."""
    query = """
    SELECT id, source_id, page_start, page_end, raw_extraction, checksum, status, extraction_method, created_at
    FROM source_segments WHERE id = %s;
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(query, (segment_id,))
        segment = cur.fetchone()
        if segment is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source segment not found")
        return segment


# --- CRUD Operations for EXERCISES ---

@app.post("/exercises/", response_model=ExerciseDB, status_code=status.HTTP_201_CREATED)
def create_exercise(exercise: ExerciseCreate, conn: Connection = Depends(get_db_conn)):
    """Create a new exercise entry."""
    query = """
    INSERT INTO exercises (
        exam_type, profile, subject_part, item_type, statement_latex, statement_text,
        answer_latex, solution_latex, scoring_guide_latex, scoring_guide_text,
        difficulty, estimated_time_sec, points, metadata, status, created_by_user_id
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    RETURNING id, exam_type, profile, subject_part, item_type, statement_latex, statement_text,
              answer_latex, solution_latex, scoring_guide_latex, scoring_guide_text,
              difficulty, estimated_time_sec, points, metadata, status, created_by_user_id,
              created_at, updated_at;
    """
    try:
        with conn.cursor(row_factory=dict_row) as cur:
            # Convert enums to their string values
            exam_type_value = exercise.exam_type.value if hasattr(exercise.exam_type, 'value') else exercise.exam_type
            subject_part_value = exercise.subject_part.value if exercise.subject_part and hasattr(exercise.subject_part, 'value') else exercise.subject_part
            item_type_value = exercise.item_type.value if exercise.item_type and hasattr(exercise.item_type, 'value') else exercise.item_type
            status_value = exercise.status.value if hasattr(exercise.status, 'value') else exercise.status

            # Convert metadata dict to JSON string if present
            import json
            metadata_json = json.dumps(exercise.metadata) if exercise.metadata else None

            cur.execute(query, (
                exam_type_value, exercise.profile, subject_part_value, item_type_value,
                exercise.statement_latex, exercise.statement_text,
                exercise.answer_latex, exercise.solution_latex,
                exercise.scoring_guide_latex, exercise.scoring_guide_text,
                exercise.difficulty, exercise.estimated_time_sec, exercise.points,
                metadata_json, status_value, exercise.created_by_user_id
            ))
            new_exercise = cur.fetchone()
            conn.commit()
            return new_exercise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {e}")


@app.get("/exercises/", response_model=List[ExerciseDB])
def read_exercises(
    exam_type: Optional[str] = None,
    status_filter: Optional[str] = None,
    conn: Connection = Depends(get_db_conn)
):
    """Retrieve exercises, optionally filtered by exam_type or status."""
    conditions = []
    params = []

    if exam_type:
        conditions.append("exam_type = %s")
        params.append(exam_type)

    if status_filter:
        conditions.append("status = %s")
        params.append(status_filter)

    where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""

    query = f"""
    SELECT id, exam_type, profile, subject_part, item_type, statement_latex, statement_text,
           answer_latex, solution_latex, scoring_guide_latex, scoring_guide_text,
           difficulty, estimated_time_sec, points, metadata, status, created_by_user_id,
           created_at, updated_at
    FROM exercises{where_clause} ORDER BY created_at DESC;
    """

    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(query, tuple(params))
        exercises = cur.fetchall()
        return exercises


@app.get("/exercises/{exercise_id}", response_model=ExerciseDB)
def read_exercise(exercise_id: uuid.UUID, conn: Connection = Depends(get_db_conn)):
    """Retrieve a single exercise by ID."""
    query = """
    SELECT id, exam_type, profile, subject_part, item_type, statement_latex, statement_text,
           answer_latex, solution_latex, scoring_guide_latex, scoring_guide_text,
           difficulty, estimated_time_sec, points, metadata, status, created_by_user_id,
           created_at, updated_at
    FROM exercises WHERE id = %s;
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(query, (exercise_id,))
        exercise = cur.fetchone()
        if exercise is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercise not found")
        return exercise


@app.put("/exercises/{exercise_id}", response_model=ExerciseDB)
def update_exercise(exercise_id: uuid.UUID, exercise: ExerciseUpdate, conn: Connection = Depends(get_db_conn)):
    """Update an existing exercise."""
    updates = []
    values = []

    update_data = exercise.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields provided for update")

    import json
    for key, value in update_data.items():
        updates.append(f"{key} = %s")
        # Convert enum to value if needed
        if hasattr(value, 'value'):
            value = value.value
        # Convert dict to JSON string
        if isinstance(value, dict):
            value = json.dumps(value)
        values.append(value)

    # Add updated_at timestamp
    updates.append("updated_at = CURRENT_TIMESTAMP")
    values.append(exercise_id)

    query = f"""
    UPDATE exercises SET {', '.join(updates)}
    WHERE id = %s
    RETURNING id, exam_type, profile, subject_part, item_type, statement_latex, statement_text,
              answer_latex, solution_latex, scoring_guide_latex, scoring_guide_text,
              difficulty, estimated_time_sec, points, metadata, status, created_by_user_id,
              created_at, updated_at;
    """

    try:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, values)
            updated_exercise = cur.fetchone()
            conn.commit()
            if updated_exercise is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercise not found")
            return updated_exercise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {e}")


@app.delete("/exercises/{exercise_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_exercise(exercise_id: uuid.UUID, conn: Connection = Depends(get_db_conn)):
    """Delete an exercise by ID."""
    query = "DELETE FROM exercises WHERE id = %s RETURNING id;"
    try:
        with conn.cursor() as cur:
            cur.execute(query, (exercise_id,))
            deleted_count = cur.rowcount
            conn.commit()
            if deleted_count == 0:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercise not found")
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {e}")


# --- CRUD for TAGS ---

@app.post("/tags/", response_model=TagDB, status_code=status.HTTP_201_CREATED)
def create_tag(tag: TagCreate, conn: Connection = Depends(get_db_conn)):
    """Create a new tag."""
    query = """
    INSERT INTO tags (namespace, key, label, parent_id)
    VALUES (%s, %s, %s, %s)
    ON CONFLICT (namespace, key) DO UPDATE SET label = EXCLUDED.label
    RETURNING id, namespace, key, label, parent_id, created_at;
    """
    try:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, (tag.namespace, tag.key, tag.label, tag.parent_id))
            new_tag = cur.fetchone()
            conn.commit()
            return new_tag
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {e}")


@app.get("/tags/", response_model=List[TagDB])
def read_tags(namespace: Optional[str] = None, conn: Connection = Depends(get_db_conn)):
    """Retrieve all tags, optionally filtered by namespace."""
    if namespace:
        query = "SELECT id, namespace, key, label, parent_id, created_at FROM tags WHERE namespace = %s ORDER BY namespace, key;"
        params = (namespace,)
    else:
        query = "SELECT id, namespace, key, label, parent_id, created_at FROM tags ORDER BY namespace, key;"
        params = ()

    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(query, params)
        return cur.fetchall()


# --- AI Tagging Endpoint ---

@app.post("/exercises/{exercise_id}/tag")
def tag_exercise_endpoint(exercise_id: uuid.UUID, conn: Connection = Depends(get_db_conn)):
    """Trigger AI tagging for a specific exercise."""
    # 1. Fetch exercise
    query = "SELECT statement_text, solution_latex FROM exercises WHERE id = %s;"
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(query, (exercise_id,))
        exercise = cur.fetchone()

    if not exercise:
        raise HTTPException(status_code=404, detail="Exercise not found")

    # 2. Call AI Tagger
    tagger = get_ai_tagger()
    tags = tagger.tag_exercise(exercise['statement_text'], exercise['solution_latex'])

    # 3. Save tags and links
    results = []
    try:
        for t in tags:
            # Create/Get tag
            tag_query = """
            INSERT INTO tags (namespace, key, label)
            VALUES (%s, %s, %s)
            ON CONFLICT (namespace, key) DO UPDATE SET label = EXCLUDED.label
            RETURNING id;
            """
            with conn.cursor() as cur:
                cur.execute(tag_query, (t['namespace'], t['key'], t['label']))
                res = cur.fetchone()
                if res:
                    # Handle both dict and tuple rows
                    tag_id = res['id'] if isinstance(res, dict) else res[0]
                else:
                    continue

                # Link to exercise
                link_query = """
                INSERT INTO exercise_tags (exercise_id, tag_id, weight, confidence, created_by)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (exercise_id, tag_id) DO UPDATE SET weight = EXCLUDED.weight
                RETURNING tag_id;
                """
                cur.execute(link_query, (exercise_id, tag_id, t.get('weight', 1.0), 0.8, 'model'))
                # Just consume the result to ensure it runs
                cur.fetchone()

            results.append(t)
        conn.commit()
        return {"status": "success", "tags_applied": results}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error applying tags: {e}")


# --- PDF Processing Endpoint ---

@app.post("/process-pdf/{source_id}", response_model=ProcessingResult)
async def process_existing_pdf(
    source_id: uuid.UUID,
    page_start: Optional[int] = None,
    page_end: Optional[int] = None,
    conn: Connection = Depends(get_db_conn)
):
    """
    Process an already uploaded PDF using pix2text.
    Can optionally specify a page range to process.
    """
    # 1. Get the source from database
    query = "SELECT id, url_file_path, year, session, notes FROM sources WHERE id = %s;"
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(query, (source_id,))
        source = cur.fetchone()

    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    pdf_path = source.get('url_file_path')
    if not pdf_path or not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="PDF file not found")

    try:
        processor = get_pix2text_processor()

        # Process PDF (either full or specific range)
        if page_start and page_end:
            print(f"Processing pages {page_start}-{page_end} of: {pdf_path}")
            page_results = processor.process_pdf_segment(pdf_path, page_start, page_end)
        else:
            print(f"Processing entire PDF: {pdf_path}")
            page_results = processor.process_pdf(pdf_path)
            page_start = 1
            page_end = len(page_results)

        # Combine text from all processed pages
        combined_text = processor.combine_segment_text(page_results)

        # Create a source segment entry
        segment_data = SourceSegmentCreate(
            source_id=source_id,
            page_start=page_start,
            page_end=page_end,
            raw_extraction=combined_text,
            status=SegmentStatus.PROCESSED,
            extraction_method=ExtractionMethod.PIX2TEXT
        )

        # Save to database
        segment_query = """
        INSERT INTO source_segments (source_id, page_start, page_end, raw_extraction, status, extraction_method)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id, source_id, page_start, page_end, raw_extraction, status, extraction_method, created_at;
        """

        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(segment_query, (
                segment_data.source_id,
                segment_data.page_start,
                segment_data.page_end,
                segment_data.raw_extraction,
                segment_data.status.value,
                segment_data.extraction_method.value
            ))
            segment_entry = cur.fetchone()
            conn.commit()

        # 5. Extract individual exercises using AI
        _extract_and_save_exercises(
            combined_text=combined_text,
            context={
                "year": source.get('year'),
                "session": source.get('session'),
                "notes": source.get('notes')
            },
            segment_id=segment_entry["id"] if isinstance(segment_entry["id"], uuid.UUID) else uuid.UUID(segment_entry["id"]),
            conn=conn
        )
        processing_pages = [
            ProcessingPageResult(
                page_number=page['page_number'],
                raw_text=page.get('raw_text', ''),
                latex_formulas=page.get('latex_formulas', []),
                width=page.get('width'),
                height=page.get('height'),
                error=page.get('error')
            )
            for page in page_results
        ]

        # Convert segment_id to UUID if it's a string
        segment_uuid = segment_entry["id"] if isinstance(segment_entry["id"], uuid.UUID) else uuid.UUID(segment_entry["id"])

        return ProcessingResult(
            source_id=source_id,
            segment_id=segment_uuid,
            pages=processing_pages,
            combined_text=combined_text,
            total_pages=len(page_results),
            status="success"
        )

    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error processing PDF: {str(e)}"
        )


# --- JSON Import Endpoint ---

@app.post("/import-json/")
async def import_json_endpoint(
    json_file: UploadFile = File(...),
    include_containers: bool = Form(False),
    conn: Connection = Depends(get_db_conn)
):
    """
    Upload și procesare fișier JSON pre-procesat cu exerciții.
    Această metodă înlocuiește fluxul automat (OCR → LaTeX → AI tagging).

    Fișierul JSON trebuie să conțină:
    - source: date despre sursa PDF (external_id, name, year, type, etc.)
    - tag_catalog: lista de tag-uri disponibile
    - exercises: lista de exerciții cu statement_latex, tags, source_ref, etc.

    Args:
        json_file: Fișierul JSON cu exercițiile pre-procesate
        include_containers: Dacă True, include și exercițiile container (points=0)

    Returns:
        Statistici despre import (nr de surse, exerciții, tag-uri, etc.)
    """
    import json
    import tempfile

    # Verifică tipul fișierului
    if not json_file.filename.lower().endswith('.json'):
        raise HTTPException(status_code=400, detail="Doar fișiere JSON sunt acceptate")

    # Salvează temporar fișierul JSON
    try:
        with tempfile.NamedTemporaryFile(mode='w+b', delete=False, suffix='.json') as tmp_file:
            content = await json_file.read()
            tmp_file.write(content)
            tmp_json_path = tmp_file.name

        # Validează JSON
        try:
            with open(tmp_json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Validare minimă
            required_keys = ['source', 'tag_catalog', 'exercises']
            for key in required_keys:
                if key not in data:
                    raise ValueError(f"JSON lipsește cheia obligatorie: {key}")

        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"JSON invalid: {e}")
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # Creează importer și rulează
        importer = JSONImporter(tmp_json_path, include_containers=include_containers)
        importer.conn = conn

        try:
            # Rulează fiecare pas și colectează statistici
            print(f"=== Import JSON: {json_file.filename} ===")

            # Pas 1: Import SOURCE
            source_data = data['source']
            source_id = importer.import_source(source_data)

            # Pas 2: Import SOURCE_SEGMENTS
            page_count = source_data.get('page_count', 0)
            importer.import_source_segments(source_id, page_count)

            # Pas 3: Import TAGS
            importer.import_tags(data['tag_catalog'])

            # Pas 4: Import EXERCISES
            importer.import_exercises(data['exercises'])

            # Pas 5: Import EXERCISE_TAGS
            importer.import_exercise_tags(data['exercises'])

            # Pas 6: Import EXERCISE_SOURCE_SEGMENTS
            importer.import_exercise_source_segments(data['exercises'], source_id)

            # Nu uităm să facem commit!
            conn.commit()

            return {
                "status": "success",
                "message": f"Import finalizat pentru {json_file.filename}",
                "source_id": str(source_id),
                "statistics": importer.stats
            }

        except Exception as e:
            conn.rollback()
            print(f"Eroare la import: {e}")
            import traceback
            traceback.print_exc()
            raise HTTPException(
                status_code=500,
                detail=f"Eroare la import JSON: {str(e)}"
            )
        finally:
            # Cleanup temp file
            import os
            if os.path.exists(tmp_json_path):
                os.unlink(tmp_json_path)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Eroare la procesarea fișierului: {str(e)}"
        )


# --- CRUD Operations for VARIANTS ---

@app.post("/variants/", response_model=VariantDB, status_code=status.HTTP_201_CREATED)
def create_variant(variant: VariantCreate, conn: Connection = Depends(get_db_conn)):
    """Create a new variant (test subject)."""
    query = """
    INSERT INTO variants (
        name, exam_type, profile, year, session, total_points,
        duration_minutes, instructions, status, created_by_user_id
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    RETURNING id, name, exam_type, profile, year, session, total_points,
              duration_minutes, instructions, status, created_by_user_id,
              created_at, updated_at;
    """
    try:
        with conn.cursor(row_factory=dict_row) as cur:
            exam_type_value = variant.exam_type.value if hasattr(variant.exam_type, 'value') else variant.exam_type
            status_value = variant.status.value if hasattr(variant.status, 'value') else variant.status

            cur.execute(query, (
                variant.name, exam_type_value, variant.profile, variant.year, variant.session,
                variant.total_points, variant.duration_minutes, variant.instructions,
                status_value, variant.created_by_user_id
            ))
            new_variant = cur.fetchone()
            conn.commit()
            return new_variant
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {e}")


@app.get("/variants/", response_model=List[VariantDB])
def read_variants(
    exam_type: Optional[str] = None,
    status_filter: Optional[str] = None,
    conn: Connection = Depends(get_db_conn)
):
    """Retrieve variants, optionally filtered by exam_type or status."""
    conditions = []
    params = []

    if exam_type:
        conditions.append("exam_type = %s")
        params.append(exam_type)

    if status_filter:
        conditions.append("status = %s")
        params.append(status_filter)

    where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""

    query = f"""
    SELECT id, name, exam_type, profile, year, session, total_points,
           duration_minutes, instructions, status, created_by_user_id,
           created_at, updated_at
    FROM variants{where_clause} ORDER BY created_at DESC;
    """

    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(query, tuple(params))
        variants = cur.fetchall()
        return variants


@app.get("/variants/{variant_id}", response_model=VariantDB)
def read_variant(variant_id: uuid.UUID, conn: Connection = Depends(get_db_conn)):
    """Retrieve a single variant by ID."""
    query = """
    SELECT id, name, exam_type, profile, year, session, total_points,
           duration_minutes, instructions, status, created_by_user_id,
           created_at, updated_at
    FROM variants WHERE id = %s;
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(query, (variant_id,))
        variant = cur.fetchone()
        if variant is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Variant not found")
        return variant


@app.put("/variants/{variant_id}", response_model=VariantDB)
def update_variant(variant_id: uuid.UUID, variant: VariantUpdate, conn: Connection = Depends(get_db_conn)):
    """Update an existing variant."""
    updates = []
    values = []

    update_data = variant.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields provided for update")

    for key, value in update_data.items():
        updates.append(f"{key} = %s")
        if hasattr(value, 'value'):
            value = value.value
        values.append(value)

    values.append(variant_id)

    query = f"""
    UPDATE variants SET {', '.join(updates)}
    WHERE id = %s
    RETURNING id, name, exam_type, profile, year, session, total_points,
              duration_minutes, instructions, status, created_by_user_id,
              created_at, updated_at;
    """

    try:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, values)
            updated_variant = cur.fetchone()
            conn.commit()
            if updated_variant is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Variant not found")
            return updated_variant
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {e}")


@app.delete("/variants/{variant_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_variant(variant_id: uuid.UUID, conn: Connection = Depends(get_db_conn)):
    """Delete a variant by ID."""
    query = "DELETE FROM variants WHERE id = %s RETURNING id;"
    try:
        with conn.cursor() as cur:
            cur.execute(query, (variant_id,))
            deleted_count = cur.rowcount
            conn.commit()
            if deleted_count == 0:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Variant not found")
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {e}")


# --- Operations for VARIANT EXERCISES ---

@app.post("/variants/{variant_id}/exercises/")
def add_exercises_to_variant(
    variant_id: uuid.UUID,
    exercise_ids: List[uuid.UUID],
    conn: Connection = Depends(get_db_conn)
):
    """Add multiple exercises to a variant with automatic ordering."""
    try:
        # Get current max order_index for this variant
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT COALESCE(MAX(order_index), -1) as max_order FROM variant_exercises WHERE variant_id = %s",
                (variant_id,)
            )
            result = cur.fetchone()
            current_max = result['max_order'] if result else -1

        # Insert exercises
        query = """
        INSERT INTO variant_exercises (variant_id, exercise_id, order_index)
        VALUES (%s, %s, %s)
        ON CONFLICT (variant_id, exercise_id) DO NOTHING
        RETURNING id;
        """

        added_count = 0
        with conn.cursor(row_factory=dict_row) as cur:
            for idx, exercise_id in enumerate(exercise_ids):
                cur.execute(query, (variant_id, exercise_id, current_max + idx + 1))
                if cur.fetchone():
                    added_count += 1

        conn.commit()
        return {"status": "success", "added_count": added_count}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {e}")


@app.get("/variants/{variant_id}/exercises/")
def get_variant_exercises(variant_id: uuid.UUID, conn: Connection = Depends(get_db_conn)):
    """Get all exercises for a specific variant, ordered by order_index."""
    query = """
    SELECT
        ve.id, ve.variant_id, ve.exercise_id, ve.order_index, ve.section_name,
        e.statement_latex, e.statement_text, e.points, e.item_type, e.subject_part,
        e.difficulty, e.exam_type
    FROM variant_exercises ve
    JOIN exercises e ON ve.exercise_id = e.id
    WHERE ve.variant_id = %s
    ORDER BY ve.order_index;
    """

    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(query, (variant_id,))
        exercises = cur.fetchall()
        return exercises


@app.delete("/variants/{variant_id}/exercises/{exercise_id}")
def remove_exercise_from_variant(
    variant_id: uuid.UUID,
    exercise_id: uuid.UUID,
    conn: Connection = Depends(get_db_conn)
):
    """Remove an exercise from a variant."""
    query = "DELETE FROM variant_exercises WHERE variant_id = %s AND exercise_id = %s RETURNING id;"
    try:
        with conn.cursor() as cur:
            cur.execute(query, (variant_id, exercise_id))
            deleted_count = cur.rowcount
            conn.commit()
            if deleted_count == 0:
                raise HTTPException(status_code=404, detail="Exercise not found in variant")
            return {"status": "success"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {e}")


@app.put("/variants/{variant_id}/exercises/reorder")
def reorder_variant_exercises(
    variant_id: uuid.UUID,
    exercise_order: List[uuid.UUID],
    conn: Connection = Depends(get_db_conn)
):
    """Reorder exercises in a variant by providing the exercise IDs in desired order."""
    query = """
    UPDATE variant_exercises
    SET order_index = %s
    WHERE variant_id = %s AND exercise_id = %s;
    """
    try:
        with conn.cursor() as cur:
            for idx, exercise_id in enumerate(exercise_order):
                cur.execute(query, (idx, variant_id, exercise_id))
        conn.commit()
        return {"status": "success", "reordered_count": len(exercise_order)}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {e}")


# --- PDF Download Endpoint ---

@app.get("/variants/{variant_id}/download-pdf")
def download_variant_pdf(variant_id: uuid.UUID, conn: Connection = Depends(get_db_conn)):
    """
    Generează și descarcă PDF-ul unei variante.
    """
    # Verifică dacă varianta există
    query = "SELECT id, name FROM variants WHERE id = %s;"
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(query, (variant_id,))
        variant = cur.fetchone()

    if not variant:
        raise HTTPException(status_code=404, detail="Varianta nu a fost găsită")

    try:
        generator = get_pdf_generator(conn)
        pdf_buffer = generator.generate_variant_pdf(variant_id)

        # Creează un filename sigur din numele variantei
        safe_name = variant['name'].replace(' ', '_').replace('/', '-')
        filename = f"{safe_name}.pdf"

        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Eroare la generarea PDF-ului: {str(e)}"
        )


# --- Auto-Generation Endpoint ---

@app.post("/variants/generate")
def generate_variant_auto(
    name: str = Form(...),
    exam_type: str = Form(...),
    profile: Optional[str] = Form(None),
    year: Optional[int] = Form(None),
    session: Optional[str] = Form(None),
    difficulty_min: int = Form(3),
    difficulty_max: int = Form(7),
    duration_minutes: int = Form(180),
    conn: Connection = Depends(get_db_conn)
):
    """
    Generează automat o variantă completă pe baza criteriilor.

    Respectă structura standard a examenului:
    - Bacalaureat:
        * Subiectul I: 6 exerciții (5p fiecare)
        * Subiectul II: 2 probleme x 3 variante (15p fiecare)
        * Subiectul III: 2 probleme x 3 variante (15p fiecare)
    - Evaluare Națională:
        * Subiectul I: 6 exerciții (5p fiecare)
        * Subiectul II: 3 probleme (10p fiecare)
    """
    try:
        generator = get_variant_generator(conn)

        result = generator.generate_variant(
            name=name,
            exam_type=exam_type,
            profile=profile,
            year=year,
            session=session,
            difficulty_range=(difficulty_min, difficulty_max),
            duration_minutes=duration_minutes
        )

        return {
            "status": "success",
            "message": f"Variantă generată automat: {name}",
            **result
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error generating variant: {e}")
