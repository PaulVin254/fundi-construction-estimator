# =============================================================================
# FILE: agent.py
# PURPOSE:
#   This file defines the root LLM agent for the construction cost estimator.
#   The agent gathers project details from users and generates detailed cost
#   estimates for residential building projects in Kenya.
# =============================================================================

import os
import sys
import re
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

# Import the base class for a language-model-powered agent from Google ADK.
from google.adk.agents import LlmAgent

# Import the custom tool that handles writing estimate reports to timestamped files.
from tools.file_writer_tool import write_to_file, write_estimate_report

# Import a utility function that reads instruction and description files from disk.
from utils.file_loader import load_instructions_file

def load_decoupled_instructions() -> str:
    """Loads persona and dynamic skills to build the agent's system prompt."""
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    
    # 1. Load Persona
    agents_path = os.path.join(base_dir, ".agents", "AGENTS.md")
    persona = load_instructions_file(agents_path)
    if not persona:
        # Fallback to instructions.txt if .agents/AGENTS.md is missing/empty
        fallback_path = os.path.join(os.path.dirname(__file__), "instructions.txt")
        return load_instructions_file(fallback_path)
        
    # 2. Scan and load skills from .agents/skills/
    skills_dir = os.path.join(base_dir, ".agents", "skills")
    skills_content = []
    if os.path.exists(skills_dir):
        # We sort them to ensure deterministic instruction order
        for skill_name in sorted(os.listdir(skills_dir)):
            skill_path = os.path.join(skills_dir, skill_name, "SKILL.md")
            if os.path.exists(skill_path):
                content = load_instructions_file(skill_path)
                if content:
                    # Strip YAML frontmatter if present
                    content_clean = re.sub(r"^---[\s\S]*?---", "", content).strip()
                    skills_content.append(f"# SKILL: {skill_name.upper()}\n{content_clean}")
                    
    if skills_content:
        return persona + "\n\n" + "\n\n".join(skills_content)
    return persona

# -----------------------------------------------------------------------------
# Define the root LLM agent for this app. It is a single-agent app (no sub-agents).
# -----------------------------------------------------------------------------
root_agent = LlmAgent(
    name="construction_cost_estimator",  # Unique name for the agent; also shown in the UI.

    model="gemini-2.5-flash",   # The ID of the Gemini model used to generate responses.

    # Dynamically build instruction prompt from decoupled persona and skills
    instruction=load_decoupled_instructions(),

    # A short summary of what the agent does.
    # It is loaded from a file
    description=load_instructions_file("agents/fundi_estimator/description.txt"),

    # No tools for basic chat to prevent strict schema failures.
    # The report generation logic will be handled outside the chat loop or via a dedicated path.
    tools=[],
)