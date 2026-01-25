import * as vscode from 'vscode';
import { SecureCodeAIClient } from './client';
import { DiagnosticManager } from './diagnostics';
import { CodeActionProvider, registerApplyPatchCommand } from './codeActions';

let diagnosticManager: DiagnosticManager;
let client: SecureCodeAIClient;
let statusBarItem: vscode.StatusBarItem;

export function activate(context: vscode.ExtensionContext) {
    console.log('SecureCodeAI extension is now active');

    // Initialize components
    const config = vscode.workspace.getConfiguration('securecodai');
    const apiEndpoint = config.get<string>('apiEndpoint', 'http://localhost:8000');
    
    client = new SecureCodeAIClient(apiEndpoint);
    diagnosticManager = new DiagnosticManager();
    
    // Create status bar item
    statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
    statusBarItem.text = "$(shield) SecureCodeAI";
    statusBarItem.tooltip = "Click to analyze current file";
    statusBarItem.command = 'securecodai.analyzeFile';
    statusBarItem.show();
    context.subscriptions.push(statusBarItem);

    // Register commands
    context.subscriptions.push(
        vscode.commands.registerCommand('securecodai.analyzeFile', () => analyzeCurrentFile())
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('securecodai.analyzeWorkspace', () => analyzeWorkspace())
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('securecodai.configure', () => configureEndpoint())
    );

    // Register code action provider
    const codeActionProvider = new CodeActionProvider(client, diagnosticManager);
    context.subscriptions.push(
        vscode.languages.registerCodeActionsProvider(
            { language: 'python' },
            codeActionProvider,
            {
                providedCodeActionKinds: CodeActionProvider.providedCodeActionKinds
            }
        )
    );

    // Register apply patch command
    registerApplyPatchCommand(context);

    // Auto-analyze on save if enabled
    context.subscriptions.push(
        vscode.workspace.onDidSaveTextDocument((document) => {
            const autoAnalyze = vscode.workspace.getConfiguration('securecodai').get<boolean>('autoAnalyze', false);
            if (autoAnalyze && document.languageId === 'python') {
                analyzeDocument(document);
            }
        })
    );

    // Check API health on activation
    checkAPIHealth();
}

async function checkAPIHealth() {
    try {
        const isHealthy = await client.checkHealth();
        if (isHealthy) {
            vscode.window.showInformationMessage('SecureCodeAI: Connected to API successfully');
        } else {
            vscode.window.showWarningMessage('SecureCodeAI: API is not ready. Please check your configuration.');
        }
    } catch (error) {
        vscode.window.showErrorMessage(`SecureCodeAI: Failed to connect to API. ${error}`);
    }
}

async function analyzeCurrentFile() {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
        vscode.window.showWarningMessage('No active editor');
        return;
    }

    if (editor.document.languageId !== 'python') {
        vscode.window.showWarningMessage('SecureCodeAI only supports Python files');
        return;
    }

    await analyzeDocument(editor.document);
}

async function analyzeDocument(document: vscode.TextDocument) {
    statusBarItem.text = "$(sync~spin) Analyzing...";
    
    try {
        const code = document.getText();
        const filePath = document.fileName;
        
        vscode.window.showInformationMessage('SecureCodeAI: Analyzing file...');
        
        const result = await client.analyzeCode(code, filePath);
        
        // Clear previous diagnostics
        diagnosticManager.clear(document.uri);
        
        if (result.vulnerabilities && result.vulnerabilities.length > 0) {
            // Create diagnostics for vulnerabilities
            const diagnostics: vscode.Diagnostic[] = result.vulnerabilities.map(vuln => {
                const line = parseLineNumber(vuln.location);
                const range = new vscode.Range(line, 0, line, 1000);
                
                const diagnostic = new vscode.Diagnostic(
                    range,
                    `${vuln.vuln_type}: ${vuln.description}`,
                    getSeverity(vuln.severity)
                );
                
                diagnostic.source = 'SecureCodeAI';
                diagnostic.code = vuln.cwe_id || vuln.vuln_type;
                
                return diagnostic;
            });
            
            diagnosticManager.set(document.uri, diagnostics);
            
            // Store patches for code actions
            if (result.patches && result.patches.length > 0) {
                diagnosticManager.storePatches(document.uri, result.patches);
            }
            
            vscode.window.showWarningMessage(
                `SecureCodeAI: Found ${result.vulnerabilities.length} vulnerability(ies)`
            );
        } else {
            vscode.window.showInformationMessage('SecureCodeAI: No vulnerabilities found');
        }
        
        statusBarItem.text = "$(shield) SecureCodeAI";
    } catch (error) {
        statusBarItem.text = "$(shield) SecureCodeAI";
        vscode.window.showErrorMessage(`SecureCodeAI: Analysis failed - ${error}`);
    }
}

async function analyzeWorkspace() {
    const workspaceFolders = vscode.workspace.workspaceFolders;
    if (!workspaceFolders) {
        vscode.window.showWarningMessage('No workspace folder open');
        return;
    }

    const pythonFiles = await vscode.workspace.findFiles('**/*.py', '**/node_modules/**');
    
    if (pythonFiles.length === 0) {
        vscode.window.showInformationMessage('No Python files found in workspace');
        return;
    }

    vscode.window.showInformationMessage(`Analyzing ${pythonFiles.length} Python files...`);
    
    let vulnerabilityCount = 0;
    
    for (const file of pythonFiles) {
        const document = await vscode.workspace.openTextDocument(file);
        await analyzeDocument(document);
        
        const diagnostics = diagnosticManager.get(file);
        vulnerabilityCount += diagnostics.length;
    }
    
    vscode.window.showInformationMessage(
        `SecureCodeAI: Workspace analysis complete. Found ${vulnerabilityCount} vulnerability(ies) across ${pythonFiles.length} files.`
    );
}

async function configureEndpoint() {
    const currentEndpoint = vscode.workspace.getConfiguration('securecodai').get<string>('apiEndpoint');
    
    const newEndpoint = await vscode.window.showInputBox({
        prompt: 'Enter SecureCodeAI API endpoint URL',
        value: currentEndpoint,
        placeHolder: 'http://localhost:8000'
    });
    
    if (newEndpoint) {
        await vscode.workspace.getConfiguration('securecodai').update(
            'apiEndpoint',
            newEndpoint,
            vscode.ConfigurationTarget.Global
        );
        
        client.updateEndpoint(newEndpoint);
        vscode.window.showInformationMessage(`SecureCodeAI: API endpoint updated to ${newEndpoint}`);
        
        // Re-check health
        await checkAPIHealth();
    }
}

function parseLineNumber(location: string): number {
    // Parse location like "file.py:42" or "line 42"
    const match = location.match(/(\d+)/);
    return match ? parseInt(match[1]) - 1 : 0; // VS Code uses 0-based line numbers
}

function getSeverity(severity: string): vscode.DiagnosticSeverity {
    switch (severity.toLowerCase()) {
        case 'high':
        case 'critical':
            return vscode.DiagnosticSeverity.Error;
        case 'medium':
            return vscode.DiagnosticSeverity.Warning;
        case 'low':
            return vscode.DiagnosticSeverity.Information;
        default:
            return vscode.DiagnosticSeverity.Warning;
    }
}

export function deactivate() {
    if (diagnosticManager) {
        diagnosticManager.dispose();
    }
}
