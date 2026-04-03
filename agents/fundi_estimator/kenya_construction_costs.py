# =============================================================================
# FILE: kenya_construction_costs.py
# PURPOSE:
#   Reference data for construction costs in Kenya. Used to support accurate
#   estimates for residential building projects across different regions.
# =============================================================================

# Kenyan construction cost data (in KES per unit)
# Based on 2025 market rates

CONSTRUCTION_COSTS_KENYA = {
    "foundation": {
        "description": "Excavation and concrete foundation",
        "unit": "per square meter of building",
        "nairobi": 8500,
        "mombasa": 7500,
        "upcountry": 6500,
    },
    "concrete_columns_beams": {
        "description": "Concrete columns, beams, and structural elements",
        "unit": "per square meter",
        "nairobi": 12000,
        "mombasa": 11000,
        "upcountry": 10000,
    },
    "brickwork_walls": {
        "description": "Brick walls with plastering",
        "unit": "per square meter",
        "nairobi": 6500,
        "mombasa": 6000,
        "upcountry": 5500,
    },
    "roofing": {
        "description": "Roofing materials (tiles/iron sheets) and installation",
        "unit": "per square meter",
        "options": {
            "iron_sheets": {"nairobi": 1200, "mombasa": 1100, "upcountry": 1000},
            "concrete_tiles": {"nairobi": 2500, "mombasa": 2300, "upcountry": 2000},
            "ceramic_tiles": {"nairobi": 3500, "mombasa": 3200, "upcountry": 2800},
        }
    },
    "flooring": {
        "description": "Concrete slab and flooring",
        "unit": "per square meter",
        "options": {
            "concrete": {"nairobi": 2000, "mombasa": 1800, "upcountry": 1600},
            "tiles": {"nairobi": 3500, "mombasa": 3200, "upcountry": 2800},
            "wooden": {"nairobi": 4000, "mombasa": 3700, "upcountry": 3300},
        }
    },
    "windows_doors": {
        "description": "Windows and doors (frames and installation)",
        "unit": "per unit",
        "standard_door": {"nairobi": 8000, "mombasa": 7500, "upcountry": 6500},
        "standard_window": {"nairobi": 5000, "mombasa": 4500, "upcountry": 4000},
    },
    "electrical": {
        "description": "Electrical wiring, distribution boards, fittings",
        "unit": "per square meter",
        "nairobi": 2500,
        "mombasa": 2300,
        "upcountry": 2000,
    },
    "plumbing": {
        "description": "Water supply and drainage systems",
        "unit": "per square meter",
        "nairobi": 2200,
        "mombasa": 2000,
        "upcountry": 1800,
    },
    "finishing_paint": {
        "description": "Interior and exterior painting",
        "unit": "per square meter",
        "basic": {"nairobi": 800, "mombasa": 700, "upcountry": 600},
        "premium": {"nairobi": 1500, "mombasa": 1400, "upcountry": 1200},
    },
    "kitchen_sanitary": {
        "description": "Kitchen cabinets, bathroom fittings (per unit)",
        "unit": "unit",
        "basic_kitchen": {"nairobi": 80000, "mombasa": 70000, "upcountry": 60000},
        "premium_kitchen": {"nairobi": 150000, "mombasa": 140000, "upcountry": 120000},
        "bathroom_suite": {"nairobi": 50000, "mombasa": 45000, "upcountry": 40000},
    },
    "labor": {
        "description": "Labor costs (typically 20-30% of material costs)",
        "percentage": 0.25,  # 25% average
    },
}

HOUSE_TYPES = {
    "1_bedroom": {
        "typical_size": 40,  # square meters
        "description": "Small single bedroom house"
    },
    "2_bedroom": {
        "typical_size": 80,
        "description": "Two bedroom house with living area"
    },
    "3_bedroom": {
        "typical_size": 120,
        "description": "Three bedroom house with kitchen and bathrooms"
    },
    "4_bedroom": {
        "typical_size": 160,
        "description": "Four bedroom house with more amenities"
    },
    "5_bedroom": {
        "typical_size": 200,
        "description": "Larger five bedroom house"
    },
}

LOCATIONS = {
    "nairobi": "Nairobi (capital, highest costs)",
    "mombasa": "Mombasa (coastal, moderate costs)",
    "upcountry": "Upcountry (other regions, lower costs)",
}

FINISH_LEVELS = {
    "basic": {
        "description": "Basic finishes - plastered walls, basic paint, minimal fittings",
        "cost_multiplier": 1.0
    },
    "standard": {
        "description": "Standard finishes - painted walls, tiled floors, adequate fittings",
        "cost_multiplier": 1.3
    },
    "premium": {
        "description": "Premium finishes - high-quality paint, premium tiles, quality fittings",
        "cost_multiplier": 1.6
    },
}


def get_location_code(location_name: str) -> str:
    """Convert location name to code (nairobi, mombasa, upcountry)."""
    location_lower = location_name.lower().strip()
    if "nairobi" in location_lower or "nai" in location_lower:
        return "nairobi"
    elif "mombasa" in location_lower or "mom" in location_lower or "coast" in location_lower:
        return "mombasa"
    else:
        return "upcountry"


def get_house_size(house_type: str) -> int:
    """Get typical square meters for a house type."""
    house_type_lower = house_type.lower().replace(" ", "_").replace("-", "_")
    if house_type_lower in HOUSE_TYPES:
        return HOUSE_TYPES[house_type_lower]["typical_size"]
    return 100  # Default


def calculate_basic_estimate(
    house_type: str = "3_bedroom",
    location: str = "nairobi",
    size_sqm: int = None,
    finish_level: str = "standard"
) -> dict:
    """
    Calculate a basic construction estimate.
    
    Args:
        house_type: Type of house (1_bedroom, 2_bedroom, etc.)
        location: Location (nairobi, mombasa, upcountry)
        size_sqm: Custom size in square meters (optional)
        finish_level: Finish level (basic, standard, premium)
    
    Returns:
        Dictionary with cost breakdown
    """
    
    # Get location code
    loc = get_location_code(location)
    
    # Get size
    if size_sqm is None:
        size_sqm = get_house_size(house_type)
    
    # Get finish multiplier
    finish_mult = FINISH_LEVELS.get(finish_level.lower(), FINISH_LEVELS["standard"])["cost_multiplier"]
    
    # Calculate costs
    costs = {
        "location": loc,
        "house_type": house_type,
        "size_sqm": size_sqm,
        "finish_level": finish_level,
        "breakdown": {}
    }
    
    # Foundation
    foundation_cost = (CONSTRUCTION_COSTS_KENYA["foundation"][loc] * size_sqm * finish_mult)
    costs["breakdown"]["Foundation"] = foundation_cost
    
    # Structural elements
    structural = (CONSTRUCTION_COSTS_KENYA["concrete_columns_beams"][loc] * size_sqm * finish_mult)
    costs["breakdown"]["Structural (Columns/Beams)"] = structural
    
    # Walls
    walls = (CONSTRUCTION_COSTS_KENYA["brickwork_walls"][loc] * size_sqm * finish_mult)
    costs["breakdown"]["Walls & Plastering"] = walls
    
    # Roofing (using standard tiles)
    roof_cost = (CONSTRUCTION_COSTS_KENYA["roofing"]["options"]["concrete_tiles"][loc] * size_sqm * finish_mult)
    costs["breakdown"]["Roofing"] = roof_cost
    
    # Flooring
    floor_cost = (CONSTRUCTION_COSTS_KENYA["flooring"]["options"]["tiles"][loc] * size_sqm * finish_mult)
    costs["breakdown"]["Flooring"] = floor_cost
    
    # Windows and doors (estimate based on size)
    num_windows = max(2, size_sqm // 20)
    num_doors = max(2, size_sqm // 40)
    windows_doors = (
        num_windows * CONSTRUCTION_COSTS_KENYA["windows_doors"]["standard_window"][loc] +
        num_doors * CONSTRUCTION_COSTS_KENYA["windows_doors"]["standard_door"][loc]
    ) * finish_mult
    costs["breakdown"]["Windows & Doors"] = windows_doors
    
    # Electrical
    electrical = (CONSTRUCTION_COSTS_KENYA["electrical"][loc] * size_sqm * finish_mult)
    costs["breakdown"]["Electrical"] = electrical
    
    # Plumbing
    plumbing = (CONSTRUCTION_COSTS_KENYA["plumbing"][loc] * size_sqm * finish_mult)
    costs["breakdown"]["Plumbing"] = plumbing
    
    # Painting
    painting = (CONSTRUCTION_COSTS_KENYA["finishing_paint"]["basic"][loc] * size_sqm * finish_mult)
    costs["breakdown"]["Painting"] = painting
    
    # Kitchen and sanitary
    kitchen = CONSTRUCTION_COSTS_KENYA["kitchen_sanitary"]["basic_kitchen"][loc] * finish_mult
    bathrooms = int(size_sqm / 30) * CONSTRUCTION_COSTS_KENYA["kitchen_sanitary"]["bathroom_suite"][loc] * finish_mult
    costs["breakdown"]["Kitchen"] = kitchen
    costs["breakdown"]["Bathrooms"] = bathrooms
    
    # Subtotal (materials + basic labor)
    subtotal = sum(costs["breakdown"].values())
    
    # Add labor (additional)
    labor = subtotal * CONSTRUCTION_COSTS_KENYA["labor"]["percentage"]
    costs["breakdown"]["Labor"] = labor
    
    # Contingency (10-15%)
    contingency = subtotal * 0.12
    costs["breakdown"]["Contingency (12%)"] = contingency
    
    # Total
    costs["total"] = sum(costs["breakdown"].values())
    costs["cost_per_sqm"] = costs["total"] / size_sqm
    
    return costs


if __name__ == "__main__":
    # Example usage
    estimate = calculate_basic_estimate(
        house_type="3_bedroom",
        location="Nairobi",
        finish_level="standard"
    )
    
    print("Construction Estimate for Kenya")
    print("=" * 50)
    print(f"House Type: {estimate['house_type']}")
    print(f"Location: {estimate['location']}")
    print(f"Size: {estimate['size_sqm']} sq.m")
    print(f"Finish Level: {estimate['finish_level']}")
    print()
    print("Cost Breakdown (KES):")
    print("-" * 50)
    
    for item, cost in estimate['breakdown'].items():
        print(f"{item:.<40} KES {cost:>12,.0f}")
    
    print("-" * 50)
    print(f"{'TOTAL':.<40} KES {estimate['total']:>12,.0f}")
    print(f"{'Cost per sq.m':.<40} KES {estimate['cost_per_sqm']:>12,.0f}")
