import pytest

from app.engines import ExtractionEngineError, engine_descriptors, extract_with_engine


def test_local_engine_contract_preserves_result_and_lists_optional_engines():
    page_model = {"schema_version": 1, "document_id": "engine-doc", "pages": [{"page_number": 1,
        "elements": [{"id": "e1", "text": "Invoice Number: INV-1", "box": [1, 2, 30, 40]}]}]}
    schema = {"id": "invoice", "fields": [{"name": "invoice_number", "type": "string",
                                               "labels": ["invoice number"]}]}
    result = extract_with_engine("local-label-extractor", page_model, schema, "en")
    assert result["engine"] == {"id": "local-label-extractor", "version": "0.1"}
    assert any(item.id == "local-label-extractor" and item.available for item in engine_descriptors())


def test_unknown_engine_is_rejected_without_network_access():
    try:
        extract_with_engine("missing-engine", {"pages": []}, {"fields": []}, "en")
    except ExtractionEngineError as exc:
        assert "unavailable" in str(exc)
    else:
        raise AssertionError("unknown engine was accepted")


def test_engine_contract_rejects_invalid_plugin_confidence(monkeypatch):
    class Candidate:
        name = "invalid"

        def load(self):
            class InvalidEngine:
                id = "invalid-engine"
                version = "1.0"
                capabilities = ("scalar-fields",)

                def extract(self, page_model, schema, locale):
                    return {"schema_version": 1, "fields": {"total": {"confidence": 2}}, "tables": {}}

            return InvalidEngine

    class EntryPoints:
        def select(self, *, group):
            assert group == "docplatform.extraction_engines"
            return [Candidate()]

    monkeypatch.setattr("app.engines.entry_points", lambda: EntryPoints())
    try:
        extract_with_engine("invalid-engine", {"pages": []}, {"fields": []}, "en")
    except ExtractionEngineError as exc:
        assert "invalid confidence" in str(exc)
    else:
        raise AssertionError("invalid plugin result was accepted")


def test_engine_contract_rejects_invalid_plugin_provenance(monkeypatch):
    class Candidate:
        name = "invalid-provenance"

        def load(self):
            class InvalidEngine:
                id = "invalid-provenance-engine"
                version = "1.0"
                capabilities = ("scalar-fields", "provenance")

                def extract(self, page_model, schema, locale):
                    return {"schema_version": 1, "fields": {"total": {
                        "confidence": 0.8, "source": {"page_number": 1, "box": [5, 5, 5, 10]},
                    }}, "tables": {}}

            return InvalidEngine

    class EntryPoints:
        def select(self, *, group):
            assert group == "docplatform.extraction_engines"
            return [Candidate()]

    monkeypatch.setattr("app.engines.entry_points", lambda: EntryPoints())
    with pytest.raises(ExtractionEngineError, match="source box"):
        extract_with_engine("invalid-provenance-engine", {"pages": []}, {"fields": []}, "en")


def test_engine_contract_rejects_value_without_provenance(monkeypatch):
    class Candidate:
        name = "missing-source"

        def load(self):
            class MissingSourceEngine:
                id = "missing-source-engine"
                version = "1.0"

                def extract(self, page_model, schema, locale):
                    return {"schema_version": 1, "fields": {"total": {
                        "original_value": "12.00", "normalized_value": "12.00", "confidence": 0.9,
                        "source": None, "validation": [],
                    }}, "tables": {}}

            return MissingSourceEngine

    class EntryPoints:
        def select(self, *, group):
            assert group == "docplatform.extraction_engines"
            return [Candidate()]

    monkeypatch.setattr("app.engines.entry_points", lambda: EntryPoints())
    with pytest.raises(ExtractionEngineError, match="missing provenance"):
        extract_with_engine("missing-source-engine", {"pages": []}, {"fields": []}, "en")


def test_engine_registry_rejects_malformed_plugin_descriptor(monkeypatch):
    class Candidate:
        name = "malformed"

        def load(self):
            class InvalidEngine:
                id = "Not Valid"
                version = "1.0"
                capabilities = ("scalar-fields",)

                def extract(self, page_model, schema, locale):
                    return {"schema_version": 1, "fields": {}, "tables": {}}

            return InvalidEngine

    class EntryPoints:
        def select(self, *, group):
            assert group == "docplatform.extraction_engines"
            return [Candidate()]

    monkeypatch.setattr("app.engines.entry_points", lambda: EntryPoints())
    assert not any(item.id == "Not Valid" for item in engine_descriptors())


def test_valid_plugin_runs_through_registry_and_deduplicates_capabilities(monkeypatch):
    class Candidate:
        name = "sample"

        def load(self):
            class SampleEngine:
                id = "sample-engine"
                version = "1.2.3"
                capabilities = ("provenance", "provenance", "scalar-fields")

                def extract(self, page_model, schema, locale):
                    return {"schema_version": 1, "fields": {}, "tables": {}}

            return SampleEngine

    class EntryPoints:
        def select(self, *, group):
            assert group == "docplatform.extraction_engines"
            return [Candidate()]

    monkeypatch.setattr("app.engines.entry_points", lambda: EntryPoints())
    descriptor = next(item for item in engine_descriptors() if item.id == "sample-engine")
    assert descriptor.capabilities == ("provenance", "scalar-fields")
    result = extract_with_engine("sample-engine", {"pages": []}, {"fields": []}, "en")
    assert result["engine"] == {"id": "sample-engine", "version": "1.2.3"}
