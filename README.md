#!/usr/bin/env bash
set -u

# Generalized RCS changelog tool
# Finds the latest tag matching:
#   <anything>_interim_MM_DD_YYYY
# Then compares that load's tagged revision to the current HEAD revision
# of each RCS-controlled file.

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

all_tags="$tmpdir/all_tags.txt"
unique_tags="$tmpdir/unique_tags.txt"
work_list="$tmpdir/work.txt"
load_list="$tmpdir/load.txt"
added="$tmpdir/added.txt"
removed="$tmpdir/removed.txt"
common="$tmpdir/common.txt"
unchanged="$tmpdir/unchanged.txt"

awk_escape() {
  local s="$1"
  s="${s//\\/\\\\}"
  s="${s//\"/\\\"}"
  printf '%s' "$s"
}

# Match any tag ending in _interim_MM_DD_YYYY
is_interim_tag() {
  case "$1" in
    *_interim_[0-9][0-9]_[0-9][0-9]_[0-9][0-9][0-9][0-9]) return 0 ;;
    *) return 1 ;;
  esac
}

# Convert <prefix>_interim_MM_DD_YYYY -> YYYYMMDD
tag_to_key() {
  local tag="$1"
  local rest mm dd yyyy
  rest="${tag##*_interim_}"
  IFS=_ read -r mm dd yyyy <<< "$rest"
  printf "%s%s%s" "$yyyy" "$mm" "$dd"
}

# Returns 0 if A < B, else 1
rev_lt() {
  local A="$1"
  local B="$2"

  local IFS='.'
  local -a a b
  read -ra a <<< "$A"
  read -ra b <<< "$B"

  local len=${#a[@]}
  if [ ${#b[@]} -gt "$len" ]; then
    len=${#b[@]}
  fi

  local i ai bi
  for ((i=0; i<len; i++)); do
    ai="${a[i]:-0}"
    bi="${b[i]:-0}"

    if ((10#$ai < 10#$bi)); then
      return 0
    elif ((10#$ai > 10#$bi)); then
      return 1
    fi
  done

  return 1
}

# Only include files actually under RCS control
list_working_files() {
  find . -type f ! -path "*/RCS/*" |
  while IFS= read -r f; do
    if rlog "$f" >/dev/null 2>&1; then
      echo "$f"
    fi
  done | LC_ALL=C sort
}

list_files_in_load() {
  local load="$1"
  local outfile="$2"

  list_working_files |
  while IFS= read -r f; do
    if co -q -p -r"$load" "$f" > /dev/null 2>&1; then
      echo "$f"
    fi
  done | LC_ALL=C sort > "$outfile"
}

extract_tags_from_file() {
  local file="$1"

  rlog "$file" 2>/dev/null | awk '
    /symbolic names:/ { inblock=1; next }
    /keyword substitution:/ { inblock=0 }
    inblock {
      if ($0 ~ /^[[:space:]]*$/) next
      sub(/^[[:space:]]*/, "", $0)
      if ($0 ~ /:/) {
        split($0, a, ":")
        if (a[1] != "") print a[1]
      }
    }
  '
}

get_rev_for_tag() {
  local file="$1"
  local tag="$2"
  local etag
  etag="$(awk_escape "$tag")"

  rlog -h "$file" 2>/dev/null | awk "
    BEGIN { tag=\"$etag\"; inblock=0 }
    /symbolic names:/ { inblock=1; next }
    /keyword substitution:/ { inblock=0 }
    inblock {
      if (\$0 ~ /^[[:space:]]*$/) next
      sub(/^[[:space:]]*/, \"\", \$0)
      if (\$0 ~ /:/) {
        split(\$0, a, \":\")
        name=a[1]
        rev=a[2]
        gsub(/[[:space:]]*/, \"\", rev)
        if (name == tag) {
          print rev
          exit
        }
      }
    }
  "
}

get_head_rev() {
  local file="$1"

  rlog -h "$file" 2>/dev/null | awk '
    /^head:/ {
      sub(/^head:[[:space:]]*/, "", $0)
      print $0
      exit
    }
  '
}

emit_rlog_between() {
  local file="$1"
  local revA="$2"
  local revB="$3"

  local efile erevA
  efile="$(awk_escape "$file")"
  erevA="$(awk_escape "$revA")"

  rlog -r"${revA}:${revB}" "$file" 2>/dev/null | awk "
    BEGIN { file=\"$efile\"; revA=\"$erevA\" }

    function trim(s){ gsub(/^[ \t]+|[ \t]+$/, \"\", s); return s }

    /^revision[ \t]+/ {
      if (rev != \"\" && rev != revA) {
        printf \"commit %s@%s\\n\", file, rev
        printf \"Author: %s\\n\", author
        printf \"Date:   %s\\n\\n\", date
        printf \"%s\\n\", msg
      }
      rev=\$2
      date=\"\"; author=\"\"; msg=\"\"
      in_log=0
      next
    }

    /^date:[ \t]+/ {
      line=\$0
      sub(/^date:[ \t]+/, \"\", line)
      split(line, parts, \";\")

      date=trim(parts[1])
      author=\"\"

      for (i=1; i<=length(parts); i++) {
        if (parts[i] ~ /author:/) {
          a=parts[i]
          sub(/.*author:[ \t]+/, \"\", a)
          author=trim(a)
        }
      }

      in_log=1
      next
    }

    /^----------------------------$/ { next }
    /^============================$/ { next }

    {
      if (in_log) {
        if (\$0 == \"\") msg = msg \"\\n\"
        else msg = msg \"    \" \$0 \"\\n\"
      }
    }

    END {
      if (rev != \"\" && rev != revA) {
        printf \"commit %s@%s\\n\", file, rev
        printf \"Author: %s\\n\", author
        printf \"Date:   %s\\n\\n\", date
        printf \"%s\\n\", msg
      }
    }
  "
}

echo "Finding latest interim load..."

: > "$all_tags"

while IFS= read -r f; do
  extract_tags_from_file "$f" >> "$all_tags"
done < <(list_working_files)

LC_ALL=C sort -u "$all_tags" > "$unique_tags"

LATEST_LOAD=""
LATEST_KEY=""

while IFS= read -r tag; do
  if is_interim_tag "$tag"; then
    key="$(tag_to_key "$tag")"
    if [ -z "$LATEST_KEY" ] || [ "$key" -gt "$LATEST_KEY" ]; then
      LATEST_KEY="$key"
      LATEST_LOAD="$tag"
    fi
  fi
done < "$unique_tags"

if [ -z "$LATEST_LOAD" ]; then
  echo "ERROR: No tags found matching *_interim_MM_DD_YYYY" >&2
  exit 1
fi

echo "Latest load detected: $LATEST_LOAD"

OUTFILE="change_log_${LATEST_LOAD}_to_current_head.txt"

list_working_files > "$work_list"
list_files_in_load "$LATEST_LOAD" "$load_list"

comm -12 "$work_list" "$load_list" > "$common"
comm -23 "$work_list" "$load_list" > "$added"
comm -13 "$work_list" "$load_list" > "$removed"

: > "$unchanged"

{
echo "============================================================"
echo "CHANGE LOG: LATEST LOAD TO CURRENT HEAD"
echo "============================================================"
echo "Latest load: $LATEST_LOAD"
echo "Run directory: $(pwd)"
echo "Generated: $(date)"
echo
echo "This report compares the most recent *_interim_MM_DD_YYYY"
echo "load tag to the current HEAD revision of each RCS-controlled file."
echo

echo "SUMMARY COUNTS"
echo "------------------------------------------------------------"
echo "RCS-controlled files now      : $(wc -l < "$work_list" | tr -d ' ')"
echo "Files in latest load          : $(wc -l < "$load_list" | tr -d ' ')"
echo "Added since latest load       : $(wc -l < "$added" | tr -d ' ')"
echo "Removed since latest load     : $(wc -l < "$removed" | tr -d ' ')"
echo

echo "============================================================"
echo "FILES ADDED (RCS-controlled now, not in $LATEST_LOAD)"
echo "============================================================"
cat "$added"
echo

echo "============================================================"
echo "FILES REMOVED (in $LATEST_LOAD, not present now)"
echo "============================================================"
cat "$removed"
echo

echo "============================================================"
echo "PER-FILE LOG ENTRIES (from $LATEST_LOAD to current HEAD)"
echo "============================================================"

while IFS= read -r f; do
  load_rev="$(get_rev_for_tag "$f" "$LATEST_LOAD")"
  head_rev="$(get_head_rev "$f")"

  if [ -z "${load_rev:-}" ] || [ -z "${head_rev:-}" ]; then
    echo "------------------------------------------------------------"
    echo "FILE: $f"
    echo "WARN: could not resolve revisions (load='$load_rev', head='$head_rev')"
    echo
    continue
  fi

  if [ "$load_rev" = "$head_rev" ]; then
    echo "$f" >> "$unchanged"
    continue
  fi

  echo "------------------------------------------------------------"
  echo "FILE: $f"
  echo "Load revision ($LATEST_LOAD): $load_rev"
  echo "Current head revision       : $head_rev"
  echo

  if rev_lt "$load_rev" "$head_rev"; then
    emit_rlog_between "$f" "$load_rev" "$head_rev" || echo "WARN: rlog extraction failed for $f"
  else
    echo "WARN: revision order is not increasing ($load_rev -> $head_rev)"
    echo "This may indicate a branch or unusual tag placement."
    echo "Inspect manually with: rlog $f"
    echo
  fi
done < "$common"

echo "============================================================"
echo "FILES UNCHANGED (load revision == current HEAD)"
echo "============================================================"
cat "$unchanged"

} > "$OUTFILE"

echo "Wrote: $OUTFILE"
