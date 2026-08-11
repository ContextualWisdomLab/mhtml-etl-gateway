# ADR 0009: Nonreflecting metadata surfaces

**Status:** Accepted
**Date:** 2026-08-07

## Context

Malformed input can place sensitive or hostile values in paths, MIME identifiers, parameters, encodings, locations, headers, and cells. Echoing those values into errors, CI logs, issue comments, metrics, or default JSON creates a second data-exfiltration path.

## Decision

Error and diagnostic messages are fixed and generic. Content-Location is represented by scheme plus SHA-256. Header values are absent by default. Source row values and decoded HTML are never serialized in the inspection contract. Tests assert that representative attacker-controlled strings are not reflected.

## Consequences

Operators use stable codes and cryptographic identity to investigate. Detailed protected evidence must be accessed through an authorized source-custody workflow rather than public operational surfaces.
