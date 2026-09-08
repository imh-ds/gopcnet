"""The top-level `gopcnet` namespace is the package's public API
contract -- these tests pin exactly what it exports, so an accidental
removal or omission during future refactors is caught here rather than
discovered by a downstream user."""

import gopcnet


def test_public_api_matches_all() -> None:
    assert set(gopcnet.__all__) == {
        "fit_gopc",
        "fit_gopc_fixed_order",
        "GOPCResult",
        "fit_ebicglasso",
        "EBICglassoResult",
        "fit_pc_skeleton",
        "PCSkeletonResult",
        "bootstrap_edge_stability",
        "EdgeStabilityResult",
        "case_drop_bootstrap",
        "CaseDropResult",
        "cs_coefficient",
        "CSCoefficientResult",
        "bootstrap_replicates",
        "BootstrapReplicates",
        "difference_test",
        "DifferenceTestResult",
        "threshold_by_inclusion_probability",
        "compute_centrality",
        "CentralityResult",
        "strength",
        "expected_influence",
        "closeness_centrality",
        "betweenness_centrality",
        "fit_gaussian_graphical_model",
        "GGMFitResult",
        "fit_indices",
        "FitIndicesResult",
        "train_test_fit_indices",
        "TrainTestFitResult",
        "__version__",
    }


def test_public_names_are_importable_from_top_level() -> None:
    from gopcnet import (
        BootstrapReplicates,
        CaseDropResult,
        CentralityResult,
        CSCoefficientResult,
        DifferenceTestResult,
        EBICglassoResult,
        EdgeStabilityResult,
        FitIndicesResult,
        GGMFitResult,
        GOPCResult,
        PCSkeletonResult,
        TrainTestFitResult,
        betweenness_centrality,
        bootstrap_edge_stability,
        bootstrap_replicates,
        case_drop_bootstrap,
        closeness_centrality,
        compute_centrality,
        cs_coefficient,
        difference_test,
        expected_influence,
        fit_ebicglasso,
        fit_gaussian_graphical_model,
        fit_gopc,
        fit_gopc_fixed_order,
        fit_indices,
        fit_pc_skeleton,
        strength,
        threshold_by_inclusion_probability,
        train_test_fit_indices,
    )

    assert callable(fit_gopc)
    assert callable(fit_gopc_fixed_order)
    assert callable(fit_ebicglasso)
    assert callable(fit_pc_skeleton)
    assert callable(bootstrap_edge_stability)
    assert callable(case_drop_bootstrap)
    assert callable(cs_coefficient)
    assert callable(bootstrap_replicates)
    assert callable(difference_test)
    assert callable(threshold_by_inclusion_probability)
    assert callable(compute_centrality)
    assert callable(strength)
    assert callable(expected_influence)
    assert callable(closeness_centrality)
    assert callable(betweenness_centrality)
    assert callable(fit_gaussian_graphical_model)
    assert callable(fit_indices)
    assert callable(train_test_fit_indices)
    assert GOPCResult is not None
    assert EBICglassoResult is not None
    assert PCSkeletonResult is not None
    assert EdgeStabilityResult is not None
    assert CaseDropResult is not None
    assert CSCoefficientResult is not None
    assert BootstrapReplicates is not None
    assert DifferenceTestResult is not None
    assert CentralityResult is not None
    assert GGMFitResult is not None
    assert FitIndicesResult is not None
    assert TrainTestFitResult is not None


def test_internal_research_scaffolding_is_not_part_of_the_public_api() -> None:
    """gopcnet.experiments/simulation/bootstrap are excluded from the
    *built* package (pyproject.toml), but remain importable from a
    checkout of this repository itself -- this test only pins that
    they're absent from the documented public surface, not that they
    fail to import here."""
    assert "experiments" not in gopcnet.__all__
    assert "simulation" not in gopcnet.__all__
    assert "bootstrap" not in gopcnet.__all__
