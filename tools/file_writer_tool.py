# =============================================================================
# FILE: file_writer_tool.py
# PURPOSE:
#   This module defines tool functions for saving construction cost estimates
#   to timestamped files. Used to persist generated estimate reports.
# =============================================================================

import os
import sys
import json
from datetime import datetime
from pathlib import Path

# Add parent directory to path to import retry utilities
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from utils.retry_config import with_retry, FILE_RETRY_CONFIG, get_user_friendly_error

# -----------------------------------------------------------------------------
# TOOL FUNCTION: write_estimate_report
# -----------------------------------------------------------------------------
@with_retry(FILE_RETRY_CONFIG)
def write_estimate_report(html_content: str, estimate_data_json: str = None, user_email: str = None) -> dict:
    """
    Saves the estimate locally for debugging and records.
    
    Args:
        html_content: The full HTML string of the report.
        estimate_data_json: JSON string containing raw estimate numbers (optional).
        user_email: The email address to send the PDF to (optional - unused here now, handled by estimate_handler).
    """
    try:
        # Ensure output directory exists
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)

        # Generate timestamp
        timestamp = datetime.now().strftime("%y%m%d_%H%M%S")
        
        # Define filenames
        base_name = f"{timestamp}_construction_estimate"
        html_filename = output_dir / f"{base_name}.html"
        json_filename = output_dir / f"{base_name}.json"

        # 1. Save HTML (as backup/source)
        with open(html_filename, "w", encoding="utf-8") as f:
            f.write(html_content)

        # 2. Save JSON Data (if provided)
        if estimate_data_json:
            try:
                estimate_data = json.loads(estimate_data_json)
                with open(json_filename, "w", encoding="utf-8") as f:
                    json.dump(estimate_data, f, indent=2)
            except json.JSONDecodeError:
                # Fallback if invalid JSON
                with open(json_filename, "w", encoding="utf-8") as f:
                    f.write(estimate_data_json)

        return {
            "success": True,
            "files": {
                "html": str(html_filename),
                "json": str(json_filename) if estimate_data_json else None
            },
            "email_status": "Handled by estimate delivery workflow",
            "message": f"Report generated: {html_filename}"
        }

    except Exception as e:
        return get_user_friendly_error(e, "saving estimate report")


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
        "status": result["success"],
        "file": result["files"]["html"]
    }
