import subprocess
import sys
import os
import requests
from urllib.parse import urlparse

def download_image(image_url, save_path="input_image.jpg"):
    """Download image from URL"""
    print(f"Downloading image from: {image_url}")
    response = requests.get(image_url, timeout=30)
    response.raise_for_status()
    
    with open(save_path, 'wb') as f:
        f.write(response.content)
    print(f"Image saved to: {save_path}")
    return save_path

def blur_faces(input_file, output_file):
    """Blur all faces in an image"""
    print(f"Blurring faces in: {input_file}")
    cmd = ['deface', input_file, '--output', output_file]
    subprocess.run(cmd, check=True)
    print(f"Blurred image saved to: {output_file}")

if __name__ == "__main__":    
    
    # Input: Image URL
    # image_url = "https://mohini-static.shikshalokam.org/chatbot/storymedia/4284/1756603829-IMG_20250619_130106.jpg"  
    # image_url = "https://mohini-static.shikshalokam.org/chatbot/storymedia/5803/1758116256-IMG20250917151810.jpg"  
    # image_url = "https://mohini-static.shikshalokam.org/chatbot/storymedia/7129/1758290796-1000092521.jpg"  
    image_url = "https://mohini-static.shikshalokam.org/chatbot/storymedia/15450/1763429568-IMG-20251005-WA0012.jpg"  
    # image_url = ""  
    
    # Output: Blurred image path
    output_file = "blurred_output.jpg"  # Replace with desired output path
    
    # Download image
    input_file = download_image(image_url)
    
    # Blur faces
    blur_faces(input_file, output_file)
    
    # Clean up temporary file
    if os.path.exists(input_file):
        os.remove(input_file)
        print(f"Cleaned up temporary file: {input_file}")
