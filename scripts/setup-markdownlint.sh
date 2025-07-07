#!/bin/bash

# Setup script for markdownlint in SpanPanel_Docs workspace
# This script installs markdownlint-cli if not already installed

echo "Setting up markdownlint for SpanPanel_Docs..."

# Check if markdownlint is already installed
if command -v markdownlint &> /dev/null; then
    echo "✓ markdownlint-cli is already installed"
else
    echo "Installing markdownlint-cli..."
    
    # Check if npm is available
    if command -v npm &> /dev/null; then
        npm install -g markdownlint-cli
        echo "✓ markdownlint-cli installed successfully"
    else
        echo "❌ npm not found. Please install Node.js and npm first."
        echo "Visit: https://nodejs.org/"
        exit 1
    fi
fi

# Verify installation
if command -v markdownlint &> /dev/null; then
    echo "✓ Setup complete! markdownlint is ready to use."
    markdownlint --version
    echo ""
    echo "📝 Available VS Code Tasks:"
    echo "  • Markdownlint: Check All Files - Shows all lint violations"
    echo "  • Markdownlint: Fix All Files - Automatically fixes what it can"
    echo ""
    echo "ℹ️  Note: Exit code 1 from markdownlint is normal when violations are found"
    echo "   It doesn't mean the tool failed - it's reporting formatting issues to fix"
else
    echo "❌ Installation failed. Please check your Node.js/npm setup."
    exit 1
fi
