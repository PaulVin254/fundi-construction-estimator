---
name: agent_testing
description: Standards for running and creating Pytest suites, testing agent memory systems, testing session persistence, and mocking external APIs in this repository.
---

# Agent Testing & Quality Assurance Skill

## Overview
This skill guides the agent when creating, running, or updating tests (`test_*.py`) for memory management, agent runners, database persistence, and delivery services.

## Core Test Files Reference
- `test_memory_system.py`: Verifies long-term and short-term memory handlers.
- `test_persistence.py`: Verifies session persistence and state loading.
- `test_email.py`: Verifies email template rendering and delivery functions.
- `test_pdf_parity.py`: Verifies PDF layout consistency.
- `test_decoupled_agent.py`: Tests decoupled agent runner logic.

## Directives
1. **Run Tests First (TDD)**: When fixing bugs or building features, write a test in `test_*.py` first and verify failure.
2. **Mocking External APIs**: Always mock network calls to external APIs (Supabase, SendGrid, OpenAI/Gemini) in unit tests to keep test suites fast and reliable.
3. **Execution Command**: Use `pytest` to execute test suites across the workspace.

## Verification Checklist
- [ ] Test fails before feature implementation (Red).
- [ ] Test passes after code update (Green).
- [ ] No external API credentials required to run unit test suite.
