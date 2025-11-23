#!/bin/bash
# Installation script for SmartGrep

echo "Installing SmartGrep..."

# Install in editable mode
uv pip install -e .

echo ""
echo "✅ Installation complete!"
echo ""
echo "You can now use SmartGrep with these commands:"
echo "  smartgrep index .          # Index current directory"
echo "  smartgrep search 'query'   # Search your code"
echo ""
echo "Or use the short alias:"
echo "  sgrep index ."
echo "  sgrep search 'query'"
