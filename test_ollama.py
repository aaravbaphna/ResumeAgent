import requests
import json

OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3:8b"

print(f"Attempting to connect to Ollama at {OLLAMA_API_URL}...")

try:
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": "Hello, is anyone there?",
        "stream": False # Use False for a simple, single response test
    }

    response = requests.post(OLLAMA_API_URL, json=payload)

    # Raise an exception if the HTTP request returned an error
    response.raise_for_status()

    print("Connection successful!")
    print("Response from Ollama:")
    print(response.json())

except requests.exceptions.ConnectionError as e:
    print("\n--- CONNECTION ERROR ---")
    print(f"Failed to connect to Ollama. Is the server running at http://localhost:11434?")
    print(f"Details: {e}")

except requests.exceptions.HTTPError as e:
    print("\n--- HTTP ERROR ---")
    print(f"Received an HTTP error: {e.response.status_code}")
    print(f"Response body: {e.response.text}")

except Exception as e:
    print(f"\n--- An unexpected error occurred --- \n{e}")
