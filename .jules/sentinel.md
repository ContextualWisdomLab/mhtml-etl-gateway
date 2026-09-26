## 2024-05-18 - [Fix DoS vulnerability in HTML colspan parsing]
**Vulnerability:** Uncontrolled resource consumption leading to Denial of Service (DoS) in HTML table extraction. The HTML parser blindly trusted the `colspan` attribute from user-provided MHTML files and expanded columns accordingly in a loop.
**Learning:** We must not blindly trust size-related attributes like `colspan` or `rowspan` parsed from untrusted HTML/MHTML sources. An attacker could specify artificially large sizes, forcing unbounded loops and enormous memory allocation, crashing the ETL gateway pipeline.
**Prevention:** Bound looping constructs driven by user input. In this case, `colspan` has been bounded to `100000`, failing closed aggressively and returning a `TableExtractError` when the limit is exceeded.
## 2024-10-25 - Fix string-based query B608
**Vulnerability:** A static analysis tool flagged a dynamic query utilizing f-strings for an IN statement.
**Learning:** Hardcoded string formatting for queries should be avoided. The driver supports array adaptation perfectly when using ANY and passing a Python list instance.
**Prevention:** Rather than joining placeholders manually, use the parameterizer format AND field = ANY and provide the items inside a list.
