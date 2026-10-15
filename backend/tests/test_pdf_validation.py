from io import BytesIO

import pytest
from pypdf import PdfWriter
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from app.config import Settings
from app.main import create_app
from app.models import Base
from app.pipeline import PipelineError, ProcessingArtifact, run_pipeline
from app.pdf_validation import PdfValidationStage
from app.pdf_geometry import normalize_pdf_box
from app.storage import LocalStore


def _pdf(*, pages: int = 1, encrypted: bool = False) -> bytes:
    writer = PdfWriter()
    writer.add_metadata({"/Title": "Test intake", "/Author": "Local fixture"})
    for _ in range(pages):
        writer.add_blank_page(width=612, height=792)
    if encrypted:
        writer.encrypt("secret")
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def _artifact(data: bytes) -> ProcessingArtifact:
    return ProcessingArtifact(filename="fixture.pdf", media_type="application/pdf", content=data)


def test_pdf_validation_captures_hash_metadata_and_page_geometry():
    data = _pdf(pages=2)
    result = PdfValidationStage(max_pages=5).process(_artifact(data))

    import hashlib
    assert result.sha256 == hashlib.sha256(data).hexdigest()
    assert result.metadata["title"] == "Test intake"
    assert result.metadata["author"] == "Local fixture"
    assert result.metadata["page_count"] == 2
    assert result.metadata["pages"] == [
        {"page_number": 1, "width_points": 612.0, "height_points": 792.0, "rotation": 0,
         "coordinate_system": "top-left-points", "media_box_pdf_user_space": [0.0, 0.0, 612.0, 792.0],
         "crop_box_pdf_user_space": [0.0, 0.0, 612.0, 792.0],
         "original_width_points": 612.0, "original_height_points": 792.0},
        {"page_number": 2, "width_points": 612.0, "height_points": 792.0, "rotation": 0,
         "coordinate_system": "top-left-points", "media_box_pdf_user_space": [0.0, 0.0, 612.0, 792.0],
         "crop_box_pdf_user_space": [0.0, 0.0, 612.0, 792.0],
         "original_width_points": 612.0, "original_height_points": 792.0},
    ]


@pytest.mark.parametrize(("rotation", "expected", "size"), [
    (0, [10, 160, 30, 180], (100, 200)),
    (90, [20, 10, 40, 30], (200, 100)),
    (180, [70, 20, 90, 40], (100, 200)),
    (270, [160, 70, 180, 90], (200, 100)),
])
def test_pdf_box_normalization_handles_crop_offsets_and_all_right_angle_rotations(rotation, expected, size):
    from app.pdf_geometry import display_size
    assert normalize_pdf_box([110, 220, 130, 240], crop_box=[100, 200, 200, 400], rotation=rotation) == expected
    assert display_size([100, 200, 200, 400], rotation) == size


def test_pdf_validation_returns_structured_reasons_for_invalid_encrypted_and_over_limit():
    stage = PdfValidationStage(max_pages=1)
    with pytest.raises(PipelineError, match="incomplete or malformed") as invalid:
        stage.process(_artifact(_pdf().rsplit(b"%%EOF", 1)[0]))
    assert (invalid.value.stage, invalid.value.code) == ("validate_pdf", "pdf_eof_missing")

    with pytest.raises(PipelineError) as encrypted:
        stage.process(_artifact(_pdf(encrypted=True)))
    assert encrypted.value.code == "pdf_encrypted"

    with pytest.raises(PipelineError) as over_limit:
        stage.process(_artifact(_pdf(pages=2)))
    assert over_limit.value.code == "page_limit_exceeded"


def test_pipeline_runs_replaceable_stages_in_order_and_wraps_unexpected_errors(caplog):
    class Stage:
        def __init__(self, stage_id: str, value: str, fail: bool = False):
            self.stage_id, self.value, self.fail = stage_id, value, fail

        def process(self, artifact: ProcessingArtifact) -> ProcessingArtifact:
            if self.fail:
                raise RuntimeError("internal detail")
            return artifact.model_copy(update={"metadata": {**artifact.metadata, self.stage_id: self.value}})

    result = run_pipeline(_artifact(_pdf()), [Stage("one", "1"), Stage("two", "2")])
    assert result.metadata == {"one": "1", "two": "2"}
    with pytest.raises(PipelineError) as failure:
        run_pipeline(_artifact(_pdf()), [Stage("broken", "", fail=True)])
    assert (failure.value.stage, failure.value.code) == ("broken", "stage_failed")
    assert any(record.processing_stage == "broken" and record.message == "processing_stage_failed"
               for record in caplog.records)


def test_upload_runs_pdf_inspection_in_worker_and_persists_source_evidence(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with TestClient(create_app(
        settings=Settings(job_cpu_seconds=20, job_memory_bytes=512 * 1024 * 1024),
        engine=engine, store=LocalStore(tmp_path / "objects", 1_000_000), frontend=tmp_path,
    )) as client:
        response = client.post("/api/ingestions?filename=fixture.pdf", content=_pdf(),
                               headers={"content-type": "application/pdf"})
        assert response.status_code == 201, response.text
        result = client.get(f"/api/ingestions/{response.json()['id']}/result").json()
        source = result["page_model"]["source"]
        assert len(source["sha256"]) == 64
        assert source["metadata"]["page_count"] == 1
        assert source["metadata"]["pages"][0]["width_points"] == 612


def test_upload_returns_structured_reasons_for_malformed_encrypted_and_over_limit_pdfs(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with TestClient(create_app(
        settings=Settings(max_pages_per_document=1), engine=engine,
        store=LocalStore(tmp_path / "objects", 1_000_000), frontend=tmp_path,
    )) as client:
        cases = [
            (_pdf().rsplit(b"%%EOF", 1)[0], 422, "pdf_eof_missing"),
            (_pdf(encrypted=True), 422, "pdf_encrypted"),
            (_pdf(pages=2), 413, "page_limit_exceeded"),
        ]
        for data, status, code in cases:
            response = client.post("/api/ingestions?filename=invalid.pdf", content=data,
                                   headers={"content-type": "application/pdf"})
            assert response.status_code == status
            assert response.json()["detail"]["code"] == code
