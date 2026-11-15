from app.llm import GeminiClient
from app.prompts import EXECUTOR_PROMPT


class Executor:

    def __init__(self):
        self.llm = GeminiClient()

    def execute(self, request: str, tasks: list):

        execution_plan = ""

        for index, task in enumerate(tasks, start=1):

            execution_plan += (
                f"{index}. "
                f"Section Title: {task['title']}\n"
                f"Purpose: {task['purpose']}\n\n"
            )

        prompt = EXECUTOR_PROMPT.format(
            request=request,
            tasks=execution_plan
        )

        return self.llm.generate(prompt)