"""The top-level `gopcnet` namespace is the package's public API
contract -- these tests pin exactly what it exports, so an accidental
removal or omission during future refactors is caught here rather than
discovered by a downstream user."""

import gopcnet


def test_public_api_matches_all() -> None:
    assert set(gopcnet.__all__) == {
        "fit_gopc",
        "fit_gopc_fixed_order",
        "fit_ebicglasso",
        "EBICglassoResult",
        "fit_pc_skeleton",
        "PCSkeletonResult",
        "__version__",
    }


def test_public_names_are_importable_from_top_level() -> None:
    from gopcnet import (
        EBICglassoResult,
        PCSkeletonResult,
        fit_ebicglasso,
        fit_gopc,
        fit_gopc_fixed_order,
        fit_pc_skeleton,
    )

    assert callable(fit_gopc)
    assert callable(fit_gopc_fixed_order)
    assert callable(fit_ebicglasso)
    assert callable(fit_pc_skeleton)
    assert EBICglassoResult is not None
    assert PCSkeletonResult is not None


def test_internal_research_scaffolding_is_not_part_of_the_public_api() -> None:
    """gopcnet.experiments/simulation/bootstrap are excluded from the
    *built* package (pyproject.toml), but remain importable from a
    checkout of this repository itself -- this test only pins that
    they're absent from the documented public surface, not that they
    fail to import here."""
    assert "experiments" not in gopcnet.__all__
    assert "simulation" not in gopcnet.__all__
    assert "bootstrap" not in gopcnet.__all__
