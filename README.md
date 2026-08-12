# Conformesh pipeline CLI

The Conformesh pipeline CLI uploads build evidence to a product-scoped Conformesh account and returns a CRA dossier-readiness result for the build.

It supports GitHub Actions, GitLab CI, Azure Pipelines, Jenkins and generic CI runners. The image contains no customer or Conformesh credentials. Supply the product-bound `CONFORMESH_PIPELINE_TOKEN` through the CI provider's secret store at runtime.

## Container usage

```sh
docker run --rm \
  -e CONFORMESH_PIPELINE_TOKEN \
  -v "$PWD:/work" \
  ghcr.io/conformesh/conformesh-pipeline-cli:1.0.2 \
  preview --sbom build/sbom.cdx.json
```

For release builds, pin a semantic version or image digest rather than `latest`.

```sh
docker run --rm \
  -e CONFORMESH_PIPELINE_TOKEN \
  -v "$PWD:/work" \
  ghcr.io/conformesh/conformesh-pipeline-cli:1.0.2 \
  publish --sbom build/sbom.cdx.json \
  --release-key "gateway@$VERSION" --version "$VERSION"
```

The gate evaluates the product's current dossier-readiness checklist. It validates the SBOM format and preserves other uploaded artifacts, but it does not certify CRA compliance or replace accountable human review.

## This repository uses Conformesh

Every push and pull request tests the CLI, builds and smoke-tests its container, and generates a CycloneDX SBOM. Pushes to `main` then use a product-scoped GitHub Actions secret to submit that evidence back to Conformesh in preview mode. Pull requests never receive the credential. The resulting CRA readiness report and evidence snapshot are retained as workflow artifacts.

See the [full setup guide](https://conformesh.com/how-to) and [API documentation](https://conformesh.com/api/docs).

## Claude and coding-agent skill

The repository includes an agent-readable skill that can inspect a customer repository and install the appropriate pinned integration for GitHub Actions, GitLab CI, Azure Pipelines, Jenkins, or a generic runner.

For Claude Code, copy [`skills/integrate-conformesh-pipeline`](skills/integrate-conformesh-pipeline) into the customer's `.claude/skills/` directory. For Codex, copy it into the applicable `.codex/skills/` directory. Then ask:

```text
Use $integrate-conformesh-pipeline to add Conformesh to this repository's CI pipeline.
```

The skill never handles the product token. It modifies only the pipeline configuration and leaves an authorized customer administrator to place `CONFORMESH_PIPELINE_TOKEN` in the provider's protected secret store.

## Security

The CLI uses the Python standard library and reads its token only from `CONFORMESH_PIPELINE_TOKEN`. It refuses non-HTTPS API URLs except localhost and rejects HTTP redirects so credentials are not forwarded to another origin.

Report security issues privately to security@conformesh.com.

Copyright 2026 Conformesh. All rights reserved. No licence is granted for redistribution or modification of the source code beyond use of the published CLI and container with the Conformesh service.
