# =============================================================================
# FILE: file_writer_tool.py
# PURPOSE:
#   This module defines tool functions for saving construction cost estimates
#   to timestamped files. Used to persist generated estimate reports.
# =============================================================================

# Import the `datetime` module to generate a unique timestamp for the filename.
import datetime
import sys
import os

# Add parent directory to path to import retry utilities
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import `Path` from `pathlib` for convenient and safe file/directory handling.
from pathlib import Path

# Import `json` for saving structured estimate data
import json

# Import retry configuration for robust file operations
from utils.retry_config import with_retry, FILE_RETRY_CONFIG, get_user_friendly_error

# -----------------------------------------------------------------------------
# TOOL FUNCTION: write_estimate_report
# -----------------------------------------------------------------------------
@with_retry(FILE_RETRY_CONFIG)
def write_estimate_report(html_content: str, estimate_data: dict = None) -> dict:
    """
    Writes a construction cost estimate report to a timestamped HTML file.
    Includes automatic retry with exponential backoff for file operations.

    Args:
        html_content (str): Full HTML content of the estimate report as a string.
        estimate_data (dict): Optional structured estimate data for JSON backup.

    Returns:
        dict: A dictionary containing the status and generated filenames.
        
    Raises:
        RetryExhaustedError: If all retry attempts fail
    """
    
    try:
        # Get the current date and time, format it as YYMMDD_HHMMSS.
        # Example: "251118_142317"
        timestamp = datetime.datetime.now().strftime("%y%m%d_%H%M%S")

        # Construct the output filenames using the timestamp.
        # Example: "output/251118_142317_construction_estimate.html"
        html_filename = f"output/{timestamp}_construction_estimate.html"
        json_filename = f"output/{timestamp}_construction_estimate.json"

        # Ensure the "output" directory exists. If it doesn't, create it.
        # `exist_ok=True` prevents an error if the directory already exists.
        Path("output").mkdir(exist_ok=True)

        # Write the HTML content to the constructed file.
        # `encoding='utf-8'` ensures proper character encoding.
        Path(html_filename).write_text(html_content, encoding="utf-8")

        # If estimate data provided, also save as JSON for data portability
        if estimate_data:
            Path(json_filename).write_text(
                json.dumps(estimate_data, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )

        # Return a dictionary indicating success and the filenames that were written.
        return {
            "status": "success",
            "html_file": html_filename,
            "json_file": json_filename if estimate_data else None,
            "timestamp": timestamp,
            "message": "Estimate report saved successfully"
        }
        
    except Exception as e:
        # Return graceful error message
        error_msg = get_user_friendly_error(e)
        return {
            "status": "error",
            "error": error_msg,
            "technical_error": str(e),
            "message": "Failed to save estimate report. Please try again."
        }


# Backward compatibility: alias for old function name
def write_to_file(content: str) -> dict:
    """
    Legacy function name for backward compatibility.
    Writes content to a timestamped HTML file.

    Args:
        content (str): HTML content to save.

    Returns:
        dict: A dictionary containing the status and generated filename.
    """
    result = write_estimate_report(content)
    return {
        "status": result["status"],
        "file": result["html_file"]
    }
