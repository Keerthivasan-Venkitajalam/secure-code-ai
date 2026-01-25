import * as vscode from 'vscode';
import { Patch } from './client';

export class DiagnosticManager {
    private diagnosticCollection: vscode.DiagnosticCollection;
    private patchCache: Map<string, Patch[]>;

    constructor() {
        this.diagnosticCollection = vscode.languages.createDiagnosticCollection('securecodai');
        this.patchCache = new Map();
    }

    set(uri: vscode.Uri, diagnostics: vscode.Diagnostic[]) {
        this.diagnosticCollection.set(uri, diagnostics);
    }

    get(uri: vscode.Uri): readonly vscode.Diagnostic[] {
        return this.diagnosticCollection.get(uri) || [];
    }

    clear(uri: vscode.Uri) {
        this.diagnosticCollection.delete(uri);
        this.patchCache.delete(uri.toString());
    }

    clearAll() {
        this.diagnosticCollection.clear();
        this.patchCache.clear();
    }

    storePatches(uri: vscode.Uri, patches: Patch[]) {
        this.patchCache.set(uri.toString(), patches);
    }

    getPatches(uri: vscode.Uri): Patch[] {
        return this.patchCache.get(uri.toString()) || [];
    }

    dispose() {
        this.diagnosticCollection.dispose();
        this.patchCache.clear();
    }
}
