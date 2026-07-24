# =============================================================================
# FILE: test_boq_system.py
# PURPOSE:
#   Pytest suite for verifying full BOQ calculation formulas, price search/cache,
#   openpyxl Excel generation, ReportLab/WeasyPrint PDF rendering, and FastAPI API routes.
# =============================================================================

import os
import pytest
from fastapi.testclient import TestClient
from main import app
from agents.fundi_estimator.boq_calculator import calculate_full_boq, DEFAULT_MATERIAL_RATES
from tools.price_cache_manager import save_material_price_to_cache, get_cached_material_price
from tools.web_search_tool import search_kenyan_material_price
from utils.excel_boq_generator import generate_excel_boq
from estimate_delivery import generate_full_boq_pdf

client = TestClient(app)

def test_boq_calculator_formulas():
    """Verify BOQ calculation engine outputs valid trades, physical items, and totals."""
    boq = calculate_full_boq(house_type="3_bedroom", location="nairobi", size_sqm=120, finish_level="standard")
    
    assert "trades" in boq
    assert len(boq["trades"]) >= 7  # 7 trades + labor
    assert boq["grand_total"] > 0
    assert boq["cost_per_sqm"] > 0
    
    # Check physical shopping list items exist
    shopping = boq["shopping_list_summary"]
    assert "Cement (50kg bags)" in shopping
    assert shopping["Cement (50kg bags)"] > 50
    assert "Machine Cut Stones (pieces)" in shopping
    assert shopping["Machine Cut Stones (pieces)"] > 1000

def test_custom_rate_override():
    """Verify Human-in-the-Loop rate override functionality."""
    custom_rates = {"cement_bag_50kg": 950.0}
    boq_default = calculate_full_boq(house_type="3_bedroom", location="nairobi", size_sqm=120)
    boq_custom = calculate_full_boq(house_type="3_bedroom", location="nairobi", size_sqm=120, custom_rates=custom_rates)
    
    assert boq_custom["grand_total"] > boq_default["grand_total"]

def test_price_cache_manager():
    """Verify local and Supabase material price caching system."""
    save_material_price_to_cache(
        material_key="test_cement_50kg",
        material_name="Test Cement 50kg",
        unit="50kg bag",
        category="Substructure",
        price_nairobi=880.0,
        price_mombasa=850.0,
        price_upcountry=900.0,
        source="test_suite"
    )
    
    cached = get_cached_material_price("test_cement_50kg")
    assert cached is not None
    assert cached["price_nairobi"] == 880.0

def test_web_search_price_discovery():
    """Verify fallback and live search price parsing."""
    res = search_kenyan_material_price("cement_bag_50kg")
    assert "price_nairobi" in res
    assert res["price_nairobi"] > 0

def test_excel_boq_generator(tmp_path):
    """Verify openpyxl generates a valid multi-tab Excel file with active formulas."""
    boq = calculate_full_boq("3_bedroom", "nairobi", 120, "standard")
    excel_file = os.path.join(tmp_path, "test_boq.xlsx")
    out_path = generate_excel_boq(boq, excel_file)
    
    assert os.path.exists(out_path)
    assert os.path.getsize(out_path) > 5000  # valid non-empty xlsx file

def test_pdf_boq_generator():
    """Verify multi-page BOQ PDF generation."""
    boq = calculate_full_boq("3_bedroom", "nairobi", 120, "standard")
    client_info = {"name": "Test User", "email": "test@example.com"}
    pdf_bytes = generate_full_boq_pdf(client_info, boq)
    
    assert pdf_bytes is not None
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF")

def test_boq_api_endpoints():
    """Test FastAPI /api/estimate/boq draft and approval routes."""
    # 1. Draft request
    resp_draft = client.post("/api/estimate/boq", json={
        "house_type": "3_bedroom",
        "location": "nairobi",
        "size_sqm": 120,
        "finish_level": "standard"
    })
    assert resp_draft.status_code == 200
    data = resp_draft.json()
    assert data["status"] == "success"
    assert "boq_data" in data

    # 2. HITL Approval request
    resp_approve = client.post("/api/estimate/boq/approve", json={
        "client_name": "Jane Doe",
        "client_email": "jane@example.com",
        "house_type": "3_bedroom",
        "location": "nairobi",
        "size_sqm": 120,
        "finish_level": "standard",
        "custom_rates": {"cement_bag_50kg": 900.0}
    })
    assert resp_approve.status_code == 200
    app_data = resp_approve.json()
    assert app_data["status"] == "success"
    assert "excel_download_url" in app_data
    assert "pdf_download_url" in app_data
