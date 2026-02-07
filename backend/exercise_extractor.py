import os
import json
import logging
from typing import List, Dict, Any, Optional
from openai import OpenAI
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class ExerciseExtractor:
    def __init__(self):
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        
        if self.openai_key:
            self.openai_client = OpenAI(api_key=self.openai_key)
            logger.info("ExerciseExtractor initialized with OpenAI")
        elif self.gemini_key:
            genai.configure(api_key=self.gemini_key)
            self.gemini_model = genai.GenerativeModel('gemini-1.5-pro')
            logger.info("ExerciseExtractor initialized with Gemini")
        else:
            logger.warning("No AI API key found. ExerciseExtractor will use MOCK mode for extraction.")

    def get_extraction_prompt(self, raw_text: str, context: Dict[str, Any]) -> str:
        return f"""
Ești un expert în digitizarea conținutului educațional (matematică). 
Sarcina ta este să extragi exercițiile individuale dintr-un text brut obținut prin OCR dintr-un PDF.

CONTEXT DOCUMENT:
- Tip examen: {context.get('exam_type', 'nespecificat')}
- An: {context.get('year', 'nespecificat')}
- Sesiune: {context.get('session', 'nespecificat')}
- Note: {context.get('notes', 'nespecificat')}

TEXT BRUT (OCR):
---
{raw_text}
---

CERINȚE:
1. Identifică fiecare exercițiu/problemă individuală.
2. Pentru fiecare exercițiu, extrage:
   - statement_latex: Enunțul complet în format LaTeX. Asigură-te că formulele matematice sunt încadrate corect (ex: $...$ sau $$...$$).
   - statement_text: Enunțul în text simplu (fără LaTeX pe cât posibil).
   - solution_latex: Soluția/Rezolvarea în format LaTeX (dacă este prezentă în text).
   - answer_latex: Răspunsul final scurt în format LaTeX.
   - scoring_guide_latex: Baremul de notare în format LaTeX (dacă este prezent).
   - points: Punctajul alocat (ex: 5, 10, 30).
   - item_type: Clasificarea (subiect_1, subiect_2, subiect_3, problema, exercitiu).
   - subject_part: Partea materiei (algebra, geometrie, analiza, trigonometrie).
   - difficulty: O estimare a dificultății de la 1 la 10.

3. Returnează rezultatul EXCLUSIV ca un obiect JSON valid cu structura:
{{
  "exercises": [
    {{
      "statement_latex": "...",
      "statement_text": "...",
      "solution_latex": "...",
      "answer_latex": "...",
      "scoring_guide_latex": "...",
      "points": 5,
      "item_type": "exercitiu",
      "subject_part": "algebra",
      "difficulty": 3
    }},
    ...
  ]
}}

Reguli importante:
- Separă fiecare exercițiu individual. Un document poate conține multe exerciții (ex: 10-20).
- Dacă textul conține marcaje de punctaj (ex: "5p", "10p", "5 puncte"), acestea indică de obicei finalul unui exercițiu sau al unei sub-cerințe.
- Dacă textul conține "Subiectul I", "Subiectul II", etc., folosește-le pentru a seta `item_type`.
- Păstrează diacriticele în română.
- Asigură-te că TOT conținutul matematic este în format LaTeX valid.
- Dacă o informație lipsește (ex: soluția), lasă câmpul respectiv null sau string gol.
- Returnează DOAR JSON-ul valid.
"""

    def extract_exercises(self, raw_text: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        if not raw_text or len(raw_text.strip()) < 10:
            return []
            
        if not self.openai_key and not self.gemini_key:
            return self._mock_extraction(raw_text)

        prompt = self.get_extraction_prompt(raw_text, context)
        
        try:
            if self.openai_key:
                response = self.openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}
                )
                result_text = response.choices[0].message.content
            elif self.gemini_key: # Gemini
                response = self.gemini_model.generate_content(prompt)
                result_text = response.text
                # Cleanup markdown
                if "```json" in result_text:
                    result_text = result_text.split("```json")[1].split("```")[0]
                elif "```" in result_text:
                    result_text = result_text.split("```")[1].split("```")[0]
            else:
                return self._mock_extraction(raw_text)

            data = json.loads(result_text)
            return data.get("exercises", [])
            
        except Exception as e:
            logger.error(f"Error during Exercise Extraction: {e}")
            return self._mock_extraction(raw_text)

    def _mock_extraction(self, raw_text: str) -> List[Dict[str, Any]]:
        """Fallback extraction when AI is not available."""
        logger.warning("Using MOCK extraction for exercises")
        
        import re
        
        # 1. Identify all markers and their positions
        # Markers: "5p", "10p", "30p", "1.", "2.", "SUBIECTUL I"
        point_pattern = r'(\b\d{1,2}\s*p\b)'
        num_pattern = r'(^\s*\d+[\.\)])'
        header_pattern = r'(\bSUBIECTUL\s+(?:I|II|III|al\s+[IVXLC]+-lea)\b)'
        
        # We split by points mostly as they are strong indicators of exercise end
        parts = re.split(point_pattern, raw_text)
        
        exercises = []
        # Pre-process parts to handle cases where multiple exercises are before a points marker
        # But for MOCK, we keep it simple: each points marker ends ONE exercise.
        
        for i in range(0, len(parts) - 1, 2):
            content = parts[i].strip()
            marker = parts[i+1].strip()
            
            if not content and i > 0:
                continue
                
            # Try to see if content contains multiple numbered exercises
            sub_parts = re.split(num_pattern, content, flags=re.MULTILINE)
            if len(sub_parts) > 1:
                # Add all except the last one as separate exercises
                for j in range(1, len(sub_parts) - 2, 2):
                    sub_ex_text = (sub_parts[j] + sub_parts[j+1]).strip()
                    if len(sub_ex_text) > 10:
                        exercises.append({
                            "statement_latex": sub_ex_text,
                            "statement_text": sub_ex_text,
                            "points": 5, # Default
                            "item_type": "exercitiu",
                            "difficulty": 5,
                            "exam_type": "alta"
                        })
                # The last sub-part goes with the current points marker
                current_statement = (sub_parts[-2] + sub_parts[-1] + " " + marker).strip()
            else:
                current_statement = (content + " " + marker).strip()
                
            if len(current_statement) > 10:
                points_match = re.search(r'(\d+)', marker)
                points = int(points_match.group(1)) if points_match else 5
                
                exercises.append({
                    "statement_latex": current_statement,
                    "statement_text": current_statement,
                    "points": points,
                    "item_type": "exercitiu",
                    "difficulty": 5,
                    "exam_type": "alta"
                })
        
        # Handle the remaining text after the last points marker
        last_part = parts[-1].strip()
        if last_part:
            # Check if there are more numbered exercises in the last part
            sub_parts = re.split(num_pattern, last_part, flags=re.MULTILINE)
            if len(sub_parts) > 1:
                for j in range(1, len(sub_parts), 2):
                    sub_ex_text = (sub_parts[j] + sub_parts[j+1]).strip()
                    if len(sub_ex_text) > 10:
                        exercises.append({
                            "statement_latex": sub_ex_text,
                            "statement_text": sub_ex_text,
                            "points": 5,
                            "item_type": "exercitiu",
                            "difficulty": 5,
                            "exam_type": "alta"
                        })
            elif len(last_part) > 20 and not exercises:
                exercises.append({
                    "statement_latex": last_part,
                    "statement_text": last_part,
                    "item_type": "exercitiu",
                    "difficulty": 5,
                    "exam_type": "alta"
                })
            elif len(last_part) > 50: # If it's long enough, maybe it's another exercise
                 exercises.append({
                    "statement_latex": last_part,
                    "statement_text": last_part,
                    "item_type": "exercitiu",
                    "difficulty": 5,
                    "exam_type": "alta"
                })

        return exercises

_extractor_instance = None

def get_exercise_extractor() -> ExerciseExtractor:
    global _extractor_instance
    if _extractor_instance is None:
        _extractor_instance = ExerciseExtractor()
    return _extractor_instance
