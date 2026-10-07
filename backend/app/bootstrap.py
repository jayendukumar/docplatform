"""Apply migrations and seed without logging credentials or database exceptions."""
import json
from pathlib import Path
import sys
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from app.config import load_settings
from app.database import create_database
from app.migrations import migrate
from app.models import Template, TemplateVersion
from app.storage import create_store
from app.isda_template import editable_isda_blocks, is_placeholder_isda, isda_data_schema, isda_sample_data

SAMPLE = Path(__file__).resolve().parents[1] / "samples" / "welcome.json"


def _merge_sample_defaults(defaults, existing):
    """Keep existing preview values while filling newly governed nested paths."""
    if not isinstance(defaults, dict) or not isinstance(existing, dict):
        return existing if existing is not None else defaults
    merged = dict(defaults)
    for key, value in existing.items():
        if isinstance(merged.get(key), dict) and isinstance(value, dict):
            merged[key] = _merge_sample_defaults(merged[key], value)
        else:
            merged[key] = value
    return merged


def seed(engine, store):
    sample = json.loads(SAMPLE.read_text(encoding="utf-8"))
    key = "templates/sample-welcome/v1.json"
    with engine.begin() as connection:
        if not connection.execute(select(Template.id).where(Template.id == "sample-welcome")).first():
            # Store first: a failed database transaction can leave an unreferenced object,
            # but cannot publish metadata pointing to an object that was never written.
            store.put(key, json.dumps(sample, ensure_ascii=False).encode("utf-8"))
            connection.execute(insert(Template).values(
                id="sample-welcome", name=sample["name"], object_key=key, schema_version=1,
            ).on_conflict_do_nothing(index_elements=[Template.id]))

        isda = connection.execute(select(Template.id, Template.object_key).where(Template.id == "isda-template")).mappings().one_or_none()
        if isda:
            try:
                definition = json.loads(store.get(isda["object_key"]))
            except (FileNotFoundError, json.JSONDecodeError):
                definition = {}
            latest_draft = connection.execute(select(TemplateVersion.definition_json).where(TemplateVersion.template_id == "isda-template", TemplateVersion.status == "draft").order_by(TemplateVersion.version.desc())).scalars().first()
            if latest_draft:
                try:
                    definition = json.loads(latest_draft)
                except json.JSONDecodeError:
                    pass
            page = definition.get("page") if isinstance(definition, dict) else None
            removed_locked_background = isinstance(page, dict) and "background_pdf" in page
            if removed_locked_background:
                definition["page"] = {key: value for key, value in page.items() if key != "background_pdf"}
            if is_placeholder_isda(definition):
                definition["blocks"] = editable_isda_blocks()
                definition.setdefault("name", "ISDA Template")
                definition["sample_data"] = {**isda_sample_data(), **(definition.get("sample_data") or {})}
                definition["data_schema"] = isda_data_schema()
                definition["data_schema_id"] = "isda-master-agreement"
                definition["data_schema_version"] = 2
                store.put(isda["object_key"], json.dumps(definition, ensure_ascii=False).encode("utf-8"))
                connection.execute(TemplateVersion.__table__.update().where(TemplateVersion.template_id == "isda-template", TemplateVersion.status == "draft").values(definition_json=json.dumps(definition, ensure_ascii=False)))
            else:
                blocks = definition.get("blocks")
                table = next((block for block in blocks if isinstance(block, dict) and block.get("semantic_id") == "schedule-documents"), None) if isinstance(blocks, list) else None
                tax_table = next((block for block in blocks if isinstance(block, dict) and block.get("semantic_id") == "schedule-tax-documents"), None) if isinstance(blocks, list) else None
                if isinstance(table, dict) and [column.get("path") for column in table.get("columns", []) if isinstance(column, dict)] != ["party_required", "form_document", "delivery_date", "covered_by_section_3d"]:
                    table = None
                if isinstance(tax_table, dict) and [column.get("path") for column in tax_table.get("columns", []) if isinstance(column, dict)] != ["party_required", "form_document", "delivery_date"]:
                    tax_table = None
                sample_documents = (definition.get("sample_data") or {}).get("schedule_documents") if isinstance(definition.get("sample_data"), dict) else None
                if isinstance(table, dict) and (not isinstance(sample_documents, list) or any(not isinstance(row, dict) or "party_required" not in row or "form_document" not in row for row in sample_documents)):
                    table = None
                sample_tax_documents = (definition.get("sample_data") or {}).get("schedule_tax_documents") if isinstance(definition.get("sample_data"), dict) else None
                if isinstance(tax_table, dict) and (not isinstance(sample_tax_documents, list) or any(not isinstance(row, dict) or "party_required" not in row or "form_document" not in row or "delivery_date" not in row for row in sample_tax_documents)):
                    tax_table = None
                semantic_ids = {block.get("semantic_id") for block in blocks if isinstance(block, dict)} if isinstance(blocks, list) else set()
                source_owner_expectations = {"credit-support-provider-party-x": 34, "credit-support-document-party-x": 34}
                if isinstance(table, dict) and any(
                    next((block.get("page_number") for block in blocks if isinstance(block, dict) and block.get("semantic_id") == semantic_id), None) != page_number
                    for semantic_id, page_number in source_owner_expectations.items()
                ):
                    table = None
                required_isda_ids = {
                    "specified-indebtedness", "additional-termination-event", "notice-email-party-x", "notice-email-party-y", "absence-litigation-specified-entity-party-x", "absence-litigation-specified-entity-party-y", "master-signature-party-x-name-of-party", "master-signature-party-y-name-of-party", "signature-party-x-name-of-party", "signature-party-y-name-of-party", "section-5-force-majeure", "section-5-tax-event-upon-merger", "section-5-additional-termination-event", "section-6-termination-event-notice", "section-6-transfer-to-avoid-event", "section-6-right-to-terminate", "section-6-effect-designation", "section-6-payments-early-termination", "section-6-mid-market-events", "section-6-adjustments", "section-6-pre-estimate", "section-7-transfer-exceptions", "section-8-payment-currency", "section-8-separate-indemnities", "section-8-evidence-of-loss", "section-9-entire-agreement", "section-9-amendments", "definitions-affected-transactions", "definitions-affiliate-agreement", "definitions-automatic-early-termination", "definitions-close-out-amount", "definitions-confirmation-consent", "definitions-credit-event-merger", "definitions-credit-support-document", "definitions-credit-support-provider", "definitions-default-and-determining-party", "definitions-early-termination-illegality", "section-9-defaulted-payments", "section-9-defaulted-deliveries", "section-9-deferred-payments", "section-9-interest-calculation", "section-9-early-termination-interest", "section-9-unpaid-amounts", "section-10-office-recourse", "section-10-office-selection", "section-12-change-details", "section-13-service-process",
                    "notice-messaging-party-x", "notice-messaging-party-y", "notice-instructions-party-x", "notice-instructions-party-y", "definition-indemnifiable-tax", "definition-law", "definition-local-business-day", "definition-loss", "definition-non-defaulting-party", "definition-notice", "definition-potential-event-of-default", "definition-specified-entity", "definition-specified-indebtedness", "definition-tax", "definition-unpaid-amounts", "definition-additional-representation", "definition-additional-termination-event", "definition-affected-party", "definition-applicable-close-out-rate", "definition-applicable-deferral-rate", "definition-burdened-party", "definition-change-tax-law", "definition-contractual-currency", "definition-close-out-good-faith", "definition-confirmation", "definition-default-rate", "definition-defaulting-party", "definition-designated-event", "definition-determining-party", "definition-early-termination-amount", "definition-early-termination-date", "definition-illegality", "schedule-part1-termination-purpose", "schedule-cross-default-purpose", "schedule-tax-purpose", "schedule-agreements-purpose", "schedule-process-agent-purpose", "schedule-payment-netting-purpose", "schedule-other-provisions-purpose", "signature-attestation", "section-1-definitions", "section-1-inconsistency", "section-1-single-agreement", "section-2-payment-obligations", "section-2-delivery-obligations", "section-2-netting-payments", "section-2-tax-withholding", "section-3-status", "section-3-powers", "section-3-authorisations", "section-3-no-conflict", "section-3-binding-obligations", "section-3-absence-litigation", "section-3-specified-information", "section-3-payer-tax", "section-3-payee-tax", "section-3-no-agency", "section-4-furnish-information", "section-4-maintain-authorisations", "section-4-comply-laws", "section-4-notify-tax-failure", "section-4-stamp-tax", "section-5-failure-pay-deliver", "section-5-breach-repudiation", "section-5-credit-support-default", "section-5-misrepresentation", "section-5-default-specified-transaction", "section-5-cross-default", "section-5-bankruptcy", "section-5-merger-without-assumption", "section-5-misrepresentation-consequence", "section-5-specified-transaction-consequence", "section-5-cross-default-consequence", "section-5-bankruptcy-consequence", "section-5-merger-consequence", "section-5-waiting-period-deferrals", "section-6-designation-notice", "section-6-no-further-payments", "section-6-calculation-delivery", "section-6-set-off-right", "section-7-consent", "section-7-permitted-transfers", "section-8-judgment-conversion", "section-9-survival", "section-9-remedies", "section-9-counterparts-confirmations",
                    "offices-application", "credit-support-provider-party-y", "governing-law", "additional-representation",
                    "specified-entity-5a-v-party-x", "specified-entity-5b-v-party-y", "tax-jurisdiction-party-y", "schedule-agreement-date", "schedule-tax-documents", "additional-representation-detail", "recording-conversations", "specified-treaty-party-x", "specified-treaty-party-y", "specified-jurisdiction-party-x", "specified-jurisdiction-party-y", "payer-representation-choice-party-x", "payer-representation-choice-party-y", "payee-representation-choice-party-x", "payee-representation-choice-party-y", "grace-period-party-x", "grace-period-party-y", "automatic-early-termination-party-x", "automatic-early-termination-party-y",
                }
                required_isda_ids.update({"schedule-agreement-date", "specified-transaction-detail", "specified-indebtedness-detail", "additional-termination-event-detail", "termination-currency-detail", "payer-representation-detail-party-x", "payer-representation-detail-party-y", "payee-representation-detail-party-x", "payee-representation-detail-party-y", "multibranch-offices-party-x", "multibranch-offices-party-y", "section-6-termination-event-notice", "section-6-force-majeure-notice", "section-7-corporate-asset-transfers", "section-7-early-termination-interest-transfers", "section-5-designated-event", "section-5-designated-event-consolidation", "section-5-designated-event-control", "section-5-designated-event-capital-structure", "section-5-hierarchy-illegality-default", "section-5-hierarchy-other-termination-event", "section-5-hierarchy-force-majeure-illegality", "section-5-deferral-waiting-period", "section-5-deferral-event-ceases", "section-5-head-home-office-obligations", "section-6-right-to-terminate-illegality", "section-6-effect-designation-due-amount", "section-6-early-termination-default-amount", "section-6-early-termination-one-affected-party", "section-6-early-termination-two-affected-parties", "section-6-mid-market-values", "section-6-adjustment-illegality-force-majeure", "section-6-set-off-other-amounts", "section-6-set-off-conversion", "section-9-illegality-force-majeure-interest", "section-9-early-termination-amount-interest", "section-10-multibranch-offices", "section-10-office-booking-consent", "section-12-notice-methods", "section-12-notice-local-business-day", "section-13-jurisdiction-submission", "section-13-jurisdiction-multiple", "section-13-process-agent-replacement", "definitions-applicable-close-out-rate-early-termination", "definitions-applicable-close-out-rate-post-payment", "definitions-affected-transactions-other", "definitions-agreement", "definitions-applicable-deferral-rate-prime", "definitions-applicable-deferral-rate-mean", "definitions-close-out-amount-scope", "definitions-close-out-amount-determination", "definitions-close-out-amount-information", "definitions-close-out-market-information", "definitions-close-out-valuation-methods", "definitions-consent", "definitions-cross-default", "definitions-electronic-messages", "definitions-english-law", "definitions-event-of-default", "definitions-force-majeure-event", "definitions-general-business-day", "definitions-indemnifiable-tax", "definitions-law", "definitions-local-business-day", "definitions-loss", "definitions-market-quotation", "definitions-non-defaulting-party", "definitions-notice", "definitions-office", "definitions-potential-event-of-default", "definitions-proceedings", "definitions-specified-entity", "definitions-specified-indebtedness", "definitions-tax", "definitions-termination-event", "definitions-transaction-term", "definitions-unpaid-amounts"})
                if isinstance(table, dict) and not required_isda_ids.issubset(semantic_ids):
                    table = None
                if isinstance(blocks, list) and "schedule-intro-purpose" not in semantic_ids:
                    table = None
                signature_field = next((block for block in blocks if isinstance(block, dict) and block.get("semantic_id") == "signature-party-x-by"), None) if isinstance(blocks, list) else None
                if isinstance(blocks, list) and (removed_locked_background or len(blocks) < 143 or "master-signature-party-x-by" not in semantic_ids or "schedule-other-provisions" not in semantic_ids or "section-5-illegality" not in semantic_ids or "section-6-early-termination" not in semantic_ids or "section-9-miscellaneous" not in semantic_ids or "agreement-opening" not in semantic_ids or "agreement-opening-party-x" not in semantic_ids or "agreement-opening-party-y" not in semantic_ids or "execution-attestation" not in semantic_ids or "section-1-interpretation" not in semantic_ids or "section-9-interest" not in semantic_ids or "definitions-credit-support" not in semantic_ids or "definition-market-quotation" not in semantic_ids or "counterparty-type-party-x" not in semantic_ids or "schedule-intro" not in semantic_ids or "execution-clause" not in semantic_ids or not isinstance(signature_field, dict) or signature_field.get("position_mode") != "absolute" or table is None or tax_table is None or any(not isinstance(column, dict) or column.get("width") is None for column in table.get("columns", [])) or any(not isinstance(column, dict) or column.get("width") is None for column in tax_table.get("columns", [])) or not isinstance(definition.get("data_schema"), dict) or definition.get("data_schema_id") != "isda-master-agreement" or definition.get("data_schema_version") != 3 or not any("1. Interpretation" in str(block.get("text", "")) for block in blocks if isinstance(block, dict)) or not any("6. Early Termination; Close-Out Netting" in str(block.get("text", "")) for block in blocks if isinstance(block, dict)) or not any("10. Offices; Multibranch Parties" in str(block.get("text", "")) for block in blocks if isinstance(block, dict))):
                    definition["blocks"] = editable_isda_blocks()
                    definition["sample_data"] = _merge_sample_defaults(isda_sample_data(), definition.get("sample_data") or {})
                    definition["sample_data"]["schedule_documents"] = isda_sample_data()["schedule_documents"]
                    definition["sample_data"]["schedule_tax_documents"] = isda_sample_data()["schedule_tax_documents"]
                    definition["data_schema"] = isda_data_schema()
                    definition["data_schema_id"] = "isda-master-agreement"
                    definition["data_schema_version"] = 3
                    store.put(isda["object_key"], json.dumps(definition, ensure_ascii=False).encode("utf-8"))
                    connection.execute(TemplateVersion.__table__.update().where(TemplateVersion.template_id == "isda-template", TemplateVersion.status == "draft").values(definition_json=json.dumps(definition, ensure_ascii=False)))


def main():
    engine = None
    try:
        settings = load_settings()
        engine = create_database(settings)
        migrate(engine)
        store = create_store(settings)
        store.check()
        if settings.seed_sample:
            seed(engine, store)
        print("Foundation initialized: migrations, storage and sample are ready")
        return 0
    except Exception:
        print("Foundation initialization failed; check database, storage and configuration", file=sys.stderr)
        return 1
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
