import os
import uuid
import json
import logging

import duckdb
import fitz  # PyMuPDF
import requests
from flask import Flask, render_template, request, jsonify, Response, stream_with_context

# --- Configuration ---
UPLOAD_FOLDER = 'uploads'
DUCKDB_FILE = 'resumes.duckdb'
OLLAMA_API_URL = "http://localhost:11434/api/generate" # Ollama API endpoint
OLLAMA_MODEL = "mistral:latest" # The model you've pulled in Ollama

# This is the core of your extensible features system.
# Add new prompts here to create new features in the UI.
FEATURES = {
    "extract_skills": (
        "You are a technical recruiter. Parse the following resume text and extract all technical skills, programming languages, "
        "and software tools mentioned. Group them into logical categories (e.g., 'Programming Languages', 'Databases', 'Cloud Technologies', 'Developer Tools'). "
        "Present the output in a clean, bulleted list format.\n\n"
        "Resume Text:\n---\n{resume_text}"
    ),
    "identify_verbs": (
        "You are a resume writing coach. Read through this resume text and identify all the strong action verbs used to describe accomplishments "
        "(e.g., 'developed', 'managed', 'architected', 'led'). List the top 10-15 most impactful verbs you find. "
        "This helps the user understand their own powerful language.\n\n"
        "Resume Text:\n---\n{resume_text}"
    ),
    "suggest_improvements": (
        "You are a professional career coach providing constructive feedback. Based on the following resume, provide 3 concrete suggestions for improvement. "
        "Focus on areas like impact quantification (using numbers and metrics), clarity, and conciseness. Format your suggestions as a numbered list with a brief explanation for each.\n\n"
        "Resume Text:\n---\n{resume_text}"
    ),
}

# --- Application Setup ---
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
logging.basicConfig(level=logging.INFO)

def get_db_connection():
    """Establishes a connection to DuckDB and ensures the table exists."""
    conn = duckdb.connect(DUCKDB_FILE)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS resumes (
            id TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            full_text TEXT,
            upload_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    return conn

@app.route('/')
def index():
    """Render the main UI."""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_resume():
    """Handle resume file uploads, parse text, and store in DB."""
    if 'resume' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400
    file = request.files['resume']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    if file:
        filename = file.filename
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        try:
            full_text = ""
            if filename.lower().endswith('.pdf'):
                with fitz.open(file_path) as doc:
                    for page in doc:
                        full_text += page.get_text()
            elif filename.lower().endswith('.txt'):
                with open(file_path, 'r', encoding='utf-8') as f:
                    full_text = f.read()
            else:
                os.remove(file_path)
                return jsonify({"error": "Unsupported file type. Please upload PDF or TXT."}), 400

            # Save to DuckDB
            conn = get_db_connection()
            resume_id = str(uuid.uuid4())
            conn.execute(
                "INSERT INTO resumes (id, filename, full_text) VALUES (?, ?, ?)",
                (resume_id, filename, full_text)
            )
            conn.close()
            os.remove(file_path) # Clean up uploaded file
            
            logging.info(f"Successfully processed and stored resume: {filename}")
            return jsonify({"message": f"Successfully uploaded and processed {filename}", "id": resume_id}), 201

        except Exception as e:
            logging.error(f"Error processing file {filename}: {e}")
            os.remove(file_path) # Clean up on error
            return jsonify({"error": "Failed to process file."}), 500

@app.route('/get_resumes', methods=['GET'])
def get_resumes():
    """Fetch all uploaded resumes from the database."""
    conn = get_db_connection()
    resumes = conn.execute("SELECT id, filename FROM resumes ORDER BY upload_timestamp DESC").fetchall()
    conn.close()
    resume_list = [{"id": row[0], "filename": row[1]} for row in resumes]
    return jsonify(resume_list)

@app.route('/run_feature', methods=['POST'])
def run_feature():
    """Run a selected AI feature on a resume and stream the response."""
    data = request.get_json()
    resume_id = data.get('resume_id')
    feature_name = data.get('feature_name')

    if not resume_id or not feature_name:
        return jsonify({"error": "Resume ID and feature name are required."}), 400

    if feature_name not in FEATURES:
        return jsonify({"error": "Feature not found."}), 404

    logging.info(f"Received feature: '{feature_name}' on resume ID: {resume_id}")
    try:
        conn = get_db_connection()
        result = conn.execute("SELECT full_text FROM resumes WHERE id = ?", (resume_id,)).fetchone()
        conn.close()

        if not result:
            return jsonify({"error": "Resume not found."}), 404
        
        resume_text = result[0]
        prompt = FEATURES[feature_name].format(resume_text=resume_text)
        
        # Data payload for Ollama API
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": True  # Enable streaming response
        }

        logging.info(f"Received prompt '{prompt}' to run feature: '{feature_name}' on resume ID: {resume_id}")

        # Use a generator function with stream_with_context for streaming
        def generate():
            try:
                # Make the request to the local Ollama API
                response = requests.post(OLLAMA_API_URL, json=payload, stream=True)
                response.raise_for_status() # Raise an exception for bad status codes
                
                logging.info(f"Streaming response from Ollama for feature: {feature_name}")
                for chunk in response.iter_content(chunk_size=None):
                    # Ollama streaming sends a JSON object on each line
                    line = chunk.decode('utf-8')
                    try:
                        json_line = json.loads(line)
                        if 'response' in json_line:
                            yield json_line['response']
                    except json.JSONDecodeError:
                        logging.warning(f"Could not decode JSON line: {line}")
                        continue
            except requests.exceptions.RequestException as e:
                logging.error(f"Failed to connect to Ollama API: {e}")
                yield f"\n\n--- ERROR ---\nFailed to connect to the local AI model at {OLLAMA_API_URL}.\nPlease ensure Ollama is running and the model '{OLLAMA_MODEL}' is available."
            except Exception as e:
                logging.error(f"An error occurred during streaming: {e}")
                yield f"\n\n--- ERROR ---\nAn unexpected error occurred."


        return Response(stream_with_context(generate()), mimetype='text/plain')

    except Exception as e:
        logging.error(f"Error in run_feature: {e}")
        return jsonify({"error": "An internal error occurred."}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050, debug=True)
