import json
from typing import List
from datetime import datetime
import time
import uuid
from supabase import create_client, Client
from google.adk.sessions import BaseSessionService, Session
from google.genai.types import Content, Part
from google.adk.events.event import Event

class SupabaseSessionService(BaseSessionService):
    def __init__(self, supabase_url: str, supabase_key: str):
        """
        Initialize with Supabase credentials.
        Get these from your Supabase dashboard.
        """
        self.supabase: Client = create_client(supabase_url, supabase_key)
    
    def _get_unix_timestamp(self) -> float:
        """Get current Unix timestamp (seconds since epoch)"""
        return time.time()

    async def create_session(self, app_name: str, user_id: str, session_id: str) -> Session:
        """Create a new session with proper Google ADK Session structure"""
        # Create Session with required fields
        session = Session(
            id=session_id,  # Use session_id as the id field
            app_name=app_name,
            user_id=user_id,
            state={},  # Empty state dict
            events=[],  # Empty events list
            last_update_time=self._get_unix_timestamp()  # Unix timestamp as float
        )
        
        try:
            self.supabase.table("sessions").insert({
                "session_id": session_id,
                "app_name": app_name,
                "user_id": user_id,
                "history": []
            }).execute()
            print(f"✅ Session created in Supabase: {session_id}")
        except Exception as e:
            print(f"⚠️ Error creating session in Supabase: {e}")
        
        return session

    async def get_session(self, app_name: str, user_id: str, session_id: str) -> Session:
        """Retrieve a session from Supabase"""
        try:
            response = self.supabase.table("sessions").select("*").eq("session_id", session_id).execute()
            
            if not response.data or len(response.data) == 0:
                raise Exception(f"Session {session_id} not found")
            
            data = response.data[0]
            
            # Reconstruct history from JSON
            history = []
            events = []
            for item in data.get("history", []):
                parts = [Part(text=p.get("text", "")) for p in item.get("parts", [])]
                content = Content(role=item.get("role"), parts=parts)
                history.append(content)
                
                # Create Event for Runner compatibility
                # Note: We assume the agent name is 'construction_cost_estimator' for model messages
                author = "user" if item.get("role") == "user" else "construction_cost_estimator"
                event = Event(
                    author=author,
                    content=content,
                    invocation_id=str(uuid.uuid4()) # Dummy invocation ID needed for Runner
                )
                events.append(event)
            
            # Create Session with proper Google ADK structure
            session = Session(
                id=session_id,
                app_name=app_name,
                user_id=user_id,
                state={"history": history},  # Store history in state
                events=events,
                last_update_time=self._get_unix_timestamp()  # Unix timestamp as float
            )
            
            print(f"✅ Session retrieved from Supabase: {session_id}")
            return session
        
        except Exception as e:
            print(f"⚠️ Session not found in Supabase: {e}")
            raise Exception(f"Session {session_id} not found")

    async def update_session(self, session: Session) -> None:
        """Update a session in Supabase"""
        try:
            # Extract history from state
            history_data = []
            history = session.state.get("history", []) if session.state else []
            
            print(f"🔍 Saving session {session.id}: {len(history)} messages in state")
            
            for i, content in enumerate(history):
                if hasattr(content, 'parts') and hasattr(content, 'role'):
                    parts_data = [{"text": p.text} for p in content.parts if hasattr(p, 'text')]
                    history_data.append({"role": content.role, "parts": parts_data})
                    print(f"   [{i}] {content.role}: {len(parts_data)} parts")
            
            print(f"📤 Uploading {len(history_data)} messages to Supabase")
            
            self.supabase.table("sessions").update({
                "history": history_data,
                "updated_at": datetime.now().isoformat()
            }).eq("session_id", session.id).execute()
            
            print(f"✅ Session updated in Supabase: {session.id} ({len(history_data)} messages saved)")
        
        except Exception as e:
            print(f"❌ Error updating session in Supabase: {e}")

    async def delete_session(self, app_name: str, user_id: str, session_id: str) -> None:
        """Delete a session from Supabase"""
        try:
            self.supabase.table("sessions").delete().eq("session_id", session_id).execute()
            print(f"✅ Session deleted from Supabase: {session_id}")
        except Exception as e:
            print(f"❌ Error deleting session in Supabase: {e}")

    async def list_sessions(self, app_name: str, user_id: str) -> List[Session]:
        """List all sessions for a user"""
        try:
            response = self.supabase.table("sessions").select("*").eq(
                "app_name", app_name
            ).eq("user_id", user_id).execute()
            
            sessions = []
            for data in response.data:
                history = []
                for item in data.get("history", []):
                    parts = [Part(text=p.get("text", "")) for p in item.get("parts", [])]
                    history.append(Content(role=item.get("role"), parts=parts))
                
                session = Session(
                    id=data.get("session_id"),
                    app_name=app_name,
                    user_id=user_id,
                    state={"history": history},
                    events=[],
                    last_update_time=self._get_unix_timestamp()  # Unix timestamp as float
                )
                sessions.append(session)
            
            print(f"✅ Retrieved {len(sessions)} sessions from Supabase")
            return sessions
        except Exception as e:
            print(f"⚠️ Error listing sessions: {e}")
            return []
