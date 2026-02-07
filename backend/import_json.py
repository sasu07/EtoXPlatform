#!/usr/bin/env python3
"""
Script de import pentru integrarea exercițiilor din JSON în baza de date PostgreSQL.

Ordinea de import:
1. SOURCES - inserează sursa (PDF-ul)
2. SOURCE_SEGMENTS - creează câte un segment per pagină
3. TAGS - upsert tag-uri din tag_catalog
4. EXERCISES - inserează exercițiile (doar cele cu points > 0 sau toate)
5. EXERCISE_TAGS - leagă exercițiile de tag-uri
6. EXERCISE_SOURCE_SEGMENTS - leagă exercițiile de segmentele de pagini
"""

import json
import sys
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from pathlib import Path

from database import get_db_conn
from psycopg.rows import dict_row


class JSONImporter:
    def __init__(self, json_path: str, include_containers: bool = False):
        """
        Args:
            json_path: Calea către fișierul JSON
            include_containers: Dacă True, importă și exercițiile container (points=0)
        """
        self.json_path = json_path
        self.include_containers = include_containers
        self.conn = None

        # Cache pentru maparea external_id -> UUID
        self.source_uuid_cache: Dict[str, uuid.UUID] = {}
        self.tag_uuid_cache: Dict[tuple, uuid.UUID] = {}  # (namespace, key) -> UUID
        self.exercise_uuid_cache: Dict[str, uuid.UUID] = {}
        self.segment_cache: Dict[tuple, uuid.UUID] = {}  # (source_id, page_start, page_end) -> UUID

        # Statistici
        self.stats = {
            'sources': 0,
            'segments': 0,
            'tags': 0,
            'exercises': 0,
            'exercise_tags': 0,
            'exercise_source_segments': 0,
        }

    def load_json(self) -> Dict[str, Any]:
        """Încarcă și validează fișierul JSON."""
        with open(self.json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Validare minimă
        required_keys = ['source', 'tag_catalog', 'exercises']
        for key in required_keys:
            if key not in data:
                raise ValueError(f"JSON-ul lipsește cheia obligatorie: {key}")

        return data

    def import_source(self, source_data: Dict[str, Any]) -> uuid.UUID:
        """
        Pas 1: Inserează sursa în tabelul SOURCES.

        Returns:
            UUID-ul sursei create
        """
        external_id = source_data.get('external_id')

        # Verifică dacă sursa există deja (după external_id în notes/metadata)
        existing_source = self._find_source_by_external_id(external_id)
        if existing_source:
            print(f"✓ Source deja există: {external_id} -> {existing_source}")
            self.source_uuid_cache[external_id] = existing_source
            return existing_source

        # Pregătește datele pentru insert
        source_id = uuid.uuid4()

        # Construiește file_path (ex: 2025/BAC/M_mate-info/filename.pdf)
        year = source_data.get('year', '')
        type_val = source_data.get('type', 'BAC')
        profile = source_data.get('profile', '')
        file_name = source_data.get('file_name', '')

        file_path = f"{year}/{type_val}/{profile}/{file_name}" if all([year, type_val, profile, file_name]) else file_name

        # Notes cu external_id pentru identificare ulterioară
        notes = json.dumps({
            'external_id': external_id,
            'page_count': source_data.get('page_count'),
            'imported_at': datetime.now(timezone.utc).isoformat()
        })

        query = """
        INSERT INTO sources (id, name, type, year, session, url_file_path, notes, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """

        with self.conn.cursor() as cur:
            cur.execute(query, (
                source_id,
                source_data.get('name', f"Source {external_id}"),
                'pdf',  # type în DB (enum: pdf, oficial, culegere)
                source_data.get('year'),
                source_data.get('session'),
                file_path,
                notes,
                datetime.now(timezone.utc)
            ))
            self.conn.commit()

        self.source_uuid_cache[external_id] = source_id
        self.stats['sources'] += 1
        print(f"✓ Creat source: {external_id} -> {source_id}")

        return source_id

    def import_source_segments(self, source_id: uuid.UUID, page_count: int) -> List[uuid.UUID]:
        """
        Pas 2: Creează câte un segment per pagină (minim viabil).

        Args:
            source_id: UUID-ul sursei
            page_count: Numărul total de pagini

        Returns:
            Lista de UUID-uri pentru segmentele create
        """
        segment_ids = []

        query = """
        INSERT INTO source_segments (id, source_id, page_start, page_end, status, extraction_method, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """

        with self.conn.cursor() as cur:
            for page_num in range(1, page_count + 1):
                segment_id = uuid.uuid4()
                cur.execute(query, (
                    segment_id,
                    source_id,
                    page_num,
                    page_num,
                    'EXTRACTED',  # status
                    'MANUAL',  # extraction_method (deocamdată manual, ulterior OCR)
                    datetime.now(timezone.utc)
                ))

                # Cache pentru linking ulterior
                self.segment_cache[(source_id, page_num, page_num)] = segment_id
                segment_ids.append(segment_id)

            self.conn.commit()

        self.stats['segments'] += len(segment_ids)
        print(f"✓ Creat {len(segment_ids)} segmente de pagini")

        return segment_ids

    def import_tags(self, tag_catalog: List[Dict[str, Any]]) -> Dict[tuple, uuid.UUID]:
        """
        Pas 3: Upsert tag-uri din tag_catalog.

        Fiecare tag e identificat unic prin (namespace, key).

        Returns:
            Dict mapare (namespace, key) -> UUID
        """
        query_check = """
        SELECT id FROM tags WHERE namespace = %s AND key = %s
        """

        query_insert = """
        INSERT INTO tags (id, namespace, key, label, parent_id, created_at)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id
        """

        with self.conn.cursor() as cur:
            for tag_data in tag_catalog:
                namespace = tag_data['namespace']
                key = tag_data['key']
                label = tag_data.get('label', key)
                parent = tag_data.get('parent')  # Deocamdată None

                # Check dacă există
                cur.execute(query_check, (namespace, key))
                row = cur.fetchone()

                if row:
                    tag_id = row[0]
                    self.tag_uuid_cache[(namespace, key)] = tag_id
                else:
                    # Insert nou
                    tag_id = uuid.uuid4()
                    cur.execute(query_insert, (
                        tag_id,
                        namespace,
                        key,
                        label,
                        None,  # parent_id (dacă vrei ierarhie, mapezi parent aici)
                        datetime.now(timezone.utc)
                    ))
                    self.tag_uuid_cache[(namespace, key)] = tag_id
                    self.stats['tags'] += 1

            self.conn.commit()

        print(f"✓ Procesat {len(tag_catalog)} tag-uri (inserat/actualizat {self.stats['tags']} noi)")

        return self.tag_uuid_cache

    def import_exercises(self, exercises: List[Dict[str, Any]]) -> Dict[str, uuid.UUID]:
        """
        Pas 4: Inserează exercițiile.

        Returns:
            Dict mapare external_id -> UUID
        """
        query = """
        INSERT INTO exercises (
            id, exam_type, profile, subject_part, item_type,
            statement_latex, statement_text, answer_latex, solution_latex,
            scoring_guide_latex, scoring_guide_text,
            difficulty, estimated_time_sec, points, metadata, status,
            created_at, updated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """

        with self.conn.cursor() as cur:
            for ex_data in exercises:
                external_id = ex_data.get('external_id')
                points = ex_data.get('points', 0)

                # Dacă nu includem containers și points == 0, skip
                if not self.include_containers and points == 0:
                    print(f"  Skip container: {external_id}")
                    continue

                # Verifică dacă există deja (după external_id în metadata)
                existing_ex = self._find_exercise_by_external_id(external_id)
                if existing_ex:
                    print(f"  Exercise deja există: {external_id} -> {existing_ex}")
                    self.exercise_uuid_cache[external_id] = existing_ex
                    continue

                exercise_id = uuid.uuid4()

                # Metadata cu external_id
                metadata = {
                    'external_id': external_id,
                    'parent_external_id': ex_data.get('parent_external_id'),
                    'imported_at': datetime.now(timezone.utc).isoformat()
                }

                # Mapare item_type
                item_type_map = {
                    'item': 'exercitiu',
                    'problem': 'problema'
                }
                item_type = item_type_map.get(ex_data.get('item_type'), 'exercitiu')

                # Mapare exam_type
                exam_type_map = {
                    'BAC': 'bacalaureat',
                    'EN': 'evaluare_nationala'
                }
                exam_type = exam_type_map.get(ex_data.get('exam_type'), 'bacalaureat')

                cur.execute(query, (
                    exercise_id,
                    exam_type,
                    ex_data.get('profile'),
                    None,  # subject_part (poate fi mapat din ex_data dacă există)
                    item_type,
                    ex_data.get('statement_latex'),
                    ex_data.get('statement_text'),
                    ex_data.get('answer_latex'),
                    ex_data.get('solution_latex'),
                    None,  # scoring_guide_latex
                    None,  # scoring_guide_text
                    ex_data.get('difficulty'),
                    ex_data.get('estimated_time_sec'),
                    points,
                    json.dumps(metadata),
                    ex_data.get('status', 'DRAFT'),
                    datetime.now(timezone.utc),
                    datetime.now(timezone.utc)
                ))

                self.exercise_uuid_cache[external_id] = exercise_id
                self.stats['exercises'] += 1

            self.conn.commit()

        print(f"✓ Creat {self.stats['exercises']} exerciții")

        return self.exercise_uuid_cache

    def import_exercise_tags(self, exercises: List[Dict[str, Any]]):
        """
        Pas 5: Leagă exercițiile de tag-uri prin EXERCISE_TAGS.
        """
        query = """
        INSERT INTO exercise_tags (exercise_id, tag_id, weight, confidence, created_by)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (exercise_id, tag_id) DO UPDATE
        SET weight = EXCLUDED.weight, confidence = EXCLUDED.confidence
        """

        with self.conn.cursor() as cur:
            for ex_data in exercises:
                external_id = ex_data.get('external_id')
                exercise_id = self.exercise_uuid_cache.get(external_id)

                if not exercise_id:
                    continue  # Exercise nu a fost importat (posibil container skipat)

                tags = ex_data.get('tags', [])
                for tag_data in tags:
                    namespace = tag_data['namespace']
                    key = tag_data['key']
                    weight = tag_data.get('weight', 1.0)
                    confidence = tag_data.get('confidence', 1.0)

                    tag_id = self.tag_uuid_cache.get((namespace, key))
                    if not tag_id:
                        print(f"  Warning: Tag ({namespace}, {key}) nu găsit în cache")
                        continue

                    cur.execute(query, (
                        exercise_id,
                        tag_id,
                        weight,
                        confidence,
                        'import_script'
                    ))
                    self.stats['exercise_tags'] += 1

            self.conn.commit()

        print(f"✓ Creat {self.stats['exercise_tags']} legături exercise-tag")

    def import_exercise_source_segments(self, exercises: List[Dict[str, Any]], source_id: uuid.UUID):
        """
        Pas 6: Leagă exercițiile de segmentele de pagini prin EXERCISE_SOURCE_SEGMENTS.
        """
        query = """
        INSERT INTO exercise_source_segments (exercise_id, source_segment_id, role)
        VALUES (%s, %s, %s)
        ON CONFLICT (exercise_id, source_segment_id) DO NOTHING
        """

        with self.conn.cursor() as cur:
            for ex_data in exercises:
                external_id = ex_data.get('external_id')
                exercise_id = self.exercise_uuid_cache.get(external_id)

                if not exercise_id:
                    continue

                source_ref = ex_data.get('source_ref', {})
                page_start = source_ref.get('page_start')
                page_end = source_ref.get('page_end')

                if not (page_start and page_end):
                    print(f"  Warning: Exercise {external_id} lipsește page_start/page_end")
                    continue

                # Găsește toate segmentele care se suprapun cu [page_start, page_end]
                for page_num in range(page_start, page_end + 1):
                    segment_id = self.segment_cache.get((source_id, page_num, page_num))
                    if not segment_id:
                        print(f"  Warning: Segment pentru pagina {page_num} nu găsit")
                        continue

                    cur.execute(query, (
                        exercise_id,
                        segment_id,
                        'statement'  # role: statement / solution / etc.
                    ))
                    self.stats['exercise_source_segments'] += 1

            self.conn.commit()

        print(f"✓ Creat {self.stats['exercise_source_segments']} legături exercise-segment")

    def run(self):
        """Rulează importul complet."""
        print("=== Import JSON în baza de date ===\n")

        # 1. Încarcă JSON
        print(f"Încărcare JSON din: {self.json_path}")
        data = self.load_json()
        print(f"✓ JSON încărcat: {data.get('schema_version', 'unknown')}\n")

        # Obține conexiune la DB
        conn_gen = get_db_conn()
        self.conn = next(conn_gen)

        try:
            # 2. Import SOURCES
            print("Pas 1: Import SOURCES")
            source_data = data['source']
            source_id = self.import_source(source_data)
            print()

            # 3. Import SOURCE_SEGMENTS
            print("Pas 2: Import SOURCE_SEGMENTS")
            page_count = source_data.get('page_count', 0)
            self.import_source_segments(source_id, page_count)
            print()

            # 4. Import TAGS
            print("Pas 3: Import TAGS")
            self.import_tags(data['tag_catalog'])
            print()

            # 5. Import EXERCISES
            print("Pas 4: Import EXERCISES")
            self.import_exercises(data['exercises'])
            print()

            # 6. Import EXERCISE_TAGS
            print("Pas 5: Import EXERCISE_TAGS")
            self.import_exercise_tags(data['exercises'])
            print()

            # 7. Import EXERCISE_SOURCE_SEGMENTS
            print("Pas 6: Import EXERCISE_SOURCE_SEGMENTS")
            self.import_exercise_source_segments(data['exercises'], source_id)
            print()

            # Raport final
            print("=== SUMAR ===")
            for key, value in self.stats.items():
                print(f"  {key}: {value}")
            print("\n✓ Import finalizat cu succes!")

        except Exception as e:
            print(f"\n✗ Eroare la import: {e}")
            self.conn.rollback()
            raise
        finally:
            try:
                next(conn_gen)
            except StopIteration:
                pass

    # --- Helper methods ---

    def _find_source_by_external_id(self, external_id: str) -> Optional[uuid.UUID]:
        """Găsește o sursă după external_id din câmpul notes."""
        query = """
        SELECT id FROM sources
        WHERE notes LIKE %s
        LIMIT 1
        """
        with self.conn.cursor() as cur:
            # Caută în text pentru external_id (notes este TEXT, nu JSONB)
            cur.execute(query, (f'%"external_id": "{external_id}"%',))
            row = cur.fetchone()
            return row[0] if row else None

    def _find_exercise_by_external_id(self, external_id: str) -> Optional[uuid.UUID]:
        """Găsește un exercițiu după external_id din câmpul metadata."""
        query = """
        SELECT id FROM exercises
        WHERE metadata::jsonb->>'external_id' = %s
        LIMIT 1
        """
        with self.conn.cursor() as cur:
            cur.execute(query, (external_id,))
            row = cur.fetchone()
            return row[0] if row else None


def main():
    """Entry point."""
    if len(sys.argv) < 2:
        print("Usage: python import_json.py <path-to-json> [--include-containers]")
        print("\nExample:")
        print("  python import_json.py test.json")
        print("  python import_json.py test.json --include-containers")
        sys.exit(1)

    json_path = sys.argv[1]
    include_containers = '--include-containers' in sys.argv

    if not Path(json_path).exists():
        print(f"Eroare: Fișierul {json_path} nu există!")
        sys.exit(1)

    importer = JSONImporter(json_path, include_containers=include_containers)
    importer.run()


if __name__ == '__main__':
    main()
