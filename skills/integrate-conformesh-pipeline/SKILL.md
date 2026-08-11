---
name: integrate-conformesh-pipeline
description: Integrate the Conformesh CRA build-evidence CLI into an existing customer CI/CD repository. Use when an agent must detect and configure GitHub Actions, GitLab CI, Azure Pipelines, Jenkins, or a generic container pipeline; connect an existing CycloneDX or SPDX SBOM; add preview and protected-release jobs; or troubleshoot a Conformesh pipeline integration without handling customer secrets.
---

# Integrate Conformesh Pipeline

Add a pinned Conformesh evidence workflow to the repository while preserving its existing build and release behavior.

## Workflow

1. Inspect the repository before editing.
   - Detect CI files and release jobs.
   - Find the existing SBOM generator and its output path. Accept CycloneDX 1.3-1.6 JSON/XML or SPDX 2.2-2.3 JSON/tag-value/RDF/XML.
   - Find test, scan, provenance, VEX, and user-documentation outputs worth preserving.
   - Read repository-local agent instructions and avoid overwriting unrelated changes.
2. Select one provider template from `assets/`:
   - GitHub Actions: `assets/github-action/action.yml`
   - GitLab CI: `assets/gitlab/conformesh-cra.yml`
   - Azure Pipelines: `assets/azure/conformesh-cra.yml`
   - Jenkins shared library: `assets/jenkins/conformeshCra.groovy`
   - For other systems, invoke the container directly using `references/integration-contract.md`.
3. Adapt the template to the repository rather than replacing the existing pipeline.
   - Run `preview` for pull or merge requests after the SBOM exists.
   - Run `publish` only from the customer-designated protected release path.
   - Pin `ghcr.io/conformesh/conformesh-pipeline-cli:1.0.2` or the digest in the reference. Never introduce `latest`.
   - Mount only the workspace paths needed by the CLI.
   - Preserve the returned output directory as a CI artifact even when a strict gate fails.
4. Configure only the secret reference.
   - Use the exact environment variable `CONFORMESH_PIPELINE_TOKEN`.
   - Never request, read, generate, log, commit, or place its value in a command line.
   - Tell an authorized customer owner or administrator to create a product-bound credential in **SaaS administration → Build-pipeline automation** and store it in the CI provider's protected secret store.
   - Do not use a general API key, GitHub token, repository credential, or platform environment secret as a substitute.
5. Choose gate behavior deliberately.
   - Default new integrations to `warn` unless the user explicitly requests an enforcing gate or the repository already documents that policy.
   - Use `strict` only with an agreed exception process; it exits `3` when dossier readiness has blockers.
   - Do not claim that uploaded tests, scans, or provenance are semantically evaluated. They are retained and checksummed; only SBOM syntax/schema is validated automatically.
6. Validate before finishing.
   - Run the CI provider's local syntax/lint validation when available.
   - Confirm the referenced SBOM path is produced before the Conformesh step.
   - Confirm release key and version values are stable and available in the release job.
   - Search the diff for literal tokens and unpinned `latest` references.
   - Report the files changed, validation performed, and the one manual secret-store action remaining.

## Safety boundaries

- Do not run `publish` against production merely to test configuration. Use `preview` unless the user explicitly authorizes publishing a real release.
- Do not invent an SBOM. If none exists, add or recommend the build ecosystem's established SBOM generator and clearly identify that separate change.
- Do not weaken branch protection, CI secret controls, or existing release approvals.
- Do not describe a successful gate as CRA certification, legal approval, conformity assessment, or proof that every manufacturer obligation is fulfilled.
- Do not send credentials across redirects or non-HTTPS endpoints. The CLI permits HTTP only for localhost testing and rejects redirects.

## Output contract

Expect `conformesh-result.json`, `conformesh.env`, `cra-build-report.pdf`, and `cra-evidence-snapshot.zip`. A ready published release can also return `cra-technical-file.zip`. Read `references/integration-contract.md` for command syntax, exit codes, verified image identity, and CI artifact guidance.
