#!/bin/sh

set -e
set -u

REPO_PATH="${1}"
SCC_DIR="${2}"
COMMIT="${3}"

OUT_FILE="${SCC_DIR}/${COMMIT}.json"
OUT_TMP="${OUT_FILE}.tmp"

# Skip if already done
if [ -f "${OUT_FILE}" ]; then
    exit 0
fi

# Worktree directory — unique per commit to allow parallel runs
WORKTREE_DIR="${SCC_DIR}/.worktree-${COMMIT}"

# Clean up worktree and temp files on any exit
cleanup() {
    if [ -d "${WORKTREE_DIR}" ]; then
        git -C "${REPO_PATH}" worktree remove --force "${WORKTREE_DIR}" || rm -rf "${WORKTREE_DIR}"
    fi
    rm -f "${OUT_TMP}" "${OUT_TMP}.enriched"
}
trap cleanup EXIT

# Create a detached worktree for this commit
git -C "${REPO_PATH}" worktree prune
git -C "${REPO_PATH}" worktree add --detach "${WORKTREE_DIR}" "${COMMIT}"

EXCLUDE_DIR=""

if [ -f "${REPO_PATH}/../exclude-dir.txt" ]; then
    # Join non-empty lines into a comma-separated list
    EXCLUDE_DIR=$(grep -v '^$' "${REPO_PATH}/../exclude-dir.txt" | paste -sd ',' -)
fi

# Run scc on the worktree
if [ -n "${EXCLUDE_DIR}" ]; then
    scc --format json --exclude-dir "${EXCLUDE_DIR}" "${WORKTREE_DIR}" > "${OUT_TMP}"
else
    scc --format json "${WORKTREE_DIR}" > "${OUT_TMP}"
fi

# Get git metadata
AUTHOR_DATE=$(git -C "${REPO_PATH}" log -1 --format="%aI" "${COMMIT}")
COMMIT_DATE=$(git -C "${REPO_PATH}" log -1 --format="%cI" "${COMMIT}")

# Wrap scc array output with commit metadata
jq --arg author_date "${AUTHOR_DATE}" \
   --arg commit_date "${COMMIT_DATE}" \
   --arg commit_sha "${COMMIT}" \
   '{ languages: ., commit: { sha: $commit_sha, author_date: $author_date, commit_date: $commit_date } }' \
   "${OUT_TMP}" > "${OUT_TMP}.enriched"

# Atomic move into final location
mv -f "${OUT_TMP}.enriched" "${OUT_FILE}"
