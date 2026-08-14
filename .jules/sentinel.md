## 2024-05-18 - Extracted HTML content includes raw scripts/styles
**Vulnerability:** HTML table parser `_TopLevelTableParser` extracts active content (`<script>`, `<style>`) from cells because it lacked suppression filtering.
**Learning:** Raw HTML data extraction algorithms require explicit suppression lists to avoid carrying forward embedded XSS payloads or styling blobs.
**Prevention:** Always maintain a `_suppression_stack` for data extraction algorithms parsing HTML documents, especially when extracting raw character data across elements.
