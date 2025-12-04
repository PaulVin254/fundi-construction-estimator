import os
import uuid
import requests
from typing import Optional
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY") # Fallback to standard key if service key not set
N8N_SECRET = os.getenv("N8N_SECRET")

# Constants
N8N_WEBHOOK_URL = "https://n8n.sitesync.tech/webhook/send-estimate"
BUCKET_NAME = "estimates"

def get_supabase_client() -> Optional[Client]:
    """Initialize and return the Supabase client."""
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        print("❌ Error: Missing Supabase credentials in environment variables.")
        return None
    try:
        return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    except Exception as e:
        print(f"❌ Error initializing Supabase client: {e}")
        return None

def handle_estimate_workflow(user_email: str, user_name: str, pdf_bytes: bytes) -> bool:
    """
    Uploads a PDF estimate to Supabase and triggers an n8n webhook for delivery.

    Args:
        user_email (str): The recipient's email address.
        user_name (str): The recipient's name.
        pdf_bytes (bytes): The PDF content in bytes.

    Returns:
        bool: True if the workflow completed successfully, False otherwise.
    """
    print(f"🚀 Starting estimate workflow for {user_email}...")

    # 1. Initialize Supabase Client
    supabase = get_supabase_client()
    if not supabase:
        return False

    # 2. Generate unique filename
    file_name = f"estimate_{uuid.uuid4()}.pdf"
    
    try:
        # 3. Upload to Supabase Storage
        print(f"📤 Uploading {file_name} to bucket '{BUCKET_NAME}'...")
        
        # Upload returns a response object, we check for errors implicitly via try/except
        # Note: supabase-py storage upload signature might vary slightly by version, 
        # but generally takes path, file, and options.
        res = supabase.storage.from_(BUCKET_NAME).upload(
            path=file_name,
            file=pdf_bytes,
            file_options={"content-type": "application/pdf"}
        )
        
        # 4. Get Public URL
        # get_public_url returns a string URL directly in newer versions
        public_url_response = supabase.storage.from_(BUCKET_NAME).get_public_url(file_name)
        
        # Handle different return types depending on version (string vs object)
        if isinstance(public_url_response, str):
            public_url = public_url_response
        elif hasattr(public_url_response, 'publicURL'): # Older versions
             public_url = public_url_response.publicURL
        else:
             # Fallback/Assumption if it's a dict or other
             public_url = str(public_url_response)

        print(f"✅ Upload successful. URL: {public_url}")

        # 5. Trigger n8n Webhook
        if not N8N_SECRET:
            print("⚠️ Warning: N8N_SECRET not found. Webhook might fail auth.")

        payload = {
            "email": user_email,
            "name": user_name,
            "pdf_url": public_url
        }

        headers = {
            "Content-Type": "application/json",
            "x-n8n-secret": N8N_SECRET if N8N_SECRET else ""
        }

        print(f"🔗 Triggering webhook at {N8N_WEBHOOK_URL}...")
        response = requests.post(N8N_WEBHOOK_URL, json=payload, headers=headers, timeout=10)

        if response.status_code == 200:
            print("✅ Webhook triggered successfully.")
            return True
        else:
            print(f"❌ Webhook failed with status {response.status_code}: {response.text}")
            return False

    except Exception as e:
        print(f"❌ Error in estimate workflow: {str(e)}")
        return False
