#!/bin/bash

# ===================== CONFIG =====================
REPO_DIR="/home/cyamsys/Desktop/attendance/attendance_deploy"      # path to your git repo
BRANCH="main"                             # branch to push
REMOTE="origin"                           # remote name
COMMIT_PREFIX="Auto update"               # prefix for commit message
LOG_FILE="/home/cyamsys/Desktop/attendance/auto_git_push.log"
# ====================================================

cd "$REPO_DIR" || { echo "$(date): Repo dir not found: $REPO_DIR" >> "$LOG_FILE"; exit 1; }

TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Check if there are any changes (staged, unstaged, or untracked)
if [[ -z $(git status --porcelain) ]]; then
    echo "$TIMESTAMP: No changes to commit." >> "$LOG_FILE"
    exit 0
fi

git add -A
git commit -m "$COMMIT_PREFIX - $TIMESTAMP"

if git push "$REMOTE" "$BRANCH" >> "$LOG_FILE" 2>&1; then
    echo "$TIMESTAMP: Push successful." >> "$LOG_FILE"
else
    echo "$TIMESTAMP: Push FAILED." >> "$LOG_FILE"
fi