#!/bin/sh

# set -x
set -e
set -u

REPO_PATH=${1}
CLOC_DIR=${2}
COMMIT=${3}

CLOC_FILE=${CLOC_DIR}/${COMMIT}.json

cd ${REPO_PATH}
cloc --json --out=${CLOC_FILE} ${COMMIT}

AUTHOR_DATE=$(git log -1 --format="%aI" ${COMMIT})
COMMIT_DATE=$(git log -1 --format="%cI" ${COMMIT})

jq --arg author_date "${AUTHOR_DATE}" --arg commit_date "${COMMIT_DATE}" \
  '. + { commit: {author_date: $author_date, commit_date: $commit_date} }' \
  ${CLOC_FILE} > ${CLOC_FILE}.tmp

mv -f ${CLOC_FILE}.tmp ${CLOC_FILE}
