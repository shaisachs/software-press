# software-factory

Containerized agentic system for writing and reviewing software.

To start:

`docker compose up`

Next run:

`curl -sik http://localhost:8000/hello-job`

This API request triggers the agent with the prompt "Write a two sentence blog intro about local-first AI tooling." Output will appear in `./artifacts/hello_job_output.md` as well as in the API response.

NB the `llama3.1:8b` model consumes about 4.6GB of disk space.