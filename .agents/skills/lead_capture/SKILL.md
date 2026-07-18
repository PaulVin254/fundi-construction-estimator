---
name: Lead Capture & PDF Delivery
description: Prompting for user details and formatting structured data for PDF/Email/WhatsApp generation.
---

# THE TEASER HOOK
Once you have estimated the teaser cost range:

- **IF the user's details (Name, and Email or Phone) are already known** (you will see a `[System Note]` at the start of their message with their name, email, and/or phone):
  * You **MUST** output the `<ESTIMATE_DATA>` block in the **SAME response** as your cost summary.
  * Do **NOT** say "I can send you a report" and wait for confirmation.
  * Do **NOT** ask "Would you like me to send it?" - just output the data block immediately.
  * The 'Email Report' or 'Get PDF on WhatsApp' button will appear automatically when you output the block.
  * **Example response for WhatsApp delivery (follow this structure exactly):**
    ```
    Based on your inputs, a 3-bedroom house in Nairobi with basic finish costs between KES 2.8M and KES 3.3M.
    
    Click the button below to receive the full breakdown as a PDF on WhatsApp!
    
    <ESTIMATE_DATA>
    {
      "client_name": "Paul",
      "client_email": "whatsapp",
      ...other json fields...
    }
    </ESTIMATE_DATA>
    
    [Disclaimers]
    ```

- **IF the user's details are NOT known**:
  Ask the user to provide their details using the inline form. Append the exact tag `<REQUEST_LEAD_INFO>` at the very end of your message.
  Do **NOT** output `<ESTIMATE_DATA>` until you have the name and email/phone.

- **The Delivery:** When the user provides their details (or if you already have them from the System Note), generate the detailed breakdown using the `<ESTIMATE_DATA>` format below.

# OUTPUT FORMAT FOR DELIVERY
When the user provides their details for the report, you must output the detailed breakdown in a specific XML-like format so my system can generate the PDF.

**IMPORTANT RULES FOR WhatsApp vs Email:**
- If the user requested delivery via **WhatsApp**, you MUST set `"client_email": "whatsapp"` in the JSON block below.
- If the user requested delivery via **Email**, set `"client_email"` to their actual email address.

**Format:**
"Great! I'm creating your detailed report now. It will be ready in a moment!

<ESTIMATE_DATA>
{
  "client_name": "Valued Client",
  "client_email": "whatsapp", // Use "whatsapp" for WhatsApp delivery, or actual email for email delivery
  "project_title": "3 Bedroom House in Nairobi (Premium)",
  "items": [
    {"item": "Foundation", "description": "Excavation, footing, slab", "cost": "600,000"},
    {"item": "Walling", "description": "Stone masonry, mortar", "cost": "900,000"},
    {"item": "Roofing", "description": "Timber truss, iron sheets/tiles", "cost": "700,000"},
    {"item": "Electrical", "description": "Wiring, fittings, labor", "cost": "400,000"},
    {"item": "Plumbing", "description": "Piping, sanitary ware, labor", "cost": "350,000"},
    {"item": "Finishing", "description": "Tiles, paint, ceiling, cabinets", "cost": "1,500,000"},
    {"item": "Labor", "description": "Skilled and unskilled labor", "cost": "900,000"},
    {"item": "Contingency", "description": "10% buffer for unforeseen costs", "cost": "535,000"}
  ],
  "total_cost": "5,885,000",
  "cost_per_sqm": "49,041"
}
</ESTIMATE_DATA>

Please click the button below to get your PDF!"

**IMPORTANT:**
- Do NOT output the full breakdown table in the chat text.
- The `<ESTIMATE_DATA>` block MUST be valid JSON inside the tags.
- **Do NOT wrap the <ESTIMATE_DATA> block in markdown code fences (no ```xml, ```json, or ``` around it). Output the tags directly in the text.**
- Ensure the costs are realistic for 2025 Kenyan market rates.
