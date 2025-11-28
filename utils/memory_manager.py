"""
Advanced Memory Management for Fundi Agent
Handles conversation summarization, compaction, and intelligent retrieval
"""

import json
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from google.genai.types import Content, Part
import os
from dotenv import load_dotenv

load_dotenv()

class MemoryCompactionStrategy:
    """Base class for memory compaction strategies"""
    
    def compact(self, history: List[Content]) -> List[Content]:
        """Compact conversation history"""
        raise NotImplementedError


class WindowBasedCompaction(MemoryCompactionStrategy):
    """
    Keeps recent messages and summarizes older ones.
    Useful for preventing token bloat while retaining context.
    """
    
    def __init__(self, recent_messages: int = 10, max_history: int = 50):
        self.recent_messages = recent_messages
        self.max_history = max_history
    
    def compact(self, history: List[Content]) -> List[Content]:
        """
        Keep recent messages, summarize middle section if needed.
        """
        if len(history) <= self.recent_messages:
            return history
        
        # Keep the most recent N messages
        return history[-self.recent_messages:]


class ImportanceBasedCompaction(MemoryCompactionStrategy):
    """
    Removes low-importance messages (repeated clarifications, small talk)
    while keeping important context (decisions, key information)
    """
    
    def __init__(self, importance_threshold: float = 0.5):
        self.importance_threshold = importance_threshold
    
    def compact(self, history: List[Content]) -> List[Content]:
        """Filter out low-importance messages"""
        if len(history) <= 20:
            return history
        
        important_messages = []
        for content in history:
            if self._is_important(content):
                important_messages.append(content)
        
        # Always keep at least the last message
        if not important_messages and history:
            important_messages = [history[-1]]
        
        return important_messages
    
    def _is_important(self, content: Content) -> bool:
        """Determine if a message is important"""
        if not content.parts:
            return False
        
        text = content.parts[0].text.lower()
        
        # Keywords indicating important content
        important_keywords = [
            'cost', 'price', 'estimate', 'total', 'project',
            'confirm', 'agreed', 'yes', 'no', 'requirement',
            'specification', 'material', 'labour', 'budget',
            'timeline', 'deadline', 'urgent', 'decision'
        ]
        
        return any(keyword in text for keyword in important_keywords)


class MemoryAnalytics:
    """Provides insights into conversation patterns"""
    
    @staticmethod
    def analyze_session(history: List[Content]) -> Dict:
        """Analyze conversation statistics"""
        if not history:
            return {
                "total_messages": 0,
                "user_messages": 0,
                "assistant_messages": 0,
                "average_message_length": 0,
                "longest_message": 0,
                "session_duration_estimated": "0 minutes"
            }
        
        user_msgs = [c for c in history if c.role == "user"]
        assistant_msgs = [c for c in history if c.role == "model"]
        
        all_texts = [c.parts[0].text if c.parts else "" for c in history]
        lengths = [len(t) for t in all_texts]
        
        return {
            "total_messages": len(history),
            "user_messages": len(user_msgs),
            "assistant_messages": len(assistant_msgs),
            "average_message_length": int(sum(lengths) / len(lengths)) if lengths else 0,
            "longest_message": max(lengths) if lengths else 0,
            "total_characters": sum(lengths),
            "session_duration_estimated": f"{len(history) * 2} minutes (rough estimate)"
        }
    
    @staticmethod
    def extract_key_topics(history: List[Content]) -> List[str]:
        """Extract key discussion topics from history"""
        topics = []
        keywords = {
            'residential': ['house', 'home', 'residential', 'apartment'],
            'commercial': ['commercial', 'shop', 'office', 'retail'],
            'materials': ['cement', 'sand', 'brick', 'steel', 'wood', 'tile'],
            'labor': ['labour', 'labor', 'worker', 'mason', 'carpenter'],
            'timeline': ['month', 'week', 'day', 'timeline', 'deadline'],
            'budget': ['budget', 'cost', 'price', 'expensive', 'cheap'],
            'foundation': ['foundation', 'footing', 'concrete'],
            'roofing': ['roof', 'tile', 'metal', 'asbestos']
        }
        
        all_text = " ".join([c.parts[0].text.lower() if c.parts else "" for c in history])
        
        for topic, keywords_list in keywords.items():
            if any(kw in all_text for kw in keywords_list):
                topics.append(topic)
        
        return list(set(topics))  # Remove duplicates


class MemoryManager:
    """
    Orchestrates memory compaction, storage, and retrieval.
    Integrates with SupabaseSessionService for persistence.
    """
    
    def __init__(self, compaction_strategy: Optional[MemoryCompactionStrategy] = None):
        """
        Initialize memory manager.
        Default: WindowBasedCompaction with recent_messages=15, max_history=100
        """
        self.compaction_strategy = compaction_strategy or WindowBasedCompaction(
            recent_messages=15,
            max_history=100
        )
        self.analytics = MemoryAnalytics()
    
    def compress_history(self, history: List[Content]) -> List[Content]:
        """
        Apply compaction strategy to history.
        Called before saving to Supabase to optimize storage and retrieval.
        """
        return self.compaction_strategy.compact(history)
    
    def get_context_window(self, history: List[Content], window_size: int = 10) -> List[Content]:
        """
        Get the most recent N messages for LLM context.
        Ensures we always have relevant recent context.
        """
        return history[-window_size:] if len(history) > window_size else history
    
    def should_trigger_compaction(self, history: List[Content]) -> bool:
        """
        Determine if compaction should be triggered.
        Rules:
        - If history > 100 messages
        - If total character count > 50KB
        """
        if len(history) > 100:
            return True
        
        total_chars = sum(len(c.parts[0].text) if c.parts else 0 for c in history)
        return total_chars > 50000  # 50KB threshold
    
    def get_session_summary(self, history: List[Content]) -> str:
        """
        Generate a brief summary of the session.
        Used for quick context without processing full history.
        """
        if not history:
            return "No conversation history"
        
        analytics = self.analytics.analyze_session(history)
        topics = self.analytics.extract_key_topics(history)
        
        summary = f"""
Session Summary:
- Total messages: {analytics['total_messages']}
- User: {analytics['user_messages']}, Assistant: {analytics['assistant_messages']}
- Topics discussed: {', '.join(topics) if topics else 'general queries'}
- Total conversation size: {analytics['total_characters']} characters
- Estimated duration: {analytics['session_duration_estimated']}
        """
        return summary.strip()
    
    def prepare_for_llm(self, history: List[Content], max_messages: int = 20) -> List[Content]:
        """
        Prepare history for LLM consumption.
        - Limit to recent messages
        - Ensure all required fields are present
        - Remove corrupted entries
        """
        recent = self.get_context_window(history, max_messages)
        
        cleaned = []
        for content in recent:
            if content.parts and content.role in ["user", "model"]:
                cleaned.append(content)
        
        return cleaned if cleaned else history


class ConversationMemory:
    """
    High-level interface for conversation memory operations.
    Combines MemoryManager with session service integration.
    """
    
    def __init__(self, session_service=None):
        """Initialize with optional session service for persistence"""
        self.memory_manager = MemoryManager()
        self.session_service = session_service
    
    async def save_with_optimization(self, session, history: List[Content]) -> None:
        """
        Save history with automatic optimization:
        1. Check if compaction needed
        2. Apply compaction if needed
        3. Save to session
        """
        if not self.session_service:
            return
        
        if self.memory_manager.should_trigger_compaction(history):
            history = self.memory_manager.compress_history(history)
        
        # Update session state with optimized history
        if not session.state:
            session.state = {}
        session.state["history"] = history
        
        await self.session_service.update_session(session)
    
    async def get_optimized_history(self, session) -> List[Content]:
        """
        Get history prepared for LLM processing.
        Applies memory manager's preparation logic.
        """
        # Extract history from session state
        if session.state and "history" in session.state:
            history = session.state["history"]
        else:
            history = []
        
        return self.memory_manager.prepare_for_llm(history)
    
    def get_memory_stats(self, session) -> Dict:
        """Get detailed memory statistics for a session"""
        # Extract history from session state
        if session.state and "history" in session.state:
            history = session.state["history"]
        else:
            history = []
        
        return {
            "analytics": self.memory_manager.analytics.analyze_session(history),
            "topics": self.memory_manager.analytics.extract_key_topics(history),
            "compaction_needed": self.memory_manager.should_trigger_compaction(history),
            "summary": self.memory_manager.get_session_summary(history)
        }
