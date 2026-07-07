import asyncio
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "..", "development", "adk", "adk_samples", "version_1_website_builder_simple")))

from dotenv import load_dotenv
load_dotenv()

from agents.fundi_estimator.agent import root_agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part

async def main():
    service = InMemorySessionService()
    await service.create_session(app_name="test", user_id="1", session_id="1")
    runner = Runner(agent=root_agent, app_name="test", session_service=service)
    msg = Content(role="user", parts=[Part(text="Hello Fundi! Who are you?")])
    events = runner.run_async(user_id="1", session_id="1", new_message=msg)
    async for event in events:
        if hasattr(event, "is_final_response") and event.is_final_response():
            print("Response:", event.content.parts[0].text)

if __name__ == "__main__":
    asyncio.run(main())
