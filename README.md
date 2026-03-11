#!/usr/bin/env bash
set -u

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

all_tags="$tmpdir/all_tags.txt"
unique_tags="$tmpdir/unique_tags.txt"
interim_tags="$tmpdir/interim_tags.txt"
sorted_interims="$tmpdir/sorted_interims.txt"
old_list="$tmpdir/old.txt"
new_list="$tmpdir/new.txt"
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

echo "Collecting interim tags..."

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

NEW_LOAD="$(tail -1 "$sorted_interims" | awk '{print $2}')"
PREV_LOAD="$(tail -2 "$sorted_interims" | head -1 | awk '{print $2}')"

if [ -z "${NEW_LOAD:-}" ] || [ -z "${PREV_LOAD:-}" ]; then
  echo "ERROR: Could not determine the newest and previous interim tags." >&2
  exit 1
fi

echo "Previous interim: $PREV_LOAD"
echo "Newest interim:   $NEW_LOAD"

TODAY="$(date +%m_%d_%Y)"
OUTFILE="change_log_${NEW_LOAD}_${TODAY}.txt"

list_files_in_load "$PREV_LOAD" "$old_list"
list_files_in_load "$NEW_LOAD" "$new_list"

comm -12 "$old_list" "$new_list" > "$common"
comm -13 "$old_list" "$new_list" > "$added"
comm -23 "$old_list" "$new_list" > "$removed"

: > "$unchanged"

{
echo "============================================================"
echo "CHANGE LOG: PREVIOUS INTERIM TO NEWEST INTERIM"
echo "============================================================"
echo "Previous interim: $PREV_LOAD"
echo "Newest interim:   $NEW_LOAD"
echo "Run directory:    $(pwd)"
echo "Generated:        $(date)"
echo
echo "This report compares the previous interim tag to the most"
echo "recent interim tag across all RCS-controlled files."
echo

echo "SUMMARY COUNTS"
echo "------------------------------------------------------------"
echo "Files in previous interim     : $(wc -l < "$old_list" | tr -d ' ')"
echo "Files in newest interim       : $(wc -l < "$new_list" | tr -d ' ')"
echo "Added in newest interim       : $(wc -l < "$added" | tr -d ' ')"
echo "Removed from previous interim : $(wc -l < "$removed" | tr -d ' ')"
echo

echo "============================================================"
echo "FILES ADDED (present in $NEW_LOAD, not in $PREV_LOAD)"
echo "============================================================"
cat "$added"
echo

echo "============================================================"
echo "FILES REMOVED (present in $PREV_LOAD, not in $NEW_LOAD)"
echo "============================================================"
cat "$removed"
echo

echo "============================================================"
echo "PER-FILE LOG ENTRIES (from $PREV_LOAD to $NEW_LOAD)"
echo "============================================================"

while IFS= read -r f; do
  prev_rev="$(get_rev_for_tag "$f" "$PREV_LOAD")"
  new_rev="$(get_rev_for_tag "$f" "$NEW_LOAD")"

  if [ -z "${prev_rev:-}" ] || [ -z "${new_rev:-}" ]; then
    echo "------------------------------------------------------------"
    echo "FILE: $f"
    echo "WARN: could not resolve revisions (prev='$prev_rev', new='$new_rev')"
    echo
    continue
  fi

  if [ "$prev_rev" = "$new_rev" ]; then
    echo "$f" >> "$unchanged"
    continue
  fi

  echo "------------------------------------------------------------"
  echo "FILE: $f"
  echo "Previous revision ($PREV_LOAD): $prev_rev"
  echo "Newest revision   ($NEW_LOAD):  $new_rev"
  echo

  if rev_lt "$prev_rev" "$new_rev"; then
    emit_rlog_between "$f" "$prev_rev" "$new_rev" || echo "WARN: rlog extraction failed for $f"
  else
    echo "WARN: revision order is not increasing ($prev_rev -> $new_rev)"
    echo "This may indicate a branch or unusual tag placement."
    echo "Inspect manually with: rlog $f"
    echo
  fi
done < "$common"

echo "============================================================"
echo "FILES UNCHANGED (same revision in both interims)"
echo "============================================================"
cat "$unchanged"

} > "$OUTFILE"

echo "Wrote: $OUTFILE"
