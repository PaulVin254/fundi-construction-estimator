import os
from estimate_delivery import generate_professional_pdf, WEASYPRINT_AVAILABLE, WEASYPRINT_VERSION


def main() -> None:
    """Generate a parity PDF using the same production code path and print renderer diagnostics."""
    print("=== PDF Parity Check ===")
    print(f"WEASYPRINT_AVAILABLE={WEASYPRINT_AVAILABLE}")
    print(f"WEASYPRINT_VERSION={WEASYPRINT_VERSION}")
    print(f"PDF_ALLOW_LEGACY_FALLBACK={os.getenv('PDF_ALLOW_LEGACY_FALLBACK', 'false')}")
    print(f"ESTIMATE_LOGO_URL={os.getenv('ESTIMATE_LOGO_URL', 'https://eris.co.ke/eris-engineering-logo.svg')}")

    client_data = {
        "name": "Acme Corp Ltd",
        "email": "procurement@acmecorp.co.ke",
        "project": "Headquarters Renovation",
    }

    estimate_items = [
        {"description": "Site Preparation and Demolition", "cost": "250000"},
        {"description": "Foundation and Substructure", "cost": "1200000"},
        {"description": "Walling and Roofing Framework", "cost": "850000"},
        {"description": "Plumbing and Electrical First Fix", "cost": "450000"},
        {"description": "Finishes: plaster, paint, and tiles", "cost": "900000"},
        {"description": "Fixtures and Fittings", "cost": "600000"},
    ]

    pdf_bytes = generate_professional_pdf(client_data, estimate_items)

    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "parity_estimate.pdf")

    with open(output_path, "wb") as f:
        f.write(pdf_bytes)

    print(f"OK: parity PDF written to {output_path} ({len(pdf_bytes)} bytes)")


if __name__ == "__main__":
    main()
