# Contributing

Thanks for helping. This project stays small on purpose: standard library only, no network in tests.

1. Fork, create a branch, make your change.
2. Run `pip install -e ".[test]"` and `python -m pytest`. Tests use the saved pages in `tests/fixtures/` and a fake transport; they must never touch the network.
3. If Telegram changed its markup, save the new page into `tests/fixtures/` (remove inline scripts, SVG and tracking attributes first), add a test for the new selector and keep the old one working when possible.
4. Keep requests gentle: do not lower the one second minimum between requests.
5. Open a pull request that says what changed and why.

By contributing you agree that your code is released under the MIT license.
