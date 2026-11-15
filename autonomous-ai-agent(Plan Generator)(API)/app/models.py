from pydantic import BaseModel, field_validator


class AgentRequest(BaseModel):
    request: str

    @field_validator("request")
    @classmethod
    def validate_request(cls, value: str):

        if not value.strip():
            raise ValueError("Request cannot be empty.")

        return value.strip()