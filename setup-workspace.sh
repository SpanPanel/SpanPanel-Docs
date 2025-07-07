#!/bin/bash

# Setup script for SpanPanel_Docs workspace
# This script installs markdownlint-cli and sets up the development environment

echo "🔧 Setting up SpanPanel_Docs workspace..."

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is required but not installed. Please install Node.js first."
    exit 1
fi

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo "❌ npm is required but not installed. Please install npm first."
    exit 1
fi

echo "📦 Installing markdownlint-cli globally..."
npm install -g markdownlint-cli

# Verify installation
if command -v markdownlint &> /dev/null; then
    echo "✅ markdownlint-cli installed successfully"
    echo "📋 Running markdownlint on all markdown files..."
    markdownlint --config .markdownlint.json *.md --fix
    echo "✅ Markdown files formatted with 156 character line length"
else
    echo "❌ Failed to install markdownlint-cli"
    exit 1
fi

echo "🎉 Workspace setup complete!"
