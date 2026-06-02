from unittest.mock import MagicMock, patch

from autodoc.core.models import BundleAttachment, BundleSummary, ComputedPolicy
from autodoc.scanning.bundle_scanner import (
    ACTIVE_BUNDLE_STATE,
    BundleScanner,
    bundle_matches_models,
)


def _bundle(
    bundle_id: str,
    state: str,
    model_name: str,
    policy_id: str = "policy-1",
) -> BundleSummary:
    return BundleSummary(
        id=bundle_id,
        name=f"bundle-{bundle_id}",
        project_id="proj-1",
        policy_id=policy_id,
        policy_name="Policy",
        state=state,
        evidence_restricted=False,
        attachments=[
            BundleAttachment(
                id="att-1",
                type="ModelVersion",
                identifier={"name": model_name, "version": 1},
            )
        ],
    )


class TestBundleMatchesModels:
    def test_matches_model_version_name(self):
        b = _bundle("b1", ACTIVE_BUNDLE_STATE, "churn-model")
        assert bundle_matches_models(b, {"churn-model"})

    def test_no_match_wrong_name(self):
        b = _bundle("b1", ACTIVE_BUNDLE_STATE, "other")
        assert not bundle_matches_models(b, {"churn-model"})


class TestBundleScanner:
    @patch("autodoc.scanning.bundle_scanner.get_findings")
    @patch("autodoc.scanning.bundle_scanner.compute_policy")
    @patch("autodoc.scanning.bundle_scanner.list_bundles")
    def test_only_active_matching_bundles(
        self, mock_list, mock_compute, mock_findings
    ):
        active = _bundle("active-1", ACTIVE_BUNDLE_STATE, "mymodel")
        archived = _bundle("arch-1", "Archived", "mymodel")
        other_model = _bundle("active-2", ACTIVE_BUNDLE_STATE, "other")
        mock_list.return_value = [active, archived, other_model]

        cp = ComputedPolicy(
            bundle=active,
            policy_id="policy-1",
            policy_name="Policy",
            policy_stages=[],
            results=[],
        )
        mock_compute.return_value = cp
        mock_findings.return_value = []

        out = BundleScanner().scan_for_models({"mymodel"}, project_id="proj-1")

        assert out == [cp]
        mock_compute.assert_called_once_with("active-1", "policy-1")
        mock_findings.assert_called_once_with("active-1")

    @patch("autodoc.scanning.bundle_scanner.list_bundles")
    def test_empty_without_project_id(self, mock_list):
        out = BundleScanner().scan_for_models({"mymodel"}, project_id="")
        assert out == []
        mock_list.assert_not_called()

    @patch("autodoc.scanning.bundle_scanner.list_bundles")
    def test_empty_without_model_names(self, mock_list):
        out = BundleScanner().scan_for_models(set(), project_id="proj-1")
        assert out == []
        mock_list.assert_not_called()

    @patch("autodoc.scanning.bundle_scanner.get_findings")
    @patch("autodoc.scanning.bundle_scanner.compute_policy")
    @patch("autodoc.scanning.bundle_scanner.list_bundles")
    def test_skips_when_compute_policy_fails(
        self, mock_list, mock_compute, mock_findings
    ):
        b = _bundle("b1", ACTIVE_BUNDLE_STATE, "mymodel")
        mock_list.return_value = [b]
        mock_compute.return_value = None

        out = BundleScanner().scan_for_models({"mymodel"}, project_id="proj-1")

        assert out == []
        mock_findings.assert_not_called()
