#!/bin/bash
# Build Tailwind CSS
set -euo pipefail

INPUT="./static/css/input.css"
OUTPUT="./static/css/output.css"
WATCH=0
MINIFY=0

usage() {
    cat <<EOF
Usage: ${0##*/} [options]

Options:
  -i, --input <file>   Input CSS file (default: ${INPUT})
  -o, --output <file>  Output CSS file (default: ${OUTPUT})
  -w, --watch          Watch for changes and rebuild automatically
  -m, --minify         Minify the output CSS
  -h, --help           Show this help message and exit
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -i|--input)
            [[ $# -ge 2 ]] || { echo "Error: $1 requires a value" >&2; exit 1; }
            INPUT="$2"
            shift 2
            ;;
        -o|--output)
            [[ $# -ge 2 ]] || { echo "Error: $1 requires a value" >&2; exit 1; }
            OUTPUT="$2"
            shift 2
            ;;
        -w|--watch)
            WATCH=1
            shift
            ;;
        -m|--minify)
            MINIFY=1
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Error: unknown option '$1'" >&2
            usage >&2
            exit 1
            ;;
    esac
done

if [[ ! -f "$INPUT" ]]; then
    echo "Error: input file '$INPUT' not found" >&2
    exit 1
fi

ARGS=(-i "$INPUT" -o "$OUTPUT")
[[ $WATCH -eq 1 ]] && ARGS+=(--watch)
[[ $MINIFY -eq 1 ]] && ARGS+=(--minify)

bun run tailwindcss "${ARGS[@]}"