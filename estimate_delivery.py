import os
import uuid
import io
import requests
from datetime import datetime
from typing import List, Dict, Optional
from supabase import create_client, Client
from dotenv import load_dotenv

# PDF Generation Libraries
try:
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False
    print("⚠️ WeasyPrint not available. Falling back to xhtml2pdf.")

from xhtml2pdf import pisa
from jinja2 import Environment, FileSystemLoader, select_autoescape

# Load environment variables
load_dotenv()

# =============================================================================
# 1. CONFIGURATION
# =============================================================================

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY') or os.getenv('SUPABASE_KEY')
N8N_WEBHOOK_URL = "https://n8n.sitesync.tech/webhook/send-estimate"
N8N_SECRET = os.getenv('N8N_SECRET')
BUCKET_NAME = 'estimates'
LOGO_URL = 'https://eris.co.ke/eris-engineering-logo.svg'

# Template Directory
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), 'templates')

# Initialize Jinja2 Environment
jinja_env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=select_autoescape(['html', 'xml'])
)

# =============================================================================
# 2. PDF GENERATION (WeasyPrint + Jinja2 - Primary)
# =============================================================================

def generate_professional_pdf(client_data: Dict[str, str], estimate_items: List[Dict[str, str]]) -> bytes:
    """
    Generates a professional PDF estimate using WeasyPrint + Jinja2.
    
    Args:
        client_data: Dict with 'name', 'email', 'project'.
        estimate_items: List of dicts with 'item', 'description', 'cost'.
        
    Returns:
        bytes: The generated PDF content.
    """
    
    # Calculate Total
    total_cost = 0.0
    processed_items = []
    
    for item in estimate_items:
        cost_str = str(item.get('cost', '0')).replace(',', '').replace('KES', '').strip()
        try:
            cost_val = float(cost_str)
            total_cost += cost_val
        except ValueError:
            cost_val = 0.0
        
        processed_items.append({
            'item': item.get('item', ''),
            'description': item.get('description', ''),
            'cost': f"{cost_val:,.0f}"
        })
    
    # Generate estimate number
    estimate_number = datetime.now().strftime("%Y%m%d") + "-" + uuid.uuid4().hex[:6].upper()
    
    # Prepare template context
    context = {
        'client_name': client_data.get('name', 'Valued Client'),
        'client_email': client_data.get('email', 'N/A'),
        'project_title': client_data.get('project', 'Residential Construction'),
        'estimate_number': estimate_number,
        'issue_date': datetime.now().strftime("%B %d, %Y"),
        'current_year': datetime.now().year,
        'items': processed_items,
        'total_cost': f"{total_cost:,.0f}",
        'cost_per_sqm': None,  # Can be calculated if square meters provided
    }
    
    # Load and render template
    try:
        template = jinja_env.get_template('estimate_template.html')
        html_content = template.render(**context)
    except Exception as e:
        print(f"❌ Template Error: {e}")
        # Fallback to legacy method
        return generate_simple_pdf(client_data, estimate_items)
    
    # Generate PDF with WeasyPrint
    if WEASYPRINT_AVAILABLE:
        try:
            print("📄 Generating PDF with WeasyPrint...")
            html = HTML(string=html_content, base_url=TEMPLATE_DIR)
            pdf_bytes = html.write_pdf()
            print("✅ Professional PDF generated successfully!")
            return pdf_bytes
        except Exception as e:
            print(f"⚠️ WeasyPrint Error: {e}. Falling back to xhtml2pdf.")
            return generate_simple_pdf(client_data, estimate_items)
    else:
        print("⚠️ WeasyPrint not installed. Using xhtml2pdf fallback.")
        return generate_simple_pdf(client_data, estimate_items)

# =============================================================================
# 3. PDF GENERATION (xhtml2pdf - Fallback)
# =============================================================================

def generate_simple_pdf(client_data: Dict[str, str], estimate_items: List[Dict[str, str]]) -> bytes:
    """
    Generates a PDF estimate using xhtml2pdf (CSS 2.1 compliant).
    This is the fallback method when WeasyPrint is not available.
    
    Args:
        client_data: Dict with 'name', 'email', 'project'.
        estimate_items: List of dicts with 'item', 'description', 'cost'.
        
    Returns:
        bytes: The generated PDF content.
    """
    
    # Calculate Total
    total_cost = 0.0
    rows_html = ""
    
    for i, item in enumerate(estimate_items):
        cost_str = str(item.get('cost', '0')).replace(',', '').replace('KES', '').strip()
        try:
            cost_val = float(cost_str)
            total_cost += cost_val
        except ValueError:
            cost_val = 0.0
            
        # Alternating row colors
        bg_color = "#f9f9f9" if i % 2 == 0 else "#ffffff"
            
        rows_html += f"""
        <tr style="background-color: {bg_color};">
            <td style="padding: 10px; border-bottom: 1px solid #eee;">{item.get('item', '')}</td>
            <td style="padding: 10px; border-bottom: 1px solid #eee;">{item.get('description', '')}</td>
            <td style="padding: 10px; border-bottom: 1px solid #eee; text-align: right; font-family: monospace;">{cost_val:,.2f}</td>
        </tr>
        """

    # HTML Template (CSS 2.1 compatible - No Flexbox)
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            @page {{
                size: A4;
                margin: 2cm;
                @frame footer_frame {{
                    -pdf-frame-content: footerContent;
                    bottom: 1cm;
                    margin-left: 2cm;
                    margin-right: 2cm;
                    height: 1cm;
                }}
            }}
            body {{
                font-family: Helvetica, sans-serif;
                font-size: 11px;
                color: #333333;
                line-height: 1.4;
            }}
            .header-table {{
                width: 100%;
                margin-bottom: 30px;
                border-bottom: 3px solid #2c3e50;
                padding-bottom: 10px;
            }}
            .logo {{
                width: 150px;
                height: auto;
            }}
            .title {{
                font-size: 28px;
                font-weight: bold;
                color: #2c3e50;
                text-align: right;
                margin-bottom: 5px;
            }}
            .subtitle {{
                font-size: 12px;
                color: #7f8c8d;
                text-align: right;
            }}
            .client-box {{
                background-color: #f8f9fa;
                padding: 20px;
                margin-bottom: 30px;
                border-left: 5px solid #2c3e50;
                border-radius: 4px;
            }}
            .client-box h3 {{
                margin-top: 0;
                color: #2c3e50;
                font-size: 14px;
                text-transform: uppercase;
                letter-spacing: 1px;
                border-bottom: 1px solid #ddd;
                padding-bottom: 5px;
                margin-bottom: 10px;
            }}
            .items-table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
            }}
            .items-table th {{
                background-color: #2c3e50;
                color: #ffffff;
                font-weight: bold;
                padding: 12px;
                text-align: left;
                font-size: 12px;
                text-transform: uppercase;
            }}
            .total-row td {{
                font-weight: bold;
                font-size: 16px;
                padding: 15px;
                background-color: #2c3e50;
                color: #ffffff;
                text-align: right;
            }}
            .watermark {{
                position: fixed;
                top: 40%;
                left: 50%;
                transform: rotate(45deg);
                font-size: 100px;
                color: #ecf0f1;
                z-index: -1000;
                text-align: center;
                width: 100%;
                opacity: 0.4;
                font-weight: bold;
            }}
            .disclaimer {{
                font-size: 9px;
                color: #7f8c8d;
                margin-top: 30px;
                text-align: justify;
                border-top: 1px solid #eee;
                padding-top: 10px;
            }}
        </style>
    </head>
    <body>
        <!-- Watermark -->
        <div class="watermark">ESTIMATE</div>

        <!-- Header Layout using Table -->
        <table class="header-table">
            <tr>
                <td valign="middle">
                    <img src="{LOGO_URL}" class="logo" />
                </td>
                <td valign="middle" align="right">
                    <div class="title">Construction Estimate</div>
                    <div class="subtitle">Generated by Fundi Agent</div>
                    <div class="subtitle">Date: {uuid.uuid4().hex[:8]}</div>
                </td>
            </tr>
        </table>

        <!-- Client Info -->
        <div class="client-box">
            <h3>Client Details</h3>
            <table width="100%">
                <tr>
                    <td width="15%"><b>Name:</b></td>
                    <td width="35%">{client_data.get('name', 'Valued Client')}</td>
                    <td width="15%"><b>Project:</b></td>
                    <td width="35%">{client_data.get('project', 'Residential Construction')}</td>
                </tr>
                <tr>
                    <td><b>Email:</b></td>
                    <td>{client_data.get('email', 'N/A')}</td>
                    <td><b>Ref ID:</b></td>
                    <td>{uuid.uuid4().hex[:8].upper()}</td>
                </tr>
            </table>
        </div>

        <!-- Items Table -->
        <table class="items-table">
            <thead>
                <tr>
                    <th width="25%">Item</th>
                    <th width="55%">Description</th>
                    <th width="20%" align="right">Cost (KES)</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
                <tr class="total-row">
                    <td colspan="2">TOTAL ESTIMATED COST</td>
                    <td>{total_cost:,.2f}</td>
                </tr>
            </tbody>
        </table>

        <!-- Disclaimer -->
        <div class="disclaimer">
            <b>Disclaimer:</b> This is an AI-generated rough estimate based on 2025 Kenyan market rates. 
            Actual costs may vary significantly based on specific materials chosen, contractor rates, site conditions, and market fluctuations. 
            This document does not constitute a binding contract or a guaranteed price. 
            We strongly recommend obtaining at least three professional quotes from licensed contractors and consulting with a quantity surveyor before commencing construction.
        </div>

        <!-- Footer (Defined in @page frame) -->
        <div id="footerContent" align="center" style="color: #999; font-size: 10px;">
            &copy; 2025 Eris Engineering. All Rights Reserved. | www.eris.co.ke
        </div>
    </body>
    </html>
    """

    # Convert HTML to PDF
    print("📄 Generating PDF with xhtml2pdf...")
    pdf_buffer = io.BytesIO()
    pisa_status = pisa.CreatePDF(io.StringIO(html_content), dest=pdf_buffer)
    
    if pisa_status.err:
        print("❌ PDF Generation Error")
        return b""
        
    return pdf_buffer.getvalue()

# =============================================================================
# 3. WORKFLOW ORCHESTRATION
# =============================================================================

def handle_estimate_workflow(user_email: str, user_name: str, pdf_bytes: bytes) -> bool:
    """
    Orchestrates the secure delivery: Upload -> Webhook.
    """
    print(f"🚀 Starting workflow for {user_email}...")

    if not pdf_bytes:
        print("❌ Error: PDF content is empty.")
        return False

    # 1. Initialize Supabase
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        print("❌ Error: Missing Supabase credentials.")
        return False
        
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    except Exception as e:
        print(f"❌ Error initializing Supabase: {e}")
        return False

    # 2. Generate Filename
    filename = f"estimate_{uuid.uuid4()}.pdf"

    try:
        # 3. Upload to Supabase
        print(f"📤 Uploading {filename}...")
        supabase.storage.from_(BUCKET_NAME).upload(
            path=filename,
            file=pdf_bytes,
            file_options={"content-type": "application/pdf"}
        )

        # 4. Get Public URL
        public_url = supabase.storage.from_(BUCKET_NAME).get_public_url(filename)
        
        # Handle legacy return type if necessary
        if not isinstance(public_url, str) and hasattr(public_url, 'publicURL'):
             public_url = public_url.publicURL
             
        print(f"✅ Uploaded: {public_url}")

        # 5. Trigger n8n Webhook
        payload = {
            "email": user_email,
            "name": user_name,
            "pdf_url": public_url
        }

        headers = {
            "Content-Type": "application/json",
            "x-n8n-header-auth": N8N_SECRET if N8N_SECRET else ""
        }

        print(f"🔗 Calling Webhook: {N8N_WEBHOOK_URL}")
        response = requests.post(N8N_WEBHOOK_URL, json=payload, headers=headers, timeout=15)

        if response.status_code == 200:
            print("✅ Webhook Success! Estimate sent.")
            return True
        else:
            print(f"❌ Webhook Failed: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        print(f"❌ Workflow Error: {str(e)}")
        return False

# =============================================================================
# 5. MAIN EXECUTION (TEST)
# =============================================================================

if __name__ == "__main__":
    print("🧪 Running Estimate Delivery Test...")
    print(f"   WeasyPrint Available: {WEASYPRINT_AVAILABLE}")
    
    # Dummy Data
    client = {
        "name": "Jane Doe",
        "email": "jane.test@example.com",
        "project": "3BR Bungalow in Mombasa (Premium)"
    }
    
    items = [
        {"item": "Foundation", "description": "Excavation, reinforced concrete footing, slab", "cost": "600000"},
        {"item": "Walling", "description": "Stone masonry, mortar, plaster", "cost": "900000"},
        {"item": "Roofing", "description": "Timber truss, iron sheets/tiles", "cost": "700000"},
        {"item": "Electrical", "description": "Wiring, fittings, labor", "cost": "400000"},
        {"item": "Plumbing", "description": "Piping, sanitary ware, labor", "cost": "350000"},
        {"item": "Finishing", "description": "Tiles, paint, ceiling, cabinets", "cost": "1500000"},
        {"item": "Labor", "description": "Skilled and unskilled labor", "cost": "900000"},
        {"item": "Contingency", "description": "10% buffer for unforeseen costs", "cost": "535000"}
    ]

    # Test Professional PDF (WeasyPrint)
    print("\n📄 Testing Professional PDF Generation...")
    pdf_content = generate_professional_pdf(client, items)
    
    if pdf_content:
        # Save locally for preview
        with open("test_estimate.pdf", "wb") as f:
            f.write(pdf_content)
        print(f"✅ PDF saved to test_estimate.pdf ({len(pdf_content)} bytes)")
        
        # Optionally run workflow
        # handle_estimate_workflow(client["email"], client["name"], pdf_content)
    else:
        print("❌ Failed to generate PDF.")
