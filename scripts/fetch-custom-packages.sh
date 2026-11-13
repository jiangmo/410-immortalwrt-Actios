#!/usr/bin/env bash
set -euo pipefail
test -f include/toplevel.mk
test -d package
lock_file=${1:?Usage: fetch-custom-packages.sh LOCK_FILE}
: > custom-package-revisions.txt
while read -r name url revision extra; do
  [[ -z "$name" || "$name" == \#* ]] && continue
  [[ "$name" =~ ^[a-zA-Z0-9][a-zA-Z0-9._+-]*$ ]]
  [[ "$revision" =~ ^[0-9a-f]{40}$ ]]
  test -z "$extra"
  destination="package/custom/$name"
  if [ ! -e "$destination" ]; then
    mkdir -p "$destination"
    git -C "$destination" init
    git -C "$destination" remote add origin "$url"
    git -C "$destination" fetch --depth 1 origin "$revision"
    git -C "$destination" checkout --detach FETCH_HEAD
  fi
  test "$(git -C "$destination" rev-parse HEAD)" = "$revision"
  printf '%s %s %s\n' "$destination" "$revision" "$url" >> custom-package-revisions.txt
done < "$lock_file"
cat custom-package-revisions.txt
