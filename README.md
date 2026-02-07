# EtoXPlatform
Proiectul vizează dezvoltarea unei aplicații educaționale moderne care automatizează procesul de colectare, organizare, validare și generare a exercițiilor școlare, utilizând tehnologii avansate de procesare a datelor și inteligență artificială. Sistemul este conceput să acopere întregul ciclu de viață al conținutului educațional 


# 📚 EtoXPlatform - Sistem de Gestiune Conținut Educațional

Platformă completă pentru procesarea, organizarea și gestionarea exercițiilor matematice din documente PDF, cu suport pentru recunoaștere formule LaTeX.

![Status](https://img.shields.io/badge/status-functional-brightgreen)
![Version](https://img.shields.io/badge/version-1.0.1-blue)
![Python](https://img.shields.io/badge/python-3.12+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.128.0-green)
![React](https://img.shields.io/badge/React-18-61dafb)

---

## ✨ Features

✅ **Upload automat PDF** cu procesare inteligentă
✅ **OCR avansat** cu pix2text pentru text și formule matematice LaTeX
✅ **Salvare automată** în baza de date PostgreSQL
✅ **API REST complet** pentru management exerciții, surse, segmente
✅ **Interfață React modernă** pentru upload și vizualizare
✅ **Suport multilingual** (inclusiv română)
✅ **Recunoaștere formule LaTeX** din imagini

---


### Prerequisite

1. **Python 3.12+**
2. **Node.js 18+**
3. **PostgreSQL** (sau Neon DB)
4. **Poppler** (OBLIGATORIU):
   ```bash
   # macOS
   brew install poppler

   # Ubuntu/Debian
   sudo apt-get install poppler-utils
   ```

### Instalare și Pornire

1. **Clone repository**
   ```bash
   cd edu_content_app
   ```

2. **Setup Backend**
   ```bash
   cd edu_content_api
   source venv/bin/activate
   pip install -r requirements.txt
   uvicorn main:app --reload
   ```
   Backend: http://localhost:8000
   API Docs: http://localhost:8000/docs

3. **Setup Frontend**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
   Frontend: http://localhost:5173

---

## 📖 Documentație

- **[SETUP_QUICK.md](SETUP_QUICK.md)** - Setup rapid în 3 pași
- **[INTEGRATION_SUMMARY.md](INTEGRATION_SUMMARY.md)** - Documentație completă integrare
- **[POPPLER_FIX.md](POPPLER_FIX.md)** - Rezolvare problemă poppler
- **[BUGFIX_SUMMARY.md](BUGFIX_SUMMARY.md)** - Bug-uri rezolvate
- **[CHANGELOG.md](CHANGELOG.md)** - Istoric modificări

---

## 🏗️ Arhitectură

### Stack Tehnologic

**Backend:**
- FastAPI (Python 3.12)
- PostgreSQL (Neon DB)
- pix2text (OCR + LaTeX)
- pdf2image + poppler

**Frontend:**
- React + TypeScript
- Vite
- Modern CSS

### Structură Baza de Date

```
sources              → Documente PDF încărcate
  ├── source_segments    → Segmente extrase din PDF-uri
  └── exercises          → Exerciții identificate
       ├── assets            → Imagini, diagrame
       ├── exercise_tags     → Tag-uri domenii matematice
       └── variants          → Variante de examen
```

Vezi `INTEGRATION_SUMMARY.md` pentru schema completă.

---

## 🔌 API Endpoints

### Sources (Surse)
- `POST /sources/` - Creează sursă nouă
- `GET /sources/` - Listează toate sursele
- `GET /sources/{id}` - Detalii sursă
- `PUT /sources/{id}` - Actualizează sursă
- `DELETE /sources/{id}` - Șterge sursă

### Processing (Procesare)
- `POST /upload-and-process/` - Upload + procesare automată PDF
- `POST /process-pdf/{source_id}` - Procesează PDF existent
  - Query params: `page_start`, `page_end` (opțional)

### Exercises (Exerciții)
- `POST /exercises/` - Creează exercițiu
- `GET /exercises/` - Listează exerciții
  - Query params: `exam_type`, `status`
- `GET /exercises/{id}` - Detalii exercițiu
- `PUT /exercises/{id}` - Actualizează exercițiu
- `DELETE /exercises/{id}` - Șterge exercițiu

### Segments (Segmente)
- `POST /source-segments/` - Creează segment
- `GET /source-segments/` - Listează segmente
  - Query params: `source_id`
- `GET /source-segments/{id}` - Detalii segment

**API Documentation interactivă:** http://localhost:8000/docs

---

## 💡 Exemple Utilizare

### Upload și Procesare PDF

```bash
curl -X POST "http://localhost:8000/upload-and-process/" \
  -F "file=@bacalaureat_2024.pdf" \
  -F "source_name=Bacalaureat Matematică 2024" \
  -F "source_type=oficial" \
  -F "source_year=2024" \
  -F "source_session=iunie"
```

**Răspuns:**
```json
{
  "source_id": "uuid-here",
  "segment_id": "uuid-here",
  "pages": [
    {
      "page_number": 1,
      "raw_text": "Subiectul I...",
      "latex_formulas": ["$x^2 + 5x + 6 = 0$"],
      "width": 595,
      "height": 842
    }
  ],
  "combined_text": "--- Page 1 ---\nSubiectul I...",
  "total_pages": 4,
  "status": "success"
}
```

### Creare Exercise

```bash
curl -X POST "http://localhost:8000/exercises/" \
  -H "Content-Type: application/json" \
  -d '{
    "exam_type": "bacalaureat",
    "item_type": "subiect_1",
    "statement_latex": "Să se rezolve ecuația: $x^2 + 5x + 6 = 0$",
    "answer_latex": "$x_1 = -2, x_2 = -3$",
    "subject_part": "algebra",
    "difficulty": 3,
    "points": 10,
    "status": "READY"
  }'
```

---

## 🐛 Troubleshooting

### Eroare: "Unable to get page count"
**Cauză:** Poppler nu este instalat
**Soluție:** `brew install poppler` (macOS) sau vezi `POPPLER_FIX.md`

### Procesarea este lentă
**Normal:** pix2text folosește modele deep learning (CPU-intensiv)
**Soluție:** Pentru producție, folosiți GPU

### Eroare conexiune bază de date
**Soluție:** Verificați `DATABASE_URL` în `.env`

Vezi `BUGFIX_SUMMARY.md` pentru mai multe soluții.

---

## 🛣️ Roadmap

### ✅ Phase 1 - Core Infrastructure (Complet)
- [x] Backend FastAPI complet
- [x] Integrare pix2text
- [x] Salvare automată în DB
- [x] Frontend React funcțional

### 🔄 Phase 2 - Smart Processing (În Progres)
- [ ] Identificare automată exerciții
- [ ] Segmentare pe baza pattern-urilor
- [ ] Extragere statement/answer/solution

### 📅 Phase 3 - Asset Management
- [ ] Extragere imagini din PDF
- [ ] Asociere automată cu exerciții
- [ ] Management diagrame/grafice

### 🤖 Phase 4 - AI Tagging
- [ ] Integrare OpenAI/Gemini
- [ ] Tag-uire automată domenii
- [ ] Clasificare dificultate

### 🎨 Phase 5 - Advanced UI
- [ ] Editor LaTeX cu preview
- [ ] Sistem revizuire/aprobare
- [ ] Generator variante PDF

---

## 📊 Status Actual

| Feature | Status |
|---------|--------|
| Upload PDF | ✅ Funcțional |
| OCR Text | ✅ Funcțional |
| LaTeX Recognition | ✅ Funcțional |
| Database Storage | ✅ Funcțional |
| CRUD API | ✅ Funcțional |
| Frontend UI | ✅ Funcțional |
| Auto Exercise Detection | ⏳ Planificat |
| AI Tagging | ⏳ Planificat |

---

## 🤝 Contributing

Proiect educațional - Dezvoltat cu asistența Claude AI Code

---

## 📝 License

Proprietary - Educational Use Only

---

## 📞 Support

Pentru probleme sau întrebări:
1. Consultați documentația în fișierele `.md`
2. Verificați logs în terminal
3. Accesați `/docs` pentru API documentation interactivă

---

**Versiune:** 1.0.1
**Data:** 2026-01-03
**Status:** ✅ Testing
