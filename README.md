# software-press

Containerized agentic system for writing and reviewing software.

## Setup:

* Provide your Docker API key in `.env`.
* Copy the SSH private key you use to access your git remote server into `services/agent-runner/id_rsa`.

To start:

`docker compose up`

The first time you spin up the system, run:

`docker exec -i sp-postgres psql -U sp_user -d software_press < migrations/001_create_jobs.sql`

NB the first `up` command `up` will download a local model (Qwen 2.5 0.5B), which will take a while.

## Usage

To enqueue a job:

```
curl -X POST http://localhost:8000/jobs \
    -H "Content-Type: application/json" \
    -d '{
        "prompt": "Write a hello world Python script and save it to helloworld.py"
    }'
```

Response:

```
{"job_id":"c733610a-9714-430e-8d07-3941afd8e29c","status":"queued"}
```

When the job completes, you should see:
* Artifacts from the job in `artifacts/{job_id}` - e.g. `artifacts/c733610a-9714-430e-8d07-3941afd8e29c/prompt.txt` and `artifacts/c733610a-9714-430e-8d07-3941afd8e29c/output.txt`.
* Files written by the job in `workspaces/` - e.g. `workspaces/hello.py` in this case.

Output will appear in `./artifacts/` eventually.

## Models in use

We have configured two providers and three models:

* Ollama - Qwen 2.5 0.5B
* Deepseek - Flash v4
* Deepseek - Pro v4

The Qwen model is quite underpowered so it is not recommended for daily coding, but it is suitable for testing Ollama connectivity. With sufficient hardware you can run a more powerful local model.

The Deepseek models require API keys. Flash is recommended for lightweight tasks, Pro for more heavy-duty tasks. Flash is the default.

## Debugging

Test ollama connectivity from within the sp-agent-runner container:

```
curl http://ollama:11434/api/generate -d '{
  "model": "qwen2.5:0.5b",
  "prompt": "Write a hello world poem",
  "stream": false
}'
```

Test opencode from within the sp-agent-runner container:

```
opencode --dir /workspace --model sp-ollama/qwen2.5:0.5b run "Write a poem about penguins to penguins.txt."
```

The poem should appear in `./workspace/penguins.txt`.