# =============================================================================
# FILE: tools/web_search_tool.py
# PURPOSE:
#   Web search price discovery tool with automatic Supabase caching.
#   Searches current Kenyan construction market prices and updates cache.
# =============================================================================

import re
import requests
from typing import Dict, Any, Optional
from tools.price_cache_manager import get_cached_material_price, save_material_price_to_cache
from agents.fundi_estimator.boq_calculator import DEFAULT_MATERIAL_RATES

def search_kenyan_material_price(material_key: str, force_refresh: bool = False) -> Dict[str, Any]:
    """
    Looks up material price. First checks Supabase cache. If missing/stale or force_refresh=True,
    performs web search query for current Kenyan hardware/supplier prices, extracts KES value, and caches result.
    """
    base_info = DEFAULT_MATERIAL_RATES.get(material_key, {})
    material_name = base_info.get("name", material_key)
    unit = base_info.get("unit", "unit")
    category = base_info.get("category", "General")
    
    # 1. Try cache lookup unless forced refresh
    if not force_refresh:
        cached = get_cached_material_price(material_key, max_age_days=30)
        if cached:
            return cached

    # 2. Perform live web search for material rate in Kenya
    query = f"current price of {material_name} per {unit} Nairobi Kenya KES hardware supplier"
    print(f"🔎 Executing Web Search: '{query}'")
    
    found_nairobi = None
    found_mombasa = None
    found_upcountry = None
    source = "google_search"

    try:
        # Search via DuckDuckGo HTML / free search endpoint
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
        resp = requests.get(url, headers=headers, timeout=8)
        
        if resp.status_code == 200:
            text = resp.text
            # Regex for KES or Ksh prices (e.g. KES 850, Ksh 1,200)
            matches = re.findall(r'(?:KES|Ksh|KSh)\.?\s*([0-9,]+)', text, re.IGNORECASE)
            valid_prices = []
            for m in matches:
                clean_val = float(m.replace(",", ""))
                # Filter reasonable price range relative to baseline
                baseline = base_info.get("nairobi", 1000)
                if 0.3 * baseline <= clean_val <= 3.0 * baseline:
                    valid_prices.append(clean_val)
                    
            if valid_prices:
                found_nairobi = float(valid_prices[0])
                found_mombasa = round(found_nairobi * 0.96, 2)
                found_upcountry = round(found_nairobi * 1.05, 2)
                print(f"✅ Web search extracted price for '{material_key}': KES {found_nairobi}")
    except Exception as e:
        print(f"⚠️ Web search request warning: {e}")

    # Fallback to local QS baseline benchmark if search didn't parse a price
    if not found_nairobi:
        found_nairobi = float(base_info.get("nairobi", 1000))
        found_mombasa = float(base_info.get("mombasa", 950))
        found_upcountry = float(base_info.get("upcountry", 1050))
        source = "baseline_qs"

    # Save into Supabase Cache
    save_material_price_to_cache(
        material_key=material_key,
        material_name=material_name,
        unit=unit,
        category=category,
        price_nairobi=found_nairobi,
        price_mombasa=found_mombasa,
        price_upcountry=found_upcountry,
        source=source
    )
    
    return {
        "material_key": material_key,
        "material_name": material_name,
        "unit": unit,
        "price_nairobi": found_nairobi,
        "price_mombasa": found_mombasa,
        "price_upcountry": found_upcountry,
        "source": source
    }


if __name__ == "__main__":
    res = search_kenyan_material_price("cement_bag_50kg")
    print("Result:", res)
