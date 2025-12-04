"""
Quick test script for PDF generation and email workflow.
Run: python test_email.py

Change TEST_MODE at the bottom to switch between:
  1 = PDF generation only (saves to test_output.pdf)
  2 = Full workflow (PDF + upload + webhook)
  3 = Webhook only (test n8n connection)
"""
from dotenv import load_dotenv
load_dotenv()

import os

# Debug: Print env vars immediately
print("=" * 50)
print("🔧 ENVIRONMENT CHECK")
print("=" * 50)
print(f"N8N_SECRET from env: '{os.getenv('N8N_SECRET', 'NOT FOUND')}'")
print(f"N8N_WEBHOOK_URL from env: '{os.getenv('N8N_WEBHOOK_URL', 'NOT FOUND')}'")
print("=" * 50)

from estimate_delivery import generate_professional_pdf, handle_estimate_workflow

# Test Data - Modify as needed
TEST_EMAIL = "vinwakolipaul@gmail.com"  # Your email for testing
TEST_NAME = "Paul Test"

TEST_CLIENT_DATA = {
    "name": TEST_NAME,
    "email": TEST_EMAIL,
    "project": "3 Bedroom House in Nairobi (Basic)"
}

TEST_ITEMS = [
    {"item": "Foundation", "description": "Excavation, concrete slab", "cost": "350,000"},
    {"item": "Walling", "description": "Stone masonry, basic plaster", "cost": "550,000"},
    {"item": "Roofing", "description": "Timber truss, corrugated iron sheets", "cost": "400,000"},
    {"item": "Electrical", "description": "Basic wiring, minimal fittings", "cost": "200,000"},
    {"item": "Plumbing", "description": "Basic piping, standard sanitary ware", "cost": "150,000"},
    {"item": "Finishing", "description": "Basic tiles, paint, simple ceilings", "cost": "450,000"},
    {"item": "Labor", "description": "Skilled and unskilled labor", "cost": "500,000"},
    {"item": "Contingency", "description": "10% buffer for unforeseen costs", "cost": "260,000"}
]

def test_pdf_only():
    """Test PDF generation without sending email"""
    print("=" * 50)
    print("🧪 TEST: PDF Generation Only")
    print("=" * 50)
    
    pdf_bytes = generate_professional_pdf(TEST_CLIENT_DATA, TEST_ITEMS)
    
    if pdf_bytes:
        # Save locally to inspect
        with open("test_output.pdf", "wb") as f:
            f.write(pdf_bytes)
        print(f"✅ PDF generated! Size: {len(pdf_bytes)} bytes")
        print(f"📁 Saved to: test_output.pdf")
        print("   Open this file to check the design.")
    else:
        print("❌ PDF generation failed!")
    
    return pdf_bytes

def test_full_workflow():
    """Test PDF generation AND email sending"""
    print("=" * 50)
    print("🧪 TEST: Full Workflow (PDF + Email)")
    print("=" * 50)
    
    pdf_bytes = generate_professional_pdf(TEST_CLIENT_DATA, TEST_ITEMS)
    
    if not pdf_bytes:
        print("❌ PDF generation failed! Cannot proceed.")
        return
    
    print(f"✅ PDF generated: {len(pdf_bytes)} bytes")
    print(f"📧 Attempting to send to: {TEST_EMAIL}")
    
    success = handle_estimate_workflow(TEST_EMAIL, TEST_NAME, pdf_bytes)
    
    if success:
        print("✅ Email workflow completed successfully!")
    else:
        print("❌ Email workflow failed! Check logs above.")

def test_webhook_only():
    """Test just the webhook with dummy data"""
    print("=" * 50)
    print("🧪 TEST: Webhook Only (No PDF)")
    print("=" * 50)
    
    import requests
    
    N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "https://n8n.sitesync.tech/webhook/send-estimate")
    N8N_SECRET_VALUE = os.getenv("N8N_SECRET", "")
    
    payload = {
        "email": TEST_EMAIL,
        "name": TEST_NAME,
        "pdf_url": "https://example.com/test.pdf",
        "subject": "TEST: Your Construction Estimate",
        "project_title": "Test Project"
    }
    
    # Use x-n8n-secret (no underscores - Nginx drops those headers)
    headers = {
        "Content-Type": "application/json",
        "x-n8n-secret": N8N_SECRET_VALUE
    }
    
    print(f"🔗 Webhook URL: {N8N_WEBHOOK_URL}")
    print(f"🔑 Header Name: 'x-n8n-secret'")
    print(f"🔑 Header Value: '{N8N_SECRET_VALUE}'")
    print(f"📦 Payload: {payload}")
    print(f"📤 Full Headers: {headers}")
    
    try:
        response = requests.post(N8N_WEBHOOK_URL, json=payload, headers=headers, timeout=30)
        print(f"📬 Response Status: {response.status_code}")
        print(f"📬 Response Body: {response.text[:500]}")
        
        if response.status_code == 200:
            print("✅ Webhook call successful!")
        else:
            print(f"❌ Webhook failed with status {response.status_code}")
    except Exception as e:
        print(f"❌ Webhook error: {e}")

# ===== RUN TESTS =====
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("   FUNDI ESTIMATE - QUICK TEST SUITE")
    print("=" * 60 + "\n")
    
    # Choose what to test:
    # 1 = PDF only, 2 = Full workflow, 3 = Webhook only
    TEST_MODE = 2  # <-- Testing full workflow
    
    if TEST_MODE == 1:
        test_pdf_only()
    elif TEST_MODE == 2:
        test_full_workflow()
    elif TEST_MODE == 3:
        test_webhook_only()
    else:
        print("Invalid TEST_MODE. Use 1, 2, or 3.")
