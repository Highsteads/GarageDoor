#! /usr/bin/env bash
# Filename:    run.sh
# Description: Single gate for the GarageDoor contract tests. Exit 0 only if
#              everything passes.
# Author:      CliveS & Claude Opus 5
# Date:        02-08-2026
# Version:     1.0
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE/.."

echo "== pytest (door state, alarm, light, HomeKit mirror) =="
python3 -m pytest tests -q

echo
echo "== python syntax =="
python3 -m py_compile "GarageDoor.indigoPlugin/Contents/Server Plugin/plugin.py" \
                      "GarageDoor.indigoPlugin/Contents/Server Plugin/garage_logic.py"
echo "  ok"

echo
echo "== XML well-formed =="
for f in "GarageDoor.indigoPlugin/Contents/Server Plugin"/*.xml "GarageDoor.indigoPlugin/Contents/Info.plist"; do
    python3 -c "import xml.dom.minidom,sys; xml.dom.minidom.parse(sys.argv[1])" "$f"
    echo "  ok  $(basename "$f")"
done

echo
echo "== lint (errors only) =="
python3 -m ruff check . && echo "  ok"

echo
echo "All GarageDoor contract tests passed."
