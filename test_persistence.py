#!/usr/bin/env python
"""
Quick test to verify session history persistence in Supabase
"""

import asyncio
import httpx
import json
from datetime import datetime

async def test_memory_persistence():
    """Test that conversation history is saved to Supabase"""
    
    base_url = "http://127.0.0.1:8000"
    test_email = "test_memory@example.com"
    
    print("=" * 70)
    print("MEMORY PERSISTENCE TEST")
    print("=" * 70)
    print()
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Message 1: Tell the agent your name
        print("📝 Message 1: Telling agent my name...")
        response1 = await client.post(
            f"{base_url}/api/consult-fundi",
            json={
                "user_input": "My name is John Smith",
                "email": test_email
            }
        )
        
        if response1.status_code == 200:
            data1 = response1.json()
            print(f"✅ Response: {data1['fundi_response'][:100]}...")
            msg_count_1 = data1['session_info']['messages_in_history']
            print(f"   Messages in session: {msg_count_1}")
        else:
            print(f"❌ Error: {response1.status_code}")
            return
        
        print()
        
        # Check Supabase before 2nd message
        print("🔍 Checking Supabase history after message 1...")
        response_stats = await client.get(f"{base_url}/api/session-stats/{test_email}")
        if response_stats.status_code == 200:
            stats = response_stats.json()['memory_stats']
            print(f"   Total messages: {stats['analytics']['total_messages']}")
            print(f"   User: {stats['analytics']['user_messages']}, Assistant: {stats['analytics']['assistant_messages']}")
        
        print()
        
        # Message 2: Ask for your name back
        print("📝 Message 2: Asking agent for my name (should remember)...")
        response2 = await client.post(
            f"{base_url}/api/consult-fundi",
            json={
                "user_input": "What is my name?",
                "email": test_email
            }
        )
        
        if response2.status_code == 200:
            data2 = response2.json()
            print(f"✅ Response: {data2['fundi_response'][:200]}...")
            msg_count_2 = data2['session_info']['messages_in_history']
            print(f"   Messages in session: {msg_count_2}")
            
            # Check if the response contains the name
            response_text = data2['fundi_response'].lower()
            if 'john' in response_text or 'smith' in response_text:
                print(f"✅ SUCCESS: Agent remembered your name!")
            else:
                print(f"⚠️  Agent did NOT remember your name")
        else:
            print(f"❌ Error: {response2.status_code}")
            return
        
        print()
        
        # Final check of Supabase
        print("📊 Final Supabase history check...")
        response_final = await client.get(f"{base_url}/api/session-stats/{test_email}")
        if response_final.status_code == 200:
            stats = response_final.json()['memory_stats']
            print(f"   Total messages: {stats['analytics']['total_messages']}")
            print(f"   User: {stats['analytics']['user_messages']}, Assistant: {stats['analytics']['assistant_messages']}")
            print(f"   Topics: {', '.join(stats['topics']) if stats['topics'] else 'none'}")
            if stats['analytics']['total_messages'] >= 4:
                print(f"✅ SUCCESS: History is being saved (at least 4 messages)")
            else:
                print(f"❌ WARNING: Not enough messages saved")
    
    print()
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(test_memory_persistence())
