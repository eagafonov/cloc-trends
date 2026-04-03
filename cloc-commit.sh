#!/bin/sh

# set -x
set -e
set -u

REPO_PATH="${1}"
CLOC_DIR="${2}"
COMMIT="${3}"

CLOC_FILE="${CLOC_DIR}/${COMMIT}.json"
CLOC_TMP="${CLOC_FILE}.tmp"
CLOC_STDERR="${CLOC_TMP}.stderr"

CLOC_TIMEOUT="${CLOC_TIMEOUT:-10}"

# Clean up temp files on any failure so corrupt data never remains on disk
trap 'rm -f "${CLOC_TMP}" "${CLOC_TMP}.enriched" "${CLOC_STDERR}"' EXIT

cd "${REPO_PATH}"

# Write cloc output to temp file — never directly to the final location
# Capture stderr: cloc writes timeout warnings there (not to --ignored)
cloc --json --out="${CLOC_TMP}" --timeout "${CLOC_TIMEOUT}" "${COMMIT}" 2>"${CLOC_STDERR}"

# Fail fast if cloc timed out on any files
# cloc's print_errors outputs "Line count, exceeded timeout:  <file>" to stderr
if grep -q "Line count, exceeded timeout" "${CLOC_STDERR}"; then
    echo "ERROR: cloc timed out on files for commit ${COMMIT}:" >&2
    grep "Line count, exceeded timeout" "${CLOC_STDERR}" >&2
    exit 1
fi

AUTHOR_DATE=$(git log -1 --format="%aI" "${COMMIT}")
COMMIT_DATE=$(git log -1 --format="%cI" "${COMMIT}")

# Enrich with git metadata; jq validates JSON as a side effect
jq --arg author_date "${AUTHOR_DATE}" --arg commit_date "${COMMIT_DATE}" \
  '. + { commit: {author_date: $author_date, commit_date: $commit_date} }' \
  "${CLOC_TMP}" > "${CLOC_TMP}.enriched"

# Atomic move into final location — only reached if all steps succeeded
mv -f "${CLOC_TMP}.enriched" "${CLOC_FILE}"
rm -f "${CLOC_TMP}" "${CLOC_STDERR}"
trap - EXIT
