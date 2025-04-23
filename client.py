# client.py
import asyncio
import sys
import os
import json
from typing import List, Dict, Any, Optional

# MCP Imports
from mcp import ClientSession, StdioServerParameters, types as mcp_types
from mcp.client.stdio import stdio_client

# Gemini Imports
import google.generativeai as genai
# Explicitly import types needed if using start_chat's automatic handling doesn't suffice
# from google.generativeai.types import Content, Part, FunctionResponse, FunctionDeclaration, Tool as GeminiTool
from google.generativeai.types import FunctionDeclaration, Tool as GeminiTool

# Environment Variable Loading
from dotenv import load_dotenv

# 1. Load Environment Variables and Configure Gemini
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("Error: GEMINI_API_KEY not found in .env file.")
    sys.exit(1)

genai.configure(api_key=GEMINI_API_KEY)
# Using a model known to support function calling well
gemini_model = genai.GenerativeModel(model_name="gemini-1.5-flash")

# --- Helper Function to Convert MCP Tool Schema to Gemini FunctionDeclaration ---
def mcp_tool_to_gemini_function(mcp_tool: mcp_types.Tool) -> FunctionDeclaration:
    """Converts an MCP Tool schema to a Gemini FunctionDeclaration."""
    properties = {}
    required = []
    if mcp_tool.inputSchema and 'properties' in mcp_tool.inputSchema:
        for name, schema in mcp_tool.inputSchema['properties'].items():
            param_type = "STRING" # Default
            schema_type = schema.get('type')

            if schema_type == 'number':
                param_type = "NUMBER"
            elif schema_type == 'integer':
                param_type = "INTEGER"
            elif schema_type == 'boolean':
                param_type = "BOOLEAN"
            elif schema_type == 'string':
                param_type = "STRING"
            elif schema_type == 'array':
                param_type = "ARRAY"
            elif schema_type == 'object':
                 param_type = "OBJECT"

            prop_definition = {
                "type": param_type,
                "description": schema.get('description', '')
            }
            properties[name] = prop_definition
        required = mcp_tool.inputSchema.get('required', [])

    return FunctionDeclaration(
        name=mcp_tool.name,
        description=mcp_tool.description or "",
        parameters={
            "type": "OBJECT",
            "properties": properties,
            "required": required,
        },
    )
# ---------------------------------------------------------------------------

async def main():
    # 2. Get Server Path from Command Line Argument
    if len(sys.argv) < 2:
        print("Usage: python client.py <path_to_server_script.py>")
        sys.exit(1)
    server_script_path = sys.argv[1]
    print(f"[Client] Attempting to connect to server: {server_script_path}")

    # 3. Setup MCP Connection Parameters
    server_params = StdioServerParameters(
        command="python",
        args=[server_script_path],
        env=None
    )

    mcp_session: Optional[ClientSession] = None
    gemini_tools_list: List[GeminiTool] = []
    available_mcp_tools: List[mcp_types.Tool] = []

    try:
        # 4. Connect to Server using stdio_client context manager
        async with stdio_client(server_params) as (read_stream, write_stream):
            print("[Client] Stdio transport established.")

            # 5. Create and Initialize MCP Client Session
            async with ClientSession(read_stream, write_stream) as session:
                mcp_session = session
                print("[Client] Initializing MCP session...")
                await session.initialize()
                print("[Client] MCP Session Initialized.")

                # 6. Discover Available Tools from the Server
                print("[Client] Discovering tools from server...")
                try:
                    list_tools_result: mcp_types.ListToolsResult = await session.list_tools()
                    available_mcp_tools = list_tools_result.tools

                    # Print Discovered Tools
                    if available_mcp_tools:
                        print("-" * 20)
                        print("Available Tools from this Server:")
                        for tool in available_mcp_tools:
                            print(f"  - Name: {tool.name}")
                            print(f"    Description: {tool.description or 'No description'}")
                        print("-" * 20)
                    else:
                        print("[Client] No tools discovered from this server.")
                except Exception as e:
                    print(f"[Client] Error listing tools: {e}")

                # 7. Convert MCP Tools to Gemini Tools format
                gemini_functions = [mcp_tool_to_gemini_function(tool) for tool in available_mcp_tools]
                if gemini_functions:
                    # Create the Tool object for Gemini
                    gemini_tools_list = [GeminiTool(function_declarations=gemini_functions)]
                    print("[Client] Converted MCP tools for Gemini.")
                else:
                     print("[Client] No tools discovered or converted for Gemini.")

                # 8. Start Gemini Chat Session
                # Pass the prepared tools list here
                # enable_automatic_function_calling=True might handle some steps, but we'll do it manually
                # to ensure MCP is called. Let's keep it False or omit it for manual control.
                chat = gemini_model.start_chat(
                    # history=[] # Start with empty history
                )
                print("\n--- MCP Client Ready (Using Gemini Chat) ---")
                print("Enter your query, or type 'quit' to exit.")

                # 9. Interactive Chat Loop
                while True:
                    user_query = input("> ")
                    if user_query.lower() == 'quit':
                        break
                    if not user_query:
                        continue

                    try:
                        print("[Client] Sending query to Gemini Chat...")
                        # 10. Send message to chat, including tools
                        response = await chat.send_message_async(
                            user_query,
                            tools=gemini_tools_list if gemini_tools_list else None
                        )

                        # 11. Process response - Check for function call
                        # Access parts correctly via response.parts
                        response_part = response.parts[0] if response.parts else None

                        if response_part and response_part.function_call:
                            function_call = response_part.function_call
                            tool_name = function_call.name
                            tool_args = dict(function_call.args)

                            print(f"[Client] Gemini requested tool call: {tool_name}({tool_args})")

                            # 12. Call the MCP Tool via the Session
                            if mcp_session:
                                print(f"[Client] Calling MCP tool '{tool_name}'...")
                                try:
                                    tool_call_result: mcp_types.CallToolResult = await mcp_session.call_tool(tool_name, tool_args)

                                    # Process result content
                                    result_content_str = "Error: Tool executed but no parsable content returned."
                                    tool_failed = tool_call_result.isError
                                    if tool_call_result.content and isinstance(tool_call_result.content, list) and len(tool_call_result.content) > 0:
                                        first_content = tool_call_result.content[0]
                                        if isinstance(first_content, mcp_types.TextContent) and first_content.text is not None:
                                            result_content_str = first_content.text
                                            try:
                                                parsed = json.loads(result_content_str)
                                                result_content_str = json.dumps(parsed, indent=2)
                                            except json.JSONDecodeError: pass
                                    elif tool_failed: result_content_str = "Tool execution failed on server."

                                    print(f"[Client] MCP Tool Result (isError={tool_failed}): {result_content_str}")

                                    # 13. Send Tool Result back to Gemini Chat using dictionary format
                                    print("[Client] Sending tool result back to Gemini Chat...")
                                    function_response_dict = {
                                        "function_response": {
                                            "name": tool_name,
                                            "response": {"content": result_content_str}
                                        }
                                    }
                                    # Send the dictionary representing the function response
                                    response = await chat.send_message_async(
                                        function_response_dict, # Send the result dict
                                        tools=gemini_tools_list if gemini_tools_list else None
                                    )
                                    # Get the final text part after processing the result
                                    if response.parts and response.parts[0].text:
                                        print(f"\nLLM Response:\n{response.parts[0].text}\n")
                                    else:
                                        print("[Client] Gemini Chat did not provide a final text response after tool call.")

                                except Exception as tool_err:
                                     print(f"[Client] Error calling MCP tool '{tool_name}': {tool_err}")
                                     print("LLM Response: Sorry, I encountered an error trying to use the tool.")
                            else:
                                print("[Client] Error: MCP Session not available to call tool.")
                                print("LLM Response: Sorry, I cannot currently use tools.")

                        elif response_part and response_part.text:
                            # 14. Handle Direct Text Response
                            print(f"\nLLM Response:\n{response_part.text}\n")
                        else:
                             print("[Client] Received unexpected or empty response part from Gemini Chat.")

                    except Exception as e:
                        # Catch potential errors during the Gemini API call itself
                        print(f"[Client] Error during Gemini chat interaction: {type(e).__name__}: {e}")
                        # Safely check for feedback (structure might vary with chat)
                        try:
                             if response and response.prompt_feedback:
                                 print(f"Gemini Prompt Feedback: {response.prompt_feedback}")
                        except AttributeError: pass # Ignore if feedback structure isn't present
                        except Exception as inner_e: print(f"[Client] Error accessing feedback: {inner_e}")

                        print("LLM Response: Sorry, an error occurred while processing your request with the language model.")
                        # import traceback
                        # traceback.print_exc()


    except ConnectionRefusedError:
        print(f"[Client] Error: Connection refused. Is the server script path correct ('{server_script_path}') and is Python installed/runnable?")
    except FileNotFoundError:
         print(f"[Client] Error: Server script not found at '{server_script_path}'. Please check the path.")
    except Exception as e:
        print(f"[Client] An unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("[Client] Exiting.")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(main())