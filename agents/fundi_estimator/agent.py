# =============================================================================
# FILE: agent.py
# PURPOSE:
#   This file defines the root LLM agent for the construction cost estimator.
#   The agent gathers project details from users and generates detailed cost
#   estimates for residential building projects in Kenya.
# =============================================================================

import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

# Import the base class for a language-model-powered agent from Google ADK.
from google.adk.agents import LlmAgent

# Import the custom tool that handles writing estimate reports to timestamped files.
from tools.file_writer_tool import write_to_file, write_estimate_report

# Import a utility function that reads instruction and description files from disk.
from utils.file_loader import load_instructions_file

# -----------------------------------------------------------------------------
# Define the root LLM agent for this app. It is a single-agent app (no sub-agents).
# -----------------------------------------------------------------------------
root_agent = LlmAgent(
    name="construction_cost_estimator",  # Unique name for the agent; also shown in the UI.

    model="gemini-2.5-flash",   # The ID of the Gemini model used to generate responses.

    # The prompt/instruction that tells the agent what kind of behavior to exhibit.
    # It is loaded from a file
    instruction=load_instructions_file("agents/fundi_estimator/instructions.txt"),

    # A short summary of what the agent does.
    # It is loaded from a file
    description=load_instructions_file("agents/fundi_estimator/description.txt"),

    # No tools for basic chat to prevent strict schema failures.
    # The report generation logic will be handled outside the chat loop or via a dedicated path.
    tools=[],
)