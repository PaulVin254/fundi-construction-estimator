# =============================================================================
# FILE: conversation_memory.py
# PURPOSE:
#   Manages conversation history with intelligent context compaction strategies.
#   Handles conversation history storage, summarization, and token optimization.
# =============================================================================

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import json

# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class ConversationTurn:
    """Represents a single turn in the conversation (user + assistant)."""
    user_message: str
    assistant_response: str
    timestamp: datetime = field(default_factory=datetime.now)
    tokens_used: int = 0
    
    def to_dict(self) -> dict:
        """Convert turn to dictionary for serialization."""
        return {
            "user_message": self.user_message,
            "assistant_response": self.assistant_response,
            "timestamp": self.timestamp.isoformat(),
            "tokens_used": self.tokens_used
        }
    
    def get_text(self) -> str:
        """Get full turn as text."""
        return f"User: {self.user_message}\n\nAssistant: {self.assistant_response}"


@dataclass
class ConversationSummary:
    """Stores compressed conversation context."""
    summary_text: str
    turns_count: int
    date_range: Tuple[datetime, datetime]
    key_topics: List[str] = field(default_factory=list)
    estimated_tokens: int = 0


# =============================================================================
# CONVERSATION MEMORY MANAGER
# =============================================================================

class ConversationMemoryManager:
    """Manages conversation history with compaction strategies."""
    
    def __init__(
        self,
        max_turns: int = 20,
        max_tokens: int = 8000,
        compaction_threshold: float = 0.75,
        summarization_enabled: bool = True
    ):
        """
        Initialize the conversation memory manager.
        
        Args:
            max_turns: Maximum number of recent turns to keep uncompressed
            max_tokens: Maximum tokens to allow in active conversation
            compaction_threshold: When to trigger compaction (% of max_tokens)
            summarization_enabled: Whether to use summarization for old turns
        """
        self.max_turns = max_turns
        self.max_tokens = max_tokens
        self.compaction_threshold = compaction_threshold
        self.summarization_enabled = summarization_enabled
        
        self.current_turns: List[ConversationTurn] = []
        self.summaries: List[ConversationSummary] = []
        self.total_tokens_used: int = 0
    
    def add_turn(
        self,
        user_message: str,
        assistant_response: str,
        tokens_used: int = 0
    ) -> None:
        """
        Add a new conversation turn.
        
        Args:
            user_message: The user's input
            assistant_response: The assistant's response
            tokens_used: Estimated tokens for this turn
        """
        turn = ConversationTurn(
            user_message=user_message,
            assistant_response=assistant_response,
            tokens_used=tokens_used
        )
        
        self.current_turns.append(turn)
        self.total_tokens_used += tokens_used
        
        # Check if compaction is needed
        if self._should_compact():
            self._compact_conversation()
    
    def _should_compact(self) -> bool:
        """Determine if conversation should be compacted."""
        current_tokens = self._estimate_tokens()
        threshold_tokens = self.max_tokens * self.compaction_threshold
        
        return (
            current_tokens > threshold_tokens or 
            len(self.current_turns) > self.max_turns
        )
    
    def _compact_conversation(self) -> None:
        """Apply compaction strategy to reduce conversation size."""
        if len(self.current_turns) <= self.max_turns // 2:
            return  # Don't compact if we're well under the limit
        
        # Keep the most recent turns
        turns_to_keep = self.max_turns // 2
        turns_to_compact = self.current_turns[:-turns_to_keep]
        self.current_turns = self.current_turns[-turns_to_keep:]
        
        if self.summarization_enabled and turns_to_compact:
            # Create a summary of compacted turns
            summary = self._create_summary(turns_to_compact)
            self.summaries.append(summary)
    
    def _create_summary(self, turns: List[ConversationTurn]) -> ConversationSummary:
        """
        Create a summary of conversation turns.
        
        This is a simple extractive summary. In production, you'd use
        an LLM to generate abstractive summaries.
        
        Args:
            turns: List of conversation turns to summarize
            
        Returns:
            ConversationSummary object
        """
        if not turns:
            return ConversationSummary(
                summary_text="",
                turns_count=0,
                date_range=(datetime.now(), datetime.now())
            )
        
        # Extract key points from user messages
        user_messages = [turn.user_message for turn in turns]
        key_topics = self._extract_key_topics(user_messages)
        
        # Create summary text
        summary_lines = [
            f"Previous conversation summary ({len(turns)} turns):",
            f"Key topics: {', '.join(key_topics)}",
            "Recent context: " + " | ".join([m[:50] + "..." if len(m) > 50 else m for m in user_messages[-3:]])
        ]
        
        summary_text = "\n".join(summary_lines)
        
        return ConversationSummary(
            summary_text=summary_text,
            turns_count=len(turns),
            date_range=(turns[0].timestamp, turns[-1].timestamp),
            key_topics=key_topics,
            estimated_tokens=self._estimate_turn_tokens(turns)
        )
    
    def _extract_key_topics(self, messages: List[str]) -> List[str]:
        """
        Extract key topics from messages (simple implementation).
        In production, use NLP/NER for better results.
        
        Args:
            messages: List of message strings
            
        Returns:
            List of extracted topics
        """
        # Simple keyword extraction - get first few capitalized words
        topics = set()
        for msg in messages:
            words = msg.split()
            for word in words[:5]:
                if word and word[0].isupper() and len(word) > 3:
                    topics.add(word.rstrip('.,!?'))
        
        return list(topics)[:5]  # Return top 5 topics
    
    def _estimate_tokens(self) -> int:
        """Estimate total tokens in current conversation."""
        tokens = sum(turn.tokens_used for turn in self.current_turns)
        tokens += sum(s.estimated_tokens for s in self.summaries)
        return tokens
    
    def _estimate_turn_tokens(self, turns: List[ConversationTurn]) -> int:
        """Estimate tokens for a list of turns."""
        return sum(turn.tokens_used for turn in turns)
    
    def get_context_for_model(self) -> str:
        """
        Get formatted context to send to the model.
        
        Includes summaries of old conversations + recent turns.
        
        Returns:
            Formatted context string
        """
        context_parts = []
        
        # Add summaries of compacted conversations
        if self.summaries:
            context_parts.append("=" * 50)
            context_parts.append("CONVERSATION HISTORY SUMMARY")
            context_parts.append("=" * 50)
            for i, summary in enumerate(self.summaries):
                context_parts.append(f"\n[Summary {i+1}]")
                context_parts.append(summary.summary_text)
            context_parts.append("\n" + "=" * 50)
            context_parts.append("RECENT CONVERSATION")
            context_parts.append("=" * 50 + "\n")
        
        # Add recent turns
        for turn in self.current_turns:
            context_parts.append(turn.get_text())
            context_parts.append("")  # Blank line separator
        
        return "\n".join(context_parts)
    
    def get_status(self) -> Dict:
        """Get status of conversation memory."""
        return {
            "current_turns": len(self.current_turns),
            "summaries": len(self.summaries),
            "estimated_tokens": self._estimate_tokens(),
            "total_tokens_used": self.total_tokens_used,
            "compression_ratio": (
                len(self.summaries) * 10 / max(len(self.current_turns), 1)
            )  # Rough estimate of compression
        }
    
    def clear(self) -> None:
        """Clear all conversation history."""
        self.current_turns = []
        self.summaries = []
        self.total_tokens_used = 0
    
    def export_history(self) -> Dict:
        """Export conversation history as JSON-serializable dict."""
        return {
            "current_turns": [turn.to_dict() for turn in self.current_turns],
            "summaries": [
                {
                    "summary_text": s.summary_text,
                    "turns_count": s.turns_count,
                    "date_range": [s.date_range[0].isoformat(), s.date_range[1].isoformat()],
                    "key_topics": s.key_topics,
                    "estimated_tokens": s.estimated_tokens
                }
                for s in self.summaries
            ],
            "metadata": self.get_status()
        }
    
    def save_to_file(self, filepath: str) -> None:
        """Save conversation history to JSON file."""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.export_history(), f, indent=2, ensure_ascii=False)
    
    def load_from_file(self, filepath: str) -> None:
        """Load conversation history from JSON file."""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Reconstruct turns
        self.current_turns = [
            ConversationTurn(
                user_message=turn['user_message'],
                assistant_response=turn['assistant_response'],
                timestamp=datetime.fromisoformat(turn['timestamp']),
                tokens_used=turn['tokens_used']
            )
            for turn in data.get('current_turns', [])
        ]
        
        # Reconstruct summaries
        self.summaries = [
            ConversationSummary(
                summary_text=s['summary_text'],
                turns_count=s['turns_count'],
                date_range=(
                    datetime.fromisoformat(s['date_range'][0]),
                    datetime.fromisoformat(s['date_range'][1])
                ),
                key_topics=s.get('key_topics', []),
                estimated_tokens=s.get('estimated_tokens', 0)
            )
            for s in data.get('summaries', [])
        ]


# =============================================================================
# CONTEXT COMPACTION STRATEGIES
# =============================================================================

class ContextCompactionStrategy:
    """Base class for different compaction strategies."""
    
    def compact(self, turns: List[ConversationTurn]) -> str:
        """
        Compact conversation turns into a summary.
        
        Args:
            turns: List of turns to compact
            
        Returns:
            Compacted context string
        """
        raise NotImplementedError


class SlidingWindowStrategy(ContextCompactionStrategy):
    """Keep only the most recent N turns."""
    
    def __init__(self, window_size: int = 10):
        self.window_size = window_size
    
    def compact(self, turns: List[ConversationTurn]) -> str:
        """Keep only recent turns, discard old ones."""
        if len(turns) <= self.window_size:
            return "\n".join([turn.get_text() for turn in turns])
        
        recent_turns = turns[-self.window_size:]
        return "\n".join([turn.get_text() for turn in recent_turns])


class SummarizationStrategy(ContextCompactionStrategy):
    """Summarize old turns and keep recent ones."""
    
    def __init__(self, keep_recent: int = 5, summarize_older: bool = True):
        self.keep_recent = keep_recent
        self.summarize_older = summarize_older
    
    def compact(self, turns: List[ConversationTurn]) -> str:
        """Summarize older turns, keep recent ones."""
        if len(turns) <= self.keep_recent:
            return "\n".join([turn.get_text() for turn in turns])
        
        older_turns = turns[:-self.keep_recent]
        recent_turns = turns[-self.keep_recent:]
        
        context_parts = []
        
        # Add summary of older turns
        if self.summarize_older and older_turns:
            context_parts.append("[CONVERSATION SUMMARY]")
            context_parts.append(self._summarize_turns(older_turns))
            context_parts.append("")
        
        # Add recent turns
        context_parts.append("[RECENT CONVERSATION]")
        context_parts.extend([turn.get_text() for turn in recent_turns])
        
        return "\n".join(context_parts)
    
    def _summarize_turns(self, turns: List[ConversationTurn]) -> str:
        """Simple summarization of turns."""
        topics = set()
        for turn in turns:
            words = turn.user_message.split()
            for word in words[:3]:
                if len(word) > 4:
                    topics.add(word)
        
        return f"Topics discussed: {', '.join(list(topics)[:5])}"


class TokenBudgetStrategy(ContextCompactionStrategy):
    """Discard turns to stay within token budget."""
    
    def __init__(self, max_tokens: int = 4000, tokens_per_turn: int = 100):
        self.max_tokens = max_tokens
        self.tokens_per_turn = tokens_per_turn
    
    def compact(self, turns: List[ConversationTurn]) -> str:
        """Keep turns until token budget is reached."""
        total_tokens = 0
        kept_turns = []
        
        # Iterate from most recent to oldest
        for turn in reversed(turns):
            turn_tokens = turn.tokens_used or self.tokens_per_turn
            if total_tokens + turn_tokens > self.max_tokens:
                break
            kept_turns.insert(0, turn)
            total_tokens += turn_tokens
        
        return "\n".join([turn.get_text() for turn in kept_turns])
