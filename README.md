# software-factory

Containerized agentic system for writing and reviewing software.

To start:

`docker compose up`

Next run:

`docker exec -i sf-postgres psql -U sf_user -d software_factory < migrations/001_create_jobs.sql`

Finally:

```
curl -X POST http://localhost:8000/jobs \
    -H "Content-Type: application/json" \
    -d '{
        "prompt": "Write a hello world Python script"
    }'
```

This API request triggers the agent with the prompt "Write a two sentence blog intro about local-first AI tooling." Output will appear in `./artifacts/` eventually.

NB the `llama3.1:8b` model consumes about 4.6GB of disk space.