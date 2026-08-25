# 🥗 NutriMenu AI — Intelligent Menu OCR & 3-Tier Nutrition Recommender

NutriMenu AI bridges physical and digital restaurant menus with personalized biometric health matrices to classify food dishes into three distinct clinical and nutritional tiers: **🟢 GOOD**, **🟡 MEDIUM**, and **🔴 BAD**.

---

## 🏛️ System Architecture

```text
User Health Profile (Biometrics, Medical Conditions, Allergens, Diets)
                     │
                     ▼
Model 2: Personalized Health Matrix Generator (BMR, TDEE, Macros, Clinical Guardrails)
                     │
                     ▼
Model 1: Menu Input (Preset Menu / OCR Image Scanner / Manual Input)
                     │
                     ▼
Deterministic Safety Rule Engine (Hard Allergen & Dietary Exclusions -> BAD [Score 0])
                     │
                     ▼
Nutritional Compatibility & Feature Scoring (Caloric Fit, Sodium, Glycemic Index, Macros)
                     │
                     ▼
Model 3: 3-Tier Matchmaker Dashboard (🟢 GOOD, 🟡 MEDIUM, 🔴 BAD)
                     │
                     ▼
Streamlit Web UI & Export Reports (.md / .json)
```

---

## ✨ Key Features

1. **Deterministic Safety-First Authority**:
   - Hard exclusions (e.g. peanuts for peanut allergy, non-veg for vegetarian/vegan) are evaluated by a 100% deterministic rule engine.
   - Hard conflicts immediately assign **Tier 🔴 BAD (Fit Score = 0)**. AI models cannot override safety exclusions.
2. **Offline Independence**:
   - The entire pipeline operates completely offline without an API key using deterministic scientific calculators (Mifflin-St Jeor) and local deep OCR (EasyOCR / PyTorch).
3. **Optional Gemini AI Enrichment**:
   - When configured with `GEMINI_API_KEY`, Google Gemini provides enhanced semantic menu hierarchy extraction, typo auto-correction, and natural-language culinary tips.
4. **4-Stage OCR Pipeline**:
   - **Stage A (Validation)**: Validates formats, readability, dimensions.
   - **Stage B (Deep OCR)**: Offline CRAFT text detection & CRNN text recognition.
   - **Stage C (Layout Analysis)**: Multi-column parsing and line merging.
   - **Stage D (Normalization)**: Deduplication, price extraction, and calibrated confidence estimation.
5. **Automatic GPU $\to$ CPU Fallback**:
   - Seamlessly uses CUDA GPU when available, falling back gracefully to CPU if GPU initialization fails.

---

## 🚀 Quick Start

### 1. Installation

Clone the repository and install dependencies:

```bash
git clone https://github.com/CodeClosed/AI-Project.git
cd AI-Project
pip install -r requirements.txt
```

### 2. Environment Configuration (Optional)

Create a `.env` file in the project root to enable Gemini AI features (never commit real secrets):

```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
```

> **Note**: If no `GEMINI_API_KEY` is provided, NutriMenu AI automatically runs using its deterministic offline engines.

### 3. Launch the Web Application

Launch with Streamlit:

```bash
streamlit run app.py
```

Or using the launcher:

```bash
python run_ui.py
```

Open your browser at `http://localhost:8501`.

---

## 🧪 Running Automated Tests

Run the complete test suite offline with pytest:

```bash
python -m pytest -v
```

Verify Python syntax and byte-compilation:

```bash
python -m compileall src tests app.py run_ui.py
```

---

## 📁 Repository Structure

```text
├── app.py                     # Streamlit Web UI Orchestration
├── run_ui.py                  # CLI App Launcher
├── requirements.txt           # Project Dependencies
├── src/
│   ├── config.py              # Centralized Configuration & Model Resolver
│   ├── gemini_client.py       # Robust Gemini API HTTP Client with Error Mapping
│   ├── matrix_generator.py    # Standalone User Nutritional Matrix Generator
│   ├── nutrition_ai.py        # Clinical Health Matrix Profiler
│   ├── models.py              # Menu Recognition & Layout Data Models
│   ├── user_models.py         # User Profile & Clinical Biomarker Models
│   ├── recommendation_engine.py# 3-Tier Matchmaking & Safety Rule Engine
│   ├── dish_evaluator.py      # Dish & Ingredient Evaluator
│   ├── pipeline.py            # Unified OCR & Menu Parsing Pipeline
│   ├── ocr_engine.py          # Local PyTorch EasyOCR Engine (GPU/CPU Fallback)
│   ├── preprocessing.py       # Image Enhancement, Deskew, Illumination Normalization
│   ├── layout_analyzer.py     # Spatial Geometry & Multi-Column Analysis
│   ├── menu_parser.py         # Semantic Price, Category & Dietary Tag Parser
│   ├── visualizer.py          # Diagnostic Visual Annotation Tool
│   ├── sample_data.py         # Sample Restaurant Menus
│   └── ui_components.py       # Modular Streamlit Presentation Components
├── tests/
│   ├── test_gemini_client.py  # Mocked API Layer Tests (200, 400, 401, 404, 429, 500, timeout)
│   ├── test_safety_and_rules.py# Hard Exclusion, Allergy, and Guardrail Tests
│   ├── test_integration_pipeline.py # End-to-End Pipeline Integration Tests
│   ├── test_matrix_generator.py # User Matrix Generator Unit Tests
│   ├── test_nutrition_ai.py   # Nutrition Profiler Unit Tests
│   ├── test_recognizer.py     # OCR & Layout Parsing Unit Tests
│   └── test_recommendation_engine.py # 3-Tier Engine Unit Tests
└── doc/                       # Technical Specifications & Documentation
```

---

## ⚖️ Nutritional Guidance Disclaimer

NutriMenu AI provides personalized computational nutritional estimates and dietary suggestions based on user-entered parameters and clinical nutritional reference standards. It does not provide medical diagnoses, treatment plans, or formal healthcare prescriptions. Individuals with acute medical conditions, severe allergies, or clinical dietary requirements should always consult a licensed medical professional or registered dietitian.
