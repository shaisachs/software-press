#!/usr/bin/env sh

set -e

export OLLAMA_HOST=http://ollama:11434

echo "Waiting for Ollama..."

until ollama list >/dev/null 2>&1
do
  sleep 2
done

MODEL="${OLLAMA_MODEL:-llama3.1:8b}"

if ollama list | grep -q "$MODEL"; then
  echo "Model already installed: $MODEL"
else
  echo "Pulling model: $MODEL"
  ollama pull "$MODEL"
fi

echo "Bootstrap complete."