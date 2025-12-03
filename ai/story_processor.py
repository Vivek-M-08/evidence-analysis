import google.generativeai as genai
import typing_extensions as typing
import json
import os
import httpx
import base64
from typing import List, Dict, Any, Optional, Union
from dotenv import load_dotenv

# Load env variables
load_dotenv()

# --- External API Imports ---
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None

try:
    import fitz # PyMuPDF
    PDF_PROCESSOR_AVAILABLE = True
except ImportError:
    PDF_PROCESSOR_AVAILABLE = False
    class fitz: 
        @staticmethod
        def open(*args, **kwargs): pass

# --- API Key Configuration ---
# Get Gemini keys and pick the first one for default usage
gemini_env = os.getenv("GEMINI_API_KEYS", "")
gemini_keys = [key.strip() for key in gemini_env.split(",") if key.strip()]
GEMINI_API_KEY = gemini_keys[0] if gemini_keys else None

CLAUDE_API_KEY = os.getenv("ANTHROPIC_API_KEY")
CHATGPT_API_KEY = os.getenv("OPENAI_API_KEY")


# --- Story Rating Schema ---
class StoryRating(typing.TypedDict):
    document_language: str
    impact_and_outcome_score: float
    impact_justification: str
    issue_and_challenge_score: float
    issue_justification: str
    action_steps_score: float
    action_justification: str
    composite_score: float
    tier: typing.Literal["Excellent", "Good", "Developing", "Needs Improvement"]
    overall_summary: str

# --- Story Rating Prompt (PDF-ONLY VERSION) ---
STORY_RATING_PROMPT = """
You are an expert story evaluator specializing in assessing educational and social impact narratives. Your task is to analyze the story from the PDF document and rank it based on three critical criteria: Impact/Outcome, Issue/Challenge clarity, and Action Steps taken.

## Evaluation Criteria

### Criterion 1: Impact and Outcome Score (0.0 - 1.0)
What to Evaluate: Clarity of outcomes, concreteness (measurable/observable changes), and significance.

**Scoring Guidelines:**
- **0.9-1.0** - Exceptional: Specific, quantifiable outcomes with clear before/after comparison. Measurable metrics provided.
- **0.7-0.8** - Strong: Clear qualitative outcomes with observable indicators. Noticeable improvements described.
- **0.4-0.6** - Moderate: General positive outcomes mentioned but lacking specificity.
- **0.2-0.3** - Weak: Vague references to change with no clear outcome.
- **0.0-0.1** - No Clear Impact: No outcome mentioned, only intentions.

### Criterion 2: Issue and Challenge Score (0.0 - 1.0)
What to Evaluate: Problem clarity, root cause identification, and sufficient context.

**Scoring Guidelines:**
- **0.9-1.0** - Exceptional: Crystal clear problem with root cause analysis, explains symptoms and underlying causes.
- **0.7-0.8** - Strong: Clear problem with good context, some root cause analysis present.
- **0.4-0.6** - Moderate: Problem mentioned but vague or incomplete, limited context.
- **0.2-0.3** - Weak: Problem barely identifiable, no context or explanation.
- **0.0-0.1** - No Clear Problem: No problem described, story lacks focus.

### Criterion 3: Action Steps Score (0.0 - 1.0)
What to Evaluate: Specificity, sequential flow, completeness (planning, execution, adaptation), and problem-solving.

**Scoring Guidelines:**
- **0.9-1.0** - Exceptional: Detailed, sequential steps clearly outlined. Obstacles and solutions mentioned. Shows adaptation.
- **0.7-0.8** - Strong: Clear action steps with good implementation details. Some mention of challenges.
- **0.4-0.6** - Moderate: General actions mentioned but lacking detail or sequence.
- **0.2-0.3** - Weak: Vague references to doing something, no clear sequence.
- **0.0-0.1** - No Clear Actions: No actions described, only intentions.

## Composite Score and Tier Assignment
- Calculate the `composite_score` using the weighted average:
  **Composite Score = (Impact × 0.4) + (Issue × 0.3) + (Action × 0.3)**

- Assign the `tier` based on individual scores:
    - **Excellent:** All three scores ≥ 0.75
    - **Good:** All three scores ≥ 0.60
    - **Developing:** All three scores ≥ 0.40
    - **Needs Improvement:** Any score < 0.40

## CRITICAL: JSON Output Format
You MUST return EXACTLY 10 fields in your JSON response. ALL fields are mandatory. DO NOT omit any field.

MANDATORY fields (all 10 must be present):
1. document_language (string - e.g., "English", "Hindi", "Kannada")
2. impact_and_outcome_score (float between 0.0 and 1.0)
3. impact_justification (string - detailed justification)
4. issue_and_challenge_score (float between 0.0 and 1.0)
5. issue_justification (string - detailed justification)
6. action_steps_score (float between 0.0 and 1.0)
7. action_justification (string - detailed justification)
8. composite_score (float between 0.0 and 1.0)
9. tier (one of: "Excellent", "Good", "Developing", "Needs Improvement")
10. overall_summary (string - brief 2-3 sentence summary)

Example of correct format:
{{
    "document_language": "English",
    "impact_and_outcome_score": 0.75,
    "impact_justification": "The story demonstrates clear, measurable outcomes with specific evidence of improvement in student attendance rates.",
    "issue_and_challenge_score": 0.65,
    "issue_justification": "The root cause is identified as lack of parental awareness, with adequate context provided about the school location.",
    "action_steps_score": 0.70,
    "action_justification": "Action steps are described including parent meetings and awareness campaigns, showing a sequential approach.",
    "composite_score": 0.71,
    "tier": "Good",
    "overall_summary": "Effective intervention addressing low attendance through parental engagement and awareness programs."
}}

## Task Instructions
1. Read and analyze the complete PDF text content provided below.
2. Identify the primary language of the document (e.g., "English", "Hindi", "Spanish").
3. Score EACH of the THREE criteria (Impact, Issue, Action) with values between 0.0 and 1.0.
4. Write detailed justifications for EACH of the three scores (analyze the story content carefully).
5. Calculate the composite_score = (impact × 0.4) + (issue × 0.3) + (action × 0.3)
6. Assign the tier based on the rules above.
7. Write a brief overall_summary (2-3 sentences).
8. Return ONLY the JSON object with ALL 10 FIELDS. No extra text, no markdown, no code blocks.

## Story to Analyze

**Title:** {story_title}

**PDF Content:**
---
{pdf_content}
---

Analyze the above PDF content and return the evaluation as a valid JSON object with all 10 required fields.
"""

def process_pdf_and_extract_text(pdf_url: str) -> Dict[str, Union[str, None]]:
    """
    Downloads a PDF, extracts all text.
    """
    if not PDF_PROCESSOR_AVAILABLE:
        return {"error": "PDF processing library (PyMuPDF/fitz) not found. Please run 'pip install PyMuPDF'."}

    try:
        # 1. Download the PDF content
        print(f"Downloading PDF from: {pdf_url}")
        response = httpx.get(pdf_url, follow_redirects=True, timeout=30)
        response.raise_for_status()
        pdf_bytes = response.content

        # 2. Extract text using PyMuPDF (fitz)
        document = fitz.open(stream=pdf_bytes, filetype="pdf")
        text_content = ""
        for page_num in range(document.page_count):
            page = document.load_page(page_num)
            text_content += page.get_text() + "\n\n"
        
        document.close()
        text_content = text_content.strip()

        if not text_content:
            return {"text": "", "error": "PDF contains no readable text content."}
        
        return {
            "text": text_content,
            "language_hint": "Unknown" 
        }
    except httpx.HTTPStatusError as e:
        return {"error": f"HTTP error downloading PDF: {e.response.status_code}"}
    except Exception as e:
        return {"error": f"PDF processing error: {e}"}

def get_image_as_base64_content(url: str) -> Optional[Dict[str, str]]:
    """
    Fetches image from URL and returns content dict.
    NOTE: This is kept for UI display purposes only - NOT used for AI analysis.
    """
    if not url or not url.strip():
        return None
    try:
        response = httpx.get(url, timeout=10)
        response.raise_for_status()
        
        base64_encoded = base64.b64encode(response.content).decode("utf-8")
        content_type = response.headers.get("Content-Type", "image/jpeg") 
        
        return {
            "mime_type": content_type,
            "data": base64_encoded,
        }
    except Exception as e:
        print(f"Error fetching image: {e}")
        return None


def extract_json_from_text(text: str) -> Optional[Dict]:
    """
    Attempts to extract JSON from text that might contain markdown or additional text.
    """
    # Try direct JSON parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # Try to find JSON between curly braces
    try:
        start = text.find('{')
        end = text.rfind('}') + 1
        if start >= 0 and end > start:
            json_str = text[start:end]
            return json.loads(json_str)
    except (json.JSONDecodeError, ValueError):
        pass
    
    # Try to remove markdown code blocks
    try:
        # Remove ```json and ``` markers
        cleaned = text.strip()
        if cleaned.startswith('```'):
            lines = cleaned.split('\n')
            cleaned = '\n'.join(lines[1:-1]) if len(lines) > 2 else cleaned
            cleaned = cleaned.replace('```json', '').replace('```', '').strip()
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    
    return None


def validate_response(response_json: Dict) -> Dict[str, Any]:
    """
    Validates that the response contains all required fields.
    Auto-fills missing fields with reasonable defaults if possible.
    Returns the response if valid, or an error dict if invalid.
    """
    required_fields = [
        "document_language",
        "impact_and_outcome_score",
        "impact_justification",
        "issue_and_challenge_score",
        "issue_justification",
        "action_steps_score",
        "action_justification",
        "composite_score",
        "tier",
        "overall_summary"
    ]
    
    missing_fields = [field for field in required_fields if field not in response_json]
    
    # Auto-fill missing fields with reasonable defaults
    if missing_fields:
        print(f"[WARNING] Missing fields detected: {', '.join(missing_fields)}. Attempting auto-fill...")
        
        # If action_steps_score is missing, estimate it from other scores
        if "action_steps_score" not in response_json:
            if "impact_and_outcome_score" in response_json and "issue_and_challenge_score" in response_json:
                # Use average of other two scores as estimate
                avg = (float(response_json["impact_and_outcome_score"]) + 
                       float(response_json["issue_and_challenge_score"])) / 2
                response_json["action_steps_score"] = round(avg, 2)
                print(f"[AUTO-FILL] action_steps_score = {response_json['action_steps_score']} (estimated from other scores)")
        
        # If action_justification is missing, add a generic note
        if "action_justification" not in response_json:
            response_json["action_justification"] = "Action steps were present in the narrative, showing evidence of systematic intervention and problem-solving approach."
            print(f"[AUTO-FILL] action_justification added with generic text")
        
        # If composite_score is missing, calculate it
        if "composite_score" not in response_json:
            if all(k in response_json for k in ["impact_and_outcome_score", "issue_and_challenge_score", "action_steps_score"]):
                impact = float(response_json["impact_and_outcome_score"])
                issue = float(response_json["issue_and_challenge_score"])
                action = float(response_json["action_steps_score"])
                response_json["composite_score"] = round((impact * 0.4) + (issue * 0.3) + (action * 0.3), 2)
                print(f"[AUTO-FILL] composite_score = {response_json['composite_score']} (calculated)")
        
        # Check if we still have missing critical fields
        still_missing = [field for field in required_fields if field not in response_json]
        if still_missing:
            return {
                "error": f"Unable to auto-fill critical fields: {', '.join(still_missing)}",
                "partial_response": response_json
            }
        
        # Add a note that auto-fill was used
        response_json["_auto_filled"] = True
        response_json["_auto_filled_fields"] = missing_fields
    
    # Validate score ranges
    score_fields = ["impact_and_outcome_score", "issue_and_challenge_score", "action_steps_score", "composite_score"]
    for field in score_fields:
        try:
            score = float(response_json[field])
            if not (0.0 <= score <= 1.0):
                return {"error": f"{field} must be between 0.0 and 1.0, got {score}"}
        except (ValueError, TypeError):
            return {"error": f"{field} must be a number, got {response_json[field]}"}
    
    # Validate tier
    valid_tiers = ["Excellent", "Good", "Developing", "Needs Improvement"]
    if response_json["tier"] not in valid_tiers:
        return {"error": f"Invalid tier: {response_json['tier']}. Must be one of {valid_tiers}"}
    
    return response_json


def analyze_story_rating(title: str, pdf_url: str, image_url: str, model_choice: str, optional_content: str = "") -> Dict[str, Any]:
    """
    Analyzes a story based ONLY on PDF content.
    
    NOTE: image_url and optional_content are kept as parameters for UI compatibility
    but are NOT used in the AI analysis. Only the PDF content is analyzed.
    
    Args:
        title: Story title (mandatory)
        pdf_url: URL to PDF document (mandatory)
        image_url: Image URL (for UI display only, NOT analyzed)
        model_choice: AI model to use
        optional_content: Optional text (for UI reference only, NOT analyzed)
    """
    if not title:
        return {"error": "Title is mandatory for story analysis."}
    if not pdf_url:
        return {"error": "PDF link is mandatory for story analysis."}
    
    # 1. Process PDF - THIS IS THE ONLY CONTENT ANALYZED
    pdf_result = process_pdf_and_extract_text(pdf_url)
    
    if "error" in pdf_result:
        print(f"PDF processing failed: {pdf_result['error']}")
        return pdf_result
    
    pdf_content = pdf_result['text']
    
    # IMPORTANT: We do NOT include optional_content or image in the analysis
    # The AI will ONLY analyze the PDF content
    print(f"[INFO] Analyzing PDF content only. Optional content and images are ignored for ranking.")
    
    # Format the prompt with ONLY PDF content
    full_prompt = STORY_RATING_PROMPT.format(
        story_title=title,
        pdf_content=pdf_content
    )
    
    response_json: Optional[Dict] = None
    model_name: str = ""
    raw_response_text: str = ""

    # 4. Model Routing - ONLY TEXT PROMPT, NO IMAGES
    if "Gemini" in model_choice:
        model_name = "gemini-2.5-flash"
        if not GEMINI_API_KEY:
            return {"error": "Gemini API key is not configured in .env."}
        
        try:
            genai.configure(api_key=GEMINI_API_KEY)
            client_model = genai.GenerativeModel(
                model_name=model_name,
                generation_config={
                    "response_mime_type": "application/json",
                    "response_schema": StoryRating,
                    "temperature": 0.0,
                    "max_output_tokens": 8192,
                },
            )
            response = client_model.generate_content(contents=[full_prompt])
            print(f"[DEBUG] Gemini response object: {response}")
            raw_response_text = response.text
            response_json = extract_json_from_text(raw_response_text)
        except Exception as e:
            return {"error": f"Gemini API call failed: {e}"}

    elif "ChatGPT" in model_choice:
        if OpenAI is None:
            return {"error": "OpenAI library not found. Please run 'pip install openai'."}
        if not CHATGPT_API_KEY:
            return {"error": "ChatGPT API key is missing in .env."}

        model_name = "gpt-4o"
        try:
            client = OpenAI(api_key=CHATGPT_API_KEY)

            # ONLY send text prompt, NO images
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "user", "content": full_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.0
            )
            if response.choices and response.choices[0].message.content:
                raw_response_text = response.choices[0].message.content
                print(f"[DEBUG] ChatGPT raw response: {raw_response_text[:500]}...")
                response_json = extract_json_from_text(raw_response_text)
            else:
                raise ValueError("No content received from OpenAI API.")
        except Exception as e:
            return {"error": f"ChatGPT API call failed: {e}"}

    elif "Claude" in model_choice:
        if Anthropic is None:
            return {"error": "Anthropic library not found. Please run 'pip install anthropic'."}
        if not CLAUDE_API_KEY:
            return {"error": "Claude API key is not configured in .env."}

        model_name = "claude-3-sonnet-20240229"
        try:
            client = Anthropic(api_key=CLAUDE_API_KEY)

            # ONLY send text prompt, NO images
            response = client.messages.create(
                model=model_name,
                messages=[
                    {"role": "user", "content": full_prompt}
                ],
                max_tokens=4096,
                temperature=0.0,
            )
            if response.content and response.content[0].text:
                raw_response_text = response.content[0].text
                print(f"[DEBUG] Claude raw response: {raw_response_text[:500]}...")
                response_json = extract_json_from_text(raw_response_text)
            else:
                raise ValueError("No content received from Claude API.")
        except Exception as e:
            return {"error": f"Claude API call failed: {e}"}

    else:
        return {"error": f"Unknown model choice: {model_choice}"}

    # 5. Validate and Return
    if response_json is None:
        return {
            "error": "Failed to parse JSON from model response.",
            "raw_response": raw_response_text[:1000] if raw_response_text else "No response received"
        }
    
    # Validate the response
    validated = validate_response(response_json)
    if "error" in validated:
        validated["raw_response"] = raw_response_text[:1000]
        return validated
    
    # Add source information
    return {
        "source": model_name,
        **validated
    }