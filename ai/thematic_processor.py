import google.generativeai as genai
import typing_extensions as typing
import json
import os
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import boto3

# Load env variables
load_dotenv()

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

def analyze_thematic_challenge(challenges_text: str, model_choice: str, context_prompt: str) -> Dict[str, Any]:
    """
    Analyzes a list of challenges using the selected AI model and classification prompt.
    """
    
    # 1. Prepare the Challenge List
    challenge_list = [c.strip() for c in challenges_text.split('\n') if c.strip()]
    if not challenge_list:
        return {"error": "No valid challenge statements provided."}

    challenges_for_prompt = "\n".join([f"- {c}" for c in challenge_list])
    full_prompt = context_prompt + "\n" + challenges_for_prompt
    
    response_json: Optional[Dict] = None
    model_name: str = ""

    # 2. Model Routing and Configuration
    if "Gemini" in model_choice:
        model_name = "gemini-2.5-flash"
        if not GEMINI_API_KEY:
            return {"error": "Gemini API key is not configured in .env."}
            
        try:
            genai.configure(api_key=GEMINI_API_KEY)
            
            # Use simpler generation config without schema enforcement
            # Gemini will follow the prompt instructions for JSON format
            client_model = genai.GenerativeModel(
                model_name=model_name,
                generation_config={
                    "temperature": 0.0,
                    "response_mime_type": "application/json"
                }
            )
            
            response = client_model.generate_content(contents=[full_prompt])
            
            # Parse and validate the response
            response_text = response.text.strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
                response_text = response_text.strip()
            
            response_json = json.loads(response_text)
            
            # Validate structure
            if "classified_data" not in response_json:
                return {"error": "Invalid response structure: missing 'classified_data' field"}
                
        except json.JSONDecodeError as e:
            return {"error": f"Failed to parse Gemini JSON response: {e}. Response: {response.text[:200]}"}
        except Exception as e:
            return {"error": f"Gemini API call failed: {e}"}

    elif "ChatGPT" in model_choice:
        if OpenAI is None:
            return {"error": "OpenAI library not found. Please run 'pip install openai'."}
        if not CHATGPT_API_KEY: 
            return {"error": "ChatGPT API key is missing in .env."}

        model_name = "gpt-4o-mini"
        try:
            client = OpenAI(api_key=CHATGPT_API_KEY)
            
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "You are an expert educational data classifier. Always respond with valid JSON only."},
                    {"role": "user", "content": full_prompt}
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

            # Read the streaming body
            response_body = json.loads(response['body'].read())
            
            print("Claude response body:", response_body)  # Debug print

            # Extract text from the response
            if 'content' in response_body and len(response_body['content']) > 0:
                text_content = response_body['content'][0]['text']
                
                # Basic JSON extraction
                try:
                    response_json = json.loads(text_content)
                except json.JSONDecodeError:
                    # Fallback cleanup - find JSON object
                    start = text_content.find('{')
                    end = text_content.rfind('}') + 1
                    if start != -1 and end > start:
                        response_json = json.loads(text_content[start:end])
                    else:
                        raise ValueError("Could not extract JSON from Claude response")
            else:
                raise ValueError("No content received from Claude API.")
        except Exception as e:
            return {"error": f"Claude API call failed: {e}"}

    else:
        return {"error": f"Unknown model choice: {model_choice}"}

    # 3. Final Processing and Validation
    if response_json:
        classified_data = response_json.get("classified_data", [])
        
        # Trim to match input count
        if len(classified_data) > len(challenge_list):
            classified_data = classified_data[:len(challenge_list)]
        
        # Validate each classification entry
        for i, item in enumerate(classified_data):
            if not isinstance(item.get("theme_id"), int):
                classified_data[i]["theme_id"] = 0
            if not isinstance(item.get("theme_name"), str):
                classified_data[i]["theme_name"] = "Unknown"
            if not isinstance(item.get("pii_flag"), bool):
                classified_data[i]["pii_flag"] = False
        
        return {
            "source": model_name,
            "classified_data": classified_data
        }
    
    return {"error": "Failed to receive or parse a valid JSON response from the model."}