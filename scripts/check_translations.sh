#!/usr/bin/env bash
# Fails if a .po catalogue is stale (a translatable string was added or changed
# without running makemessages) or has untranslated/fuzzy entries.
# Non-destructive: the catalogues are restored to exactly what they were.
set -euo pipefail

backup=$(mktemp -d)
trap 'cp -R "$backup/locale/." locale/; rm -rf "$backup"' EXIT
cp -R locale "$backup/locale"

uv run python manage.py makemessages -l sq --ignore='.venv/*' --no-location --no-obsolete >/dev/null

status=0
if ! diff -ru -I '^"POT-Creation-Date' "$backup/locale" locale >&2; then
  echo "Catalogues are out of date: run the makemessages command in CLAUDE.md and translate." >&2
  status=1
fi

for po in locale/*/LC_MESSAGES/django.po; do
  stats=$(msgfmt --check --statistics -o /dev/null "$po" 2>&1)
  echo "$po: $stats"
  if grep -Eq 'untranslated|fuzzy' <<<"$stats"; then status=1; fi
done
exit $status
