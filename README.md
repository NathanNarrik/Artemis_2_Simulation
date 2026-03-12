#!/usr/bin/env bash
set -u

if [ $# -ne 2 ]; then
  echo "Usage: $0 <sim_root> <output_file>" >&2
  exit 2
fi

SIM_ROOT="$1"
OUTFILE="$2"

cd "$SIM_ROOT" || {
  echo "ERROR: Could not cd to sim root: $SIM_ROOT" >&2
  exit 1
}

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

all_tags="$tmpdir/all_tags.txt"
unique_tags="$tmpdir/unique_tags.txt"
interim_tags="$tmpdir/interim_tags.txt"
sorted_interims="$tmpdir/sorted_interims.txt"
work_list="$tmpdir/work.txt"
load_list="$tmpdir/load.txt"
common="$tmpdir/common.txt"
added="$tmpdir/added.txt"
removed="$tmpdir/removed.txt"
unchanged="$tmpdir/unchanged.txt"

awk_escape() {
  local s="$1"
  s="${s//\\/\\\\}"
  s="${s//\"/\\\"}"
  printf '%s' "$s"
}

is_interim_tag() {
  case "$1" in
    *_interim_[0-9][0-9]_[0-9][0-9]_[0-9][0-9][0-9][0-9]) return 0 ;;
    *) return 1 ;;
  esac
}

get_tag_prefix() {
  local tag="$1"
  echo "${tag%_interim_*}"
}

get_today_interim_tag() {
  local prefix="$1"
  local today
  today="$(date +%m_%d_%Y)"
  echo "${prefix}_interim_${today}"
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

# Only include RCS-controlled files
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

: > "$all_tags"

while IFS= read -r f; do
  extract_tags_from_file "$f" >> "$all_tags"
done < <(list_working_files)

LC_ALL=C sort -u "$all_tags" > "$unique_tags"

: > "$interim_tags"
while IFS= read -r tag; do
  if is_interim_tag "$tag"; then
    echo "$tag" >> "$interim_tags"
  fi
done < "$unique_tags"

if [ ! -s "$interim_tags" ]; then
  echo "ERROR: No interim tags found." >&2
  exit 1
fi

awk -F_ '
{
  yyyy=$NF
  dd=$(NF-1)
  mm=$(NF-2)
  print yyyy mm dd, $0
}
' "$interim_tags" | LC_ALL=C sort > "$sorted_interims"

LATEST_LOAD="$(tail -1 "$sorted_interims" | awk '{print $2}')"

if [ -z "${LATEST_LOAD:-}" ]; then
  echo "ERROR: Could not determine the most recent interim tag." >&2
  exit 1
fi

SIM_PREFIX="$(get_tag_prefix "$LATEST_LOAD")"
NEW_LOAD="$(get_today_interim_tag "$SIM_PREFIX")"

list_working_files > "$work_list"
list_files_in_load "$LATEST_LOAD" "$load_list"

comm -12 "$work_list" "$load_list" > "$common"
comm -23 "$work_list" "$load_list" > "$added"
comm -13 "$work_list" "$load_list" > "$removed"

: > "$unchanged"

{
echo "============================================================"
echo "CHANGE LOG: INTERIM TO NEW INTERIM GENERATED TODAY"
echo "============================================================"
echo "Baseline interim: $LATEST_LOAD"
echo "New interim name: $NEW_LOAD"
echo "Sim root:         $SIM_ROOT"
echo "Generated:        $(date)"
echo
echo "This report compares the most recent existing interim tag"
echo "to the current RCS HEAD state, treating the current state"
echo "as the new interim being generated today."
echo

echo "SUMMARY COUNTS"
echo "------------------------------------------------------------"
echo "RCS-controlled files now      : $(wc -l < "$work_list" | tr -d ' ')"
echo "Files in baseline interim     : $(wc -l < "$load_list" | tr -d ' ')"
echo "Added in new interim          : $(wc -l < "$added" | tr -d ' ')"
echo "Removed since baseline        : $(wc -l < "$removed" | tr -d ' ')"
echo

echo "============================================================"
echo "FILES ADDED (present now, not in $LATEST_LOAD)"
echo "============================================================"
cat "$added"
echo

echo "============================================================"
echo "FILES REMOVED (present in $LATEST_LOAD, not present now)"
echo "============================================================"
cat "$removed"
echo

echo "============================================================"
echo "PER-FILE LOG ENTRIES (from $LATEST_LOAD to $NEW_LOAD)"
echo "============================================================"

while IFS= read -r f; do
  load_rev="$(get_rev_for_tag "$f" "$LATEST_LOAD")"
  head_rev="$(get_head_rev "$f")"

  if [ -z "${load_rev:-}" ] || [ -z "${head_rev:-}" ]; then
    echo "------------------------------------------------------------"
    echo "FILE: $f"
    echo "WARN: could not resolve revisions (baseline='$load_rev', head='$head_rev')"
    echo
    continue
  fi

  if [ "$load_rev" = "$head_rev" ]; then
    echo "$f" >> "$unchanged"
    continue
  fi

  echo "------------------------------------------------------------"
  echo "FILE: $f"
  echo "Baseline revision ($LATEST_LOAD): $load_rev"
  echo "New interim revision ($NEW_LOAD): $head_rev"
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
echo "FILES UNCHANGED (same revision in $LATEST_LOAD and $NEW_LOAD)"
echo "============================================================"
cat "$unchanged"

} > "$OUTFILE"
