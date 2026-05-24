#!/usr/bin/env bash
# Inject `— sources: all, gemini` into a single ARGUMENTS-style string when
# the caller did not already specify a `--/---/— sources:` directive.
#
# This helper expects exactly one argument: the full ARGUMENTS string. Callers
# are responsible for quoting it. Passing multiple positional arguments is
# rejected to avoid silently collapsing whitespace via `$*`.

set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "ERROR: expected exactly 1 argument (the full ARGUMENTS string), got $#." >&2
  echo "Usage: inject_default_sources.sh \"<arguments string>\"" >&2
  exit 2
fi

input="$1"

if [[ "$input" =~ (^|[[:space:]])(--|---|—)[[:space:]]*sources[[:space:]]*: ]]; then
  printf '%s\n' "$input"
else
  printf '%s — sources: all, gemini\n' "$input"
fi
