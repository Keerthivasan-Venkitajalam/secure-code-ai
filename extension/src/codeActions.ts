import * as vscode from 'vscode';
import { SecureCodeAIClient } from './client';
import { DiagnosticManager } from './diagnostics';

export class CodeActionProvider implements vscode.CodeActionProvider {
    public static readonly providedCodeActionKinds = [
        vscode.CodeActionKind.QuickFix
    ];

    constructor(
        private client: SecureCodeAIClient,
        private diagnosticManager: DiagnosticManager
    ) {}

    provideCodeActions(
        document: vscode.TextDocument,
        range: vscode.Range | vscode.Selection,
        context: vscode.CodeActionContext,
        token: vscode.CancellationToken
    ): vscode.CodeAction[] {
        const actions: vscode.CodeAction[] = [];

        // Get patches for this document
        const patches = this.diagnosticManager.getPatches(document.uri);
        
        if (patches.length === 0) {
            return actions;
        }

        // Check if there are diagnostics in the current range
        const diagnostics = context.diagnostics.filter(
            diagnostic => diagnostic.source === 'SecureCodeAI'
        );

        if (diagnostics.length === 0) {
            return actions;
        }

        // Create code actions for each patch
        patches.forEach((patch, index) => {
            if (patch.verified) {
                const action = new vscode.CodeAction(
                    `Apply SecureCodeAI Patch ${index + 1} (Verified)`,
                    vscode.CodeActionKind.QuickFix
                );
                action.command = {
                    command: 'securecodai.applyPatch',
                    title: 'Apply Patch',
                    arguments: [document, patch]
                };
                action.diagnostics = diagnostics;
                action.isPreferred = index === 0; // Mark first patch as preferred
                actions.push(action);
            } else {
                const action = new vscode.CodeAction(
                    `Apply SecureCodeAI Patch ${index + 1} (Unverified)`,
                    vscode.CodeActionKind.QuickFix
                );
                action.command = {
                    command: 'securecodai.applyPatch',
                    title: 'Apply Patch',
                    arguments: [document, patch]
                };
                action.diagnostics = diagnostics;
                actions.push(action);
            }
        });

        // Add "Show Diff" action
        if (patches.length > 0) {
            const showDiffAction = new vscode.CodeAction(
                'Show SecureCodeAI Patch Diff',
                vscode.CodeActionKind.QuickFix
            );
            showDiffAction.command = {
                command: 'securecodai.showDiff',
                title: 'Show Diff',
                arguments: [document, patches[0]]
            };
            actions.push(showDiffAction);
        }

        return actions;
    }
}

// Register the apply patch command
export function registerApplyPatchCommand(context: vscode.ExtensionContext) {
    context.subscriptions.push(
        vscode.commands.registerCommand(
            'securecodai.applyPatch',
            async (document: vscode.TextDocument, patch: any) => {
                const edit = new vscode.WorkspaceEdit();
                const fullRange = new vscode.Range(
                    document.positionAt(0),
                    document.positionAt(document.getText().length)
                );
                edit.replace(document.uri, fullRange, patch.code);
                
                const success = await vscode.workspace.applyEdit(edit);
                
                if (success) {
                    vscode.window.showInformationMessage('SecureCodeAI: Patch applied successfully');
                    await document.save();
                } else {
                    vscode.window.showErrorMessage('SecureCodeAI: Failed to apply patch');
                }
            }
        )
    );

    context.subscriptions.push(
        vscode.commands.registerCommand(
            'securecodai.showDiff',
            async (document: vscode.TextDocument, patch: any) => {
                // Create a temporary document with the patched code
                const patchedUri = vscode.Uri.parse(`securecodai:${document.fileName}.patched`);
                
                // Register a text document content provider
                const provider = new class implements vscode.TextDocumentContentProvider {
                    provideTextDocumentContent(uri: vscode.Uri): string {
                        return patch.code;
                    }
                };
                
                const registration = vscode.workspace.registerTextDocumentContentProvider('securecodai', provider);
                
                // Show diff
                await vscode.commands.executeCommand(
                    'vscode.diff',
                    document.uri,
                    patchedUri,
                    `${document.fileName} ↔ SecureCodeAI Patch`
                );
                
                // Clean up
                setTimeout(() => registration.dispose(), 60000); // Dispose after 1 minute
            }
        )
    );
}
