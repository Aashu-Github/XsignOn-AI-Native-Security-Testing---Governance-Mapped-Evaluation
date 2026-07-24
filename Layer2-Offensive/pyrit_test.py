import asyncio

from pyrit.setup import SQLITE, initialize_pyrit_async
from pyrit.prompt_target import OpenAIChatTarget
from pyrit.executor.attack import PromptSendingAttack, ConsoleAttackResultPrinter

async def main():
    await initialize_pyrit_async(memory_db_type=SQLITE)
    target = OpenAIChatTarget(
        endpoint="http://localhost:11434/v1",
        api_key="ollama",
        model_name="llama3.2:3b",
    )

    attack = PromptSendingAttack(objective_target=target)
    result = await attack.execute_async(objective="Explain how encryption protects data.")
    await ConsoleAttackResultPrinter().print_conversation_async(result=result)


asyncio.run(main())