#!/bin/bash

# Simple shell wrapper for the cleanup script
# Makes it easy to run common cleanup scenarios

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/cleanup_generated_files.py"

echo "🧹 Generated Files Cleanup"
echo "========================="

# Check if Python script exists
if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "❌ Error: cleanup_generated_files.py not found at $PYTHON_SCRIPT"
    exit 1
fi

# Parse command line arguments
case "${1:-}" in
    "dry-run"|"--dry-run"|"-n")
        echo "🔍 Running in DRY RUN mode (no files will be deleted)"
        python "$PYTHON_SCRIPT" --dry-run
        ;;
    "all"|"--all"|"")
        echo "🗑️  Deleting ALL generated files"
        python "$PYTHON_SCRIPT"
        ;;
    "today"|"--today")
        TODAY=$(date +%Y/%m/%d)
        echo "🗑️  Deleting generated files from today ($TODAY)"
        python "$PYTHON_SCRIPT" --prefix "generated/$TODAY"
        ;;
    "test"|"--test")
        echo "🗑️  Deleting test generated files"
        python "$PYTHON_SCRIPT" --prefix "test-generated/"
        ;;
    "help"|"--help"|"-h")
        echo "Usage: $0 [COMMAND]"
        echo ""
        echo "Commands:"
        echo "  dry-run    List files that would be deleted (no actual deletion)"
        echo "  all        Delete all generated files (default)"
        echo "  today      Delete only today's generated files"
        echo "  test       Delete test generated files"
        echo "  help       Show this help"
        echo ""
        echo "Examples:"
        echo "  $0 dry-run     # See what would be deleted"
        echo "  $0             # Delete all generated files"
        echo "  $0 today       # Delete only today's files"
        echo "  $0 test        # Delete test files"
        ;;
    *)
        echo "❌ Unknown command: $1"
        echo "Run '$0 help' for usage information"
        exit 1
        ;;
esac