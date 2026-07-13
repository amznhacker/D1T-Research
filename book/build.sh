#!/usr/bin/env bash
# Build the book, stamping the current repository revision into the colophon.
# Usage: ./build.sh   (from book/, or anywhere — it cds itself)
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

REV=$(git describe --tags --always --dirty 2>/dev/null || echo "unversioned")
printf '\\newcommand{\\repocommit}{%s}\n' "$REV" > gitrev.tex

latexmk -pdf -interaction=nonstopmode main.tex
echo ""
echo "Built main.pdf from revision: $REV"
