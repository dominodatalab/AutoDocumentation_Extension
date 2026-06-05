import pytest

from domino_client import normalize_governance_api_host


def test_normalize_governance_api_host_origin():
    assert normalize_governance_api_host("https://cluster.example.com") == "https://cluster.example.com"


def test_normalize_governance_api_host_strips_trailing_slash():
    assert normalize_governance_api_host("https://cluster.example.com/") == "https://cluster.example.com"


def test_normalize_governance_api_host_adds_https_scheme():
    assert normalize_governance_api_host("cluster.example.com") == "https://cluster.example.com"


def test_normalize_governance_api_host_empty_raises():
    with pytest.raises(ValueError):
        normalize_governance_api_host("")
