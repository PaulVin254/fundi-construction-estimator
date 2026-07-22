---
name: pdf_email_delivery
description: Guidelines for building, formatting, and verifying PDF cost estimate documents using ReportLab, HTML email delivery (SendGrid), and WhatsApp message handlers.
---

# PDF & Email Delivery Skill

## Overview
This skill provides standards for modifying `estimate_delivery.py`, formatting PDF cost estimates with ReportLab, and triggering email/WhatsApp notification pipelines.

## Core Directives
1. **ReportLab PDF Layouts**:
   - Maintain visual hierarchy, branding colors, and layout parity (refer to `test_pdf_parity.py`).
   - Use clean Flowable elements (`Paragraph`, `Table`, `Spacer`, `Image`).
   - Ensure proper page wrapping and overflow handling.
2. **Email Delivery**:
   - Use SendGrid API handlers with valid fallback error handling.
   - Use clean, inline-styled HTML email templates.
3. **WhatsApp / Messaging Payload**:
   - Format phone numbers properly (e.g., International format `+254...`).
   - Structure text summaries clearly before sending attached PDF links.

## Verification Checklist
- [ ] Run `pytest test_pdf_parity.py` or `pytest test_email.py` after changes.
- [ ] Verify PDF builds without ReportLab layout exceptions (`LayoutError`).
- [ ] Verify API keys are safely retrieved from environment variables.
