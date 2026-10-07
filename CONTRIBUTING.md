# Contributing

Thanks for your interest. This is a single-author pre-application research demonstrator, but issues
and pull requests are welcome.

1. `make install`, then `make pipeline-fast` and `make test`.
2. Keep every change honest: metrics must come from the pipeline, never typed into docs or UI.
3. Any change to the Explanation Engine must keep `tests/test_explanation_engine.py` passing
   (no treatment advice, all five concepts separated).
4. Run `make lint` before opening a PR. Use Conventional Commit messages.
5. Never add real patient data, or data derived from it, to the repository.
