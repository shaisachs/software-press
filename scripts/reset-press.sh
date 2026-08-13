docker compose down
docker compose --env-file .env.prod build
docker compose --env-file .env.prod up -d
