## 2026-08-17 - Profiling Artifacts
**Learning:** When generating profiling artifacts using tools like `cProfile`, make sure to properly delete them because committing binary artifacts is not acceptable.
**Action:** Always clean up profiling dumps before commit.

## 2026-08-17 - Regex optimizations and newlines
**Learning:** The `\s+` regex (or `[\t\f\v ]+`) does NOT match `\n` or `\r`. If you apply a whitespace regex replacement on an entire string *before* replacing newlines, you will not remove the newlines, but if you have a regex that *does* include newlines, it will destroy the formatting. It's safer to keep newline handling separate when you need to preserve explicit line breaks.
**Action:** Be extremely careful about the order of operations when attempting to optimize text normalization involving newlines and whitespace regexes. A small change in order can introduce subtle but significant functional regressions.
