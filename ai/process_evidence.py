import json
import base64
import time
import httpx
import mimetypes
import re
import os
from urllib.request import urlopen
import google.generativeai as genai
from openai import OpenAI
import typing_extensions as typing
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- CONFIGURATION ---
# Load keys from .env, split by comma if multiple exist
gemini_env = os.getenv("GEMINI_API_KEYS", "")
GEMINI_TOKENS = [key.strip() for key in gemini_env.split(",") if key.strip()]

TOGETHER_TOKEN = os.getenv("TOGETHER_API_KEY")

MAX_RETRIES = 3
current_token_index = 0

# --- TOKEN HANDLING (Gemini) ---
def get_next_gemini_token():
    global current_token_index
    if GEMINI_TOKENS and current_token_index < len(GEMINI_TOKENS):
        return GEMINI_TOKENS[current_token_index]
    return None

def switch_to_next_token():
    global current_token_index
    current_token_index += 1
    if current_token_index >= len(GEMINI_TOKENS):
        # Reset or handle exhaustion
        current_token_index = 0 
        print("Warning: Cycled through all Gemini tokens.")
    return get_next_gemini_token()

# --- Gemini Model Setup ---
class AnalysisResponse(typing.TypedDict):
    answers: list[str]
    reasonings: list[str]

initial_token = get_next_gemini_token()
if not initial_token:
    raise ValueError("No valid Gemini tokens found in .env file.")

genai.configure(api_key=initial_token)
model = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
    generation_config={
        "response_mime_type": "application/json",
        "response_schema": AnalysisResponse,
    },
)

# --- OpenAI (SambaNova) Setup ---
# Only initialize if token exists to prevent crash
if TOGETHER_TOKEN:
    client = OpenAI(
        base_url="https://api.sambanova.ai/v1",
        api_key=TOGETHER_TOKEN
    )
else:
    client = None
    print("Warning: TOGETHER_API_KEY not found in .env")

# --- Helper: Convert image to base64 ---
def get_image_as_base64(url: str) -> str:
    with urlopen(url) as response:
        image_data = response.read()
    mime_type, _ = mimetypes.guess_type(url)
    if not mime_type:
        mime_type = "image/jpeg"
    return f"data:{mime_type};base64,{base64.b64encode(image_data).decode('utf-8')}"

# --- Helper: Relevance Tag ---
def calculate_relevance_tag(answers):
    if not answers or not isinstance(answers, list):
        return 'Irrelevant'
    yes_count = sum(1 for answer in answers if str(answer).upper() == 'YES')
    if len(answers) == 0: return 'Irrelevant'
    
    percentage = (yes_count / len(answers)) * 100
    if percentage >= 50:
        return 'Relevant'
    elif percentage > 0:
        return 'Partially Relevant'
    return 'Irrelevant'

# --- Response Parser ---
def extract_structured_response(response_text):
    normalized = response_text.replace("\r\n", "\n").upper()
    answers_match = re.search(
        r"^ANSWERS[:\-\s]*((?:YES|NO)(?:\s*,\s*(?:YES|NO))*)",
        normalized,
        re.MULTILINE
    )
    reasonings_match = re.findall(
        r"(?:^REASONINGS[:\-\s]*\n)?(?:^|\n)\s*(\d+)\.?\s*([^\n]+)",
        response_text,
        re.MULTILINE
    )

    answers = [a.strip() for a in answers_match.group(1).split(",")] if answers_match else []
    answers = [a.upper()[:3] for a in answers if a.upper().startswith(("YES", "NO"))]
    reasonings = [item[1].strip() for item in sorted(reasonings_match, key=lambda x: int(x[0]))]
    
    # Relaxed validation to allow partial parsing if strict 3 count fails
    if not answers:
        return None
    return {"answers": answers, "reasonings": reasonings}

# --- MAIN FUNCTION ---
def analyze_evidence(image_url: str, prompt: str, use_openai: bool = False):
#     prompt = f"""You are an educational evidence validator. Analyze this image, which is field evidence from a Project-Based Learning classroom in Bihar, India.
# Please analyze this image carefully and answer with ONLY 'yes' or 'no' for each question below separated by commas:
# {questions}
# Consider all visible elements and context. Explain your reasoning for each answer briefly.
# """

    print(f"[Prompt]:\n{prompt}\n")

    # Step 1: Gemini
    for _ in range(MAX_RETRIES):
        try:
            image = httpx.get(image_url)
            gemini_response = model.generate_content(
                [
                    {
                        "mime_type": "image/jpeg",
                        "data": base64.b64encode(image.content).decode("utf-8"),
                    },
                    prompt,
                ]
            )
            response_json = json.loads(gemini_response.text)
            relevance = calculate_relevance_tag(response_json.get("answers", []))
            print(f"[Gemini Response] = {response_json}")
            print(f"[Relevance Tag] = {relevance} \n")
            return {
                "source": "gemini",
                "answers": response_json.get("answers"),
                "reasonings": response_json.get("reasonings"),
                "relevance": relevance
            }
        except Exception as e:
            if any(x in str(e).lower() for x in ["quota", "rate limit", "429"]):
                token = switch_to_next_token()
                if token:
                    genai.configure(api_key=token)
                    continue
            print(f"[Gemini Error] {e}")
            break

    # Step 2: OpenAI fallback (if enabled and client exists)
    if use_openai and client:
        for _ in range(MAX_RETRIES):
            try:
                openai_response = client.chat.completions.create(
                    model="Llama-4-Maverick-17B-128E-Instruct",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {"type": "image_url", "image_url": {"url": get_image_as_base64(image_url)}},
                            ],
                        }
                    ],
                )
                if openai_response.choices:
                    content = openai_response.choices[0].message.content
                    structured = extract_structured_response(content)
                    if structured:
                        relevance = calculate_relevance_tag(structured["answers"])
                        return {
                            "source": "openai",
                            "answers": structured["answers"],
                            "reasonings": structured["reasonings"],
                            "relevance": relevance
                        }
            except Exception as e:
                print(f"[OpenAI Error] {e}")
                time.sleep(3)

    return {
        "error": "Unable to process image after retries"
    }
