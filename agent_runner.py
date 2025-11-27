# --- A. IMPORTING THE NECESSARY TOOLS ---
# 'asyncio' is a Python library that helps run multiple tasks at the same time.
import asyncio
import json
from typing import Any
from rich import print as rprint    # Enhanced print function to support colors and formatting
from rich.syntax import Syntax      # Used to highlight JSON output in the terminal

# These are specific classes from Google's AI library for structuring messages.
from google.genai.types import Content, Part

from dotenv import load_dotenv
import os
load_dotenv()

# --- B. IMPORTING OUR AGENT ---
# We are importing the "brain" of our AI agent from our project.
from agents.website_builder_simple.agent import root_agent

# --- C. IMPORTING ADK (AGENT DEVELOPMENT KIT) COMPONENTS ---
# These are special tools from the ADK to run our agent programmatically.
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

# --- D. IMPORTING CONVERSATION MEMORY MANAGEMENT ---
# Import the conversation memory manager for context compaction
from utils.conversation_memory import ConversationMemoryManager

# --- E. IMPORTING RETRY CONFIGURATION ---
# Import retry utilities for robust API calls
from utils.retry_config import with_async_retry, API_RETRY_CONFIG, get_user_friendly_error

# --- 1. SETTING UP IDENTIFIERS (CONSTANTS) ---
# We define constant text variables to identify our application and conversation.
APP_NAME = "construction_cost_estimator"
USER_ID = "user_12345"
SESSION_ID = "session_chat_loop_1" # A unique ID for this entire chat session.

# --- MEMORY MANAGEMENT CONFIGURATION ---
# Configure conversation memory with compaction strategies
MEMORY_CONFIG = {
    "max_turns": 20,              # Keep up to 20 recent turns
    "max_tokens": 8000,           # Maximum tokens in conversation
    "compaction_threshold": 0.75, # Compact when at 75% token capacity
    "summarization_enabled": True # Summarize old conversations
}

# --- 2. THE MAIN CHAT LOOP FUNCTION ---
# This async function will set everything up once, then loop to allow for continuous chat.
async def chat_loop():
    """
    Initializes the agent and session, then enters a loop to
    continuously accept user queries and provide agent responses.
    """
    print("Agent Chat Session Started.")
    print("Type 'quit', 'exit', or ':q' to end the session.\n")

    # --- SETUP (Done Once) ---
    # The Session Service stores the conversation history (memory).
    session_service = InMemorySessionService()
    # We create the session object that will be used for the entire chat.
    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID
    )
    
    # Initialize conversation memory manager with compaction strategies
    memory_manager = ConversationMemoryManager(**MEMORY_CONFIG)

    # The Runner is the engine that executes the agent's logic.
    # Pass the API key from environment variables
    runner = Runner(
        agent=root_agent,
        app_name=APP_NAME,
        session_service=session_service,
        api_key=os.getenv("GOOGLE_API_KEY"),
    )

    # --- THE INTERACTIVE LOOP ---
    # This 'while True' loop will run indefinitely until the user decides to quit.
    while True:
        # Prompt the user for their next message.
        user_query = input("Enter your query: ")

        # Check for special commands
        if user_query.lower() in ["quit", "exit", ":q"]:
            print("Ending chat session. Goodbye!")
            break  # This command exits the 'while' loop.
        
        # Check for memory status command
        if user_query.lower() in [":status", ":memory"]:
            status = memory_manager.get_status()
            print("\n[MEMORY STATUS]")
            print(f"  Current turns: {status['current_turns']}")
            print(f"  Summaries: {status['summaries']}")
            print(f"  Estimated tokens: {status['estimated_tokens']}")
            print(f"  Total tokens used: {status['total_tokens_used']}")
            print(f"  Compression ratio: {status['compression_ratio']:.2f}x\n")
            continue  # Skip agent execution for status command
        
        # Check for save history command
        if user_query.lower() in [":save", ":export"]:
            filename = f"conversation_history_{SESSION_ID}.json"
            memory_manager.save_to_file(filename)
            print(f"\nConversation history saved to: {filename}\n")
            continue  # Skip agent execution for save command

        # --- Agent Interaction (Inside the Loop) ---
        # Format the user's query into the structure the agent understands.
        new_message = Content(role="user", parts=[Part(text=user_query)])

        try:
            # The runner.run() method sends the message and gets a stream of events back.
            # Because we are using the SAME runner and session IDs each time, the agent
            # remembers the previous parts of the conversation.
            # Wrapped with retry logic for robust API calls
            events = runner.run_async(
                user_id=USER_ID,
                session_id=SESSION_ID,
                new_message=new_message
            )

            # --- Process the Event Stream ---
            # We loop through the agent's "thinking steps" (events) to find the final answer.
            final_response = ""
            i = 0
            async for event in events:
            i+= 1  # Increment the event counter
            # Print each event as it comes in, with a title for clarity.
            # This helps us see the agent's thought process step-by-step.
            print_json_response(event, f"============Event #{i}=============")

            if hasattr(event, "author") and event.author == "code_writer_agent":

                if event.is_final_response():
                    # If the event is a final response, we extract the text.
                    # This is the agent's final answer to the user's query.
                    final_response = event.content.parts[0].text
                    
                    # Add turn to memory manager
                    memory_manager.add_turn(
                        user_message=user_query,
                        assistant_response=final_response,
                        tokens_used=0  # In production, get actual token count from API
                    )
                    
                    # Print a clean separation for the agent's response.
                    print(f"\nAgent Response:\n------------------------\n{final_response}\n")
                    
                    # Print memory status
                    status = memory_manager.get_status()
                    print(f"[Memory: {status['current_turns']} turns, {status['estimated_tokens']} tokens, "
                          f"{status['summaries']} summaries]\n")
                    
                    break # Stop processing events once we have the final answer.
        
        except Exception as e:
            # Handle API errors with graceful error messages
            error_msg = get_user_friendly_error(e)
            print(f"\n❌ Error: {error_msg}")
            print(f"Technical details: {str(e)}\n")
            print("Please try again. If the problem persists, check your API key and internet connection.\n")



# -----------------------------------------------------------------------------
# Helper: Pretty print JSON objects using syntax coloring
# -----------------------------------------------------------------------------
def print_json_response(response: Any, title: str) -> None:
    # Displays a formatted and color-highlighted view of the response
    print(f"\n=== {title} ===")  # Section title for clarity
    try:
        if hasattr(response, "root"):  # Check if response is wrapped by SDK
            data = response.root.model_dump(mode="json", exclude_none=True)
        else:
            data = response.model_dump(mode="json", exclude_none=True)

        json_str = json.dumps(data, indent=2, ensure_ascii=False)  # Convert dict to pretty JSON string
        syntax = Syntax(json_str, "json", theme="monokai", line_numbers=False)  # Apply syntax highlighting
        rprint(syntax)  # Print it with color
    except Exception as e:
        # Print fallback text if something fails
        rprint(f"[red bold]Error printing JSON:[/red bold] {e}")
        rprint(repr(response))


# --- 3. STARTING THE PROGRAM ---
# This is the entry point that runs our chat loop.
if __name__ == '__main__':
    asyncio.run(chat_loop())