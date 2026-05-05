#!/bin/sh

set -e
set -u

usage() {
    echo "Usage: $0 <repo-url> [branch] [repo-name]" >&2
    echo "  repo-url   - git repository URL (https or ssh)" >&2
    echo "  branch     - branch to analyse (default: main)" >&2
    echo "  repo-name  - override directory name (default: derived from URL)" >&2
    echo "" >&2
    echo "Data is stored under .repos/<repo-name>/:" >&2
    echo "  git/          - bare git clone" >&2
    echo "  scc/          - per-commit scc JSON files" >&2
    echo "  scc_summary.csv / charts/  - combine.py outputs" >&2
    exit 1
}

if [ $# -lt 1 ] || [ $# -gt 3 ]; then
    usage
fi

REPO_URL="$1"
BRANCH="${2:-main}"
REPO_NAME="${3:-$(basename "${REPO_URL}" .git)}"

SCRIPT_DIR=$(dirname "$(realpath "$0")")

CACHE_DIR="${PWD}/.repos"
REPO_DIR="${CACHE_DIR}/${REPO_NAME}"
REPO_PATH="${REPO_DIR}/git"
SCC_DIR="${REPO_DIR}/scc"

mkdir -p "${REPO_DIR}" "${SCC_DIR}"

if [ -f "${REPO_PATH}/HEAD" ]; then
    echo "Fetching updates for ${REPO_NAME} ..."
    git -C "${REPO_PATH}" fetch origin "${BRANCH}"
    git -C "${REPO_PATH}" branch -f "${BRANCH}" FETCH_HEAD
else
    echo "Cloning ${REPO_URL} into ${REPO_PATH} ..."
    git clone --bare --single-branch --branch "${BRANCH}" "${REPO_URL}" "${REPO_PATH}"
fi

cd "${REPO_PATH}"
TOTAL=$(git rev-list --count "${BRANCH}")
EXISTING=$(git log --format="%H" "${BRANCH}" | while read -r C; do
    [ -f "${SCC_DIR}/${C}.json" ] && echo "${C}"
done | wc -l)
NEW=$((TOTAL - EXISTING))
echo "Total commits: ${TOTAL}, already processed: ${EXISTING}, new: ${NEW}"

COMMIT_LIST=$(mktemp)
trap 'rm -f "${COMMIT_LIST}"' EXIT

git log --format="%H" "${BRANCH}" | while read -r COMMIT; do
    if [ ! -f "${SCC_DIR}/${COMMIT}.json" ]; then
        echo "${COMMIT}"
    fi
done | sort -R > "${COMMIT_LIST}"

P="${P:-1}"
if [ -s "${COMMIT_LIST}" ]; then
    xargs -P "${P}" -L 1 "${SCRIPT_DIR}/scc-commit.sh" "${REPO_PATH}" "${SCC_DIR}" < "${COMMIT_LIST}"
fi
