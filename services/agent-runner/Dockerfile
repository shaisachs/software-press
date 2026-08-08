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

ARG GIT_NAME
ARG GIT_EMAIL

RUN mkdir -p ~/.local/share/opencode && \
    mv opencode-auth.json ~/.local/share/opencode/auth.json && \
    mkdir -p ~/.config/opencode && \
    mv opencode-config.json ~/.config/opencode/config.json && \
    mkdir -p ~/.ssh && \
    chmod 700 ~/.ssh && \
    mv id_rsa ~/.ssh && \
    chmod 600 ~/.ssh/id_rsa && \
    ssh-keyscan -H github.com >> ~/.ssh/known_hosts && \
    git config --global user.name "$GIT_NAME" && \
    git config --global user.email "$GIT_EMAIL"

CMD ["python3", "runner.py"]