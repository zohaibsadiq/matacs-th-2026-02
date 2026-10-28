# Local sample proposals (not committed)

The brief asks that no proposal text is copied into the repository, so this folder
holds only this note. The `.gitignore` rule `prototype/samples/*.txt` keeps the
text files out of git.

To run the prototype against the five samples:

1. Create one plain-text file per proposal in this folder: `A.txt`, `B.txt`, `C.txt`, `D.txt`, `E.txt`.
2. Paste the text of each proposal from the brief into the matching file, including any appendix notes.
3. From the `prototype` folder run `python run_triage.py`.

No API key? Run `python run_triage.py --dry-run` instead. It uses hand-checked
extraction values from `fixtures/extracted_demo.json` and runs the same rules.
