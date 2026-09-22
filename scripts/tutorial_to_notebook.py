"""Regenerate examples/tutorial.ipynb from examples/tutorial.py (percent format).

`examples/tutorial.py` is the source of truth (D-064); the notebook has
no content of its own. This splits the script on its `# %%` /
`# %% [markdown]` markers into cells, with no jupytext dependency. It
reproduces the notebook committed before this script existed
byte for byte (checked when the script was added).

Usage:
    python scripts/tutorial_to_notebook.py examples/tutorial.py examples/tutorial.ipynb
    python scripts/tutorial_to_notebook.py examples/tutorial.py - --check examples/tutorial.ipynb
"""

import json
import sys


def _lines(text: str) -> list[str]:
    parts = text.split("\n")
    return [line + "\n" for line in parts[:-1]] + ([parts[-1]] if parts[-1] else [])


def convert(script: str) -> dict:
    cells = []
    kind, buffer = None, []

    def flush() -> None:
        if kind is None:
            return
        body = list(buffer)
        while body and not body[-1].strip():
            body.pop()
        while body and not body[0].strip():
            body.pop(0)
        if kind == "markdown":
            body = [line[2:] if line.startswith("# ") else line[1:] if line.startswith("#") else line for line in body]
            cells.append({"cell_type": "markdown", "metadata": {}, "source": _lines("\n".join(body))})
        else:
            cells.append(
                {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": _lines("\n".join(body))}
            )

    for line in script.split("\n"):
        if line.startswith("# %% [markdown]"):
            flush()
            kind, buffer = "markdown", []
        elif line.startswith("# %%"):
            flush()
            kind, buffer = "code", []
        elif kind is not None:
            buffer.append(line)
    flush()
    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "pygments_lexer": "ipython3"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


if __name__ == "__main__":
    source, target = sys.argv[1], sys.argv[2]
    with open(source, encoding="utf-8") as stream:
        notebook = convert(stream.read())
    if len(sys.argv) > 3 and sys.argv[3] == "--check":
        with open(sys.argv[4], encoding="utf-8") as stream:
            reference = json.load(stream)
        same = [a == b for a, b in zip(notebook["cells"], reference["cells"])]
        print("cells", len(notebook["cells"]), len(reference["cells"]), "identical cells", sum(same))
        for index, ok in enumerate(same):
            if not ok:
                print("first diff at cell", index)
                print(repr(notebook["cells"][index])[:400])
                print(repr(reference["cells"][index])[:400])
                break
        print("metadata equal", notebook["metadata"] == reference["metadata"])
    else:
        with open(target, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(notebook, stream, indent=1, ensure_ascii=False)
