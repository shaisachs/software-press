#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
    echo "usage: $0 <git-name> <git-email>" >&2
    exit 1
fi

GIT_NAME="$1"
GIT_EMAIL="$2"

cd "$(dirname "${BASH_SOURCE[0]}")"

mkdir -p "$HOME/.local/share/opencode"
mv opencode-auth.json "$HOME/.local/share/opencode/auth.json"

mkdir -p "$HOME/.config/opencode"
mv opencode-config.json "$HOME/.config/opencode/config.json"

mkdir -p "$HOME/.ssh"
chmod 700 "$HOME/.ssh"

mv id_rsa "$HOME/.ssh/id_rsa"
chmod 600 "$HOME/.ssh/id_rsa"

if [[ -f /etc/ssh/github_known_hosts ]]; then
    cat /etc/ssh/github_known_hosts >> "$HOME/.ssh/known_hosts"
else
    ssh-keyscan -H github.com >> "$HOME/.ssh/known_hosts"
fi
chmod 600 "$HOME/.ssh/known_hosts"

git config --global user.name "$GIT_NAME"
git config --global user.email "$GIT_EMAIL"
git config --global url."git@github.com:".insteadOf "https://github.com/"
git config --global core.sshCommand "ssh -i $HOME/.ssh/id_rsa -o IdentitiesOnly=yes"

mkdir -p "$HOME/.git_templates/hooks"
mv prepare-commit-msg "$HOME/.git_templates/hooks/"
chmod +x "$HOME/.git_templates/hooks/prepare-commit-msg"
git config --global core.hooksPath "$HOME/.git_templates/hooks"
