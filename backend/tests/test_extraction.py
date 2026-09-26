import json

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from app.config import Settings
from app.main import create_app
from app.models import Base
from app.storage import LocalStore


def test_local_extraction_normalizes_and_retains_provenance(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    page_model = {"schema_version": 1, "document_id": "doc-1", "pages": [{"page_number": 1,
        "elements": [{"id": "e1", "text": "Invoice Number: INV-7", "box": [1, 2, 30, 40]},
                      {"id": "e2", "text": "Total: $1,234.50", "box": [1, 50, 30, 60]}]}]}
    with TestClient(create_app(engine=engine, store=LocalStore(tmp_path / "objects", 10_000), frontend=tmp_path)) as client:
        response = client.post("/api/extractions/local", json={"schema_id": "invoice", "page_model": page_model})
        assert response.status_code == 200, response.text
        result = response.json()
        assert result["fields"]["invoice_number"]["normalized_value"] == "INV-7"
        assert result["fields"]["total"]["normalized_value"] == "1234.50"
        assert result["fields"]["total"]["source"]["box"] == [1, 50, 30, 60]
        assert result["fields"]["invoice_date"]["review_status"] == "needs_review"

        assert result["page_model"]["pages"][0]["elements"][1]["id"] == "e2"

        linked = client.post("/api/ingestions/missing/extract", json={"schema_id": "invoice"})
        assert linked.status_code == 404


def test_local_extraction_applies_explicit_confidence_profile_and_keeps_raw_score(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    page_model = {"schema_version": 1, "document_id": "calibrated-doc", "pages": [{
        "page_number": 1, "elements": [{"id": "number", "text": "Invoice Number: INV-42", "box": [1, 2, 30, 40]}],
    }]}
    profile = {"contract": "confidence-calibration-v1", "method": "isotonic", "profile_id": "test",
               "schemas": {"invoice": {"fields": {"invoice_number": {"points": [
                   {"raw": 0.0, "calibrated": 0.1}, {"raw": 0.9, "calibrated": 0.8},
                   {"raw": 1.0, "calibrated": 0.8},
               ]}}, "tables": {}}}}
    with TestClient(create_app(engine=engine, store=LocalStore(tmp_path / "objects", 10_000), frontend=tmp_path)) as client:
        response = client.post("/api/extractions/local", json={"schema_id": "invoice",
                                                                 "page_model": page_model,
                                                                 "calibration_profile": profile})
        assert response.status_code == 200, response.text
        field = response.json()["fields"]["invoice_number"]
        assert field["raw_confidence"] == 0.9
        assert field["confidence"] == 0.8
        assert response.json()["confidence_calibration"]["profile_id"] == "test"


def test_invalid_confidence_profile_returns_a_clear_error(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with TestClient(create_app(engine=engine, store=LocalStore(tmp_path / "objects", 10_000), frontend=tmp_path)) as client:
        response = client.post("/api/extractions/local", json={"schema_id": "invoice",
                                                                 "page_model": {"pages": []},
                                                                 "calibration_profile": {"contract": "bad"}})
        assert response.status_code == 422
        assert "confidence-calibration-v1" in response.json()["detail"]


def test_configured_confidence_profile_is_applied_without_request_payload(tmp_path):
    profile_path = tmp_path / "calibration.json"
    profile = {"contract": "confidence-calibration-v1", "method": "isotonic", "profile_id": "configured",
               "schemas": {"invoice": {"fields": {"invoice_number": {"points": [
                   {"raw": 0.0, "calibrated": 0.2}, {"raw": 0.9, "calibrated": 0.7},
                   {"raw": 1.0, "calibrated": 0.7},
               ]}}, "tables": {}}}}
    profile_path.write_text(json.dumps(profile), encoding="utf-8")
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    settings = Settings(confidence_calibration_path=profile_path)
    page_model = {"schema_version": 1, "document_id": "configured-doc", "pages": [{
        "page_number": 1, "elements": [{"id": "number", "text": "Invoice Number: INV-42", "box": [1, 2, 30, 40]}],
    }]}
    with TestClient(create_app(settings=settings, engine=engine,
                              store=LocalStore(tmp_path / "objects", 10_000), frontend=tmp_path)) as client:
        response = client.post("/api/extractions/local", json={"schema_id": "invoice",
                                                                 "page_model": page_model})
        assert response.status_code == 200, response.text
        assert response.json()["fields"]["invoice_number"]["confidence"] == 0.7
        assert response.json()["confidence_calibration"]["profile_id"] == "configured"


def test_local_extraction_matches_bounded_multilingual_label_aliases(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    labels = {
        "ar": "\u0627\u0644\u0625\u062c\u0645\u0627\u0644\u064a",
        "hi": "\u0915\u0941\u0932",
        "th": "\u0e23\u0e27\u0e21\u0e17\u0e31\u0e49\u0e07\u0e2b\u0e21\u0e14",
        "zh-CN": "\u5408\u8ba1",
        "ja-JP": "\u5408\u8a08",
    }
    with TestClient(create_app(engine=engine, store=LocalStore(tmp_path / "objects", 10_000), frontend=tmp_path)) as client:
        for locale, label in labels.items():
            response = client.post(
                "/api/extractions/local",
                json={
                    "page_model": {"schema_version": 1, "document_id": "doc-multi", "pages": [{
                        "page_number": 1,
                        "elements": [{"id": "e1", "text": f"{label}: 12.50", "box": [1, 2, 30, 40]}],
                    }]},
                    "schema": {"id": "invoice", "fields": [{"name": "total", "type": "currency", "required": True}]},
                    "locale": locale,
                },
            )
            assert response.status_code == 200, response.text
            field = response.json()["fields"]["total"]
            assert field["normalized_value"] == "12.50"
            assert field["original_value"] == "12.50"


def test_extraction_schema_and_validation_errors_are_explicit(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with TestClient(create_app(engine=engine, store=LocalStore(tmp_path / "objects", 10_000), frontend=tmp_path)) as client:
        schemas = client.get("/api/extraction-schemas").json()["items"]
        assert len(schemas) == 3
        for item in schemas:
            sample = client.get(item["sample_url"])
            assert sample.status_code == 200
            body = sample.json()
            assert body["schema"]["id"] == item["id"]
            assert body["sample"]["expected"]["fields"]
            extracted = client.post("/api/extractions/local", json={"schema_id": item["id"],
                                                                      "locale": body["sample"]["locale"],
                                                                      "page_model": body["sample"]["page_model"]}).json()
            for field_name, expected in body["sample"]["expected"]["fields"].items():
                assert extracted["fields"][field_name]["normalized_value"] == expected
            for table_name, rows in body["sample"]["expected"]["tables"].items():
                assert len(extracted["tables"][table_name]["rows"]) == len(rows)
        assert client.get("/api/extraction-schemas/missing/sample").status_code == 404
        invoice = client.get("/api/extraction-schemas/invoice")
        assert invoice.status_code == 200 and invoice.json()["tables"][0]["name"] == "line_items"
        json_schema = client.get("/api/extraction-schemas/invoice/json-schema")
        assert json_schema.status_code == 200 and json_schema.json()["properties"]["line_items"]["type"] == "array"
        valid = client.post("/api/extraction-schemas/validate", json={"schema": invoice.json()})
        assert valid.status_code == 200 and valid.json()["valid"] is True
        assert client.post("/api/extraction-schemas/validate", json={"schema": {"fields": "bad"}}).status_code == 422
        response = client.post("/api/extractions/local", json={"schema": {"fields": []}, "page_model": {"pages": []}})
        assert response.status_code == 200


def test_local_extraction_extracts_line_items_with_column_provenance(tmp_path):
    page_model = {"schema_version": 1, "document_id": "doc-lines", "pages": [{"page_number": 1,
        "elements": [{"id": "row-1", "text": "Widget | 2 | $3.00 | $6.00", "box": [1, 1, 100, 15]}]}]}
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with TestClient(create_app(engine=engine, store=LocalStore(tmp_path / "objects", 10_000), frontend=tmp_path)) as client:
        response = client.post("/api/extractions/local", json={"schema_id": "invoice", "page_model": page_model})
        assert response.status_code == 200, response.text
        line = response.json()["tables"]["line_items"]["rows"][0]["fields"]
        assert line["quantity"]["normalized_value"] == "2"
        assert line["amount"]["source"]["element_id"] == "row-1"


def test_validation_rules_report_range_checksum_and_total_failures(tmp_path):
    page_model = {"schema_version": 1, "document_id": "doc-validation", "pages": [{"page_number": 1,
        "elements": [{"id": "number", "text": "Amount: 12", "box": [1, 1, 20, 10]},
                      {"id": "card", "text": "Card: 79927398713", "box": [1, 11, 20, 20]},
                      {"id": "total", "text": "Total: $2.00", "box": [1, 21, 20, 30]},
                      {"id": "row", "text": "Widget | 1 | $3.00 | $3.00", "box": [1, 31, 100, 40]}]}]}
    schema = {"id": "validation", "fields": [
        {"name": "amount", "type": "number", "labels": ["amount"], "maximum": 10},
        {"name": "card", "type": "string", "labels": ["card"], "checksum": "luhn"},
        {"name": "total", "type": "currency", "labels": ["total"]},
    ], "tables": [{"name": "items", "columns": [
        {"name": "description", "type": "string", "labels": ["description"]},
        {"name": "quantity", "type": "number", "labels": ["quantity"]},
        {"name": "unit_price", "type": "currency", "labels": ["unit price"]},
        {"name": "amount", "type": "currency", "labels": ["amount"]},
    ]}], "totals": [{"field": "total", "table": "items", "column": "amount"}]}
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with TestClient(create_app(engine=engine, store=LocalStore(tmp_path / "objects", 10_000), frontend=tmp_path)) as client:
        result = client.post("/api/extractions/local", json={"schema": schema, "page_model": page_model}).json()
        assert {item["code"] for item in result["fields"]["amount"]["validation"]} == {"maximum"}
        assert result["fields"]["card"]["validation"] == []
        assert {item["code"] for item in result["fields"]["total"]["validation"]} == {"total"}
        assert result["status"] == "needs_review"


def test_locale_normalization_retains_original_values(tmp_path):
    page_model = {"schema_version": 1, "document_id": "doc-locale", "pages": [{"page_number": 1,
        "elements": [{"id": "date", "text": "Datum: 31.12.2025", "box": [1, 1, 20, 10]},
                      {"id": "total", "text": "Summe: 1.234,56 â‚¬", "box": [1, 11, 40, 20]},
                      {"id": "count", "text": "Menge: 1.234,5", "box": [1, 21, 40, 30]}]}]}
    schema = {"id": "locale", "fields": [
        {"name": "date", "type": "date", "labels": ["datum"]},
        {"name": "total", "type": "currency", "labels": ["summe"]},
        {"name": "count", "type": "number", "labels": ["menge"]},
    ]}
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with TestClient(create_app(engine=engine, store=LocalStore(tmp_path / "objects", 10_000), frontend=tmp_path)) as client:
        response = client.post("/api/extractions/local", json={"schema": schema, "locale": "de-DE",
                                                                 "page_model": page_model})
        result = response.json()
        assert response.status_code == 200, response.text
        assert result["fields"]["date"]["normalized_value"] == "2025-12-31"
        assert result["fields"]["total"]["original_value"] == "1.234,56 â‚¬"
        assert result["fields"]["total"]["normalized_value"] == "1234.56"
        assert result["fields"]["count"]["normalized_value"] == "1234.5"


def test_persisted_extraction_correction_and_approval_contract(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with TestClient(create_app(engine=engine, store=LocalStore(tmp_path / "objects", 10_000), frontend=tmp_path)) as client:
        uploaded = client.post("/api/ingestions?filename=scan.png", content=b"\x89PNG\r\n\x1a\n",
                               headers={"content-type": "image/png"}).json()
        extracted = client.post(f"/api/ingestions/{uploaded['id']}/extract",
                                json={"schema_id": "invoice"})
        assert extracted.status_code == 200, extracted.text
        result_id = extracted.json()["result_id"]
        assert client.get(f"/api/extractions/{result_id}").json()["revision"] == 1
        corrected = client.patch(f"/api/extractions/{result_id}/fields/invoice_number",
                                 json={"expected_revision": 1, "value": "INV-9", "source": {
                                     "page_number": 1, "element_id": "invoice-box", "box": [4, 5, 40, 16]},
                                     "actor": "reviewer"})
        assert corrected.status_code == 200 and corrected.json()["revision"] == 2
        added = client.post(f"/api/extractions/{result_id}/fields", json={
            "field": "tax_id", "expected_revision": 2, "value": "TAX-1",
            "source": {"page_number": 1, "element_id": "tax-box", "box": [2, 3, 20, 12]},
        })
        assert added.status_code == 200 and added.json()["revision"] == 3
        absent = client.patch(f"/api/extractions/{result_id}/fields/invoice_number",
                              json={"expected_revision": 3, "value": None, "absent": True})
        assert absent.status_code == 200 and absent.json()["revision"] == 4
        undone = client.post(f"/api/extractions/{result_id}/undo", json={"expected_revision": 4})
        assert undone.status_code == 200 and undone.json()["revision"] == 5
        current = client.get(f"/api/extractions/{result_id}").json()
        assert current["fields"]["tax_id"]["normalized_value"] == "TAX-1"
        assert current["fields"]["tax_id"]["source"]["box"] == [2, 3, 20, 12]
        assert current["fields"]["invoice_number"]["normalized_value"] == "INV-9"
        assert current["fields"]["invoice_number"]["source"]["box"] == [4, 5, 40, 16]
        for state in ("approved", "rejected", "new", "in_review", "approved"):
            assert client.post(f"/api/extractions/{result_id}/review", json={"status": state}).status_code == 200
        audited = client.get(f"/api/extractions/{result_id}").json()
        assert audited["review_events"][-1]["to_status"] == "approved"
        assert audited["review_events"][-1]["actor"] == "local"
        csv = client.get(f"/api/extractions/{result_id}/corrections.csv")
        assert csv.status_code == 200 and all(value in csv.text for value in ("field,original_value,new_value,actor,created_at", "INV-9", "local"))
        exported_json = client.get(f"/api/extractions/{result_id}/export.json")
        assert exported_json.status_code == 200 and exported_json.json()["status"] == "approved"
        assert exported_json.json()["fields"]["invoice_number"]["confidence"] is not None
        assert exported_json.json()["fields"]["invoice_number"]["review_status"]
        exported_csv = client.get(f"/api/extractions/{result_id}/export.csv")
        assert exported_csv.status_code == 200 and all(value in exported_csv.text for value in ("confidence", "review_status", "invoice_number"))
        exported_xlsx = client.get(f"/api/extractions/{result_id}/export.xlsx")
        assert exported_xlsx.status_code == 200
        assert exported_xlsx.headers["content-type"].startswith("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


def test_approved_extraction_binds_named_fields_and_rejects_unapproved_results(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with TestClient(create_app(engine=engine, store=LocalStore(tmp_path / "objects", 10_000), frontend=tmp_path)) as client:
        template = client.post("/api/templates", json={
            "id": "invoice-binding",
            "definition": {"name": "Invoice binding", "blocks": [
                {"type": "text", "text": "Invoice {{invoice_number}} total {{total}}"},
            ]},
        })
        assert template.status_code == 201, template.text
        pdf = b"%PDF-1.4 BT (Invoice Number: INV-42) Tj (Total: $42.00) Tj ET %%EOF"
        uploaded = client.post("/api/ingestions?filename=binding.pdf", content=pdf,
                               headers={"content-type": "application/pdf"})
        assert uploaded.status_code == 201, uploaded.text
        created = client.post(f"/api/ingestions/{uploaded.json()['id']}/extract",
                              json={"schema_id": "invoice"})
        assert created.status_code == 200, created.text
        result_id = created.json()["result_id"]
        assert client.post("/api/templates/invoice-binding/render-approved",
                           json={"extraction_id": result_id}).status_code == 409
        approved = client.post(f"/api/extractions/{result_id}/review", json={"status": "approved"})
        assert approved.status_code == 200, approved.text
        rendered = client.post("/api/templates/invoice-binding/render-approved",
                               json={"extraction_id": result_id})
        assert rendered.status_code == 200, rendered.text
        body = rendered.json()
        assert body["extraction_id"] == result_id
        assert body["data"]["invoice_number"] == "INV-42"
        assert body["data"]["total"] == "42.00"
        assert set(body["data"]) == {"invoice_number", "invoice_date", "total"}
        assert "Invoice INV-42 total 42.00" in body["artifact"]
        assert client.post(f"/api/extractions/{result_id}/review", json={"status": "rejected"}).status_code == 200
        assert client.post("/api/templates/invoice-binding/render-approved",
                           json={"extraction_id": result_id}).status_code == 409
