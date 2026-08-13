docker compose down
docker compose --env-file .env.prod build --no-cache
docker compose --env-file .env.prod up -d
