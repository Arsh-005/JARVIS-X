import asyncio
from uuid import uuid4

from jarvis.services import AssistantService


async def repl() -> None:
    service = AssistantService()
    session_id = str(uuid4())
    print(f"JARVIS-X CLI — provider: {service.provider.name} — session: {session_id}")
    print("Type /exit to quit or /agent <goal> to run the tool-using agent.")
    while True:
        text = input("You> ").strip()
        if not text:
            continue
        if text.lower() in {"/exit", "/quit"}:
            break
        if text.startswith("/agent "):
            result = await service.run_agent(session_id, text[7:])
            print(f"JARVIS> {result.answer}")
            if result.confirmation_token:
                print(f"Confirmation token: {result.confirmation_token}")
        else:
            result = await service.chat(session_id, text)
            print(f"JARVIS> {result.answer}")


def main() -> None:
    asyncio.run(repl())


if __name__ == "__main__":
    main()
