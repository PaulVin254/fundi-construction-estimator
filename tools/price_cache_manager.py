# =============================================================================
# FILE: tools/price_cache_manager.py
# PURPOSE:
#   Manages material price caching using Supabase DB with TTL (e.g. 30 days).
#   Prevents redundant web searches and saves API calls / costs.
# =============================================================================

import os
import datetime
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()

# Check for Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

_in_memory_price_cache: Dict[str, Dict[str, Any]] = {}

def get_supabase_client():
    """Initializes and returns Supabase client if configured."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None
    try:
        from supabase import create_client
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"⚠️ Supabase client init warning: {e}")
        return None


def get_cached_material_price(material_key: str, max_age_days: int = 30) -> Optional[Dict[str, Any]]:
    """
    Retrieves cached material price record if it exists and is fresher than max_age_days.
    Returns dict with keys: price_nairobi, price_mombasa, price_upcountry, source, last_verified_at
    """
    global _in_memory_price_cache
    
    # 1. Check local in-memory cache first
    if material_key in _in_memory_price_cache:
        cached = _in_memory_price_cache[material_key]
        verified_at = cached.get("verified_at")
        if verified_at and (datetime.datetime.now() - verified_at).days < max_age_days:
            return cached["data"]
            
    # 2. Check Supabase DB
    supabase = get_supabase_client()
    if supabase:
        try:
            res = supabase.table("material_prices").select("*").eq("material_key", material_key).execute()
            if res.data and len(res.data) > 0:
                row = res.data[0]
                last_verified_str = row.get("last_verified_at") or row.get("updated_at")
                if last_verified_str:
                    # Clean ISO format string
                    clean_ts = last_verified_str.replace("Z", "+00:00")
                    last_verified_dt = datetime.datetime.fromisoformat(clean_ts)
                    age_days = (datetime.datetime.now(datetime.timezone.utc) - last_verified_dt).days
                    if age_days < max_age_days:
                        price_data = {
                            "material_key": row["material_key"],
                            "material_name": row.get("material_name", material_key),
                            "unit": row.get("unit", "unit"),
                            "price_nairobi": float(row["price_nairobi"]),
                            "price_mombasa": float(row["price_mombasa"]),
                            "price_upcountry": float(row["price_upcountry"]),
                            "source": row.get("source", "cache"),
                            "last_verified_at": last_verified_str
                        }
                        # Save in memory
                        _in_memory_price_cache[material_key] = {
                            "verified_at": datetime.datetime.now(),
                            "data": price_data
                        }
                        return price_data
        except Exception as e:
            print(f"⚠️ Supabase price query error for {material_key}: {e}")
            
    return None


def save_material_price_to_cache(
    material_key: str,
    material_name: str,
    unit: str,
    category: str,
    price_nairobi: float,
    price_mombasa: float,
    price_upcountry: float,
    source: str = "google_search"
) -> bool:
    """
    Saves or updates a material price entry in Supabase DB and local memory cache.
    """
    global _in_memory_price_cache
    
    price_data = {
        "material_key": material_key,
        "material_name": material_name,
        "unit": unit,
        "category": category,
        "price_nairobi": price_nairobi,
        "price_mombasa": price_mombasa,
        "price_upcountry": price_upcountry,
        "source": source,
        "last_verified_at": datetime.datetime.now().isoformat()
    }
    
    # Save memory
    _in_memory_price_cache[material_key] = {
        "verified_at": datetime.datetime.now(),
        "data": price_data
    }
    
    supabase = get_supabase_client()
    if supabase:
        try:
            payload = {
                "material_key": material_key,
                "material_name": material_name,
                "unit": unit,
                "category": category,
                "price_nairobi": price_nairobi,
                "price_mombasa": price_mombasa,
                "price_upcountry": price_upcountry,
                "source": source,
                "last_verified_at": datetime.datetime.now().isoformat(),
                "updated_at": datetime.datetime.now().isoformat()
            }
            supabase.table("material_prices").upsert(payload, on_conflict="material_key").execute()
            print(f"✅ Cached material price for '{material_key}' in Supabase ({source})")
            return True
        except Exception as e:
            print(f"⚠️ Failed to cache price in Supabase: {e}")
            return False
            
    return True
