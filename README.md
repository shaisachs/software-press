# software-press

Containerized agentic system for writing and reviewing software.

To start:

`docker compose up`

Next run:

`docker exec -i sp-postgres psql -U sp_user -d software_press < migrations/001_create_jobs.sql`

Finally:

```
curl -X POST http://localhost:8000/jobs \
    -H "Content-Type: application/json" \
    -d '{
        "prompt": "Write a hello world Python script"
    }'
```

Output will appear in `./artifacts/` eventually.

NB the `llama3.1:8b` model consumes about 4.6GB of disk space.
