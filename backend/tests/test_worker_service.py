from app.worker_service import main


def test_worker_service_requires_a_supported_kind(monkeypatch):
    monkeypatch.delenv("DOCPLATFORM_WORKER_KIND", raising=False)
    try:
        main()
    except SystemExit as error:
        assert "render or extraction" in str(error)
    else:
        raise AssertionError("worker service accepted a missing worker kind")
