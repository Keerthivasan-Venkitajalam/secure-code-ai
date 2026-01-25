# SecureCodeAI VS Code Extension

Neuro-Symbolic Vulnerability Detection and Automated Patching for Python code.

## Features

- **Real-time Vulnerability Detection**: Automatically scans Python files for security vulnerabilities
- **AI-Powered Analysis**: Uses DeepSeek-Coder-V2-Lite with symbolic execution for accurate detection
- **Automated Patching**: Generates and applies verified security patches
- **Inline Diagnostics**: Shows vulnerabilities directly in your code with red squiggly lines
- **Quick Fixes**: Apply AI-generated patches with a single click
- **Workspace Analysis**: Scan entire workspace for vulnerabilities

## Requirements

- VS Code 1.85.0 or higher
- Python files (.py)
- SecureCodeAI API server running (default: http://localhost:8000)

## Installation

### From VSIX (Local Installation)

1. Download the `.vsix` file
2. Open VS Code
3. Go to Extensions view (Ctrl+Shift+X)
4. Click "..." menu → "Install from VSIX..."
5. Select the downloaded `.vsix` file

### From Marketplace (Coming Soon)

Search for "SecureCodeAI" in the VS Code Extensions Marketplace.

## Setup

1. **Start the SecureCodeAI API server**:
   ```bash
   cd secure-code-ai
   python -m api.server
   ```

2. **Configure the extension** (if using a different endpoint):
   - Open Command Palette (Ctrl+Shift+P)
   - Run "SecureCodeAI: Configure API Endpoint"
   - Enter your API URL (e.g., `https://your-api.com`)

## Usage

### Analyze Current File

- **Command Palette**: `SecureCodeAI: Analyze Current File`
- **Context Menu**: Right-click in Python file → "SecureCodeAI: Analyze Current File"
- **Status Bar**: Click the shield icon in the bottom-right

### Analyze Workspace

- **Command Palette**: `SecureCodeAI: Analyze Workspace`
- Scans all Python files in your workspace

### Apply Patches

When vulnerabilities are detected:

1. Hover over the red squiggly line
2. Click "Quick Fix" (💡 icon) or press `Ctrl+.`
3. Select "Apply SecureCodeAI Patch"
4. The verified patch will be applied automatically

### View Patch Diff

Before applying a patch:

1. Click "Quick Fix" on a vulnerability
2. Select "Show SecureCodeAI Patch Diff"
3. Review the changes in a side-by-side diff view

## Extension Settings

This extension contributes the following settings:

* `securecodai.apiEndpoint`: API endpoint URL (default: `http://localhost:8000`)
* `securecodai.maxIterations`: Maximum patch refinement iterations (default: `3`)
* `securecodai.autoAnalyze`: Automatically analyze files on save (default: `false`)
* `securecodai.showInlineHints`: Show inline vulnerability hints (default: `true`)

## Supported Vulnerabilities

- SQL Injection
- Command Injection
- Path Traversal
- Cross-Site Scripting (XSS)
- Hardcoded Credentials
- Insecure Deserialization
- Server-Side Request Forgery (SSRF)

## How It Works

1. **Scanner Agent**: Uses AST analysis and LLM to identify vulnerability hotspots
2. **Speculator Agent**: Generates formal security contracts (icontract decorators)
3. **SymBot Agent**: Performs symbolic execution to verify vulnerabilities
4. **Patcher Agent**: Generates secure patches with self-correction loops

## Troubleshooting

### "Failed to connect to API"

- Ensure the SecureCodeAI API server is running
- Check the API endpoint in settings
- Verify firewall/network settings

### "No vulnerabilities found" (but you expect some)

- The code may actually be secure
- Try adjusting `maxIterations` setting
- Check API server logs for errors

### Extension not activating

- Ensure you're working with Python files (.py)
- Reload VS Code window (Ctrl+Shift+P → "Reload Window")

## Development

### Building from Source

```bash
cd extension
npm install
npm run compile
```

### Packaging

```bash
npm run package
```

This creates a `.vsix` file you can install locally.

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](../CONTRIBUTING.md).

## License

MIT License - see [LICENSE](../LICENSE) for details.

## Links

- [GitHub Repository](https://github.com/Keerthivasan-Venkitajalam/secure-code-ai)
- [Documentation](https://github.com/Keerthivasan-Venkitajalam/secure-code-ai/blob/main/README.md)
- [Report Issues](https://github.com/Keerthivasan-Venkitajalam/secure-code-ai/issues)

## Acknowledgments

- DeepSeek-Coder-V2-Lite for LLM capabilities
- CrossHair for symbolic execution
- vLLM for high-performance inference

---

**Built with ❤️ for secure software development**
