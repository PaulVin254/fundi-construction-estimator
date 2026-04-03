import os
from datetime import datetime
from jinja2 import Environment, FileSystemLoader

def generate_test_estimate():
    # 1. Set up Jinja2 environment pointing to your templates folder
    env = Environment(loader=FileSystemLoader('templates'))
    template = env.get_template('estimate_template.html')

    # 2. Define dummy data matching your template variables
    dummy_data = {
        "project_title": "Luxury 4-Bedroom Villa Construction",
        "estimate_reference": "EST-2026-0891",
        "client_name": "Dr. Sarah Omondi",
        "generation_date": datetime.now().strftime("%B %d, %Y"),
        "total_cost": 12450000,
        "cost_per_sqm": 55000,
        "current_year": datetime.now().year,
        "items": [
            {"description": "Preliminaries & Site Clearance", "cost": 250000},
            {"description": "Substructure (Foundation to DPC)", "cost": 1800000},
            {"description": "Superstructure Concrete Framework", "cost": 2400000},
            {"description": "Walling (Machine Cut Ndarugu Stone)", "cost": 1200000},
            {"description": "Roofing (Decra Tiles & Timber Truss)", "cost": 1500000},
            {"description": "Doors & Windows (Heavy Gauge Aluminium)", "cost": 950000},
            {"description": "Internal & External Finishes (Plastering & Paint)", "cost": 1600000},
            {"description": "Plumbing & High-End Sanitary Fittings", "cost": 850000},
            {"description": "Electrical Installations & Smart Lighting", "cost": 750000},
            {"description": "Floor Finishes (Porcelain Tiles & Wood Laminate)", "cost": 1150000}
        ]
    }

    # 3. Render the template with the dummy data
    html_content = template.render(**dummy_data)

    # 4. Save the output to a file
    output_path = os.path.join('output', 'test_estimate.html')
    
    # Ensure output directory exists
    os.makedirs('output', exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"Test estimate generated successfully at: {output_path}")

if __name__ == "__main__":
    generate_test_estimate()