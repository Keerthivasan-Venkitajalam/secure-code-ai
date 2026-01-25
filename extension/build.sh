#!/bin/bash

# SecureCodeAI Extension Build Script

echo "Building SecureCodeAI VS Code Extension..."

# Install dependencies
echo "Installing dependencies..."
npm install

# Compile TypeScript
echo "Compiling TypeScript..."
npm run compile

# Package extension
echo "Packaging extension..."
npm run package

echo "Build complete! VSIX file created."
echo "Install with: code --install-extension securecodai-0.1.0.vsix"
