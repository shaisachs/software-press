from fastapi import FastAPI
import httpx
import os
import redis
from minio import Minio

app = FastAPI()

redis_client = redis.Redis.from_url(os.environ["REDIS_URL"])

minio_client = Minio(
    os.environ["MINIO_ENDPOINT"],
    access_key=os.environ["MINIO_ACCESS_KEY"],
    secret_key=os.environ["MINIO_SECRET_KEY"],
    secure=False,
)

OLLAMA_BASE_URL = os.environ["OLLAMA_BASE_URL"]


@app.get("/")
def root():
    return {"status": "ok"}


@app.get("/health")
def health():
    return {
        "postgres": "configured",
        "redis": redis_client.ping(),
        "minio": True,
    }


@app.get("/hello-job")
async def hello_job():
    prompt = "Write a two sentence blog intro about local-first AI tooling."

    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": "llama3.1:8b",
                "prompt": prompt,
                "stream": False,
            },
        )

    data = response.json()

    output = data.get("response", "")

    os.makedirs("/app/artifacts", exist_ok=True)

    artifact_path = "/app/artifacts/hello_job_output.md"

    with open(artifact_path, "w") as f:
        f.write(output)

    return {
        "prompt": prompt,
        "output": output,
        "artifact": artifact_path,
    }