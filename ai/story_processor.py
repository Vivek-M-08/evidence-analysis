import google.generativeai as genai
import typing_extensions as typing
import json
import os
import httpx
import base64
from typing import List, Dict, Any, Optional, Union
from openai import OpenAI
from dotenv import load_dotenv
import boto3

# Load env variables
load_dotenv()

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

# AWS bedrocks configuration
claude_beadrock_client = boto3.client(
    "bedrock-runtime",
    region_name=os.getenv("AWS_REGION"),
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
)

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

def analyze_story_rating(title: str, pdf_url: str, model_choice: str, context_prompt: str) -> Dict[str, Any]:
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
    
    # The AI will ONLY analyze the PDF content
    print(f"[INFO] Analyzing PDF content only. Optional content and images are ignored for ranking.")
    
    # Format the prompt with ONLY PDF content
    full_prompt = context_prompt.format(
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
        anthropic_version = "bedrock-2023-05-31"
        model_id = "global.anthropic.claude-sonnet-4-5-20250929-v1:0"
        claude_max_tokens = 4000
        try:
            body = {
                "anthropic_version": anthropic_version,
                "max_tokens": claude_max_tokens,
                "messages": [
                    {
                        "role": "user",
                        "content": full_prompt
                    }
                ]
            }

            response = claude_beadrock_client.invoke_model(
                modelId=model_id,
                body=json.dumps(body)
            )

            # Read the streaming body FIRST
            response_body = json.loads(response['body'].read())
            
            print("Claude response body:", response_body)  # Debug print AFTER reading

            # Extract text from the response
            if 'content' in response_body and len(response_body['content']) > 0:
                text_content = response_body['content'][0]['text']
                raw_response_text = text_content
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