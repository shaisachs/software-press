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
    && curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
        | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg \
    && chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
        > /etc/apt/sources.list.d/github-cli.list \
    && apt-get update \
    && apt-get install -y gh \
    && rm -rf /var/lib/apt/lists/*

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

# TODO: refactor into a bootstrap.sh; pull ssh-keyscan into an early layer so it's cached
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
    git config --global user.email "$GIT_EMAIL" && \
    git config --global url."git@github.com:".insteadOf "https://github.com/" && \
    git config --global core.sshCommand "ssh -i ~/.ssh/id_rsa -o IdentitiesOnly=yes" && \
    mkdir -p ~/.git_templates/hooks && \
    mv prepare-commit-msg ~/.git_templates/hooks/ && \
    chmod +x ~/.git_templates/hooks/prepare-commit-msg && \
    git config --global core.hooksPath ~/.git_templates/hooks

CMD ["python3", "-m", "app.runner"]
