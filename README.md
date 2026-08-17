# software-press

Containerized agentic system for writing and reviewing software.

See [docs/architecture.md](docs/architecture.md) for an overview of how the system works, the containers involved, and a Mermaid diagram of the architecture.

## Setup:

* Copy `.env` to `.env.prod`.
* Provide your Docker API key, Git name/email, and Github access token, in `.env`.
* Copy the SSH private key you use to access your git remote server into `services/agent/id_rsa`.
* Clone the repo you want into `workspaces`: `git clone git@github.com:example/foobar.git workspaces/example/foobar`

To start:

`docker compose up --env-file .env.prod`

NB the first `up` command will download a local model (Qwen 2.5 0.5B), which will take a while.

## Usage

### Ad hoc prompts

For an *ad hoc* prompt:

```
curl -X POST http://localhost:8000/jobs \
    -H "Content-Type: application/json" \
    -d '{
        "repo": "example/foobar",
        "prompt": "Write a hello world Python script and save it to helloworld.py",
        "model": "deepseek/deepseek-v4-pro"
    }'
```

The `model` field is optional and must be in `provider/model` format. If omitted, the default model from the environment is used. The `type` field is optional; when omitted it is inferred from the request (`adHoc` for a prompt, `issueResolver` for an issue number).

The agent will write and commit code to `workspaces/example/foobar`, in the current branch. It will not push.

### Github Issues

To turn a GitHub issue into a pull request:

```
curl -X POST http://localhost:8000/jobs \
    -H "Content-Type: application/json" \
    -d '{"repo": "example/foobar", "issueNumber": 42}'
```

The agent uses `gh` to fetch the specified issue, for the Github repository at `workspaces/example/foobar`; it builds a prompt around the issue, and executes the prompt. The resulting code is saved to a new branch, which is pushed and turned into a new pull request.

### Issue architecting

To research an issue and propose an implementation approach *without* changing any code, use `type: "issueArchitect"`:

```
curl -X POST http://localhost:8000/jobs \
    -H "Content-Type: application/json" \
    -d '{"repo": "example/foobar", "issueNumber": 42, "type": "issueArchitect"}'
```

The agent fetches the issue, researches the codebase, and posts the proposed implementation approach as a new comment on the issue. No code is committed and no pull request is created.

### Output and debugging

For both of the above requests, the response is:

```
{"job_id":"c733610a-9714-430e-8d07-3941afd8e29c","status":"queued"}
```

When the job completes, you should see:
* Artifacts from the job in `artifacts/{datestamp}-{job_id}` - e.g. `artifacts/20260811180005-c733610a-9714-430e-8d07-3941afd8e29c/prompt.txt` and `artifacts/20260811180005-c733610a-9714-430e-8d07-3941afd8e29c/output.txt`.
* Files written by the job in `workspaces/`
* All of the above is available by querying `curl http://localhost:8000/jobs/{job_id}`.

## Models in use

We have configured two providers and three models:

* Ollama - Qwen 2.5 0.5B
* Deepseek - Flash v4
* Deepseek - Pro v4

The Qwen model is quite underpowered so it is not recommended for daily coding, but it is suitable for testing Ollama connectivity. With sufficient hardware you can run a more powerful local model.

The Deepseek models require API keys. Flash is recommended for lightweight tasks, Pro for more heavy-duty tasks. Flash is the default.

## Tests

Run the unit tests for both services:

`scripts/test.sh`

### Functional tests

Run the functional test suite, which exercises the *real* API against throwaway
Postgres and Redis containers (no mocks):

`scripts/test-functional.sh`

The script stands up throwaway `postgres-test` and `redis-test` containers,
applies all migrations (via the same `scripts/migrate.sh` path used in
production), boots the real API, and runs a [Karate](https://karate.io) suite
(`functional_tests/karate/`) against it. Because the dependencies are real, the
Karate scenarios can assert state the API cannot see over HTTP:

* row-level assertions against Postgres (via JDBC through a small
  `karatehelpers.DbUtils` helper), and
* direct queue-membership checks against Redis (via jedis).

The suite exits non-zero on any failure, and a GitHub Actions workflow
(`.github/workflows/functional-tests.yml`) runs it as a gate on push / pull
request, so functional test breaks are visible before the API image is built or
pushed.

## Debugging

Test ollama connectivity from within the sp-agent container:

```
curl http://ollama:11434/api/generate -d '{
  "model": "qwen2.5:0.5b",
  "prompt": "Write a hello world poem",
  "stream": false
}'
```

Test opencode from within the sp-agent container:

```
opencode --dir /workspaces --model sp-ollama/qwen2.5:0.5b run "Write a poem about penguins to penguins.txt."
```

The poem should appear in `./workspaces/penguins.txt`.