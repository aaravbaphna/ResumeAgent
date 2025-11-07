# Resume Agent - Local AI/LLM based Resume Chatbot

This is a full-stack application that allows users to upload a resume, store its content in a local DuckDB, and run various AI-powered "features" on it using a locally running LLM (via Ollama). Extremely useful for recruiters, hiring managers and candidates to get maximum value out of resumes they are working with.

## Prerequisites

* Python 3.8+
* Pip (Python package installer)
* **Ollama Installed and Running:** You must have Ollama installed and serving a model.
    1.  Install Ollama from [https://ollama.com/](https://ollama.com/).
    2.  Pull a model to use. A small, fast model is recommended for this type of task.
        ```bash
        ollama pull llama3:8b
        # or a smaller model like tinyllama
        # ollama pull tinyllama
        ```
    3.  Ensure the Ollama server is running in the background. The application assumes it's accessible at `http://localhost:11434`.

## Project Setup & Running

1.  **Create Project Structure:**
    Create a folder for your project (e.g., `resume_agent/`) and create the following files and folders inside it as specified below:
    ```
    resume_agent/
    ├── app.py
    ├── templates/
    │   └── index.html
    └── README.md
    ```

2.  **Create a Virtual Environment (Recommended):**
    ```bash
    cd resume_agent
    python -m venv venv
    # On Windows
    venv\Scripts\activate
    # On macOS/Linux
    source venv/bin/activate
    ```

3.  **Install Dependencies:**
    ```bash
    pip install Flask PyMuPDF duckdb requests
    ```
    * `Flask`: The web framework.
    * `PyMuPDF`: An excellent library for parsing PDF files.
    * `duckdb`: For the local database.
    * `requests`: For making API calls to the local Ollama server.

4.  **Run the Application:**
    Set your Flask environment variables for a better development experience:
    ```bash
    # On macOS/Linux (bash/zsh)
    export FLASK_APP=app.py
    export FLASK_ENV=development

    # On Windows (Command Prompt)
    set FLASK_APP=app.py
    set FLASK_ENV=development
    ```
    Then, run the app:
    ```bash
    flask run
    ```

5.  **Access the Application:**
    * Open your web browser and navigate to `http://localhost:5050`.
    * You should see the application UI, ready for you to upload a resume.

## How to Add New "Features"

Adding a new AI feature is simple:

1.  Open `app.py`.
2.  Find the `FEATURES` dictionary near the top of the file.
3.  Add a new key-value pair.
    * The **key** is a unique identifier for your feature (e.g., `write_cover_letter`).
    * The **value** is the f-string prompt that will be sent to the LLM. The resume text will be injected into the `{resume_text}` placeholder.
4.  In `templates/index.html`, add a new button in the "features-buttons" div that calls `runFeature('your_new_feature_key')`.

That's it! The application will automatically pick up the new feature.
