# =============================================================================
# FILE: memory_demo.py
# PURPOSE:
#   Demonstrates the conversation memory management system with compaction.
#   Shows how memory is tracked, summarized, and compacted over time.
# =============================================================================

import asyncio
from utils.conversation_memory import (
    ConversationMemoryManager,
    SlidingWindowStrategy,
    SummarizationStrategy,
    TokenBudgetStrategy
)

def demo_basic_memory_management():
    """Demo 1: Basic memory management and compaction."""
    print("=" * 70)
    print("DEMO 1: Basic Memory Management and Compaction")
    print("=" * 70)
    
    memory = ConversationMemoryManager(
        max_turns=5,
        max_tokens=1000,
        compaction_threshold=0.75
    )
    
    # Simulate a conversation
    conversations = [
        ("What is machine learning?", "Machine learning is a subset of AI that enables systems to learn from data."),
        ("Tell me about neural networks.", "Neural networks are computational models inspired by biological neurons."),
        ("How do CNNs work?", "CNNs use convolutional layers to extract features from images."),
        ("What about transformers?", "Transformers use self-attention mechanisms for processing sequences."),
        ("Explain attention mechanisms.", "Attention allows models to focus on relevant parts of input."),
        ("What is BERT?", "BERT is a transformer-based model for natural language understanding."),
        ("How does BERT training work?", "BERT uses masked language modeling and next sentence prediction."),
    ]
    
    for i, (user_msg, assistant_msg) in enumerate(conversations, 1):
        memory.add_turn(user_msg, assistant_msg, tokens_used=150)
        status = memory.get_status()
        print(f"\nTurn {i}:")
        print(f"  User: {user_msg}")
        print(f"  Status: {status['current_turns']} turns, "
              f"{status['summaries']} summaries, "
              f"{status['estimated_tokens']} tokens")
    
    print("\n" + "=" * 70)
    print("FINAL MEMORY STATUS:")
    print("=" * 70)
    print(memory.get_context_for_model())
    print("\n" + "=" * 70)
    print("EXPORT:")
    print("=" * 70)
    import json
    print(json.dumps(memory.export_history(), indent=2)[:500] + "...")


def demo_compaction_strategies():
    """Demo 2: Different compaction strategies."""
    print("\n\n" + "=" * 70)
    print("DEMO 2: Compaction Strategies")
    print("=" * 70)
    
    # Create sample conversation turns
    from utils.conversation_memory import ConversationTurn
    
    turns = [
        ConversationTurn("Q1?", "A1" * 50, tokens_used=100),
        ConversationTurn("Q2?", "A2" * 50, tokens_used=100),
        ConversationTurn("Q3?", "A3" * 50, tokens_used=100),
        ConversationTurn("Q4?", "A4" * 50, tokens_used=100),
        ConversationTurn("Q5?", "A5" * 50, tokens_used=100),
    ]
    
    # Test Sliding Window Strategy
    print("\n[SLIDING WINDOW STRATEGY - Keep 2 most recent turns]")
    strategy = SlidingWindowStrategy(window_size=2)
    result = strategy.compact(turns)
    print(result[:200] + "...")
    
    # Test Summarization Strategy
    print("\n[SUMMARIZATION STRATEGY - Summarize old, keep 2 recent]")
    strategy = SummarizationStrategy(keep_recent=2)
    result = strategy.compact(turns)
    print(result[:300] + "...")
    
    # Test Token Budget Strategy
    print("\n[TOKEN BUDGET STRATEGY - Stay within 300 tokens]")
    strategy = TokenBudgetStrategy(max_tokens=300, tokens_per_turn=100)
    result = strategy.compact(turns)
    print(result[:300] + "...")


def demo_memory_persistence():
    """Demo 3: Saving and loading conversation history."""
    print("\n\n" + "=" * 70)
    print("DEMO 3: Memory Persistence (Save/Load)")
    print("=" * 70)
    
    memory = ConversationMemoryManager()
    
    # Add some conversations
    conversations = [
        ("What is Python?", "Python is a high-level programming language."),
        ("How does Python compare to Java?", "Python is more concise, Java is more strict."),
    ]
    
    for user_msg, assistant_msg in conversations:
        memory.add_turn(user_msg, assistant_msg, tokens_used=100)
    
    # Save to file
    filepath = "demo_conversation.json"
    memory.save_to_file(filepath)
    print(f"\n✓ Conversation saved to: {filepath}")
    
    # Create new memory manager and load
    memory2 = ConversationMemoryManager()
    memory2.load_from_file(filepath)
    print(f"✓ Conversation loaded from: {filepath}")
    
    print(f"\nLoaded {len(memory2.current_turns)} turns:")
    for i, turn in enumerate(memory2.current_turns, 1):
        print(f"  Turn {i}: {turn.user_message[:50]}...")
    
    # Clean up
    import os
    os.remove(filepath)
    print(f"\n✓ Demo file cleaned up")


def print_usage_guide():
    """Print usage guide for the memory system."""
    print("\n\n" + "=" * 70)
    print("USAGE GUIDE: Conversation Memory System")
    print("=" * 70)
    
    guide = """
FEATURES:
---------
1. Automatic context compaction when token/turn limits reached
2. Summarization of old conversations to preserve context
3. Multiple compaction strategies (sliding window, summarization, token budget)
4. Conversation history persistence (save/load to JSON)
5. Memory status monitoring

IN YOUR AGENT RUNNER:
---------------------
The memory manager is integrated with the following special commands:

  :status or :memory   - Show current memory usage statistics
  :save or :export     - Save conversation history to JSON file
  quit, exit, or :q    - End the chat session

CONFIGURATION:
--------------
Adjust MEMORY_CONFIG in agent_runner.py to customize:

  max_turns:           Maximum recent turns to keep uncompressed (default: 20)
  max_tokens:          Maximum tokens allowed (default: 8000)
  compaction_threshold: When to trigger compaction at % of max (default: 0.75)
  summarization_enabled: Whether to summarize old turns (default: True)

TOKEN ESTIMATION:
-----------------
For accurate token counting, update the add_turn() call with actual tokens:

  # Get token count from Gemini API response
  tokens_used = response.usage_metadata.total_tokens
  memory_manager.add_turn(user_msg, assistant_msg, tokens_used=tokens_used)

COMPACTION STRATEGIES:
---------------------
The system includes three built-in strategies:

  1. SlidingWindowStrategy
     - Keeps only the most recent N turns
     - Useful for quick, lightweight conversations
     
  2. SummarizationStrategy
     - Summarizes old turns, keeps recent ones
     - Best for long conversations with accumulated context
     
  3. TokenBudgetStrategy
     - Discards turns to stay within token budget
     - Recommended for production with API cost constraints

PRODUCTION RECOMMENDATIONS:
---------------------------
1. Use TokenBudgetStrategy for cost control
2. Implement actual token counting from API responses
3. Use LLM-based abstractive summarization instead of simple extraction
4. Add database persistence (PostgreSQL, MongoDB) instead of JSON files
5. Implement conversation pruning policies (age, relevance, etc.)
6. Add monitoring/logging for memory effectiveness
7. Consider Redis for distributed cache in multi-instance deployments
"""
    
    print(guide)


if __name__ == "__main__":
    # Run all demos
    demo_basic_memory_management()
    demo_compaction_strategies()
    demo_memory_persistence()
    print_usage_guide()
    
    print("\n" + "=" * 70)
    print("All demos completed! Check the implementation in:")
    print("  - utils/conversation_memory.py (core system)")
    print("  - agent_runner.py (integration)")
    print("=" * 70)
