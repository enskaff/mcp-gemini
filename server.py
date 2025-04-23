# server.py
import asyncio
from mcp.server.fastmcp import FastMCP # Import the easy-to-use server framework
import re # Import regex for sentence splitting

# 1. Initialize FastMCP Server
# We give it a name, "TextAnalyzer", which might be shown in client UIs.
mcp = FastMCP("TextAnalyzer")

# 2. Tool 1: analyze_text
@mcp.tool()
async def analyze_text(text: str) -> dict:
    """
    Analyzes the provided text and returns the word count and character count.

    Args:
        text: The string of text to analyze.
    """
    # Simple analysis logic
    word_count = len(text.split())
    char_count = len(text)

    print(f"[Server] Analyzing text: '{text[:50]}...'") # Server-side log
    analysis_result = {
        "word_count": word_count,
        "char_count": char_count
    }
    print(f"[Server] Analysis result: {analysis_result}")
    # FastMCP automatically serializes the dictionary return type into
    # the appropriate MCP TextContent JSON format for the client.
    return analysis_result

# 3. Tool 2: count_sentences
@mcp.tool()
async def count_sentences(text: str) -> int:
    """
    Counts the number of sentences in the provided text.
    Uses simple punctuation (.?!) as delimiters.

    Args:
        text: The string of text to analyze.
    """
    print(f"[Server] Counting sentences in: '{text[:50]}...'") # Server log
    # Simple sentence split based on common terminators
    sentences = re.split(r'[.?!]+', text)
    # Filter out empty strings that might result from splitting
    sentence_count = len([s for s in sentences if s.strip()])
    print(f"[Server] Sentence count: {sentence_count}")
    # Return the count (an integer). FastMCP handles sending this back.
    return sentence_count

# 4. Entry point to run the server
if __name__ == "__main__":
    print("[Server] Starting Text Analyzer MCP Server on stdio...")
    # mcp.run() starts the server listening for MCP messages.
    mcp.run(transport='stdio')