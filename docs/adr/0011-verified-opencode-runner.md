# ADR 0011: Verify the privileged OpenCode runner before credential exposure

**Status:** Accepted  
**Date:** 2026-08-09

## Context

The hourly scheduler originally pinned `anomalyco/opencode/github` to commit `1ec6bdc8c666e315ba85ef5276fac9b0eb7ba109`. Pinning the outer composite action did not pin the executable payload it installed. The composite action still:

- queried GitHub for the latest OpenCode release;
- invoked mutable `actions/cache@v4` internally;
- piped `https://opencode.ai/install` directly to a shell on cache miss.

The OpenCode process receives the NVIDIA model credential and obtains scoped GitHub authority through the GitHub integration. A mutable nested action, latest-release lookup, or unverified installer therefore remains inside the privileged supply-chain boundary even when repository code is later isolated through `cwl-safe-exec`.

The upstream release process computes platform SHA-256 values and publishes them into its generated Homebrew formula. Formula commit `a72a2bfe3b4114ca10a9012c23f1b3f31924b22e` records version `1.18.15` and SHA-256 `d842e0e8c622c672a481b7dc6f0329009b64db96b2ba6041e56f4f93f0293b1c` for `opencode-linux-x64.tar.gz`.

## Decision

The repository does not invoke the upstream OpenCode composite action. The hourly workflow installs and verifies the executable in a credential-free step, then invokes `opencode github run` directly.

The accepted runner contract is:

| Field | Required value |
|---|---|
| operating system | GitHub-hosted Linux |
| architecture | x64 |
| OpenCode version | `1.18.15` |
| release asset | `opencode-linux-x64.tar.gz` |
| release URL | `https://github.com/anomalyco/opencode/releases/download/v1.18.15/opencode-linux-x64.tar.gz` |
| SHA-256 | `d842e0e8c622c672a481b7dc6f0329009b64db96b2ba6041e56f4f93f0293b1c` |
| archive shape | exactly one `opencode` entry |
| version smoke | exact output `1.18.15` |
| session sharing | `SHARE="false"` and repository `share="disabled"` |
| GitHub authentication | OpenCode GitHub/OIDC path; `USE_GITHUB_TOKEN="false"` |

The workflow must:

1. reject any other runner platform or architecture;
2. use an immutable versioned GitHub release URL;
3. download without evaluating a remote installer script;
4. verify SHA-256 before extraction;
5. reject any archive containing entries other than the expected binary;
6. extract without preserving archive ownership or permissions;
7. check the exact CLI version before adding it to the command path;
8. bind no model, GitHub, or OIDC credential to installation;
9. bind credentials only to the selected direct `opencode github run` step;
10. contain no fallback to `latest`, package-manager installation, installer piping, mutable nested action, or digest-free execution.

No cross-run binary cache is trusted. Each invocation downloads and verifies the exact bytes. This favors correctness and reviewability over scheduler startup latency.

## Upgrade procedure

An OpenCode upgrade requires one reviewed change containing:

- exact version and immutable asset URL;
- digest from commit-addressed upstream release evidence;
- independent digest confirmation when the execution environment permits;
- archive-shape review;
- exact-version smoke;
- review of GitHub-mode, OIDC, provider, permission, and prompt behavior;
- updated workflow tests, security architecture, threat model, operability, doctoring references, and CHANGELOG;
- exact-head CI, security checks, independent approval, and unresolved-thread closure.

An unavailable or inconsistent digest blocks the upgrade. Rollback restores the previous accepted version/digest pair through the same protected review process.

## Attestation boundary

The repository does not claim upstream builder attestation for version `1.18.15`. The current provenance evidence is the immutable release URL, the repository-pinned digest, the upstream generated formula at a fixed commit, archive-shape validation, and exact runtime version. A cryptographic release attestation will be required when the upstream project exposes an offline-verifiable attestation contract for the selected asset.

## Consequences

### Positive

- The executable that receives privileged credentials is reviewably identified.
- A compromised latest-release endpoint, installer script, mutable cache action, or substituted archive fails before credential exposure.
- Both scheduler modes share one verified runner path.
- Version changes create a visible repository diff and exact-head evidence.
- Rollback is deterministic.

### Negative

- Every eligible hourly run downloads the archive again.
- The workflow currently supports only the GitHub-hosted Linux x64 profile.
- SHA-256 and upstream formula evidence do not independently prove builder identity.
- Upgrades require manual evidence gathering and review.

## Affected artifacts

- `.github/workflows/hourly-product-gap.yml`
- `tests/test_opencode_runner_supply_chain.py`
- `tests/test_workflow_contracts.py`
- `scripts/validate_repository.py`
- `docs/SECURITY.md`
- `docs/THREAT_MODEL.md`
- `docs/OPERABILITY.md`
- `docs/doctoring/REFERENCES.md`
- `CHANGELOG.md`
