#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="${ROOT_DIR}/skills/"
DST="${ROOT_DIR}/.trae/skills/"

DELETE_FLAG=""
if [[ "${1:-}" == "--delete" ]]; then
  # Mirror mode: delete files in DST that no longer exist in SRC.
  # Use with care; it can remove manually added skills under .trae/skills/.
  DELETE_FLAG="--delete"
elif [[ "${1:-}" != "" ]]; then
  echo "Usage: $(basename "$0") [--delete]" >&2
  exit 2
fi

mkdir -p "${DST}"

rsync -a ${DELETE_FLAG} --exclude '.DS_Store' "${SRC}" "${DST}"

echo "Synced: ${SRC} -> ${DST}"
if [[ -n "${DELETE_FLAG}" ]]; then
  echo "Mode: mirror (--delete)"
else
  echo "Mode: overwrite (no delete)"
fi

