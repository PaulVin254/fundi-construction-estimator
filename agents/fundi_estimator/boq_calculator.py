# =============================================================================
# FILE: agents/fundi_estimator/boq_calculator.py
# PURPOSE:
#   Calculates a detailed, itemized Bill of Quantities (BOQ) for residential
#   building projects in Kenya across 7 construction trades. Converts technical
#   building parameters into exact physical quantities (bags of cement, tons of sand,
#   pieces of rebar, lengths of timber, etc.) with plain-English descriptions.
# =============================================================================

import math
from typing import Dict, List, Any
from agents.fundi_estimator.kenya_construction_costs import get_location_code, get_house_size, LOCATIONS, FINISH_LEVELS

# Default baseline material rates in KES for Kenyan regions (2025/2026 market benchmarks)
DEFAULT_MATERIAL_RATES = {
    "cement_bag_50kg": {"name": "Cement 50kg Bag (Simba/Bamburi)", "unit": "50kg bag", "nairobi": 850, "mombasa": 820, "upcountry": 890, "category": "Substructure"},
    "river_sand_ton": {"name": "River Sand (Clean coarse)", "unit": "ton", "nairobi": 1800, "mombasa": 1650, "upcountry": 1500, "category": "Substructure"},
    "ballast_ton": {"name": "Crushed Stone Ballast (3/4 inch)", "unit": "ton", "nairobi": 2200, "mombasa": 2000, "upcountry": 1900, "category": "Substructure"},
    "hardcore_ton": {"name": "Hardcore Quarry Stone Filling", "unit": "ton", "nairobi": 1200, "mombasa": 1100, "upcountry": 1000, "category": "Substructure"},
    "brc_mesh_A142": {"name": "BRC Mesh A142 (Roll 2.4m x 48m)", "unit": "roll", "nairobi": 28000, "mombasa": 27000, "upcountry": 29500, "category": "Substructure"},
    "dpm_polythene_roll": {"name": "Damp Proof Membrane (DPM 1000g)", "unit": "roll", "nairobi": 4500, "mombasa": 4200, "upcountry": 4800, "category": "Substructure"},
    "anti_termite_chemical_5L": {"name": "Anti-Termite Soil Treatment Chemical", "unit": "5L container", "nairobi": 3500, "mombasa": 3400, "upcountry": 3600, "category": "Substructure"},

    "machine_cut_stone_9in": {"name": "Machine Cut Foundation/Wall Stone (9 inch)", "unit": "piece", "nairobi": 70, "mombasa": 65, "upcountry": 60, "category": "Superstructure"},
    "machine_cut_stone_6in": {"name": "Machine Cut Wall Stone (6 inch)", "unit": "piece", "nairobi": 55, "mombasa": 50, "upcountry": 48, "category": "Superstructure"},
    "rebar_y12_length": {"name": "High Yield Steel Rebar Y12 (12m length)", "unit": "12m bar", "nairobi": 1450, "mombasa": 1400, "upcountry": 1520, "category": "Superstructure"},
    "rebar_y10_length": {"name": "High Yield Steel Rebar Y10 (12m length)", "unit": "12m bar", "nairobi": 1050, "mombasa": 1000, "upcountry": 1120, "category": "Superstructure"},
    "rebar_r6_length": {"name": "Mild Steel Stirrup Wire R6 (12m length)", "unit": "12m bar", "nairobi": 420, "mombasa": 400, "upcountry": 450, "category": "Superstructure"},
    "binding_wire_roll": {"name": "Annealed Binding Wire (25kg roll)", "unit": "roll", "nairobi": 4200, "mombasa": 4000, "upcountry": 4400, "category": "Superstructure"},
    "formwork_timber_m": {"name": "Formwork Cypress Board (1x8 inch)", "unit": "running meter", "nairobi": 140, "mombasa": 130, "upcountry": 120, "category": "Superstructure"},

    "iron_sheet_it4_g28": {"name": "IT4 Roofing Sheets (Gauge 28 Pre-painted)", "unit": "sheet (3m)", "nairobi": 1350, "mombasa": 1300, "upcountry": 1420, "category": "Roofing"},
    "roof_truss_timber_2x4_m": {"name": "Treated Timber 2x4 Cypress Truss", "unit": "running meter", "nairobi": 160, "mombasa": 150, "upcountry": 135, "category": "Roofing"},
    "roof_purlin_timber_2x2_m": {"name": "Treated Timber 2x2 Purlins", "unit": "running meter", "nairobi": 85, "mombasa": 80, "upcountry": 75, "category": "Roofing"},
    "roof_cap_ridge_m": {"name": "Pre-painted Ridge Caps", "unit": "running meter", "nairobi": 450, "mombasa": 430, "upcountry": 480, "category": "Roofing"},
    "fascia_board_m": {"name": "Hardwood Fascia Board (1x9 inch)", "unit": "running meter", "nairobi": 380, "mombasa": 360, "upcountry": 350, "category": "Roofing"},
    "roofing_screws_kg": {"name": "Roofing Rubber Screws/Nails", "unit": "kg", "nairobi": 350, "mombasa": 330, "upcountry": 370, "category": "Roofing"},

    "wall_tiles_box": {"name": "Ceramic Wall Tiles (25x40cm - Box 1.5m²)", "unit": "box", "nairobi": 1200, "mombasa": 1150, "upcountry": 1250, "category": "Finishes"},
    "floor_tiles_box": {"name": "Porcelain Floor Tiles (60x60cm - Box 1.44m²)", "unit": "box", "nairobi": 2200, "mombasa": 2100, "upcountry": 2350, "category": "Finishes"},
    "tile_adhesive_25kg": {"name": "Heavy Duty Tile Adhesive", "unit": "25kg bag", "nairobi": 750, "mombasa": 720, "upcountry": 790, "category": "Finishes"},
    "interior_paint_20L": {"name": "Crown Vinyl Matt Interior Paint", "unit": "20L bucket", "nairobi": 9500, "mombasa": 9200, "upcountry": 9800, "category": "Finishes"},
    "exterior_weatherguard_20L": {"name": "Crown Weatherguard Exterior Paint", "unit": "20L bucket", "nairobi": 14500, "mombasa": 14000, "upcountry": 15000, "category": "Finishes"},
    "gypsum_board_sheet": {"name": "Gypsum Ceiling Board (9mm 4x8ft)", "unit": "sheet", "nairobi": 950, "mombasa": 920, "upcountry": 1000, "category": "Finishes"},

    "plumbing_ppr_pipe_32mm": {"name": "PPR Hot/Cold Water Pipe 32mm (4m)", "unit": "length (4m)", "nairobi": 650, "mombasa": 620, "upcountry": 680, "category": "Plumbing"},
    "pvc_waste_pipe_110mm": {"name": "PVC Heavy Duty Soil Waste Pipe 110mm", "unit": "length (6m)", "nairobi": 2400, "mombasa": 2300, "upcountry": 2500, "category": "Plumbing"},
    "wc_sanitary_suite": {"name": "Dual Flush Toilet + Basin Set", "unit": "set", "nairobi": 18500, "mombasa": 17800, "upcountry": 19500, "category": "Plumbing"},
    "instant_shower_heater": {"name": "Lorenzetti Instant Water Heater Shower Head", "unit": "unit", "nairobi": 4500, "mombasa": 4400, "upcountry": 4700, "category": "Plumbing"},

    "electrical_conduit_20mm": {"name": "PVC Heavy Gauge Conduit 20mm (3m)", "unit": "length", "nairobi": 85, "mombasa": 80, "upcountry": 90, "category": "Electrical"},
    "cable_single_core_2_5mm": {"name": "Single Core Cable 2.5mm² (100m roll)", "unit": "roll", "nairobi": 5800, "mombasa": 5600, "upcountry": 6100, "category": "Electrical"},
    "cable_single_core_1_5mm": {"name": "Single Core Cable 1.5mm² (100m roll)", "unit": "roll", "nairobi": 3800, "mombasa": 3650, "upcountry": 4000, "category": "Electrical"},
    "distribution_board_8way": {"name": "Consumer Consumer Unit DB 8-Way Metal", "unit": "unit", "nairobi": 4800, "mombasa": 4600, "upcountry": 5000, "category": "Electrical"},
    "double_socket_outlet": {"name": "Twin 13A Switched Socket Outlet", "unit": "unit", "nairobi": 450, "mombasa": 420, "upcountry": 480, "category": "Electrical"},

    "mason_labor_day": {"name": "Skilled Fundi / Mason Daily Rate", "unit": "day", "nairobi": 2000, "mombasa": 1800, "upcountry": 1500, "category": "Labor"},
    "helper_labor_day": {"name": "Casual Helper Daily Rate", "unit": "day", "nairobi": 1000, "mombasa": 900, "upcountry": 750, "category": "Labor"},
}


def calculate_full_boq(
    house_type: str = "3_bedroom",
    location: str = "nairobi",
    size_sqm: float = None,
    finish_level: str = "standard",
    custom_rates: Dict[str, float] = None
) -> Dict[str, Any]:
    """
    Computes a comprehensive, 7-trade Bill of Quantities (BOQ) with physical quantity breakdown.
    """
    loc = get_location_code(location)
    if size_sqm is None or size_sqm <= 0:
        size_sqm = float(get_house_size(house_type))
    
    finish_mult = FINISH_LEVELS.get(finish_level.lower(), FINISH_LEVELS["standard"])["cost_multiplier"]
    
    side_length = math.sqrt(size_sqm)
    perimeter_m = side_length * 4.0
    wall_height_m = 3.0
    total_wall_area_sqm = perimeter_m * wall_height_m * 1.3  # internal partitions extra
    openings_sqm = total_wall_area_sqm * 0.18  # 18% doors & windows
    net_wall_area_sqm = total_wall_area_sqm - openings_sqm
    roof_pitch_area_sqm = size_sqm * 1.25  # 25% pitch overhang allowance
    
    def get_rate(mat_key: str) -> float:
        if custom_rates and mat_key in custom_rates:
            return float(custom_rates[mat_key])
        base_item = DEFAULT_MATERIAL_RATES.get(mat_key, {})
        base_price = base_item.get(loc, base_item.get("nairobi", 1000))
        return base_price * finish_mult if mat_key not in ["cement_bag_50kg", "river_sand_ton", "ballast_ton", "hardcore_ton"] else float(base_price)

    trades = []
    
    # 1. PRELIMINARIES
    t1_items = [
        {
            "item_code": "PRE-01",
            "material_key": "site_clearance",
            "name": "Site Clearance & Setting Out",
            "description": "Clearing vegetation, topsoil stripping, and establishing building gridlines with timber pegs & site board.",
            "unit": "sum",
            "quantity": 1.0,
            "rate": round(size_sqm * 350 * (1.1 if loc=="nairobi" else 1.0)),
            "layman_note": "Crucial first step to ensure building lines are square and level."
        },
        {
            "item_code": "PRE-02",
            "material_key": "temporary_water_store",
            "name": "Temporary Water Tank & Cement Store",
            "description": "Erecting corrugated iron store for cement/tools & 2,500L water tank for mixing.",
            "unit": "sum",
            "quantity": 1.0,
            "rate": round(45000 * (1.1 if loc=="nairobi" else 1.0)),
            "layman_note": "Protects cement from moisture and rain damage."
        }
    ]
    for it in t1_items:
        it["amount"] = round(it["quantity"] * it["rate"])
    
    trades.append({
        "trade_code": "TR-01",
        "trade_name": "Preliminaries & Site Setup",
        "icon": "🏗️",
        "layman_summary": "Essential site preparation, securing materials, setting out gridlines, and temporary water connection.",
        "items": t1_items,
        "trade_total": sum(i["amount"] for i in t1_items)
    })

    # 2. SUBSTRUCTURE
    excavation_m3 = perimeter_m * 0.9 * 0.9
    hardcore_tons = round(size_sqm * 0.35 * 1.6)
    sand_substructure_tons = round(size_sqm * 0.15)
    ballast_substructure_tons = round(size_sqm * 0.22)
    cement_substructure_bags = round(size_sqm * 0.95)
    brc_mesh_rolls = max(1, math.ceil(size_sqm / 100))
    dpm_rolls = max(1, math.ceil(size_sqm / 110))
    anti_termite_bottles = max(1, math.ceil(size_sqm / 50))
    
    t2_items = [
        {
            "item_code": "SUB-01",
            "material_key": "excavation_manual",
            "name": "Foundation Trench Excavation",
            "description": f"Manual/excavator trenching ({excavation_m3:.1f} m³) to firm soil bearing stratum.",
            "unit": "m³",
            "quantity": round(excavation_m3, 1),
            "rate": 650 if loc == "nairobi" else 550,
            "layman_note": "Digging deep down to firm rock or red soil to prevent foundation sinking."
        },
        {
            "item_code": "SUB-02",
            "material_key": "hardcore_ton",
            "name": DEFAULT_MATERIAL_RATES["hardcore_ton"]["name"],
            "description": "Compacted quarry stone fill under ground floor slab.",
            "unit": DEFAULT_MATERIAL_RATES["hardcore_ton"]["unit"],
            "quantity": hardcore_tons,
            "rate": get_rate("hardcore_ton"),
            "layman_note": "Crushed stones rammed tight to create a solid rock bed under your floor."
        },
        {
            "item_code": "SUB-03",
            "material_key": "anti_termite_chemical_5L",
            "name": DEFAULT_MATERIAL_RATES["anti_termite_chemical_5L"]["name"],
            "description": "Chemical soil treatment under slab against termites and ground borers.",
            "unit": DEFAULT_MATERIAL_RATES["anti_termite_chemical_5L"]["unit"],
            "quantity": anti_termite_bottles,
            "rate": get_rate("anti_termite_chemical_5L"),
            "layman_note": "Protects timber doors, roof, and furniture from termite damage."
        },
        {
            "item_code": "SUB-04",
            "material_key": "dpm_polythene_roll",
            "name": DEFAULT_MATERIAL_RATES["dpm_polythene_roll"]["name"],
            "description": "Heavy-duty polythene sheet under slab to block rising dampness.",
            "unit": DEFAULT_MATERIAL_RATES["dpm_polythene_roll"]["unit"],
            "quantity": dpm_rolls,
            "rate": get_rate("dpm_polythene_roll"),
            "layman_note": "Stops ground moisture from seeping into your floor tiles or carpet."
        },
        {
            "item_code": "SUB-05",
            "material_key": "brc_mesh_A142",
            "name": DEFAULT_MATERIAL_RATES["brc_mesh_A142"]["name"],
            "description": "Steel mesh reinforcement embedded inside ground slab concrete.",
            "unit": DEFAULT_MATERIAL_RATES["brc_mesh_A142"]["unit"],
            "quantity": brc_mesh_rolls,
            "rate": get_rate("brc_mesh_A142"),
            "layman_note": "Steel web that binds the floor concrete so it won't crack under heavy weight."
        },
        {
            "item_code": "SUB-06",
            "material_key": "cement_bag_50kg",
            "name": "Substructure Cement (50kg Bags)",
            "description": "Cement for strip foundation, footing concrete & 100mm ground slab.",
            "unit": "bag",
            "quantity": cement_substructure_bags,
            "rate": get_rate("cement_bag_50kg"),
            "layman_note": "High-strength cement used for foundational concrete."
        },
        {
            "item_code": "SUB-07",
            "material_key": "river_sand_ton",
            "name": "Substructure River Sand",
            "description": "Clean sand for concrete slab mix (1:2:4 ratio) and foundation mortar.",
            "unit": "ton",
            "quantity": sand_substructure_tons,
            "rate": get_rate("river_sand_ton"),
            "layman_note": "Coarse sand required for solid concrete slab and foundation footing."
        },
        {
            "item_code": "SUB-08",
            "material_key": "ballast_ton",
            "name": "Substructure Crushed Ballast",
            "description": "3/4 inch crushed ballast for reinforced concrete foundation slab.",
            "unit": "ton",
            "quantity": ballast_substructure_tons,
            "rate": get_rate("ballast_ton"),
            "layman_note": "Volcanic/granite rock aggregate that provides strength to concrete."
        }
    ]
    for it in t2_items:
        it["amount"] = round(it["quantity"] * it["rate"])

    trades.append({
        "trade_code": "TR-02",
        "trade_name": "Substructure (Foundation & Slab)",
        "icon": "🧱",
        "layman_summary": "Underground work including excavation, hardcore stone bed, termite barrier, moisture sheet, BRC mesh, and concrete slab.",
        "items": t2_items,
        "trade_total": sum(i["amount"] for i in t2_items)
    })

    # 3. SUPERSTRUCTURE
    num_stones = round(net_wall_area_sqm * 12.5)
    cement_superstructure_bags = round(net_wall_area_sqm * 0.45 + (perimeter_m * 0.3))
    sand_superstructure_tons = round(net_wall_area_sqm * 0.08)
    rebar_y12_bars = round(perimeter_m * 0.8)
    rebar_r6_bars = round(perimeter_m * 0.5)
    binding_wire_rolls = max(1, round(rebar_y12_bars / 40))
    formwork_m = round(perimeter_m * 2.2)

    t3_items = [
        {
            "item_code": "SUP-01",
            "material_key": "machine_cut_stone_9in",
            "name": DEFAULT_MATERIAL_RATES["machine_cut_stone_9in"]["name"],
            "description": "Machine-cut stone blocks for external and load-bearing walls.",
            "unit": DEFAULT_MATERIAL_RATES["machine_cut_stone_9in"]["unit"],
            "quantity": num_stones,
            "rate": get_rate("machine_cut_stone_9in"),
            "layman_note": "Precision quarry stones for smooth, straight walling."
        },
        {
            "item_code": "SUP-02",
            "material_key": "cement_bag_50kg",
            "name": "Wall Mortar & Ring Beam Cement",
            "description": "Cement for mortar joints between stones and ring beam concrete.",
            "unit": "bag",
            "quantity": cement_superstructure_bags,
            "rate": get_rate("cement_bag_50kg"),
            "layman_note": "Binds the wall stones together and pours the top ring beam."
        },
        {
            "item_code": "SUP-03",
            "material_key": "river_sand_ton",
            "name": "Walling Mortar Sand",
            "description": "Filtered sand for mortar joints.",
            "unit": "ton",
            "quantity": sand_superstructure_tons,
            "rate": get_rate("river_sand_ton"),
            "layman_note": "Sand mixed with cement to glue stone blocks together."
        },
        {
            "item_code": "SUP-04",
            "material_key": "rebar_y12_length",
            "name": DEFAULT_MATERIAL_RATES["rebar_y12_length"]["name"],
            "description": "Y12 high-yield steel bars for column and ring beam reinforcement.",
            "unit": DEFAULT_MATERIAL_RATES["rebar_y12_length"]["unit"],
            "quantity": rebar_y12_bars,
            "rate": get_rate("rebar_y12_length"),
            "layman_note": "Heavy steel rods that reinforce columns and tie the top of walls together."
        },
        {
            "item_code": "SUP-05",
            "material_key": "rebar_r6_length",
            "name": DEFAULT_MATERIAL_RATES["rebar_r6_length"]["name"],
            "description": "R6 steel stirrups to tie Y12 column & beam bars.",
            "unit": DEFAULT_MATERIAL_RATES["rebar_r6_length"]["unit"],
            "quantity": rebar_r6_bars,
            "rate": get_rate("rebar_r6_length"),
            "layman_note": "Steel rings holding main structural bars in position."
        },
        {
            "item_code": "SUP-06",
            "material_key": "binding_wire_roll",
            "name": DEFAULT_MATERIAL_RATES["binding_wire_roll"]["name"],
            "description": "Annealed wire for tying steel bars.",
            "unit": DEFAULT_MATERIAL_RATES["binding_wire_roll"]["unit"],
            "quantity": binding_wire_rolls,
            "rate": get_rate("binding_wire_roll"),
            "layman_note": "Wire used by fundis to tie rebar bars together."
        },
        {
            "item_code": "SUP-07",
            "material_key": "formwork_timber_m",
            "name": DEFAULT_MATERIAL_RATES["formwork_timber_m"]["name"],
            "description": "Shuttering cypress timber for casting concrete columns and ring beams.",
            "unit": DEFAULT_MATERIAL_RATES["formwork_timber_m"]["unit"],
            "quantity": formwork_m,
            "rate": get_rate("formwork_timber_m"),
            "layman_note": "Wooden molds built around columns/ring beams before pouring wet concrete."
        }
    ]
    for it in t3_items:
        it["amount"] = round(it["quantity"] * it["rate"])

    trades.append({
        "trade_code": "TR-03",
        "trade_name": "Superstructure (Walls & Columns)",
        "icon": "🏠",
        "layman_summary": "Machine-cut stone masonry walls, concrete columns, rebar reinforcement, and top ring beam.",
        "items": t3_items,
        "trade_total": sum(i["amount"] for i in t3_items)
    })

    # 4. ROOFING
    iron_sheets_qty = round(roof_pitch_area_sqm / 2.2)
    timber_2x4_m = round(roof_pitch_area_sqm * 3.8)
    timber_2x2_m = round(roof_pitch_area_sqm * 2.5)
    ridge_caps_m = round(side_length * 1.5)
    fascia_m = round(perimeter_m * 1.1)
    roofing_screws_kg = max(2, round(iron_sheets_qty * 0.25))

    t4_items = [
        {
            "item_code": "ROOF-01",
            "material_key": "iron_sheet_it4_g28",
            "name": DEFAULT_MATERIAL_RATES["iron_sheet_it4_g28"]["name"],
            "description": "Pre-painted IT4 box profile iron sheets (Gauge 28).",
            "unit": DEFAULT_MATERIAL_RATES["iron_sheet_it4_g28"]["unit"],
            "quantity": iron_sheets_qty,
            "rate": get_rate("iron_sheet_it4_g28"),
            "layman_note": "Durable, fade-resistant pre-painted roofing sheets."
        },
        {
            "item_code": "ROOF-02",
            "material_key": "roof_truss_timber_2x4_m",
            "name": DEFAULT_MATERIAL_RATES["roof_truss_timber_2x4_m"]["name"],
            "description": "Treated 2x4 timber for building main roof trusses.",
            "unit": DEFAULT_MATERIAL_RATES["roof_truss_timber_2x4_m"]["unit"],
            "quantity": timber_2x4_m,
            "rate": get_rate("roof_truss_timber_2x4_m"),
            "layman_note": "Heavy structural wooden framework that holds the roof."
        },
        {
            "item_code": "ROOF-03",
            "material_key": "roof_purlin_timber_2x2_m",
            "name": DEFAULT_MATERIAL_RATES["roof_purlin_timber_2x2_m"]["name"],
            "description": "Treated 2x2 timber purlins for fixing iron sheets.",
            "unit": DEFAULT_MATERIAL_RATES["roof_purlin_timber_2x2_m"]["unit"],
            "quantity": timber_2x2_m,
            "rate": get_rate("roof_purlin_timber_2x2_m"),
            "layman_note": "Horizontal wood strips nailed across trusses where sheets are screwed."
        },
        {
            "item_code": "ROOF-04",
            "material_key": "roof_cap_ridge_m",
            "name": DEFAULT_MATERIAL_RATES["roof_cap_ridge_m"]["name"],
            "description": "Pre-painted matching ridge caps for roof apex.",
            "unit": DEFAULT_MATERIAL_RATES["roof_cap_ridge_m"]["unit"],
            "quantity": ridge_caps_m,
            "rate": get_rate("roof_cap_ridge_m"),
            "layman_note": "Covers the top ridge junction to prevent rainwater leakage."
        },
        {
            "item_code": "ROOF-05",
            "material_key": "fascia_board_m",
            "name": DEFAULT_MATERIAL_RATES["fascia_board_m"]["name"],
            "description": "Hardwood fascia board painted around roof edges.",
            "unit": DEFAULT_MATERIAL_RATES["fascia_board_m"]["unit"],
            "quantity": fascia_m,
            "rate": get_rate("fascia_board_m"),
            "layman_note": "Decorative finished wooden board running along the edge of roof eaves."
        },
        {
            "item_code": "ROOF-06",
            "material_key": "roofing_screws_kg",
            "name": DEFAULT_MATERIAL_RATES["roofing_screws_kg"]["name"],
            "description": "Self-drilling screws with neoprene rubber washers.",
            "unit": DEFAULT_MATERIAL_RATES["roofing_screws_kg"]["unit"],
            "quantity": roofing_screws_kg,
            "rate": get_rate("roofing_screws_kg"),
            "layman_note": "Rubber-sealed screws that fasten roof sheets without leaking water."
        }
    ]
    for it in t4_items:
        it["amount"] = round(it["quantity"] * it["rate"])

    trades.append({
        "trade_code": "TR-04",
        "trade_name": "Roofing & Ceiling Structure",
        "icon": "🛖",
        "layman_summary": "Treated cypress timber trusses, purlins, Gauge 28 pre-painted sheets, ridge caps, and fascia board.",
        "items": t4_items,
        "trade_total": sum(i["amount"] for i in t4_items)
    })

    # 5. FINISHES
    floor_tile_boxes = round((size_sqm * 1.1) / 1.44)
    wall_tile_boxes = round((size_sqm * 0.4) / 1.5)
    tile_adhesive_bags = round((floor_tile_boxes + wall_tile_boxes) * 0.45)
    interior_paint_buckets = max(1, round((net_wall_area_sqm * 1.8) / 120.0))
    exterior_paint_buckets = max(1, round((perimeter_m * wall_height_m * 1.2) / 100.0))
    cement_plaster_bags = round(net_wall_area_sqm * 0.28)

    t5_items = [
        {
            "item_code": "FIN-01",
            "material_key": "cement_bag_50kg",
            "name": "Wall Plaster Cement",
            "description": "Cement for 2-coat interior & exterior wall rendering/plastering.",
            "unit": "bag",
            "quantity": cement_plaster_bags,
            "rate": get_rate("cement_bag_50kg"),
            "layman_note": "Smooths out raw stone walls ready for paint."
        },
        {
            "item_code": "FIN-02",
            "material_key": "floor_tiles_box",
            "name": DEFAULT_MATERIAL_RATES["floor_tiles_box"]["name"],
            "description": "Porcelain non-slip floor tiles (60x60cm). Includes 10% cutting waste allowance.",
            "unit": DEFAULT_MATERIAL_RATES["floor_tiles_box"]["unit"],
            "quantity": floor_tile_boxes,
            "rate": get_rate("floor_tiles_box"),
            "layman_note": "Durable porcelain tiles for sitting room, bedrooms, and kitchen."
        },
        {
            "item_code": "FIN-03",
            "material_key": "wall_tiles_box",
            "name": DEFAULT_MATERIAL_RATES["wall_tiles_box"]["name"],
            "description": "Ceramic wall tiles for bathroom wet area & kitchen backsplash.",
            "unit": DEFAULT_MATERIAL_RATES["wall_tiles_box"]["unit"],
            "quantity": wall_tile_boxes,
            "rate": get_rate("wall_tiles_box"),
            "layman_note": "Glazed wall tiles to protect bathroom and kitchen walls from water."
        },
        {
            "item_code": "FIN-04",
            "material_key": "tile_adhesive_25kg",
            "name": DEFAULT_MATERIAL_RATES["tile_adhesive_25kg"]["name"],
            "description": "Cementitious polymer tile adhesive.",
            "unit": DEFAULT_MATERIAL_RATES["tile_adhesive_25kg"]["unit"],
            "quantity": tile_adhesive_bags,
            "rate": get_rate("tile_adhesive_25kg"),
            "layman_note": "Special adhesive mortar that sticks tiles securely without hollow popping."
        },
        {
            "item_code": "FIN-05",
            "material_key": "interior_paint_20L",
            "name": DEFAULT_MATERIAL_RATES["interior_paint_20L"]["name"],
            "description": "2-coat washable interior vinyl matt paint.",
            "unit": DEFAULT_MATERIAL_RATES["interior_paint_20L"]["unit"],
            "quantity": interior_paint_buckets,
            "rate": get_rate("interior_paint_20L"),
            "layman_note": "High-quality washable interior wall paint."
        },
        {
            "item_code": "FIN-06",
            "material_key": "exterior_weatherguard_20L",
            "name": DEFAULT_MATERIAL_RATES["exterior_weatherguard_20L"]["name"],
            "description": "Weatherproof exterior emulsion paint.",
            "unit": DEFAULT_MATERIAL_RATES["exterior_weatherguard_20L"]["unit"],
            "quantity": exterior_paint_buckets,
            "rate": get_rate("exterior_weatherguard_20L"),
            "layman_note": "Tough exterior paint that withstands sun and rain without peeling."
        }
    ]
    for it in t5_items:
        it["amount"] = round(it["quantity"] * it["rate"])

    trades.append({
        "trade_code": "TR-05",
        "trade_name": "Finishes (Plaster, Tiles & Painting)",
        "icon": "🎨",
        "layman_summary": "Interior/exterior wall plastering, porcelain floor tiling, ceramic bathroom tiles, and 2-coat painting.",
        "items": t5_items,
        "trade_total": sum(i["amount"] for i in t5_items)
    })

    # 6. PLUMBING
    num_baths = max(1, int(size_sqm / 45))
    ppr_pipes = round(size_sqm * 0.25)
    pvc_pipes = round(size_sqm * 0.15)
    
    t6_items = [
        {
            "item_code": "PLU-01",
            "material_key": "plumbing_ppr_pipe_32mm",
            "name": DEFAULT_MATERIAL_RATES["plumbing_ppr_pipe_32mm"]["name"],
            "description": "PN20 hot/cold water supply PPR piping.",
            "unit": DEFAULT_MATERIAL_RATES["plumbing_ppr_pipe_32mm"]["unit"],
            "quantity": ppr_pipes,
            "rate": get_rate("plumbing_ppr_pipe_32mm"),
            "layman_note": "Heat-welded water pipes that never rust or leak."
        },
        {
            "item_code": "PLU-02",
            "material_key": "pvc_waste_pipe_110mm",
            "name": DEFAULT_MATERIAL_RATES["pvc_waste_pipe_110mm"]["name"],
            "description": "PVC soil waste drainage pipes from toilets to septic/drain.",
            "unit": DEFAULT_MATERIAL_RATES["pvc_waste_pipe_110mm"]["unit"],
            "quantity": pvc_pipes,
            "rate": get_rate("pvc_waste_pipe_110mm"),
            "layman_note": "Heavy waste pipe connecting toilet and sink drains."
        },
        {
            "item_code": "PLU-03",
            "material_key": "wc_sanitary_suite",
            "name": DEFAULT_MATERIAL_RATES["wc_sanitary_suite"]["name"],
            "description": "Ceramic toilet bowl, flush cistern, and hand wash basin.",
            "unit": DEFAULT_MATERIAL_RATES["wc_sanitary_suite"]["unit"],
            "quantity": num_baths,
            "rate": get_rate("wc_sanitary_suite"),
            "layman_note": "Complete bathroom toilet and sink set with taps."
        },
        {
            "item_code": "PLU-04",
            "material_key": "instant_shower_heater",
            "name": DEFAULT_MATERIAL_RATES["instant_shower_heater"]["name"],
            "description": "Instant electric hot shower head heater units.",
            "unit": DEFAULT_MATERIAL_RATES["instant_shower_heater"]["unit"],
            "quantity": num_baths,
            "rate": get_rate("instant_shower_heater"),
            "layman_note": "Instant hot water shower unit."
        }
    ]
    for it in t6_items:
        it["amount"] = round(it["quantity"] * it["rate"])

    trades.append({
        "trade_code": "TR-06",
        "trade_name": "Plumbing & Sanitation",
        "icon": "🚰",
        "layman_summary": "PPR water supply lines, PVC sewage drainage, sanitary toilet/basin fixtures, and hot shower units.",
        "items": t6_items,
        "trade_total": sum(i["amount"] for i in t6_items)
    })

    # 7. ELECTRICAL
    conduits = round(size_sqm * 0.8)
    cable_2_5_rolls = max(1, round(size_sqm / 60))
    cable_1_5_rolls = max(1, round(size_sqm / 75))
    num_sockets = max(4, round(size_sqm / 6))

    t7_items = [
        {
            "item_code": "ELE-01",
            "material_key": "electrical_conduit_20mm",
            "name": DEFAULT_MATERIAL_RATES["electrical_conduit_20mm"]["name"],
            "description": "PVC conduit pipes concealed in walls & ceiling for electrical wires.",
            "unit": DEFAULT_MATERIAL_RATES["electrical_conduit_20mm"]["unit"],
            "quantity": conduits,
            "rate": get_rate("electrical_conduit_20mm"),
            "layman_note": "Plastic tubes buried in walls that hold electrical cables safely."
        },
        {
            "item_code": "ELE-02",
            "material_key": "cable_single_core_2_5mm",
            "name": DEFAULT_MATERIAL_RATES["cable_single_core_2_5mm"]["name"],
            "description": "2.5mm² single core copper wire for power socket circuits.",
            "unit": DEFAULT_MATERIAL_RATES["cable_single_core_2_5mm"]["unit"],
            "quantity": cable_2_5_rolls,
            "rate": get_rate("cable_single_core_2_5mm"),
            "layman_note": "Thicker copper wiring for socket outlets and heavy appliances."
        },
        {
            "item_code": "ELE-03",
            "material_key": "cable_single_core_1_5mm",
            "name": DEFAULT_MATERIAL_RATES["cable_single_core_1_5mm"]["name"],
            "description": "1.5mm² single core wire for lighting circuits.",
            "unit": DEFAULT_MATERIAL_RATES["cable_single_core_1_5mm"]["unit"],
            "quantity": cable_1_5_rolls,
            "rate": get_rate("cable_single_core_1_5mm"),
            "layman_note": "Standard copper wiring for ceiling light points."
        },
        {
            "item_code": "ELE-04",
            "material_key": "distribution_board_8way",
            "name": DEFAULT_MATERIAL_RATES["distribution_board_8way"]["name"],
            "description": "Metal consumer unit with circuit breakers & earth leakage protection.",
            "unit": DEFAULT_MATERIAL_RATES["distribution_board_8way"]["unit"],
            "quantity": 1.0,
            "rate": get_rate("distribution_board_8way"),
            "layman_note": "Main fuse box unit that controls electricity and trips on overload."
        },
        {
            "item_code": "ELE-05",
            "material_key": "double_socket_outlet",
            "name": DEFAULT_MATERIAL_RATES["double_socket_outlet"]["name"],
            "description": "Twin 13A switched power sockets with faceplates.",
            "unit": DEFAULT_MATERIAL_RATES["double_socket_outlet"]["unit"],
            "quantity": num_sockets,
            "rate": get_rate("double_socket_outlet"),
            "layman_note": "Wall power sockets for plugged electronics."
        }
    ]
    for it in t7_items:
        it["amount"] = round(it["quantity"] * it["rate"])

    trades.append({
        "trade_code": "TR-07",
        "trade_name": "Electrical Installation",
        "icon": "⚡",
        "layman_summary": "Concealed wall conduits, copper wiring, main distribution DB box, circuit breakers, and power sockets.",
        "items": t7_items,
        "trade_total": sum(i["amount"] for i in t7_items)
    })

    # LABOR
    mason_days = round(size_sqm * 0.85)
    helper_days = round(size_sqm * 1.5)
    labor_mason_total = mason_days * get_rate("mason_labor_day")
    labor_helper_total = helper_days * get_rate("helper_labor_day")
    total_labor_cost = labor_mason_total + labor_helper_total

    trades.append({
        "trade_code": "TR-08",
        "trade_name": "Labor & Workmanship",
        "icon": "👷‍♂️",
        "layman_summary": "Skilled mason fundis and casual helpers across structural, roofing, tiling, plumbing, and electrical trades.",
        "items": [
            {
                "item_code": "LAB-01",
                "material_key": "mason_labor_day",
                "name": "Skilled Masons / Fundis Work Days",
                "description": "Daily wage for skilled masons, carpenters, steel fixers, and roofers.",
                "unit": "man-day",
                "quantity": mason_days,
                "rate": get_rate("mason_labor_day"),
                "amount": round(labor_mason_total),
                "layman_note": "Skilled fundi labor days."
            },
            {
                "item_code": "LAB-02",
                "material_key": "helper_labor_day",
                "name": "Casual Helper Work Days",
                "description": "Daily wage for manual laborers mixing mortar, carrying stones & materials.",
                "unit": "man-day",
                "quantity": helper_days,
                "rate": get_rate("helper_labor_day"),
                "amount": round(labor_helper_total),
                "layman_note": "Manual assistance labor for fundis."
            }
        ],
        "trade_total": round(total_labor_cost)
    })

    # Grand Totals
    gross_subtotal = sum(t["trade_total"] for t in trades)
    contingency_amt = round(gross_subtotal * 0.10)
    grand_total = gross_subtotal + contingency_amt
    cost_per_sqm = grand_total / size_sqm

    consolidated_materials = {
        "Cement (50kg bags)": cement_substructure_bags + cement_superstructure_bags + cement_plaster_bags,
        "River Sand (tons)": sand_substructure_tons + sand_superstructure_tons,
        "Ballast (tons)": ballast_substructure_tons,
        "Hardcore Filling (tons)": hardcore_tons,
        "Machine Cut Stones (pieces)": num_stones,
        "Y12 Steel Rebar (12m bars)": rebar_y12_bars,
        "Roofing Sheets (IT4 Gauge 28)": iron_sheets_qty,
        "Floor Tile Boxes": floor_tile_boxes,
        "Interior Paint (20L buckets)": interior_paint_buckets
    }

    display_loc_name = location.strip().title() if location and location.lower() not in ["nairobi", "mombasa", "upcountry"] else LOCATIONS.get(loc, loc.title())

    return {
        "project_metadata": {
            "house_type": house_type,
            "location": loc,
            "location_name": display_loc_name,
            "size_sqm": size_sqm,
            "finish_level": finish_level,
            "finish_description": FINISH_LEVELS.get(finish_level, {}).get("description", ""),
            "generated_date": "2026-07-23"
        },
        "trades": trades,
        "shopping_list_summary": consolidated_materials,
        "gross_subtotal": gross_subtotal,
        "contingency_percentage": 10,
        "contingency_amount": contingency_amt,
        "grand_total": grand_total,
        "cost_per_sqm": round(cost_per_sqm)
    }


if __name__ == "__main__":
    boq = calculate_full_boq("3_bedroom", "nairobi", 120, "standard")
    print(f"Grand Total: KES {boq['grand_total']:,}")
    print(f"Cost per sqm: KES {boq['cost_per_sqm']:,}")
    print(f"Consolidated Shopping List: {boq['shopping_list_summary']}")
