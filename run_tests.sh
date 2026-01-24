#!/bin/bash
# run_tests.sh
# Shell script to run the EasyMesh Batch Exporter test suite inside Blender
#
# Usage:
#   ./run_tests.sh                    # Run all tests
#   ./run_tests.sh tests/test_attachment_points.py  # Run specific test file
#   ./run_tests.sh -v                 # Run with verbose output
#   ./run_tests.sh -m "not slow"      # Skip slow tests
#   ./run_tests.sh -m "not memory"    # Skip memory-intensive tests
#   ./run_tests.sh -k test_fbx        # Run only tests matching pattern

set -e  # Exit on error

# Colours for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Colour

echo -e "${GREEN}EasyMesh Batch Exporter Test Suite${NC}"
echo "======================================"
echo ""

# Find Blender executable
find_blender() {
    # Check if BLENDER_PATH environment variable is set
    if [ -n "$BLENDER_PATH" ]; then
        if [ -x "$BLENDER_PATH" ]; then
            echo "$BLENDER_PATH"
            return 0
        else
            echo -e "${RED}Error: BLENDER_PATH is set but not executable: $BLENDER_PATH${NC}" >&2
            return 1
        fi
    fi

    # macOS - check standard application locations
    if [ "$(uname)" == "Darwin" ]; then
        # Check common macOS locations
        local mac_paths=(
            "/Applications/Blender.app/Contents/MacOS/Blender"
            "$HOME/Applications/Blender.app/Contents/MacOS/Blender"
        )
        for path in "${mac_paths[@]}"; do
            if [ -x "$path" ]; then
                echo "$path"
                return 0
            fi
        done
    fi

    # Linux/Windows (WSL) - check if blender is in PATH
    if command -v blender &> /dev/null; then
        echo "blender"
        return 0
    fi

    # Linux - check common locations
    local linux_paths=(
        "/usr/bin/blender"
        "/usr/local/bin/blender"
        "/snap/bin/blender"
        "$HOME/blender/blender"
    )
    for path in "${linux_paths[@]}"; do
        if [ -x "$path" ]; then
            echo "$path"
            return 0
        fi
    done

    return 1
}

# Find Blender
BLENDER_EXEC=$(find_blender)
if [ -z "$BLENDER_EXEC" ]; then
    echo -e "${RED}Error: Could not find Blender executable${NC}"
    echo ""
    echo "Please either:"
    echo "  1. Install Blender to a standard location"
    echo "  2. Add Blender to your PATH"
    echo "  3. Set BLENDER_PATH environment variable:"
    echo "     export BLENDER_PATH=/path/to/blender"
    echo ""
    exit 1
fi

echo -e "${GREEN}Using Blender: ${BLENDER_EXEC}${NC}"

# Get Blender's Python path for dependency checks
# Filter out Blender startup messages and get only the Python path
BLENDER_PYTHON=$("$BLENDER_EXEC" --background --python-expr "import sys; print('PYTHON_PATH:' + sys.executable)" 2>/dev/null | grep "PYTHON_PATH:" | sed 's/PYTHON_PATH://')
echo -e "Blender Python: ${BLENDER_PYTHON}"
echo ""

# Check if pytest is installed in Blender Python
if ! "$BLENDER_EXEC" --background --python-expr "import pytest" 2>/dev/null; then
    echo -e "${YELLOW}Warning: pytest not installed in Blender Python${NC}"
    echo "Installing test dependencies..."
    echo ""

    # Try to install using Blender's Python
    "$BLENDER_EXEC" --background --python-expr "
import subprocess
import sys
import ensurepip

# Ensure pip is available
ensurepip.bootstrap()

# Install test requirements
subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'test-requirements.txt'])
"
    echo ""
fi

# Build pytest arguments
# Disable pytest-blender plugin since we're running inside Blender manually
# The plugin registers as "blender" not "pytest_blender"
BASE_ARGS="'-p', 'no:blender', "

if [ $# -eq 0 ]; then
    # No arguments - run all tests
    PYTEST_ARGS="[${BASE_ARGS}'tests/', '-v']"
    echo "Running all tests..."
else
    # Build argument list for pytest
    # Convert shell arguments to Python list format
    PYTEST_ARGS="[${BASE_ARGS}"
    for arg in "$@"; do
        # Escape single quotes in arguments
        escaped_arg=$(echo "$arg" | sed "s/'/\\\\'/g")
        PYTEST_ARGS+="'$escaped_arg', "
    done
    PYTEST_ARGS+="]"
    echo "Running tests with arguments: $@"
fi

echo ""

# Run pytest inside Blender
# Using --python-expr to execute pytest within Blender's Python environment
# This ensures bpy module is available
"$BLENDER_EXEC" --background --python-expr "
import sys
import os

# Clear sys.argv to prevent pytest-blender from seeing Blender's arguments
# This is critical - pytest-blender reads sys.argv and gets confused by
# Blender's --background --python-expr arguments
sys.argv = ['pytest']

# Add current directory to path so the addon can be found
sys.path.insert(0, os.getcwd())

import pytest

# Run pytest with the provided arguments
# Disable pytest-blender plugin since we're already inside Blender
exit_code = pytest.main($PYTEST_ARGS)
sys.exit(exit_code)
"

# Capture exit code from Blender
EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
else
    echo -e "${RED}✗ Tests failed${NC}"
fi

exit $EXIT_CODE
