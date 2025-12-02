# ai/thematic_processor.py
import google.generativeai as genai
import typing_extensions as typing
import json
import os
import time
import httpx
import base64
from typing import List, Dict, Any, Optional, Union
import io
import tempfile

# --- External API Imports ---
# Install these: pip install openai anthropic PyMuPDF
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None # Type placeholder if not installed

try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None # Type placeholder if not installed

try:
    # PyMuPDF is the recommended library for robust PDF processing
    import fitz # PyMuPDF
    PDF_PROCESSOR_AVAILABLE = True
except ImportError:
    # Set a flag if the required PDF library is missing
    PDF_PROCESSOR_AVAILABLE = False
    class fitz: # Mock class to prevent import errors in type hints
        @staticmethod
        def open(*args, **kwargs): pass


# --- PII and Classification Theme Data (Unchanged) ---

CLASSIFICATION_PROMPT = """
# Educational Challenge Classification Prompt

You are an expert data classifier specializing in educational barrier analysis. Your task is to analyze a list of challenges affecting children's education and classify each challenge into predefined themes while identifying any Personal Identifiable Information (PII).

## Classification Themes

### Theme 1: Poverty and Economic Barriers
**Definition:** This theme captures insights where families link irregular school attendance or dropouts to financial hardship. It includes responses describing how poverty forces children to prioritize work over education, how households depend on children's income for survival, and how limited resources—such as inability to afford uniforms, books, or transport—become barriers to schooling.

### Theme 2: Legal Document-linked Barriers
**Definition:** This theme includes responses where children are unable to enroll in school due to missing or incomplete legal documents such as Aadhaar cards, birth certificates, or identity proofs. It captures how lack of proper documentation creates administrative hurdles that keep children out of the education system.

### Theme 3: Early Marriage
**Definition:** This theme captures responses where child marriage or early marriage prevents girls from continuing their education. It includes situations where early marriage leads to school dropout, limits learning opportunities, or shifts responsibilities toward household duties instead of schooling.

### Theme 4: Distance and Accessibility Issues
**Definition:** This theme captures challenges that prevent children from attending school due to physical and environmental conditions. It includes long distances to school, poor road or transport infrastructure, and difficulties caused by weather or seasonal factors (such as heavy rains, heat, or floods). These conditions make daily travel to school inconvenient, unreliable, or physically demanding for children.

### Theme 5: Parental Attitudes and Socio-Cultural Barriers
**Definition:** This theme captures responses where parental beliefs, family mindsets, and cultural norms discourage girls from attending school. It includes attitudes such as prioritizing domestic roles for girls, believing education is unnecessary for them, concerns about dowry increasing with higher education, or long-standing traditions that limit girls' mobility and learning opportunities. These socio-cultural factors collectively shape decisions that keep girls out of school.

### Theme 6: School Infrastructure and Facility Issues
**Definition:** This theme captures responses highlighting gaps in school facilities and infrastructure gaps. It includes issues such as inadequate classrooms, lack of basic amenities, insufficient learning resources, as well as delays, inconsistencies, or limited access to government schemes. Together, these systemic gaps reduce the attractiveness and effectiveness of schooling for children and families.

### Theme 7: Unknown/Unclear (Add more themes if needed, based on the prompt's missing context - assuming only 6 were provided)
**Definition:** Use this theme when the challenge statement is genuinely incomplete or incomprehensible.

## PII Detection Guidelines

Flag as PII if the challenge contains:
- **Names** of individuals (students, parents, teachers, community members)
- **Specific ages** when combined with identifying details
- **Specific addresses** or identifiable location details beyond general village/community references
- **Phone numbers, email addresses, ID numbers**
- **Photographs or physical descriptions** that could identify individuals
- **Specific family details** that could identify individuals (e.g., "Ram's daughter who lives near the temple")
- **Specific school names** when combined with individual identifiers

Do NOT flag as PII:
- General demographic information (e.g., "girls," "teenage girls," "children")
- General location references (e.g., "village," "community," "Muslim community")
- General role descriptions (e.g., "parents," "teachers," "father")
- Age ranges or general age categories without specific identifiers

## Classification Rules

- Assign ONE primary theme per challenge (the most dominant barrier)
- If a challenge mentions multiple barriers, classify by the PRIMARY/MAIN issue
- Use theme 7 (Unknown/Unclear) ONLY when the statement is genuinely incomplete or incomprehensible
- Be consistent in classification across similar statements
- When in doubt between two themes, choose the one most directly preventing school attendance

---
**Your Task:** Analyze the challenges below and provide the classification strictly in the JSON format defined by the schema.
"""

# --- API Key Configuration (LOAD FROM ENVIRONMENT VARIABLES RECOMMENDED) ---
# NOTE: Using a placeholder key for demonstration.
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY") 
CLAUDE_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "YOUR_CLAUDE_API_KEY")

# WARNING: Hardcoding the key here is a security risk. Use os.environ.get() in production.
CHATGPT_API_KEY = os.environ.get("OPENAI_API_KEY", "YOUR_CHATGPT_API_KEY") 


# Fallback/Default for Gemini (if environment not set)
if GEMINI_API_KEY == "YOUR_GEMINI_API_KEY":
    try:
        # Assuming a custom file to load key
        from .process_evidence import GEMINI_TOKENS 
        GEMINI_API_KEY = GEMINI_TOKENS[0]
    except:
        pass


# --- Define the desired output schema (TypedDict for validation) ---
class ChallengeClassification(typing.TypedDict):
    theme_id: int
    theme_name: str
    pii_flag: bool

class AnalysisResponse(typing.TypedDict):
    classified_data: List[ChallengeClassification]


def analyze_thematic_challenge(challenges_text: str, model_choice: str) -> Dict[str, Any]:
    """
    Analyzes a list of challenges using the selected AI model and classification prompt.
    (This function remains unchanged as it only handles text analysis)
    """
    
    # 1. Prepare the Challenge List
    challenge_list = [c.strip() for c in challenges_text.split('\n') if c.strip()]
    if not challenge_list:
        return {"error": "No valid challenge statements provided."}

    challenges_for_prompt = "\n".join([f"- {c}" for c in challenge_list])
    full_prompt = CLASSIFICATION_PROMPT + "\n\n## Challenges to Classify\n" + challenges_for_prompt
    
    response_json: Optional[Dict] = None
    model_name: str = ""

    # 2. Model Routing and Configuration (Logic remains the same)
    if "Gemini" in model_choice:
        model_name = "gemini-2.5-flash"
        if GEMINI_API_KEY in ["YOUR_GEMINI_API_KEY", None]:
            return {"error": "Gemini API key is not configured."}
            
        try:
            genai.configure(api_key=GEMINI_API_KEY)
            client_model = genai.GenerativeModel(
                model_name=model_name,
                generation_config={
                    "response_mime_type": "application/json",
                    "response_schema": AnalysisResponse,
                    "temperature": 0.0
                },
            )
            response = client_model.generate_content(contents=[full_prompt])
            response_json = json.loads(response.text)
        except Exception as e:
            return {"error": f"Gemini API call failed: {e}"}

    elif "ChatGPT" in model_choice:
        if OpenAI is None:
            return {"error": "OpenAI library not found. Please run 'pip install openai'."}
        if CHATGPT_API_KEY in ["YOUR_CHATGPT_API_KEY", None]: 
            return {"error": "ChatGPT API key is missing or is the default placeholder."}

        model_name = "gpt-4o-mini"
        try:
            client = OpenAI(api_key=CHATGPT_API_KEY)
            
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": CLASSIFICATION_PROMPT},
                    {"role": "user", "content": "\n\n## Challenges to Classify\n" + challenges_for_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.0
            )
            if response.choices and response.choices[0].message.content:
                response_json = json.loads(response.choices[0].message.content)
            else:
                raise ValueError("No content received from OpenAI API.")
        except Exception as e:
            return {"error": f"ChatGPT API call failed: {e}"}
    
    elif "Claude" in model_choice:
        if Anthropic is None:
            return {"error": "Anthropic library not found. Please run 'pip install anthropic'."}
        if CLAUDE_API_KEY in ["YOUR_CLAUDE_API_KEY", None]:
            return {"error": "Claude API key is not configured."}

        model_name = "claude-3-haiku-20240307"
        try:
            client = Anthropic(api_key=CLAUDE_API_KEY)
            
            response = client.messages.create(
                model=model_name,
                messages=[
                    {"role": "user", "content": full_prompt}
                ],
                max_tokens=2048,
                temperature=0.0,
                response_schema=AnalysisResponse,
            )
            if response.content and response.content[0].text:
                response_json = json.loads(response.content[0].text)
            else:
                raise ValueError("No content received from Claude API.")
        except Exception as e:
            return {"error": f"Claude API call failed: {e}"}

    else:
        return {"error": f"Unknown model choice: {model_choice}"}

    # 3. Final Processing
    if response_json:
        classified_data = response_json.get("classified_data", [])
        if len(classified_data) > len(challenge_list):
             classified_data = classified_data[:len(challenge_list)]
        
        return {
            "source": model_name,
            "classified_data": classified_data
        }
    
    return {"error": "Failed to receive or parse a valid JSON response from the model."}


# --- Story Rating Schema (Updated to include document_language) ---
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

# --- Story Rating Prompt (Unchanged as it relies on content passed to it) ---
STORY_RATING_PROMPT = """
You are an expert story evaluator specializing in assessing educational and social impact narratives. Your task is to analyze the attached story (from a PDF) and rank it based on three critical criteria: Impact/Outcome, Issue/Challenge clarity, and Action Steps taken.

## Evaluation Criteria

### Criterion 1: Impact and Outcome Score (0.0 - 1.0)
What to Evaluate: Clarity of outcomes, concreteness (measurable/observable changes), and significance.

### Criterion 2: Issue and Challenge Score (0.0 - 1.0)
What to Evaluate: Problem clarity, root cause identification, and sufficient context.

### Criterion 3: Action Steps Score (0.0 - 1.0)
What to Evaluate: Specificity, sequential flow, completeness (planning, execution, adaptation), and problem-solving (obstacles and solutions).

## Composite Score and Tier Assignment
- Calculate the `composite_score` using the weighted average:
  **Composite Score = (Impact × 0.4) + (Issue × 0.3) + (Action × 0.3)**

- Assign the `tier` based on individual scores:
    - **Excellent:** All three scores ≥ 0.75
    - **Good:** All three scores ≥ 0.60
    - **Developing:** All three scores ≥ 0.40
    - **Needs Improvement:** Any score < 0.40

## Task Instructions
1. Analyze the complete text content provided under 'Extracted PDF Content', which may include a fallback text input from the user.
2. Identify the primary language of the story content and include it as `document_language`.
3. Provide a score and detailed justification for each of the three criteria based on the scoring guidelines provided in your system instructions.
4. Calculate the composite score and assign the correct tier.
5. Provide a brief, actionable `overall_summary`.
6. Return the result strictly as a single JSON object matching the provided schema, with all text fields in English.

## Story Details (from PDF and Image)

**Title:** {story_title}
**Image Context:** {image_context}

---
**Extracted PDF Content (TEXT FOR EVALUATION):**
{pdf_content}
"""

def process_pdf_and_extract_text(pdf_url: str) -> Dict[str, Union[str, None]]:
    """
    Downloads a PDF, extracts all text, and attempts to detect the language.
    Requires 'PyMuPDF' (fitz).
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
            "language_hint": "Unknown" # Actual language detection by LLM
        }
    except httpx.HTTPStatusError as e:
        return {"error": f"HTTP error downloading PDF: {e.response.status_code}"}
    except Exception as e:
        return {"error": f"PDF processing error: {e}"}

def get_image_as_base64_content(url: str) -> Optional[Dict[str, str]]:
    """Fetches image from URL and returns content dict for Gemini/OpenAI."""
    # (Unchanged)
    if not url.strip():
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
        print(f"Error fetching image for story Ranker: {e}")
        return None


def analyze_story_rating(title: str, pdf_url: str, image_url: str, model_choice: str, optional_content: str = "") -> Dict[str, Any]:
    """
    Analyzes a story of change with mandatory PDF and Title. The optional_content is used 
    to enrich the prompt, especially if PDF extraction fails.
    
    *MODIFIED TO ACCEPT optional_content*
    """
    if not title:
        return {"error": "Title is mandatory for story analysis."}
    if not pdf_url:
        return {"error": "PDF link is mandatory for story analysis."}
    
    # 1. Process PDF
    pdf_result = process_pdf_and_extract_text(pdf_url)
    
    # Determine the content to send to the model
    content_for_ai = ""
    if "error" in pdf_result:
        # PDF extraction failed or file was empty. Use optional content as fallback.
        print(f"PDF processing failed: {pdf_result['error']}. Using optional content if provided.")
        if optional_content.strip():
             content_for_ai = f"[PDF ERROR: {pdf_result['error']}] --- FALLBACK TEXT CONTENT PROVIDED BY USER: \n\n{optional_content.strip()}"
        else:
             return pdf_result # No PDF content, no optional content, so we return the error
    else:
        # PDF content is primary. Append optional content for extra context if it exists.
        pdf_content = pdf_result['text']
        content_for_ai = pdf_content
        if optional_content.strip():
            content_for_ai += f"\n\n--- SUPPLEMENTAL TEXT CONTENT PROVIDED BY USER (Use this for context): ---\n{optional_content.strip()}"


    # 2. Process Image
    image_content = get_image_as_base64_content(image_url)
    
    # 3. Prepare Prompt and Image Context
    if image_content:
        image_context = "The image provided is field evidence related to this story. Use it to check for visual consistency and context (e.g., do the photos show the 'action steps' described?)."
    else:
        image_context = "NO IMAGE PROVIDED. Please rely solely on the text content."

    # Format the prompt
    full_prompt = STORY_RATING_PROMPT.format(
        story_title=title,
        pdf_content=content_for_ai, # Use the combined/fallback content here
        image_context=image_context
    )
    
    response_json: Optional[Dict] = None
    model_name: str = ""

    # 4. Model Routing and Configuration (Multi-modal setup with image)

    if "Gemini" in model_choice:
        model_name = "gemini-2.5-flash"
        if GEMINI_API_KEY in ["YOUR_GEMINI_API_KEY", None]:
            return {"error": "Gemini API key is not configured."}
        
        contents: List[Any] = [full_prompt]
        if image_content:
            contents.insert(0, image_content)
        
        try:
            genai.configure(api_key=GEMINI_API_KEY)
            client_model = genai.GenerativeModel(
                model_name=model_name,
                generation_config={
                    "response_mime_type": "application/json",
                    "response_schema": StoryRating,
                    "temperature": 0.0
                },
            )
            response = client_model.generate_content(contents=contents)
            response_json = json.loads(response.text)
        except Exception as e:
            return {"error": f"Gemini API call failed: {e}"}

    elif "ChatGPT" in model_choice:
        if OpenAI is None:
            return {"error": "OpenAI library not found. Please run 'pip install openai'."}
        if CHATGPT_API_KEY in ["YOUR_CHATGPT_API_KEY", None]:
            return {"error": "ChatGPT API key is missing or is the default placeholder."}

        model_name = "gpt-4o"
        try:
            client = OpenAI(api_key=CHATGPT_API_KEY)

            message_content: List[Dict[str, Any]] = []
            
            if image_content:
                message_content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{image_content['mime_type']};base64,{image_content['data']}"
                    }
                })

            message_content.append({"type": "text", "text": full_prompt})
            
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "user", "content": message_content}
                ],
                response_format={"type": "json_object"},
                temperature=0.0
            )
            if response.choices and response.choices[0].message.content:
                response_json = json.loads(response.choices[0].message.content)
            else:
                raise ValueError("No content received from OpenAI API.")
        except Exception as e:
            return {"error": f"ChatGPT API call failed: {e}"}

    elif "Claude" in model_choice:
        if Anthropic is None:
            return {"error": "Anthropic library not found. Please run 'pip install anthropic'."}
        if CLAUDE_API_KEY in ["YOUR_CLAUDE_API_KEY", None]:
            return {"error": "Claude API key is not configured."}

        model_name = "claude-3-sonnet-20240229"
        try:
            client = Anthropic(api_key=CLAUDE_API_KEY)

            claude_content: List[Dict[str, Any]] = []
            
            if image_content:
                claude_content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": image_content['mime_type'],
                        "data": image_content['data'],
                    },
                })
            
            claude_content.append({"type": "text", "text": full_prompt})
            
            response = client.messages.create(
                model=model_name,
                messages=[
                    {"role": "user", "content": claude_content}
                ],
                max_tokens=4096,
                temperature=0.0,
                response_schema=StoryRating
            )
            if response.content and response.content[0].text:
                response_json = json.loads(response.content[0].text)
            else:
                raise ValueError("No content received from Claude API.")
        except Exception as e:
            return {"error": f"Claude API call failed: {e}"}

    else:
        return {"error": f"Unknown model choice: {model_choice}"}

    # 5. Final Processing
    if response_json and "composite_score" in response_json:
        return {
            "source": model_name,
            **response_json
        }
    
    return {"error": "Failed to receive or parse a valid JSON response from the model."}

# End of ai/thematic_processor.py