# gopcnet tutorial

`tutorial.py` walks through `gopcnet`'s full public API on a simulated,
deliberately messy 8-symptom depression/anxiety dataset -- fitting a
network, comparing it against the two comparator methods, checking
bootstrap edge stability and the CS-coefficient, computing centrality
and bridge centrality, checking goodness of fit (in-sample and
out-of-sample), summarizing the network as a whole, and running a
two-group network comparison test. Every step is annotated with why
it's being done, not just what the code does.

This is example/tutorial material, not part of the installed `gopcnet`
package -- it isn't shipped by `pip install`, and the network-plotting
helper it defines (`plot_network`, plain `matplotlib`, no
`networkx`/`igraph`) is demonstration code, not a `gopcnet` API.

## Running it

`tutorial.py` is written in "percent" cell format (`# %%` / `# %%
[markdown]` markers) and `tutorial.ipynb` is generated directly from
it, so both contain identical content -- pick whichever fits your
workflow:

```bash
# as a plain script -- figures are saved to tutorial_output/, not shown interactively
python examples/tutorial.py
```

```bash
# as a notebook -- figures render inline, cell by cell
jupyter notebook examples/tutorial.ipynb
```

Either way, expect it to take a few minutes to run: several steps
(bootstrap edge stability, the CS-coefficient's case-drop bootstrap,
the difference test, the network comparison test) each refit the
network hundreds of times, the same as they would on a real dataset.

## Keeping the notebook in sync

If you edit `tutorial.py`, regenerate `tutorial.ipynb` from it rather
than editing the notebook directly (the notebook has no content of its
own beyond what's in the script). There's no `jupytext` dependency
needed for this -- a notebook's `.ipynb` format is just JSON, so
regenerating it is a matter of re-splitting the script on its `# %%`
markers into notebook cells.
