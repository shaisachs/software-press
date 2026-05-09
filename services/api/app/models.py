from pydantic import BaseModel

class CreateJobRequest(BaseModel):
    prompt: str