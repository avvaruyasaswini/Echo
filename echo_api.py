import google.generativeai as genai
from dotenv import load_dotenv
load_dotenv()
import os

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") 
MODEL_NAME = "gemini-pro-latest"

if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

def generate_response(prompt: str, temperature=0.7):
    # THIS IS THE MOST IMPORTANT TEST:
    print(f"--- EXECUTING THE *NEW* generate_response FUNCTION! ---")

    if not GOOGLE_API_KEY:
        return "Error: GOOGLE_API_KEY was not found. Check your .env file and restart."
        
    try:
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"A new API Error occurred: {e}"