# import os
# from dotenv import load_dotenv
# import boto3
# import json

# # Load environment variables
# load_dotenv()

# # Create bedrock client (not bedrock-runtime)
# bedrock_client = boto3.client(
#     "bedrock",
#     region_name=os.getenv("AWS_REGION"),
#     aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
#     aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
# )

# # List all foundation models available
# print("Available Foundation Models:")
# print("-" * 80)
# response = bedrock_client.list_foundation_models()
# for model in response['modelSummaries']:
#     if 'claude' in model['modelId'].lower() and 'sonnet' in model['modelId'].lower():
#         print(f"Model ID: {model['modelId']}")
#         print(f"Model Name: {model['modelName']}")
#         print(f"Provider: {model['providerName']}")
#         print("-" * 80)

# # List inference profiles
# print("\n\nAvailable Inference Profiles:")
# print("-" * 80)
# try:
#     profiles = bedrock_client.list_inference_profiles()
#     for profile in profiles.get('inferenceProfileSummaries', []):
#         if 'claude' in profile['inferenceProfileName'].lower():
#             print(f"Profile ID: {profile['inferenceProfileId']}")
#             print(f"Profile Name: {profile['inferenceProfileName']}")
#             print(f"Status: {profile.get('status', 'N/A')}")
#             print("-" * 80)
# except Exception as e:
#     print(f"Could not list inference profiles: {e}")

import os
from dotenv import load_dotenv
import boto3
import json

# Load environment variables
load_dotenv()

client = boto3.client(
    "bedrock-runtime",
    region_name=os.getenv("AWS_REGION"),
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
)

body = {
    "anthropic_version": "bedrock-2023-05-31",
    "max_tokens": 1000,
    "messages": [
        {
            "role": "user",
            "content": "what is the capital of france?"
        }
    ]
}

# Use the GLOBAL inference profile (this is what's available in your account)
response = client.invoke_model(
    modelId="global.anthropic.claude-sonnet-4-5-20250929-v1:0",
    body=json.dumps(body)
)

# Parse and print the response
response_body = json.loads(response["body"].read())
print(response_body['content'][0]['text'])