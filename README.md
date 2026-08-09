# software-press

Containerized agentic system for writing and reviewing software.

## Setup:

* Provide your Docker API key, and your name/email for git commits, in `.env`.
* Copy the SSH private key you use to access your git remote server into `services/agent-runner/id_rsa`.
* Clone the repo you want into `workspaces`: `git clone git@github.com:example/foobar.git workspaces`

To start:

`docker compose up`

The first time you spin up the system, run:

`docker exec -i sp-postgres psql -U sp_user -d software_press < migrations/001_create_jobs.sql`
`docker exec -i sp-postgres psql -U sp_user -d software_press < migrations/002_add_github_columns.sql`

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
* A new branch (`feature/job-<job-id>` for normal jobs) created, committed, and pushed with `git push --set-upstream origin <branch>`.
* A pull request created via the `gh` cli for that branch; its number is stored in the `pr_number` column of the `jobs` table.

### Issue-driven jobs

To turn a GitHub issue into a pull request, POST to the agent-runner's `/issues` endpoint (host port 8001):

```
curl -X POST http://localhost:8001/issues \
    -H "Content-Type: application/json" \
    -d '{"issueNumber": 42}'
```

`issueNumber` must be a positive integer. The runner fetches the issue description and all comments from the repository in `workspaces/`, builds a prompt, and enqueues it as a normal job. The `issue_number` column of the `jobs` table records the source issue, and the resulting PR is opened against the repository's default branch with a title/body referencing the issue.

### GitHub credentials

Git operations use the SSH key copied to `services/agent-runner/id_rsa` (`~/.ssh/id_rsa` in the container), and `gh` is configured to use SSH (`GH_PROTOCOL=ssh`) so pushes authenticate with that key.

The `gh` cli additionally needs a GitHub token to talk to the GitHub API (fetching issues and creating PRs). Put one in `GH_TOKEN` in `.env` and it will be passed to the agent-runner container.

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