# =============================================================================
# FILE: file_writer_tool.py
# PURPOSE:
#   This module defines tool functions for saving construction cost estimates
#   to timestamped files. Used to persist generated estimate reports.
# =============================================================================

import os
import sys
import json
import smtplib
from datetime import datetime
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from xhtml2pdf import pisa  # Library for HTML to PDF conversion

# Add parent directory to path to import retry utilities
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from utils.retry_config import with_retry, FILE_RETRY_CONFIG, get_user_friendly_error

def convert_html_to_pdf(source_html: str, output_filename: str) -> bool:
    """Utility function to convert HTML string to PDF file."""
    try:
        with open(output_filename, "w+b") as result_file:
            pisa_status = pisa.CreatePDF(source_html, dest=result_file)
        return not pisa_status.err
    except Exception as e:
        print(f"Error converting PDF: {e}")
        return False

def send_email_with_attachment(recipient_email: str, pdf_path: str, project_name: str):
    """Sends the PDF report via email."""
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = os.getenv("SMTP_PORT")
    sender_email = os.getenv("SMTP_EMAIL")
    sender_password = os.getenv("SMTP_PASSWORD")

    if not all([smtp_server, smtp_port, sender_email, sender_password]):
        print("⚠️ Email credentials not set in .env. Skipping email.")
        return False, "Email credentials missing in .env"

    try:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = f"Fundi Estimate: {project_name}"

        body = f"Hello,\n\nPlease find attached your construction cost estimate for the {project_name}.\n\nBest regards,\nFundi"
        msg.attach(MIMEText(body, 'plain'))

        with open(pdf_path, "rb") as f:
            attach = MIMEApplication(f.read(), _subtype="pdf")
            attach.add_header('Content-Disposition', 'attachment', filename=os.path.basename(pdf_path))
            msg.attach(attach)

        with smtplib.SMTP(smtp_server, int(smtp_port)) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
        
        return True, "Success"
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        return False, str(e)

# -----------------------------------------------------------------------------
# TOOL FUNCTION: write_estimate_report
# -----------------------------------------------------------------------------
@with_retry(FILE_RETRY_CONFIG)
def write_estimate_report(html_content: str, estimate_data: dict = None, user_email: str = None) -> dict:
    """
    Saves the estimate as a PDF and optionally emails it to the user.
    
    Args:
        html_content: The full HTML string of the report.
        estimate_data: Dictionary containing raw estimate numbers (optional).
        user_email: The email address to send the PDF to (optional).
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
        pdf_filename = output_dir / f"{base_name}.pdf"
        json_filename = output_dir / f"{base_name}.json"

        # 1. Save HTML (as backup/source)
        with open(html_filename, "w", encoding="utf-8") as f:
            f.write(html_content)

        # 2. Save JSON Data (if provided)
        if estimate_data:
            with open(json_filename, "w", encoding="utf-8") as f:
                json.dump(estimate_data, f, indent=2)

        # 3. Convert to PDF
        pdf_success = convert_html_to_pdf(html_content, str(pdf_filename))
        
        result_message = f"Report generated: {pdf_filename}"
        email_status = "Not sent (no email provided)"

        # 4. Send Email (if email provided and PDF success)
        if pdf_success and user_email:
            sent, error_msg = send_email_with_attachment(user_email, str(pdf_filename), "Residential Project")
            if sent:
                email_status = f"Sent to {user_email}"
                result_message += f" and emailed to {user_email}"
            else:
                email_status = f"Failed to send ({error_msg})"
                result_message += f" (Email failed: {error_msg})"

        return {
            "success": True,
            "files": {
                "html": str(html_filename),
                "pdf": str(pdf_filename) if pdf_success else None,
                "json": str(json_filename) if estimate_data else None
            },
            "email_status": email_status,
            "message": result_message
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
        "status": result["status"],
        "file": result["html_file"]
    }
