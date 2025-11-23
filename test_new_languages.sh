#!/bin/bash
# Test script for new language support

echo "Installing new dependencies..."
#uv pip install tree-sitter-rust tree-sitter-cpp tree-sitter-java pathspec

echo ""
echo "Testing indexing with new languages..."
#uv run sgrep index test_files

echo ""
echo "Test 1: Exact match - 'database connection'"
#uv run sgrep search "database connection" --limit 3

echo ""
echo "Test 2: Typo test - 'subtract two numer' (should find subtract function)"
#uv run sgrep search "subtract two numer" --threshold 1.9 --limit 3

echo ""
echo "Test 3: Semantic variation - 'check user password' (should find authenticate_user)"
uv run sgrep search "check user password" --threshold 1.9 --limit 3

echo ""
echo "Test 4: Cross-language - 'start web server' (should find Go HTTP server)"
#uv run sgrep search "start web server" --limit 3

echo ""
echo "Test 5: Cross-language - 'read config file' (should find JS config loader)"
#uv run sgrep search "read config file" --limit 3

echo ""
echo "Test 6: Cross-language - 'fetch user data' (should find TS API handler)"
#uv run sgrep search "fetch user data" --limit 3

echo ""
echo "Test 7: Cross-language - 'multiply numbers' (should find Python calculator)"
#uv run sgrep search "multiply numbers" --limit 3

echo ""
echo "Test 8: Gitignore verification (should NOT find ignored files)"
#uv run sgrep search "should_not_be_indexed" --limit 3
