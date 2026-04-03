#!/bin/sh

set -e
set -u

usage() {
    echo "Usage: $0 <repo-url> [branch]" >&2
    echo "  repo-url  - git repository URL (https or ssh)" >&2
    echo "  branch    - branch to analyse (default: main)" >&2
    echo "" >&2
    echo "Data is stored under .repos/<repo-name>/:" >&2
    echo "  git/          - bare git clone" >&2
    echo "  cloc/         - per-commit cloc JSON files" >&2
    echo "  cloc_summary.csv / charts/  - combine.py outputs" >&2
    exit 1
}

if [ $# -lt 1 ] || [ $# -gt 2 ]; then
    usage
fi

REPO_URL="$1"
BRANCH="${2:-main}"
SCRIPT_DIR=$(dirname "$(realpath "$0")")

# Derive a stable directory name from the repo URL
REPO_NAME=$(basename "${REPO_URL}" .git)
CACHE_DIR="${PWD}/.repos"
REPO_DIR="${CACHE_DIR}/${REPO_NAME}"
REPO_PATH="${REPO_DIR}/git"
CLOC_DIR="${REPO_DIR}/cloc"

mkdir -p "${REPO_DIR}" "${CLOC_DIR}"

if [ -f "${REPO_PATH}/HEAD" ]; then
    echo "Fetching updates for ${REPO_NAME} ..."
    git -C "${REPO_PATH}" fetch origin "${BRANCH}"
else
    echo "Cloning ${REPO_URL} into ${REPO_PATH} ..."
    git clone --bare --single-branch --branch "${BRANCH}" "${REPO_URL}" "${REPO_PATH}"
fi

cd "${REPO_PATH}"
TOTAL=$(git rev-list --count "${BRANCH}")
EXISTING=$(git log --format="%H" "${BRANCH}" | while read -r C; do
    [ -f "${CLOC_DIR}/${C}.json" ] && echo "${C}"
done | wc -l)
NEW=$((TOTAL - EXISTING))
echo "Total commits: ${TOTAL}, already processed: ${EXISTING}, new: ${NEW}"

git log --format="%H" "${BRANCH}" |  while read -r COMMIT; do
    if [ ! -f "${CLOC_DIR}/${COMMIT}.json" ]; then
        echo "${COMMIT}"
    fi
done | xargs -r -L1 -P 10 "${SCRIPT_DIR}/cloc-commit.sh" "${REPO_PATH}" "${CLOC_DIR}"
