# WARP.md — Warp Workflow Manifest

## Project Overview
- LSM Tree Python implementation
- AI-agentic coding integrated via Warp terminal
- Docs-driven generation and testing

## Warp Workflows
- AI Project Bootstrap → `.warp/workflows/ai-bootstrap.yaml`
- Run All Tests → `.warp/workflows/run-tests.yaml`
- Regenerate Docs → `.warp/workflows/regenerate-docs.yaml`
- Run AI Agent → `.warp/workflows/run-agent.yaml`

## Project Structure Reference
- `docs/` → Source of truth (technical_spec, api_spec, sequencing_plan)
- `src/` → Implementation modules
- `tests/` → Unit, integration, performance
- `ai/` → Agent code, prompts, logs
- `tools/` → Scripts, config, workflow helpers

## AI Agent Instructions (Warp-focused)
- Always start from sequencing_plan.md
- Write modular code to `src/lsm_tree/`
- Generate tests in parallel
- Log outputs and diffs in `ai/logs/`
- Follow coding standards in `tools/config/coding_standards.md`
