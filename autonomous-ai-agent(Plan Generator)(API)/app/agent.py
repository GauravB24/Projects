from app.document_generator import DocumentGenerator
from app.executor import Executor
from app.planner import Planner


class Agent:

    def __init__(self):
        self.planner = Planner()
        self.executor = Executor()
        self.document_generator = DocumentGenerator()

    def process_request(self, request: str):

        plan = self.planner.create_plan(request)

        document_content = self.executor.execute(
            request=request,
            tasks=plan["tasks"]
        )

        document_path = self.document_generator.generate(
            document_content
        )

        return {
            "request": request,
            "plan": plan,
            "document_path": document_path,
            "status": "Completed"
        }