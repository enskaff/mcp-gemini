# MCP Gemini Text Analyzer

This project demonstrates using the Model Context Protocol (MCP) with Google Gemini.
It includes:
- `server.py`: An MCP server exposing text analysis tools (`analyze_text`, `count_sentences`).
- `client.py`: An MCP client that connects to the server, uses Gemini for natural language understanding, and orchestrates tool calls via MCP.

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <your-repo-url>
    cd mcp-gemini-analyzer
    ```
2.  **Create a virtual environment (recommended):**
    ```bash
    # Using uv
    uv venv
    source .venv/bin/activate # or .venv\Scripts\activate on Windows
    # Or using venv
    # python -m venv .venv
    # source .venv/bin/activate # or .venv\Scripts\activate on Windows
    ```
3.  **Install dependencies:**
    ```bash
    # Using uv (reads pyproject.toml)
    uv sync
    # Or using pip (reads requirements.txt)
    # pip install -r requirements.txt
    ```
4.  **Create a `.env` file:**
    Copy the `.env.example` (if you create one) or create `.env` manually and add your Gemini API key:
    ```
    GEMINI_API_KEY=YOUR_ACTUAL_API_KEY_HERE
    ```

## Usage

1.  Make sure your virtual environment is active.
2.  Run the client, providing the path to the server script:
    ```bash
    python client.py server.py
    ```
3.  Enter your queries at the prompt.

## MCP Server Tools

- `analyze_text(text: str)`: Returns word and character count.
- `count_sentences(text: str)`: Returns sentence count.