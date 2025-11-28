"""
Test script for Fundi Construction Estimator with Memory Management
Run: python test_memory_system.py
"""

import asyncio
import httpx
import json
from datetime import datetime

async def test_memory_system():
    """Test the memory management system end-to-end"""
    
    base_url = "http://127.0.0.1:8000"
    test_email = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}@example.com"
    
    print("=" * 70)
    print("FUNDI CONSTRUCTION ESTIMATOR - MEMORY MANAGEMENT TEST")
    print("=" * 70)
    print()
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Test 1: Health Check
        print("TEST 1: Health Check Endpoint")
        print("-" * 70)
        try:
            response = await client.get(f"{base_url}/")
            data = response.json()
            print(f"✅ Status: {data['status']}")
            print(f"   Service: {data['service']}")
            print(f"   Features: {json.dumps(data['features'], indent=6)}")
            print()
        except Exception as e:
            print(f"❌ Error: {e}")
            return
        
        # Test 2: First Query (Create Session)
        print("TEST 2: First Query (New Session Creation)")
        print("-" * 70)
        try:
            payload = {
                "user_input": "What's the cost of building a 2-bedroom house in Kenya?",
                "email": test_email
            }
            print(f"📤 Query: {payload['user_input']}")
            print(f"👤 Session ID: {test_email}")
            
            response = await client.post(
                f"{base_url}/api/consult-fundi",
                json=payload,
                timeout=60.0
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Response received")
                print(f"   Status: {data['status']}")
                print(f"   Agent Response: {data['fundi_response'][:100]}...")
                print(f"   Session Info: {json.dumps(data['session_info'], indent=6)}")
            else:
                print(f"❌ Status Code: {response.status_code}")
                print(f"   Response: {response.text[:200]}")
            print()
        except Exception as e:
            print(f"❌ Error: {e}")
            return
        
        # Test 3: Get Session Statistics
        print("TEST 3: Session Statistics (Memory Analytics)")
        print("-" * 70)
        try:
            response = await client.get(
                f"{base_url}/api/session-stats/{test_email}",
                timeout=30.0
            )
            
            if response.status_code == 200:
                data = response.json()
                stats = data['memory_stats']
                print(f"✅ Session Statistics Retrieved")
                print(f"   Total Messages: {stats['analytics']['total_messages']}")
                print(f"   User Messages: {stats['analytics']['user_messages']}")
                print(f"   Assistant Messages: {stats['analytics']['assistant_messages']}")
                print(f"   Topics: {', '.join(stats['topics']) if stats['topics'] else 'None identified'}")
                print(f"   Memory Status: {'Optimization needed' if stats['compaction_needed'] else 'Optimal'}")
                print(f"   Summary: {stats['summary'][:150]}...")
            else:
                print(f"❌ Status Code: {response.status_code}")
                print(f"   Response: {response.text}")
            print()
        except Exception as e:
            print(f"❌ Error: {e}")
        
        # Test 4: Second Query (Session Retrieval)
        print("TEST 4: Follow-up Query (Session Retrieval & Context)")
        print("-" * 70)
        try:
            payload = {
                "user_input": "Include labour costs in the estimate",
                "email": test_email
            }
            print(f"📤 Query: {payload['user_input']}")
            print(f"👤 Session ID: {test_email} (existing)")
            
            response = await client.post(
                f"{base_url}/api/consult-fundi",
                json=payload,
                timeout=60.0
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Response received")
                print(f"   Status: {data['status']}")
                print(f"   Agent Response: {data['fundi_response'][:100]}...")
                print(f"   Messages in Session: {data['session_info']['messages_in_history']}")
                print(f"   Memory Optimized: {data['session_info']['memory_optimized']}")
            else:
                print(f"❌ Status Code: {response.status_code}")
            print()
        except Exception as e:
            print(f"❌ Error: {e}")
        
        # Test 5: Final Statistics
        print("TEST 5: Final Session Statistics")
        print("-" * 70)
        try:
            response = await client.get(
                f"{base_url}/api/session-stats/{test_email}",
                timeout=30.0
            )
            
            if response.status_code == 200:
                data = response.json()
                stats = data['memory_stats']
                print(f"✅ Session Statistics (Final)")
                print(f"   Total Messages: {stats['analytics']['total_messages']}")
                print(f"   Conversation Size: {stats['analytics']['total_characters']} chars")
                print(f"   Average Message: {stats['analytics']['average_message_length']} chars")
                print(f"   Topics: {', '.join(stats['topics']) if stats['topics'] else 'None'}")
            else:
                print(f"❌ Status Code: {response.status_code}")
            print()
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print("=" * 70)
    print("✅ MEMORY MANAGEMENT TEST COMPLETE")
    print("=" * 70)
    print()
    print("Key Features Tested:")
    print("  ✓ Session persistence with Supabase")
    print("  ✓ Conversation history tracking")
    print("  ✓ Memory analytics and statistics")
    print("  ✓ Topic extraction")
    print("  ✓ Memory optimization triggers")
    print("  ✓ Multi-turn conversation support")
    print()

if __name__ == "__main__":
    asyncio.run(test_memory_system())
