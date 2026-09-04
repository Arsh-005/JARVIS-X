from jarvis.llm import ProviderRouter
from jarvis.schemas import ChatMessage


async def run_review_workflow(goal: str) -> dict:
    provider = ProviderRouter().get()
    supervisor = await provider.chat(
        [ChatMessage(role="user", content=goal)],
        system="You are a supervisor. Decompose the user's goal into a short, concrete execution/research plan. Do not claim actions were executed.",
    )
    specialist = await provider.chat(
        [ChatMessage(role="user", content=f"Goal:\n{goal}\n\nSupervisor plan:\n{supervisor}")],
        system="You are the specialist. Produce the strongest practical solution you can from the available information. State uncertainties.",
    )
    critic = await provider.chat(
        [ChatMessage(role="user", content=f"Goal:\n{goal}\n\nCandidate solution:\n{specialist}")],
        system="You are a rigorous critic. Identify factual gaps, unsafe assumptions, missing edge cases, and concrete improvements.",
    )
    final = await provider.chat(
        [
            ChatMessage(
                role="user",
                content=f"Goal:\n{goal}\n\nPlan:\n{supervisor}\n\nDraft:\n{specialist}\n\nCritique:\n{critic}",
            )
        ],
        system="You are the final editor. Return a corrected, concise answer incorporating valid critique. Do not invent tool results.",
    )
    return {
        "provider": provider.name,
        "plan": supervisor,
        "draft": specialist,
        "critique": critic,
        "final": final,
    }
