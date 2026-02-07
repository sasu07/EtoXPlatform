# Import JSON în Baza de Date

Ghid complet pentru importul exercițiilor din format JSON în PostgreSQL.

## Ordinea de Import

Script-ul respectă exact ordinea recomandată:

1. **SOURCES** - Inserează sursa (PDF-ul bacalaureat)
2. **SOURCE_SEGMENTS** - Creează câte 1 segment per pagină (minim viabil)
3. **TAGS** - Upsert tag-uri din `tag_catalog`
4. **EXERCISES** - Inserează exercițiile (statement, difficulty, points, etc.)
5. **EXERCISE_TAGS** - Leagă exercițiile de tag-uri
6. **EXERCISE_SOURCE_SEGMENTS** - Leagă exercițiile de pagini

## Cerințe

- Python 3.8+
- PostgreSQL cu schema creată (tabele: sources, source_segments, exercises, tags, exercise_tags, exercise_source_segments)
- Variabile de mediu: `DATABASE_URL` în `.env`

## Utilizare

### Import Standard (doar exerciții cu points > 0)

```bash
cd edu_content_api
python import_json.py test.json
```

### Import cu Container-e (include și exercițiile cu points=0)

```bash
python import_json.py test.json --include-containers
```

## Structura JSON Așteptată

```json
{
  "schema_version": "1.0",
  "source": {
    "external_id": "bac-2025-mate-info-var-09",
    "name": "Bacalaureat 2025 – Matematică M_mate-info – Varianta 9",
    "type": "BAC",
    "year": 2025,
    "profile": "M_mate-info",
    "file_name": "E_c_matematica_M_mate-info_2025_var_09_LRO.pdf",
    "page_count": 2
  },
  "tag_catalog": [
    {
      "namespace": "exam",
      "key": "bacalaureat",
      "label": "Bacalaureat"
    }
  ],
  "exercises": [
    {
      "external_id": "B2025-MI-V09-S1-1",
      "points": 5,
      "difficulty": 1,
      "statement_latex": "...",
      "source_ref": {
        "page_start": 1,
        "page_end": 1
      },
      "tags": [
        {
          "namespace": "exam",
          "key": "bacalaureat",
          "confidence": 1.0,
          "weight": 1.0
        }
      ]
    }
  ]
}
```

## Ce Face Script-ul

### 1. SOURCES

- Inserează un rând în `sources`
- `file_path` = `{year}/{type}/{profile}/{file_name}`
- `notes` (JSONB) = `{ "external_id": "...", "page_count": 2 }`
- **Idempotent**: Dacă sursa cu același `external_id` există, o refolosește

### 2. SOURCE_SEGMENTS

Pentru fiecare pagină din `page_count`:
- Creează segment: `(page_start=N, page_end=N)`
- `status = EXTRACTED`
- `extraction_method = MANUAL`
- Când vei avea OCR, actualizezi `raw_extraction`

### 3. TAGS

Pentru fiecare tag din `tag_catalog`:
- **Upsert** prin `(namespace, key)` - cheie unică
- Setează `label`
- `parent_id` = NULL (în JSON-ul tău nu ai ierarhie)

### 4. EXERCISES

Pentru fiecare exercițiu:
- Inserează în `exercises`
- `metadata` (JSONB) = `{ "external_id": "...", "parent_external_id": "..." }`
- Mapează:
  - `exam_type`: BAC → bacalaureat
  - `item_type`: item → exercitiu, problem → problema
- **Idempotent**: Dacă exercițiu cu același `external_id` există, îl skip-uiește

### 5. EXERCISE_TAGS

Pentru fiecare `exercise.tags[]`:
- Găsește `tag_id` după `(namespace, key)`
- Inserează în `exercise_tags`: `(exercise_id, tag_id, confidence, weight)`
- **ON CONFLICT**: Actualizează weight/confidence dacă deja există

### 6. EXERCISE_SOURCE_SEGMENTS

Pentru fiecare exercițiu:
- Citește `source_ref.page_start` și `page_end`
- Pentru fiecare pagină din interval:
  - Găsește `segment_id` corespunzător
  - Inserează în `exercise_source_segments`: `(exercise_id, segment_id, role='statement')`
- **ON CONFLICT**: Ignoră duplicate

## Identificatori Stabili (external_id)

Script-ul folosește `external_id` ca **cheie de business stabilă**:

- **SOURCES**: Stocat în `notes->>'external_id'` (JSONB)
- **EXERCISES**: Stocat în `metadata->>'external_id'` (JSONB)

### Avantaje:
- Poți rerula import-ul fără duplicate
- Ușor de debugat (vezi exact ce exercițiu e în DB)
- Poți face update-uri incrementale

## Output Exemplu

```
=== Import JSON în baza de date ===

Încărcare JSON din: test.json
✓ JSON încărcat: 1.0

Pas 1: Import SOURCES
✓ Creat source: bac-2025-mate-info-var-09 -> 123e4567-e89b-12d3-a456-426614174000

Pas 2: Import SOURCE_SEGMENTS
✓ Creat 2 segmente de pagini

Pas 3: Import TAGS
✓ Procesat 16 tag-uri (inserat/actualizat 16 noi)

Pas 4: Import EXERCISES
✓ Creat 18 exerciții

Pas 5: Import EXERCISE_TAGS
✓ Creat 126 legături exercise-tag

Pas 6: Import EXERCISE_SOURCE_SEGMENTS
✓ Creat 18 legături exercise-segment

=== SUMAR ===
  sources: 1
  segments: 2
  tags: 16
  exercises: 18
  exercise_tags: 126
  exercise_source_segments: 18

✓ Import finalizat cu succes!
```

## Troubleshooting

### Eroare: "Database connection pool is not initialized"
- Verifică că ai `DATABASE_URL` în `.env`
- Exemplu: `DATABASE_URL=postgresql://user:pass@localhost:5432/dbname`

### Eroare: "relation 'sources' does not exist"
- Rulează mai întâi migrațiile pentru a crea tabelele
- Verifică că schema PostgreSQL e creată

### Tag-uri lipsă
- Script-ul va afișa `Warning: Tag (namespace, key) nu găsit în cache`
- Verifică că tag-ul e în `tag_catalog` din JSON

### Exerciții duplicate
- Script-ul skip-uiește automat exercițiile cu același `external_id`
- Poți șterge manual: `DELETE FROM exercises WHERE metadata->>'external_id' = '...'`

## Următorii Pași

După import:

1. **OCR Integration**: Actualizează `source_segments.raw_extraction` cu textul OCR
   ```sql
   UPDATE source_segments
   SET raw_extraction = 'textul OCR aici',
       extraction_method = 'pix2text'
   WHERE id = '...';
   ```

2. **Verificare Date**:
   ```sql
   -- Exerciții importate
   SELECT
     metadata->>'external_id' as external_id,
     statement_text,
     points,
     difficulty
   FROM exercises
   ORDER BY metadata->>'external_id';

   -- Tag-uri per exercițiu
   SELECT
     e.metadata->>'external_id' as exercise,
     t.namespace,
     t.key,
     et.confidence
   FROM exercises e
   JOIN exercise_tags et ON e.id = et.exercise_id
   JOIN tags t ON et.tag_id = t.id;
   ```

3. **Segmente cu Exerciții**:
   ```sql
   SELECT
     ss.page_start,
     ss.page_end,
     COUNT(ess.exercise_id) as nr_exercitii
   FROM source_segments ss
   LEFT JOIN exercise_source_segments ess ON ss.id = ess.source_segment_id
   GROUP BY ss.id, ss.page_start, ss.page_end
   ORDER BY ss.page_start;
   ```

## Extinderi Viitoare

1. **Ierarhie Tag-uri**: Populează `tags.parent_id` pentru tag-uri ierarhice
2. **Relații Parent-Child Exerciții**: Leagă subprobleme de problema container
3. **Segment Regions**: Adaugă bounding boxes pentru localizare exactă în PDF
4. **Assets**: Importă figuri/diagrame din exerciții

## Contact / Suport

Pentru probleme sau îmbunătățiri, consultă documentația sau contactează echipa de dev.
