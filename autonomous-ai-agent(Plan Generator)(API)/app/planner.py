import json
import re

from app.llm import GeminiClient
from app.prompts import PLANNER_PROMPT


class Planner:

    def __init__(self):
        self.llm = GeminiClient()

    def create_plan(self, request: str):

        prompt = PLANNER_PROMPT.format(
            request=request
        )

        response = self.llm.generate(prompt)

        return self._parse_plan(response)

    def _parse_plan(self, response: str):

        # First attempt
        try:
            return json.loads(response)

        except json.JSONDecodeError:

            from app.logger import logger
            logger.warning(
            "Planner received invalid JSON. Attempting fallback parsing."
)

        cleaned_response = self._clean_json_response(response)

        # Fallback attempt
        try:
            return json.loads(cleaned_response)

        except json.JSONDecodeError as ex:

            raise ValueError(
                "Unable to parse planner response after fallback."
            ) from ex

    def _clean_json_response(self, response: str):

        # Remove markdown code fences
        response = re.sub(r"```json", "", response, flags=re.IGNORECASE)
        response = re.sub(r"```", "", response)

        response = response.strip()

        # Extract only JSON block
        start = response.find("{")
        end = response.rfind("}")

        if start != -1 and end != -1:

            response = response[start:end + 1]

        return response.strip()