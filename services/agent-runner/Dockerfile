FROM node:22-bookworm

RUN apt-get update && apt-get install -y \
    git \
    ripgrep \
    fd-find \
    jq \
    curl \
    bash \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

RUN npm install -g opencode-ai

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt --break-system-packages

COPY . .
RUN mkdir -p ~/.config/opencode && \
    mv opencode-config.json ~/.config/opencode/config.json

CMD ["python3", "runner.py"]