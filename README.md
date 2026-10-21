# data-refresh

Small utilities for keeping a local data folder fresh: deduplicate, normalise and sort the CSVs
that drift out of shape over a long collection project.

```bash
python refresh.py data/                  # normalise every CSV in place (a .bak is kept)
python refresh.py data/sales.csv -o out/ # write the normalised copy to another directory
python refresh.py data/ --check          # report what WOULD change, change nothing
```

## What "normalise" means

- rows are deduplicated on their full tuple, first occurrence wins;
- dates in any column named `*_date` or `date` are rewritten to ISO `YYYY-MM-DD`;
- every row is padded/truncated to the header's width and the header is sorted as found (columns
  keep their order; only row order changes: sorted, so the file is diff-stable);
- a trailing newline is guaranteed.

## Development

```bash
pip install -r requirements.txt   # none; the standard library only
python -m pytest -q
```

The CI runs the same suite on every push.

## License

MIT - see [LICENSE](LICENSE).
