"""
Variant Generator - Generare automată de variante pe baza unor criterii
"""
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
import uuid
from psycopg import Connection
from psycopg.rows import dict_row


@dataclass
class ExamStructure:
    """Definește structura unui tip de examen"""
    exam_type: str
    subjects: List[Dict[str, Any]]  # Lista de subiect cu structura lor

    @staticmethod
    def get_bacalaureat_structure(profile: str = "mate-info") -> 'ExamStructure':
        """Structura pentru Bacalaureat Matematică"""
        return ExamStructure(
            exam_type="bacalaureat",
            subjects=[
                {
                    "name": "Subiectul I",
                    "item_type": "subiect_1",
                    "count": 6,
                    "has_variants": False,
                    "points_each": 5,
                    "subject_parts": ["algebra", "analiza", "geometrie"]  # diverse teme
                },
                {
                    "name": "Subiectul II",
                    "item_type": "subiect_2",
                    "count": 2,  # 2 probleme
                    "has_variants": True,
                    "variants_per_problem": 3,  # a, b, c
                    "points_each": 15,  # 15p per problemă (3 variante x 5p)
                    "subject_parts": ["algebra", "analiza"]
                },
                {
                    "name": "Subiectul III",
                    "item_type": "subiect_3",
                    "count": 2,  # 2 probleme
                    "has_variants": True,
                    "variants_per_problem": 3,  # a, b, c
                    "points_each": 15,  # 15p per problemă
                    "subject_parts": ["geometrie", "trigonometrie"]
                }
            ]
        )

    @staticmethod
    def get_evaluare_nationala_structure() -> 'ExamStructure':
        """Structura pentru Evaluare Națională"""
        return ExamStructure(
            exam_type="evaluare_nationala",
            subjects=[
                {
                    "name": "Subiectul I",
                    "item_type": "subiect_1",
                    "count": 6,
                    "has_variants": False,
                    "points_each": 5,
                    "subject_parts": ["algebra", "geometrie", "probabilitati"]
                },
                {
                    "name": "Subiectul II",
                    "item_type": "subiect_2",
                    "count": 3,
                    "has_variants": False,
                    "points_each": 10,
                    "subject_parts": ["algebra", "geometrie"]
                }
            ]
        )


class VariantGenerator:
    """Generator automat de variante pe baza unor criterii"""

    def __init__(self, conn: Connection):
        self.conn = conn

    def generate_variant(
        self,
        name: str,
        exam_type: str,
        profile: Optional[str] = None,
        year: Optional[int] = None,
        session: Optional[str] = None,
        difficulty_range: tuple = (3, 7),  # (min, max) 1-10
        preferred_tags: Optional[List[str]] = None,
        exclude_tags: Optional[List[str]] = None,
        duration_minutes: int = 180
    ) -> Dict[str, Any]:
        """
        Generează automat o variantă completă pe baza criteriilor

        Args:
            name: Numele variantei
            exam_type: Tipul examenului (bacalaureat, evaluare_nationala, etc.)
            profile: Profilul (mate-info, real, uman, etc.)
            year: Anul pentru care se generează
            session: Sesiunea (iunie, august, simulare, etc.)
            difficulty_range: Intervalul de dificultate (min, max)
            preferred_tags: Tag-uri preferate pentru selecție
            exclude_tags: Tag-uri de exclus
            duration_minutes: Durata examenului în minute

        Returns:
            Dict cu variant_id și lista de exercise_ids adăugate
        """
        # 1. Obține structura examenului
        if exam_type == "bacalaureat":
            structure = ExamStructure.get_bacalaureat_structure(profile or "mate-info")
        elif exam_type == "evaluare_nationala":
            structure = ExamStructure.get_evaluare_nationala_structure()
        else:
            raise ValueError(f"Exam type {exam_type} not supported for auto-generation")

        # 2. Creează varianta în DB
        variant_id = self._create_variant_entry(
            name=name,
            exam_type=exam_type,
            profile=profile,
            year=year,
            session=session,
            duration_minutes=duration_minutes,
            structure=structure
        )

        # 3. Generează și adaugă exercițiile pentru fiecare subiect
        all_exercise_ids = []
        order_index = 0

        for subject in structure.subjects:
            exercises = self._select_exercises_for_subject(
                subject=subject,
                exam_type=exam_type,
                profile=profile,
                difficulty_range=difficulty_range,
                preferred_tags=preferred_tags,
                exclude_tags=exclude_tags
            )

            # Adaugă exercițiile la variantă
            for exercise_id in exercises:
                self._add_exercise_to_variant(
                    variant_id=variant_id,
                    exercise_id=exercise_id,
                    order_index=order_index,
                    section_name=subject["name"]
                )
                all_exercise_ids.append(exercise_id)
                order_index += 1

        # 4. Actualizează punctajul total
        total_points = sum(s["points_each"] * s["count"] for s in structure.subjects)
        self._update_variant_points(variant_id, total_points)

        return {
            "variant_id": str(variant_id),
            "exercise_count": len(all_exercise_ids),
            "total_points": total_points,
            "structure": [
                {
                    "subject": s["name"],
                    "exercises": s["count"] * (s.get("variants_per_problem", 1) if s.get("has_variants") else 1)
                }
                for s in structure.subjects
            ]
        }

    def _create_variant_entry(
        self,
        name: str,
        exam_type: str,
        profile: Optional[str],
        year: Optional[int],
        session: Optional[str],
        duration_minutes: int,
        structure: ExamStructure
    ) -> uuid.UUID:
        """Creează intrarea pentru variantă în DB"""
        query = """
        INSERT INTO variants (name, exam_type, profile, year, session, duration_minutes, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id;
        """

        with self.conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, (
                name, exam_type, profile, year, session, duration_minutes, 'DRAFT'
            ))
            result = cur.fetchone()
            self.conn.commit()
            return result['id']

    def _select_exercises_for_subject(
        self,
        subject: Dict[str, Any],
        exam_type: str,
        profile: Optional[str],
        difficulty_range: tuple,
        preferred_tags: Optional[List[str]],
        exclude_tags: Optional[List[str]]
    ) -> List[uuid.UUID]:
        """
        Selectează exercițiile pentru un subiect specific
        """
        item_type = subject["item_type"]
        count_needed = subject["count"]

        if subject.get("has_variants"):
            # Pentru subiectele cu variante (a, b, c), avem nevoie de mai multe exerciții
            count_needed = count_needed * subject.get("variants_per_problem", 3)

        # Construiește query-ul pentru selecție - flexibil pentru datele existente
        conditions = [
            "difficulty >= %s",
            "difficulty <= %s",
            "(status != 'ARCHIVED' OR status IS NULL)"
        ]
        params = [difficulty_range[0], difficulty_range[1]]

        # Încearcă să filtrezi pe item_type, dar fii flexibil
        item_type_condition = "(item_type = %s OR item_type = 'exercitiu' OR item_type IS NULL)"
        conditions.append(item_type_condition)
        params.append(item_type)

        # Filtrare pe exam_type dacă e disponibil
        if exam_type:
            conditions.append("(exam_type = %s OR exam_type IS NULL)")
            params.append(exam_type)

        where_clause = " AND ".join(conditions)

        query = f"""
        SELECT id
        FROM exercises
        WHERE {where_clause}
        ORDER BY RANDOM()
        LIMIT %s;
        """
        params.append(count_needed)

        with self.conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, params)
            results = cur.fetchall()

            # Dacă nu am găsit suficiente, relaxează condițiile
            if len(results) < count_needed:
                print(f"⚠️  Found only {len(results)}/{count_needed} exercises for {subject['name']}, relaxing conditions...")

                # Query mai permisiv - ia orice exercițiu din intervalul de dificultate
                relaxed_query = """
                SELECT id
                FROM exercises
                WHERE difficulty >= %s
                  AND difficulty <= %s
                  AND (status != 'ARCHIVED' OR status IS NULL)
                ORDER BY RANDOM()
                LIMIT %s;
                """
                cur.execute(relaxed_query, (difficulty_range[0], difficulty_range[1], count_needed))
                results = cur.fetchall()

            return [row['id'] for row in results]

    def _add_exercise_to_variant(
        self,
        variant_id: uuid.UUID,
        exercise_id: uuid.UUID,
        order_index: int,
        section_name: str
    ):
        """Adaugă un exercițiu la variantă"""
        query = """
        INSERT INTO variant_exercises (variant_id, exercise_id, order_index, section_name)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (variant_id, exercise_id) DO NOTHING;
        """

        with self.conn.cursor() as cur:
            cur.execute(query, (variant_id, exercise_id, order_index, section_name))
        self.conn.commit()

    def _update_variant_points(self, variant_id: uuid.UUID, total_points: int):
        """Actualizează punctajul total al variantei"""
        query = "UPDATE variants SET total_points = %s WHERE id = %s;"

        with self.conn.cursor() as cur:
            cur.execute(query, (total_points, variant_id))
        self.conn.commit()


def get_variant_generator(conn: Connection) -> VariantGenerator:
    """Factory function pentru VariantGenerator"""
    return VariantGenerator(conn)
