# Local Development Setup - VS Code Extension

This guide shows you how to develop and test the SecureCodeAI VS Code extension with a local backend.

## Prerequisites

- Node.js 18+ installed
- VS Code installed
- SecureCodeAI backend running locally (see `../SETUP.md` and `../WINDOWS_QUICKSTART.md`)

## Quick Start

### 1. Install Dependencies

```bash
cd secure-code-ai/extension
npm install
```

### 2. Compile Extension

```bash
npm run compile
```

### 3. Start Backend Locally

In a separate terminal:

```bash
# Windows
cd secure-code-ai
.\scripts\start_local.ps1

# Linux/Mac
cd secure-code-ai
chmod +x scripts/start_local.sh
./scripts/start_local.sh
```

Wait for: ` SecureCodeAI is running!`

### 4. Launch Extension Development Host

In VS Code:

1. Open `secure-code-ai/extension` folder
2. Press `F5` (or Run → Start Debugging)
3. A new VS Code window opens (Extension Development Host)

### 5. Test the Extension

In the Extension Development Host window:

1. Create a test file `test.py`:
   ```python
   import pickle
   
   def load_data(filename):
       with open(filename, 'rb') as f:
           return pickle.load(f)  # Insecure!
   ```

2. Right-click in editor → "SecureCodeAI: Analyze Current File"
3. Wait 15-30 seconds
4. See vulnerability detected!
5. Click "Apply Patch" to fix

## Development Workflow

### Watch Mode (Auto-Recompile)

```bash
cd secure-code-ai/extension
npm run watch
```

This automatically recompiles when you edit TypeScript files.

### Debug Extension

1. Set breakpoints in `src/extension.ts`
2. Press `F5` to launch debugger
3. Trigger commands in Extension Development Host
4. Debugger stops at breakpoints

### View Extension Logs

In Extension Development Host:

1. Open Output panel: `Ctrl+Shift+U` (Windows) or `Cmd+Shift+U` (Mac)
2. Select "SecureCodeAI" from dropdown
3. See all extension logs

### Test API Connection

```typescript
// In src/client.ts, add logging:
console.log('Connecting to:', this.apiEndpoint);
```

Then check Output panel for logs.

## Configuration

### Default Settings

The extension defaults to:

```json
{
  "securecodai.apiEndpoint": "http://localhost:8000",
  "securecodai.maxIterations": 3,
  "securecodai.autoAnalyze": false,
  "securecodai.showInlineHints": true
}
```

### Override Settings

In Extension Development Host, open Settings (`Ctrl+,`) and search "SecureCodeAI".

Or create `.vscode/settings.json`:

```json
{
  "securecodai.apiEndpoint": "http://localhost:8000",
  "securecodai.autoAnalyze": true
}
```

## Testing Different Scenarios

### Test 1: SQL Injection

```python
# test_sql.py
import sqlite3

def get_user(username):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    query = f"SELECT * FROM users WHERE username = '{username}'"
    cursor.execute(query)  # SQL injection!
    return cursor.fetchone()
```

### Test 2: Command Injection

```python
# test_cmd.py
import os

def ping_host(host):
    os.system(f"ping {host}")  # Command injection!
```

### Test 3: Path Traversal

```python
# test_path.py
def read_file(filename):
    with open(f"/data/{filename}") as f:  # Path traversal!
        return f.read()
```

## Troubleshooting

### Issue: Extension Can't Connect to API

**Check backend is running:**
```bash
curl http://localhost:8000/health
```

**Check extension logs:**
- Output panel → SecureCodeAI
- Look for connection errors

**Verify settings:**
- Settings → SecureCodeAI → API Endpoint
- Should be: `http://localhost:8000`

### Issue: No Vulnerabilities Detected

**Check file language:**
- Extension only activates for Python files
- File must have `.py` extension

**Check backend logs:**
```bash
docker-compose logs -f secureai
```

**Try simpler test:**
```python
import pickle
pickle.load(open('data.pkl', 'rb'))
```

### Issue: Extension Not Loading

**Check VS Code version:**
- Requires VS Code 1.85.0+
- Update VS Code if needed

**Reinstall dependencies:**
```bash
cd secure-code-ai/extension
rm -rf node_modules
npm install
npm run compile
```

### Issue: Compilation Errors

**Check TypeScript version:**
```bash
npm list typescript
```

**Clean and rebuild:**
```bash
npm run clean  # if available
npm run compile
```

## File Structure

```
extension/
├── src/
│   ├── extension.ts      # Main extension entry point
│   ├── client.ts         # API client
│   ├── codeActions.ts    # Code actions (apply patch)
│   └── types.ts          # TypeScript types
├── out/                  # Compiled JavaScript (generated)
├── package.json          # Extension manifest
├── tsconfig.json         # TypeScript config
└── README.md            # User documentation
```

## Key Files to Edit

### extension.ts
Main extension logic:
- Command registration
- Event handlers
- Extension activation

### client.ts
API communication:
- HTTP requests to backend
- Response parsing
- Error handling

### codeActions.ts
Code actions:
- Apply patch action
- Quick fixes
- Inline suggestions

## Adding New Features

### Add a New Command

1. **Register in package.json:**
   ```json
   {
     "command": "securecodai.myCommand",
     "title": "SecureCodeAI: My Command"
   }
   ```

2. **Implement in extension.ts:**
   ```typescript
   let myCommand = vscode.commands.registerCommand(
     'securecodai.myCommand',
     async () => {
       // Your code here
     }
   );
   context.subscriptions.push(myCommand);
   ```

3. **Test:**
   - Press F5
   - Ctrl+Shift+P → "SecureCodeAI: My Command"

### Add a New Setting

1. **Add to package.json:**
   ```json
   "securecodai.mySetting": {
     "type": "boolean",
     "default": true,
     "description": "My setting description"
   }
   ```

2. **Read in code:**
   ```typescript
   const config = vscode.workspace.getConfiguration('securecodai');
   const mySetting = config.get<boolean>('mySetting');
   ```

## Performance Tips

### Reduce API Calls

Cache results:
```typescript
private cache = new Map<string, AnalysisResult>();

async analyze(code: string): Promise<AnalysisResult> {
  const hash = this.hashCode(code);
  if (this.cache.has(hash)) {
    return this.cache.get(hash)!;
  }
  const result = await this.apiCall(code);
  this.cache.set(hash, result);
  return result;
}
```

### Debounce Auto-Analysis

```typescript
let timeout: NodeJS.Timeout;
vscode.workspace.onDidSaveTextDocument((doc) => {
  clearTimeout(timeout);
  timeout = setTimeout(() => {
    analyzeDocument(doc);
  }, 1000);  // Wait 1 second after save
});
```

## Publishing (Later)

When ready to publish:

```bash
# Install vsce
npm install -g @vscode/vsce

# Package extension
vsce package

# Publish to marketplace
vsce publish
```

See `../EXTENSION_GUIDE.md` for packaging and publication details.

## Next Steps

1.  Get backend running locally
2.  Install extension dependencies
3.  Launch Extension Development Host
4.  Test with sample vulnerabilities
5.  Start developing new features!

## Support

- **Extension Issues**: Check `README.md`
- **Backend Issues**: Check `../SETUP.md` and `../WINDOWS_QUICKSTART.md`
- **API Issues**: Check `../api/README.md`

## Summary

You now have a complete local development environment:

-  Backend running in Docker
-  Extension in development mode
-  Hot reload for TypeScript changes
-  Full debugging support

Happy coding! 
