# SecureCodeAI Extension - Quick Start Guide

## Prerequisites

1. **Node.js and npm** installed (v18 or higher)
2. **VS Code** installed (v1.85.0 or higher)
3. **SecureCodeAI API** running

## Step 1: Install Dependencies

```bash
cd extension
npm install
```

## Step 2: Compile TypeScript

```bash
npm run compile
```

Or watch for changes:

```bash
npm run watch
```

## Step 3: Test the Extension

1. Open the `extension` folder in VS Code
2. Press `F5` to launch Extension Development Host
3. A new VS Code window will open with the extension loaded
4. Open a Python file
5. The SecureCodeAI shield icon should appear in the status bar

## Step 4: Test Functionality

### Test Vulnerability Detection

1. Create a test Python file with a vulnerability:

```python
# test_vuln.py
def search_user(username):
    query = f"SELECT * FROM users WHERE name='{username}'"
    return execute_query(query)
```

2. Click the shield icon or run "SecureCodeAI: Analyze Current File"
3. You should see a red squiggly line under the vulnerable code
4. Hover to see the vulnerability description

### Test Patch Application

1. Click the 💡 (Quick Fix) icon or press `Ctrl+.`
2. Select "Apply SecureCodeAI Patch (Verified)"
3. The code should be automatically fixed

## Step 5: Package the Extension

```bash
npm run package
```

This creates a `.vsix` file that can be installed in VS Code.

## Step 6: Install Locally

1. In VS Code, go to Extensions view (Ctrl+Shift+X)
2. Click "..." menu → "Install from VSIX..."
3. Select the generated `.vsix` file

## Configuration

### Set API Endpoint

If your API is not running on `http://localhost:8000`:

1. Open Settings (Ctrl+,)
2. Search for "SecureCodeAI"
3. Update "Api Endpoint" field

Or use Command Palette:
- `Ctrl+Shift+P` → "SecureCodeAI: Configure API Endpoint"

### Enable Auto-Analyze

To automatically analyze files on save:

1. Open Settings
2. Search for "SecureCodeAI"
3. Enable "Auto Analyze"

## Troubleshooting

### Extension Not Loading

- Check VS Code version (must be 1.85.0+)
- Reload window: `Ctrl+Shift+P` → "Reload Window"
- Check Output panel: View → Output → Select "SecureCodeAI"

### API Connection Failed

- Ensure API server is running: `python -m api.server`
- Check API endpoint in settings
- Test API manually: `curl http://localhost:8000/health`

### Compilation Errors

- Delete `node_modules` and `out` folders
- Run `npm install` again
- Run `npm run compile`

## Development Tips

### Debugging

1. Set breakpoints in TypeScript files
2. Press `F5` to start debugging
3. Use Debug Console to inspect variables

### Hot Reload

Run `npm run watch` in a terminal to automatically recompile on changes.

### Logging

Add console.log statements - they appear in:
- Debug Console (when debugging)
- Output panel → "SecureCodeAI" (in Extension Development Host)

## Publishing to Marketplace

### Prerequisites

1. Create a [Visual Studio Marketplace](https://marketplace.visualstudio.com/) account
2. Create a Personal Access Token (PAT)
3. Install vsce: `npm install -g @vscode/vsce`

### Publish

```bash
vsce login <publisher-name>
vsce publish
```

Or publish a specific version:

```bash
vsce publish minor  # 0.1.0 → 0.2.0
vsce publish patch  # 0.1.0 → 0.1.1
vsce publish major  # 0.1.0 → 1.0.0
```

## Next Steps

- Add more language support
- Implement inline code lens
- Add vulnerability history tracking
- Create custom vulnerability rules
- Integrate with CI/CD

## Resources

- [VS Code Extension API](https://code.visualstudio.com/api)
- [Publishing Extensions](https://code.visualstudio.com/api/working-with-extensions/publishing-extension)
- [Extension Guidelines](https://code.visualstudio.com/api/references/extension-guidelines)
