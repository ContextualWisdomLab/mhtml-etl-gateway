1. **Add RED focused regression test**
   - Use `replace_with_git_merge_diff` to add a regression test in `tests/test_postgres_loader.py` that verifies `adapted_rows` correctly handles `str` subclasses during coercion to ensure `class S(str): pass` correctly runs through `coerce_value()` rather than raw passing.

2. **Fix GREEN coercion issue in `adapted_rows`**
   - Revert `type(raw) is str` to `isinstance(raw, str)` inside `PsycopgSink.write_artifact_rows.adapted_rows` inside `src/mhtml_etl_gateway/postgres_loader.py`.
   - Maintain the fast loop hoisting logic and local append assignment.
   - Run tests to confirm the fix works.

3. **Revert unrelated formatting**
   - Use `git checkout origin/main -- src/mhtml_etl_gateway/postgres_loader.py` to reset the file.
   - Re-apply *only* the `adapted_rows` and `prepare_typed_rows` logical performance optimizations manually via `replace_with_git_merge_diff`.
   - Use `git diff` or `cat src/mhtml_etl_gateway/postgres_loader.py` to verify the applied changes and confirm there is no formatting pollution.

4. **Write and execute a benchmark script**
   - Create a benchmark script (e.g., `benchmark_fix.py`) using `run_in_bash_session`, and execute it using `PYTHONPATH=src python benchmark_fix.py` to confirm performance gains persist.

5. **Run the full test suite**
   - Run `python -m coverage run --branch -m pytest -q` and security scans `bandit -r src/` to verify correctness.

6. Complete pre-commit steps to ensure proper testing, verification, review, and reflection are done.

7. **Respond to the PR comments and submit**
   - Use the `reply_to_pr_comments` tool to respond to the PR comments, then use the `submit` tool to submit the changes.
