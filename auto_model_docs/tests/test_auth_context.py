from auth_context import build_request_origin


def test_build_request_origin_from_host_header():
    assert build_request_origin("cluster.example.com", "https") == "https://cluster.example.com"


def test_build_request_origin_strips_apps_prefix():
    assert build_request_origin("apps.cluster.example.com", "https") == "https://cluster.example.com"


def test_build_request_origin_preserves_port():
    assert build_request_origin("cluster.example.com:8443", "https") == "https://cluster.example.com:8443"


def test_build_request_origin_empty():
    assert build_request_origin("") is None
