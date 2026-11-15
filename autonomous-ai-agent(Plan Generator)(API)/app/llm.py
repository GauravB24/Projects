import os
import time

from dotenv import load_dotenv
from google import genai

from app.logger import logger

load_dotenv()


class GeminiClient:

    def __init__(self):

        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables.")

        self.client = genai.Client(api_key=api_key)

        self.model = "gemini-2.5-flash"

        self.max_retries = 3

    def generate(self, prompt: str):

        last_exception = None

        for attempt in range(1, self.max_retries + 1):

            try:

                logger.info(
                    f"Gemini request attempt {attempt}/{self.max_retries}"
                )

                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt
                )

                if not response.text or not response.text.strip():
                    raise ValueError("Empty response received from Gemini.")

                logger.info("Gemini response received successfully.")

                return response.text.strip()

            except Exception as ex:

                last_exception = ex

                logger.error(
                    f"Attempt {attempt} failed: {ex}"
                )

                if attempt < self.max_retries:

                    wait_time = 2 ** attempt

                    logger.warning(
                        f"Retrying in {wait_time} seconds..."
                    )

                    time.sleep(wait_time)

        logger.critical(
            "All retry attempts exhausted."
        )

        raise RuntimeError(
            f"Gemini request failed after {self.max_retries} attempts."
        ) from last_exception