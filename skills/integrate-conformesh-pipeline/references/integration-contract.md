# Conformesh pipeline integration contract

## Published artifact

- Image: `ghcr.io/conformesh/conformesh-pipeline-cli:1.0.2`
- Multi-architecture digest: `sha256:34f0967cdb49dbb99729597b4515b26f5c32358ae5e3b9de7165d428295fa0d2`
- Release: `https://github.com/conformesh/conformesh-pipeline-cli/releases/tag/v1.0.2`
- API base default: `https://conformesh.com`

Prefer the version tag for readability or the digest for immutable supply-chain pinning.

## Commands

Preview a build:

```sh
docker run --rm \
  -e CONFORMESH_PIPELINE_TOKEN \
  -v "$PWD:/work" \
  ghcr.io/conformesh/conformesh-pipeline-cli:1.0.2 \
  preview --sbom build/sbom.cdx.json --gate warn \
  --artifact test_report=build/tests.xml \
  --artifact scan_report=build/security.sarif
```

Publish a real release only from the customer's protected release job:

```sh
docker run --rm \
  -e CONFORMESH_PIPELINE_TOKEN \
  -v "$PWD:/work" \
  ghcr.io/conformesh/conformesh-pipeline-cli:1.0.2 \
  publish --sbom build/sbom.cdx.json --gate strict \
  --release-key "gateway@$VERSION" --version "$VERSION" \
  --artifact provenance=build/provenance.json
```

For generic runners, add `--repository`, `--commit`, and `--build-id`. Known providers are detected from their standard environment variables.

## Configuration

Optional `conformesh.yml`:

```yaml
schema_version: 1
gate: warn
report_language: en
```

Command-line values override this file.

## Exit codes

- `0`: request completed; warning mode may still report blockers.
- `2`: authentication, input, integrity, or service error.
- `3`: strict gate found dossier-readiness blockers.

Configure the CI system to upload `conformesh-output/` on success and failure. Do not suppress exit code `2`. Only soften exit code `3` when the chosen policy is explicitly advisory.

## Claims boundary

The result reflects the product's Conformesh dossier-readiness checklist at evaluation time. The CLI validates SBOM syntax/schema. Other evidence is retained and checksummed but not semantically judged. A passing result is not CRA certification, a legal opinion, or a conformity assessment.
