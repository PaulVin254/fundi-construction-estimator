# Fundi - Kenya Construction Cost Estimator

This project is an LLM-powered Agent Development Kit (ADK) application that estimates residential building construction costs in Kenya based on regional market pricing, material choices, and finish levels.

---

## 📦 Features

- ✅ Gemini 2.0 / 2.5 Flash agent built with Google ADK
- ✅ Accurate Kenyan residential building cost calculations (Nairobi, Mombasa, Upcountry)
- ✅ Itemized breakdowns (Foundation, Walling, Roofing, Finishing, Labor, Contingency)
- ✅ ReportLab PDF quote generation & SendGrid Email / WhatsApp delivery
- ✅ Supabase session persistence & keyless GCP Vertex AI authentication
- ✅ Live production deployment on Azure Container Apps

---

## 📂 Project Location

Local Path: `C:\Users\user\Desktop\Website Information\fundi-construction-estimator`

---

## 🚀 Quickstart

### 1. Clone the Repo

```bash
git clone https://github.com/PaulVin254/fundi-construction-estimator.git
cd fundi-construction-estimator
```

### 2. Set Up Python Environment
Required - Python 3.11+, uv, VS Code, and Git
```bash
uv venv
source .venv/bin/activate  # or .venv\Scripts\activate.bat on Windows
uv sync --all-groups
```

### 3. Add Your API Key

Create a `.env` file in the project root inside version_1_website_builder_simple:

```env
GOOGLE_API_KEY=your-google-api-key
GOOGLE_GENAI_USE_VERTEXAI=FALSE
```

You can get your API key from [Google AI Studio](https://makersuite.google.com/app/apikey).

---

### 4. Run the Agent UI

```bash
cd adk_samples/version_1_website_builder_simple
adk web ./agents
```

Then open `http://localhost:8000` in your browser and select `website_builder_simple` from the agents list.

---
### **Four Ways to Run Your ADK Agent**

| S.No. | Method & Command | Description | When to Use |
|------:|------------------|-------------|-------------|
| 1 | **ADK Web**  <br>`adk web ./agents` | - Launches a browser-based UI | - Ideal for debugging or quick demos |
| 2 | **ADK API Server** <br>`adk api_server ./agents` | - Starts an HTTP API server | - Useful for REST API-based automation. |
| 3 | **Programmatic Python Script** <br>`uv run python3 -m agent_runner` | - Fully code-driven interaction using Python and the ADK SDK | - Ideal for building your own CLI tools or backend pipelines |
| 4 | **ADK CLI Run** <br>`adk run agents/root_website_builder` | - Command-line way to run a specific agent directly | - Great for quick runs or testing |

---

## 💬 Example Prompt

```
Create a webpage with a pink background and a green heading that says Hello ADK! Write this to an output file using tht tool.
```

This will generate a complete `.html` file in the `output/` folder.

---

## 🧠 How It Works

- The agent loads instructions from `instructions.txt`
- When you type a prompt, the agent generates the HTML
- It uses the `write_to_file` tool to save it
- Output file: `output/240610_132455_generated_page.html`

---

## 🛠️ Extending the Project

You can easily:
- Add sub-agents (e.g. requirement writer, layout planner)
- Add new tools (e.g. browser launcher, image fetcher)
- Support more output formats (e.g. React, Tailwind)

---

## 📜 License

This repository is licensed under the **GNU General Public License v3.0**.
See the [LICENSE](./LICENSE) file for full details.

---

Happy building with ADK! 🛠