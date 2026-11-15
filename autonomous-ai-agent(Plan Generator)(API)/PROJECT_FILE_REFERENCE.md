Project File Reference
main.py

Application entry point. Creates the FastAPI application, defines API endpoints, receives incoming requests, validates them, and passes them to the Agent for processing.

models.py

Contains the Pydantic request model used for request validation. Ensures incoming API requests have the expected structure before reaching the business logic.

agent.py

Acts as the orchestrator of the application. Coordinates the complete workflow by calling the Planner, Executor, and Document Generator, then returns the final response.

planner.py

Uses the LLM to analyze the user's request and generate a structured execution plan (task list). This is the planning stage of the autonomous agent.

executor.py

Uses the execution plan and the original user request to generate the complete document content using the LLM.

llm.py

Provides a centralized client for communicating with Google Gemini. Handles model calls, retry logic, logging, and isolates the application from the LLM implementation.

prompts.py

Stores all LLM prompts in one place. Separates prompt engineering from application logic, making prompts easier to update and maintain.

document_generator.py

Converts the AI-generated Markdown content into a professionally formatted Microsoft Word (.docx) document and saves it in the output folder.

logger.py

Configures the application's logging. Provides consistent logging for requests, retries, successes, and errors to simplify debugging and monitoring.

requirements.txt

Lists all Python packages required to run the project.

.env

Stores environment variables such as the Gemini API key. This file should never be committed to source control.

README.md

Contains project documentation, setup instructions, API usage, project overview, and implementation details.

output/

Stores all generated Microsoft Word documents created by the application during execution.