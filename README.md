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
`docker exec -i sp-postgres psql -U sp_user -d software_press < migrations/003_allow_null_prompt.sql`

NB the first `up` command `up` will download a local model (Qwen 2.5 0.5B), which will take a while.

## Usage

To enqueue a job, POST to `/jobs` with a `prompt`:

```
curl -X POST http://localhost:8000/jobs \
    -H "Content-Type: application/json" \
    -d '{
        "prompt": "Write a hello world Python script and save it to helloworld.py"
    }'
```

Alternatively, to turn a GitHub issue into a pull request, POST to `/jobs` with an `issueNumber`:

```
curl -X POST http://localhost:8000/jobs \
    -H "Content-Type: application/json" \
    -d '{"issueNumber": 42}'
```

Exactly one of `prompt` or `issueNumber` must be specified; providing neither or both returns a `400`. `issueNumber` must be a positive integer. The runner fetches the issue description and all comments, builds a prompt from it, and runs the job.

Response:

```
{"job_id":"c733610a-9714-430e-8d07-3941afd8e29c","status":"queued"}
```

When the job completes, you should see:
* Artifacts from the job in `artifacts/{job_id}` - e.g. `artifacts/c733610a-9714-430e-8d07-3941afd8e29c/prompt.txt` and `artifacts/c733610a-9714-430e-8d07-3941afd8e29c/output.txt`.
* Files written by the job in `workspaces/` - e.g. `workspaces/hello.py` in this case.
* A new branch created, committed, and pushed with `git push --set-upstream origin <branch>` (`feature/job-<job-id>` for prompt jobs, `feature/issue-<issue-number>` for issue jobs).
* A pull request created via the `gh` cli for that branch; its number is stored in the `pr_number` column of the `jobs` table. Issue jobs open the PR against the repository's default branch with a title/body referencing the issue, and the source issue is recorded in the `issue_number` column.

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
opencode --dir /workspaces --model sp-ollama/qwen2.5:0.5b run "Write a poem about penguins to penguins.txt."
```

The poem should appear in `./workspaces/penguins.txt`.