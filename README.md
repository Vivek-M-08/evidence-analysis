# 📊 Evidence Analysis with AI

Streamlit app to analyze classroom evidence images and classify challenge statements using AI models (Gemini, OpenAI, Anthropic).

## Key Features
- Image evidence analysis with YES/NO answers + short reasoning.
- Thematic classification of challenge statements with PII detection.
- Story rating (PDF-only) with 3-criterion scoring and tiering.
- Interactive Streamlit UI with pages:
  - [Evidence Analysis page](pages/evidence_analysis_page.py)
  - [Thematic Analysis page](pages/thematic_analysis_page.py)
  - [Story Ranker page](pages/story_rating_page.py)
- Exportable interactive HTML report ([report.html](report.html)).

## Important Files & Functions
- Core AI/image logic: [`ai/process_evidence.py`](ai/process_evidence.py) — function: [`analyze_evidence`](ai/process_evidence.py)
- Thematic classifier: [`ai/thematic_processor.py`](ai/thematic_processor.py) — function: [`analyze_thematic_challenge`](ai/thematic_processor.py)
- Story rating (PDF-based): [`ai/story_processor.py`](ai/story_processor.py) — functions: [`analyze_story_rating`](ai/story_processor.py), [`process_pdf_and_extract_text`](ai/story_processor.py)
- Streamlit app entry: [`app.py`](app.py)
- Page modules:
  - [`pages/evidence_analysis_page.py`](pages/evidence_analysis_page.py)
  - [`pages/thematic_analysis_page.py`](pages/thematic_analysis_page.py)
  - [`pages/story_rating_page.py`](pages/story_rating_page.py)

## Setup

1. Create a virtual environment and install dependencies:
```sh
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r [requirements.txt](http://_vscodecontentref_/0)
```

2. Add API keys in a .env file (placed in project root). Required keys used by the code:
```sh
GEMINI_API_KEYS=key1,key2        # comma-separated Gemini (Google) keys (used by ai/*)
OPENAI_API_KEY=your_openai_key   # used by OpenAI client (ChatGPT paths)
ANTHROPIC_API_KEY=your_claude_key
TOGETHER_API_KEY=optional        # used as OpenAI-compatible fallback in [process_evidence.py](http://_vscodecontentref_/1)
```

* The code expects GEMINI_API_KEYS (plural) and manages token rotation. See ai/process_evidence.py and ai/story_processor.py.
* If you rely on PDF extraction for story rating, install PyMuPDF (pip install PyMuPDF) — required by ai/story_processor.py.

3. Run the app:
```sh
streamlit run app.py
```

## Usage Notes

- Evidence analysis: enter up to 7 questions + public image URL on the Evidence Analysis page; the backend function is `analyze_evidence` (`ai/process_evidence.py`).
- Thematic analysis: paste challenge statements (pipe `|` separated) on Thematic Analysis page; the backend is `analyze_thematic_challenge` (`ai/thematic_processor.py`).
- Story rating: provide Title + PDF URL on Story Ranker page; PDF text is extracted and analyzed by `analyze_story_rating` (`ai/story_processor.py`).
- The HTML report is served from `report.html` via the "Reports" button on the Evidence Analysis page or the Reports navigation.

## Troubleshooting & Tips

- PDF extraction failing → ensure `PyMuPDF` is installed (`pip install PyMuPDF`) and PDF URLs are accessible; check errors printed by `process_pdf_and_extract_text` (`ai/story_processor.py`).
- Gemini token exhaustion / rate limits → use multiple keys in `GEMINI_API_KEYS` (comma-separated). Token rotation is implemented in `ai/process_evidence.py`.
- OpenAI / Anthropic clients require their respective Python SDKs (`openai`, `anthropic`) — the code checks for imports and returns informative errors if missing.
- If model responses include extra text or code fences, the processors attempt to extract JSON using `extract_json_from_text` / parsing helpers found in `ai/story_processor.py` and `ai/thematic_processor.py`.

## Security & Data

- Do not commit `.env` to version control. Ensure `.env` is listed in `.gitignore`.
- PII detection is implemented by the thematic classifier; review detected flags before exporting or sharing data.

## References

See implementation details in:
- `ai/process_evidence.py`
- `ai/thematic_processor.py`
- `ai/story_processor.py`
- Streamlit pages:
  - `pages/evidence_analysis_page.py`
  - `pages/thematic_analysis_page.py`
  - `pages/story_rating_page.py`