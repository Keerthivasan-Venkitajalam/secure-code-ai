# SecureCodeAI VS Code Extension - Complete Guide

## Overview

The SecureCodeAI VS Code Extension brings neuro-symbolic vulnerability detection directly into your development environment. It provides real-time security analysis, automated patching, and seamless integration with the SecureCodeAI backend API.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    VS Code Extension                         │
│  ┌────────────────────────────────────────────────────┐     │
│  │  Extension Host (extension.ts)                     │     │
│  │  - Command Registration                            │     │
│  │  - Event Handlers                                  │     │
│  │  - Status Bar Management                           │     │
│  └────────────────┬───────────────────────────────────┘     │
│                   │                                          │
│  ┌────────────────▼───────────────────────────────────┐     │
│  │  SecureCodeAI Client (client.ts)                   │     │
│  │  - HTTP Communication                              │     │
│  │  - Request/Response Handling                       │     │
│  └────────────────┬───────────────────────────────────┘     │
│                   │                                          │
│  ┌────────────────▼───────────────────────────────────┐     │
│  │  Diagnostic Manager (diagnostics.ts)               │     │
│  │  - Vulnerability Display                           │     │
│  │  - Patch Caching                                   │     │
│  └────────────────┬───────────────────────────────────┘     │
│                   │                                          │
│  ┌────────────────▼───────────────────────────────────┐     │
│  │  Code Action Provider (codeActions.ts)             │     │
│  │  - Quick Fix Suggestions                           │     │
│  │  - Patch Application                               │     │
│  └────────────────────────────────────────────────────┘     │
└─────────────────────────┬────────────────────────────────────┘
                          │ HTTPS
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              SecureCodeAI Backend API                        │
│                  (FastAPI Server)                            │
└─────────────────────────────────────────────────────────────┘
```

## Features

### 1. Real-Time Vulnerability Detection

The extension automatically detects security vulnerabilities in Python code using:
- **AST Analysis**: Static analysis of code structure
- **LLM Reasoning**: DeepSeek-Coder-V2-Lite for semantic understanding
- **Symbolic Execution**: CrossHair for formal verification

### 2. Inline Diagnostics

Vulnerabilities are displayed directly in the editor:
- **Red Squiggly Lines**: Highlight vulnerable code
- **Severity Levels**: Error (High/Critical), Warning (Medium), Info (Low)
- **Hover Information**: Detailed vulnerability descriptions
- **CWE Codes**: Industry-standard vulnerability classifications

### 3. Automated Patching

AI-generated patches with one-click application:
- **Verified Patches**: Symbolically verified to fix the vulnerability
- **Unverified Patches**: Generated but not yet verified
- **Diff View**: Review changes before applying
- **Automatic Save**: Patches are applied and saved automatically

### 4. Workspace Analysis

Scan entire projects for vulnerabilities:
- **Batch Processing**: Analyze all Python files
- **Progress Tracking**: Real-time analysis status
- **Aggregated Results**: Summary of findings across files

## Installation

### Method 1: From Source (Development)

```bash
# Clone repository
git clone https://github.com/Keerthivasan-Venkitajalam/secure-code-ai.git
cd secure-code-ai/extension

# Install dependencies
npm install

# Compile TypeScript
npm run compile

# Package extension
npm run package

# Install in VS Code
code --install-extension securecodai-0.1.0.vsix
```

### Method 2: From VSIX File

1. Download the `.vsix` file from releases
2. Open VS Code
3. Extensions view (Ctrl+Shift+X)
4. Click "..." → "Install from VSIX..."
5. Select the downloaded file

### Method 3: From Marketplace (Coming Soon)

Search for "SecureCodeAI" in the VS Code Extensions Marketplace.

## Configuration

### API Endpoint

**Default**: `http://localhost:8000`

**Change via Settings**:
1. File → Preferences → Settings (Ctrl+,)
2. Search "SecureCodeAI"
3. Update "Api Endpoint"

**Change via Command**:
1. Command Palette (Ctrl+Shift+P)
2. "SecureCodeAI: Configure API Endpoint"
3. Enter new URL

### Settings Reference

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `securecodai.apiEndpoint` | string | `http://localhost:8000` | Backend API URL |
| `securecodai.maxIterations` | number | `3` | Max patch refinement iterations |
| `securecodai.autoAnalyze` | boolean | `false` | Auto-analyze on file save |
| `securecodai.showInlineHints` | boolean | `true` | Show inline vulnerability hints |

## Usage

### Analyze Current File

**Method 1: Status Bar**
- Click the shield icon (🛡️) in the bottom-right corner

**Method 2: Command Palette**
- Press `Ctrl+Shift+P`
- Type "SecureCodeAI: Analyze Current File"
- Press Enter

**Method 3: Context Menu**
- Right-click in a Python file
- Select "SecureCodeAI: Analyze Current File"

### Analyze Workspace

**Command Palette**:
- Press `Ctrl+Shift+P`
- Type "SecureCodeAI: Analyze Workspace"
- Press Enter

This will scan all `.py` files in your workspace.

### Apply Patches

When a vulnerability is detected:

1. **Hover** over the red squiggly line to see details
2. **Click** the 💡 (Quick Fix) icon or press `Ctrl+.`
3. **Select** "Apply SecureCodeAI Patch (Verified)"
4. **Review** the changes (optional: use "Show Diff")
5. **Apply** - the patch is automatically applied and saved

### View Patch Diff

Before applying a patch:

1. Click 💡 (Quick Fix)
2. Select "Show SecureCodeAI Patch Diff"
3. Review side-by-side comparison
4. Close diff and apply if satisfied

## Supported Vulnerabilities

| Vulnerability Type | CWE | Detection Method |
|-------------------|-----|------------------|
| SQL Injection | CWE-89 | AST + LLM + Symbolic |
| Command Injection | CWE-78 | AST + LLM + Symbolic |
| Path Traversal | CWE-22 | AST + LLM + Symbolic |
| XSS | CWE-79 | AST + LLM |
| Hardcoded Credentials | CWE-798 | AST + LLM |
| Insecure Deserialization | CWE-502 | AST + LLM |
| SSRF | CWE-918 | AST + LLM |

## Workflow Example

### Example 1: SQL Injection

**Original Code**:
```python
def search_user(username):
    query = f"SELECT * FROM users WHERE name='{username}'"
    return execute_query(query)
```

**Detection**:
- Extension shows red squiggly under the query line
- Hover shows: "SQL Injection: User input concatenated directly into SQL query"

**Patch**:
```python
def search_user(username):
    # Security fix: Use parameterized query to prevent SQL injection
    query = "SELECT * FROM users WHERE name = ?"
    return execute_query(query, (username,))
```

### Example 2: Command Injection

**Original Code**:
```python
def list_files(directory):
    cmd = f"ls -la {directory}"
    return os.system(cmd)
```

**Patch**:
```python
def list_files(directory):
    # Security fix: Use list arguments with shell=False
    result = subprocess.run(
        ["ls", "-la", directory],
        shell=False,
        capture_output=True,
        text=True
    )
    return result.stdout
```

## Troubleshooting

### Extension Not Activating

**Symptoms**: No shield icon, commands not available

**Solutions**:
1. Check VS Code version (must be 1.85.0+)
2. Ensure you're working with Python files (.py)
3. Reload window: `Ctrl+Shift+P` → "Reload Window"
4. Check extension is enabled: Extensions view → SecureCodeAI

### API Connection Failed

**Symptoms**: "Failed to connect to API" error

**Solutions**:
1. Start API server: `python -m api.server`
2. Check API endpoint in settings
3. Test API manually: `curl http://localhost:8000/health`
4. Check firewall/network settings
5. Verify API is healthy: Should return `{"status": "healthy"}`

### No Vulnerabilities Found

**Symptoms**: Analysis completes but no issues shown

**Possible Reasons**:
1. Code is actually secure (good!)
2. API server not fully initialized
3. LLM model not loaded
4. File too large (check API logs)

**Solutions**:
1. Check API server logs
2. Try a known vulnerable code sample
3. Increase `maxIterations` setting
4. Restart API server

### Patches Not Applying

**Symptoms**: Quick Fix doesn't work

**Solutions**:
1. Ensure file is saved
2. Check file permissions
3. Try manual application (copy/paste)
4. Check Output panel for errors

## Development

### Project Structure

```
extension/
├── src/
│   ├── extension.ts       # Main extension entry point
│   ├── client.ts          # API client
│   ├── diagnostics.ts     # Diagnostic management
│   └── codeActions.ts     # Quick Fix provider
├── out/                   # Compiled JavaScript
├── package.json           # Extension manifest
├── tsconfig.json          # TypeScript config
├── README.md              # User documentation
├── CHANGELOG.md           # Version history
└── QUICKSTART.md          # Developer guide
```

### Building

```bash
# Install dependencies
npm install

# Compile TypeScript
npm run compile

# Watch for changes
npm run watch

# Package extension
npm run package
```

### Testing

1. Open `extension` folder in VS Code
2. Press `F5` to launch Extension Development Host
3. Test features in the new window
4. Check Debug Console for logs

### Debugging

1. Set breakpoints in `.ts` files
2. Press `F5` to start debugging
3. Use Debug Console to inspect variables
4. Check Output panel → "SecureCodeAI" for logs

## Publishing

### Prerequisites

1. Create [Visual Studio Marketplace](https://marketplace.visualstudio.com/) account
2. Create Personal Access Token (PAT)
3. Install vsce: `npm install -g @vscode/vsce`

### Publish Steps

```bash
# Login
vsce login <publisher-name>

# Publish
vsce publish

# Or publish specific version
vsce publish minor  # 0.1.0 → 0.2.0
vsce publish patch  # 0.1.0 → 0.1.1
vsce publish major  # 0.1.0 → 1.0.0
```

## Performance

### Metrics

- **Analysis Time**: 2-10 seconds per file (depending on size)
- **Memory Usage**: ~50MB (extension) + API server memory
- **Network**: ~10-50KB per analysis request

### Optimization Tips

1. **Enable Auto-Analyze**: Only for small projects
2. **Batch Analysis**: Use workspace analysis for large projects
3. **API Caching**: API caches results for identical code
4. **Local API**: Run API locally for best performance

## Security

### Data Privacy

- **Code Never Leaves Your Network**: When using local API
- **No Telemetry**: Extension doesn't collect usage data
- **Open Source**: Full transparency of code

### API Security

- **HTTPS Recommended**: For production deployments
- **Authentication**: Add API keys if deploying publicly
- **Rate Limiting**: Configure in API server

## Roadmap

### v0.2.0 (Planned)
- [ ] JavaScript/TypeScript support
- [ ] Inline code lens for metrics
- [ ] Vulnerability history tracking
- [ ] Custom rules support

### v0.3.0 (Planned)
- [ ] Java support
- [ ] Go support
- [ ] CI/CD integration
- [ ] Team collaboration features

### v1.0.0 (Planned)
- [ ] Multi-language support
- [ ] Advanced configuration
- [ ] Performance optimizations
- [ ] Enterprise features

## Contributing

Contributions welcome! See [CONTRIBUTING.md](../CONTRIBUTING.md).

## License

MIT License - see [LICENSE](../LICENSE).

## Support

- **Issues**: [GitHub Issues](https://github.com/Keerthivasan-Venkitajalam/secure-code-ai/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Keerthivasan-Venkitajalam/secure-code-ai/discussions)
- **Documentation**: [GitHub Wiki](https://github.com/Keerthivasan-Venkitajalam/secure-code-ai/wiki)

---

**Built with ❤️ for secure software development**
