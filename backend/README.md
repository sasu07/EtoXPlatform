# Edu Content API

This is the backend API for the educational content management system, built with FastAPI and PostgreSQL.

## Stack

*   **Backend:** FastAPI (Python)
*   **Database:** PostgreSQL (using `psycopg` for connection)
*   **OCR:** Mathpix API (integration planned)
*   **Tagging AI:** OpenAI/Gemini API (integration planned)

## Setup

1.  **Clone the repository** (or extract the files).
2.  **Navigate to the project directory:** `cd edu_content_api`
3.  **Activate the virtual environment:** `source venv/bin/activate`
4.  **Install dependencies:** `pip install -r requirements.txt` (or use the command from the setup phase)
5.  **Configure Environment:** Create a `.env` file based on the provided template and fill in your credentials:
    *   `DATABASE_URL`: Your PostgreSQL connection string.
    *   `MATHPIX_APP_ID`: Your Mathpix Application ID.
    *   `MATHPIX_APP_KEY`: Your Mathpix Application Key.

## Running the Application

```bash
uvicorn main:app --reload
```

The API documentation (Swagger UI) will be available at `http://127.0.0.1:8000/docs`.

## Current Status (Phase 1.2)

*   Database schema successfully applied to the remote PostgreSQL instance.
*   Basic FastAPI structure is set up.
*   Database connection pooling is configured.
*   **CRUD endpoints for the `SOURCES` table are implemented.**

## Next Steps

*   Implement file upload and Mathpix API integration (Phase 1.3).
*   Implement the logic for identifying and ingesting exercises (Phase 1.4 - 1.6).
