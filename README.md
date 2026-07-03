# software-press

## Setup:

Containerized agentic system for writing and reviewing software.

To start:

`docker compose up`

Next run:

`docker exec -i sp-postgres psql -U sp_user -d software_press < migrations/001_create_jobs.sql`

NB the `llama3.1:8b` model consumes about 4.6GB of disk space. The first `up` will download the model which will take a while.

NB2 As currently written the agent actually runs the Big Pickle model, which is cloud-based. Llama 3.1 is quite old and limited, we've just wired it up to demonstrate that it's possible to run a local model. Eventually we'll run on more heavy-duty hardware that's capable of running something more substantial like Kimi.

## Usage

To enqueue a job:

```
curl -X POST http://localhost:8000/jobs \
    -H "Content-Type: application/json" \
    -d '{
        "prompt": "Write a hello world Python script and save it to hello.py"
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

## Debugging

Test ollama connectivity from within the sp-agent-runner container:

```
curl http://ollama:11434/api/generate -d '{
  "model": "llama3.1:8b",
  "prompt": "Write a hello world poem",
  "stream": false
}'
```

Test opencode from within the sp-agent-runner container:

```
opencode --dir /workspace --model opencode/big-pickle run "Write a poem about penguins to penguins.txt."
```

The poem should appear in `/workspace/penguins.txt`.