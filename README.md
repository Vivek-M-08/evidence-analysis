# 📊 Evidence Analysis with AI

This Streamlit app enables users to analyze classroom evidence images using AI models (Gemini or OpenAI). The app allows input of custom questions and provides AI-generated answers and reasoning.

---

## 🚀 Features

- Upload or link to an image (evidence)
- Input up to 7 custom questions
- Use AI to answer questions and explain reasoning
- Display image preview and AI output
- Token switching for Gemini API
- Modular backend in `ai/process_evidence.py`

---

## 🧰 Tech Stack

- [Python](https://www.python.org/)
- [Streamlit](https://streamlit.io/)
- [Google Gemini API](https://ai.google.dev/)
- [OpenAI API](https://platform.openai.com/)
- [httpx](https://www.python-httpx.org/), [base64](https://docs.python.org/3/library/base64.html)

---

## 📂 Project Structure

```
.
├── ai/
│   └── process_evidence.py     # AI logic for image and question processing
├── utils/
│   └── auth.py (basic authentication)
├── app.py (your app logic)
├── evidence_analysis.py 
├── .gitignore
├── README.md
└── requirements.txt
```

---

## 🔧 Setup Instructions

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-username/evidence-analysis.git
   cd evidence-analysis
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Add your API keys**:
    - Create a `.env` file or securely inject them in the `ai/process_evidence.py`
    - Required keys:
        - `GEMINI`, `GEMINI_1` (Google Gemini API keys)
        - `llama-evidence-analysis` (OpenAI-compatible endpoint API key)

4. **Run the app**:
   ```bash
   streamlit run app.py
   ```

---

## 🧪 Example Usage

1. Enter up to 7 custom evaluation questions.
2. Paste a public URL of an image showing evidence (e.g., classroom project photo).
3. Click **"🔍 Analyse"**.
4. Get AI-generated YES/NO answers with reasonings.
5. See relevance tag and image preview.

---

## 🛡️ Notes

- Make sure your Gemini/OpenAI API keys have sufficient quota.
- Gemini's `response_schema` requires accurate schema handling and token management.

---

## 📜 License

MIT License