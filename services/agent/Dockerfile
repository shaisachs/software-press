FROM node:22-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    ripgrep \
    fd-find \
    jq \
    curl \
    bash \
    ca-certificates \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL -o /usr/share/keyrings/githubcli-archive-keyring.gpg \
        https://cli.github.com/packages/githubcli-archive-keyring.gpg \
    && chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
        > /etc/apt/sources.list.d/github-cli.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends gh \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /etc/ssh \
    && ssh-keyscan -H github.com > /etc/ssh/github_known_hosts 2>/dev/null

RUN useradd --create-home --shell /bin/bash agent

RUN npm install -g opencode-ai

WORKDIR /app

ENV GH_PROTOCOL=ssh
ENV HOME=/home/agent

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt pytest --break-system-packages

COPY . .

RUN chown -R agent:agent /app

RUN mkdir -p /workspaces /artifacts && chown agent:agent /workspaces /artifacts

USER agent

RUN python3 -m pytest tests

ARG GIT_NAME
ARG GIT_EMAIL

RUN /bin/bash /app/bootstrap.sh "$GIT_NAME" "$GIT_EMAIL"

CMD ["python3", "-m", "app.runner"]
