#!/bin/sh

# set -x
set -e
set -u

REPO_PATH="${1}"
CLOC_DIR="${2}"
COMMIT="${3}"

CLOC_FILE="${CLOC_DIR}/${COMMIT}.json"
CLOC_TMP="${CLOC_FILE}.tmp"

# Clean up temp file on any failure so a corrupt file never remains on disk
trap 'rm -f "${CLOC_TMP}"' EXIT

cd "${REPO_PATH}"

# Write cloc output to temp file — never directly to the final location
cloc --json --out="${CLOC_TMP}" "${COMMIT}"

AUTHOR_DATE=$(git log -1 --format="%aI" "${COMMIT}")
COMMIT_DATE=$(git log -1 --format="%cI" "${COMMIT}")

# Enrich with git metadata; jq validates JSON as a side effect
jq --arg author_date "${AUTHOR_DATE}" --arg commit_date "${COMMIT_DATE}" \
  '. + { commit: {author_date: $author_date, commit_date: $commit_date} }' \
  "${CLOC_TMP}" > "${CLOC_TMP}.enriched"

# Atomic move into final location — only reached if all steps succeeded
mv -f "${CLOC_TMP}.enriched" "${CLOC_FILE}"
rm -f "${CLOC_TMP}"
trap - EXIT
