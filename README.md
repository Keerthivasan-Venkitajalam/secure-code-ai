# SecureCodeAI

SecureCodeAI is a security analysis and patching project with API, agent workflow, and VS Code extension components.

## Repository Structure

- agent: agent graph, nodes, validators, and supporting logic
- api: FastAPI server, orchestration, and model interfaces
- extension: VS Code extension source and build output
- scripts: setup, test, and automation scripts
- tests: unit and integration tests
- deployment: container and deployment assets

## Local Setup

1. Create and activate a Python environment.
2. Install dependencies:
   pip install -r requirements.txt
3. Configure environment variables:
   copy deployment/.env.example deployment/.env
4. Start the API:
   - Windows: scripts/start_api_local.ps1
   - Linux or macOS: scripts/start_local.sh

## Extension Setup

1. cd extension
2. npm install
3. npm run compile

## Run Tests

python -m pytest tests -q
