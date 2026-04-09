import google.generativeai as genai
from config import GEMINI_API_KEY

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

try:
    response = model.generate_content("Hello, can you hear me?")
    print("Success:", response.text)
except Exception as e:
    print("Fail:", e)
