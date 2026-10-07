"""Editable, page-owned ISDA authoring scaffold.

FROZEN (DD-417): do not extend this hand-written builder. ISDA reconstruction now
belongs to the E16 fidelity harness, which may use only the editor-reachable
template contract. Retire this module once the harness reproduces the document.
"""

from __future__ import annotations


PAGE_SECTIONS = tuple(
    (heading, text) for heading, text in [
        ("2002 MASTER AGREEMENT", "ISDA 2002 Master Agreement\nDated as of {{agreement_date}}\nbetween {{party_x}} and {{party_y}}."),
        ("Section 2 - Obligations", "Payments and deliveries."), ("Section 2 - Netting and tax", "Payment netting and tax."),
        ("Section 3 - Representations", "Representations."), ("Section 4 - Agreements", "Agreements."),
        ("Section 5 - Events of Default", "Events of Default."), ("Section 5 - Cross-default", "Cross-default."),
        ("Section 5 - Merger", "Merger without assumption."), ("Section 5 - Illegality", "Illegality and force majeure."),
        ("Section 5 - Change of control", "Change of control."), ("Section 5 - Termination events", "Termination events."),
        ("Section 6 - Early termination", "Early termination."), ("Section 6 - Calculations", "Calculations and payment date."),
        ("Section 6 - Close-out", "Close-out amount."), ("Section 6 - Set-off", "Set-off."),
        ("Section 8 - Miscellaneous", "Miscellaneous."), ("Section 9 - Interest", "Interest and compensation."),
        ("Section 9 - Calculation agent", "Calculation agent."), ("Section 10 - Offices", "Offices and multibranch parties."),
        ("Section 11 - Transfers", "Transfers."), ("Section 12 - Contractual currency", "Contractual currency."),
        ("Section 13 - Notices", "Notices."), ("Section 13 - Proceedings", "Process agent and proceedings."),
        ("Section 14 - Definitions", "Definitions."), ("Section 14 - Defined terms", "Definitions continued."),
        ("Section 14 - Currency terms", "Currency and payment definitions."), ("Section 14 - Termination terms", "Termination definitions."),
        ("Execution", "IN WITNESS WHEREOF."), ("SCHEDULE - General", "SCHEDULE to the 2002 Master Agreement."),
        ("SCHEDULE - Termination provisions", "Termination provisions."), ("SCHEDULE - Tax representations", "Tax representations."),
        ("SCHEDULE - Additional provisions", "Additional representations and agreements."), ("SCHEDULE - Documents", "Documents to be delivered."),
        ("SCHEDULE - Process agent", "Process agent and offices."), ("SCHEDULE - Payment netting", "Netting of payments."),
        ("Execution signatures", "Execution signatures."),
    ]
)


SOURCE_PAGE_OVERRIDES = {
    1: "ISDA 2002 Master Agreement\ndated as of {{agreement_date}}\n{{party_x}} and {{party_y}} have entered into Transactions governed by this Master Agreement, the Schedule and Confirmations.\n\n1. Interpretation\n(a) Definitions. Terms defined in Section 14 have the specified meanings.\n(b) Inconsistency. The Schedule prevails over this Agreement and a Confirmation prevails for its Transaction.\n(c) Single Agreement. All Transactions and Confirmations form a single agreement.",
    2: "2. Obligations\n(a) General Conditions\nEach party will make each payment or delivery specified in each Confirmation, subject to the applicable conditions precedent.",
    3: "(b) Change of Account. Either party may change its receiving account by notice.\n(c) Netting of Payments. Amounts in the same currency payable on the same date may be netted.\n(d) Deduction or Withholding for Tax. Payments are made without withholding unless required by law.\n\n3. Representations\nEach party makes the representations specified in this Agreement and Schedule.",
    4: "(a) Basic Representations\nEach party represents its status, powers, authorisations, absence of conflict and binding obligations.\n(b) Absence of Certain Events. No Event of Default, Potential Event of Default or Termination Event has occurred and is continuing.",
    5: "(c) Absence of Litigation. No proceeding materially affects performance.\n(d) Accuracy of Specified Information. Information identified in the Schedule is true and complete.\n(e) Payer Tax Representation. Each specified representation is accurate.\n(f) Payee Tax Representations. Each specified representation is accurate.\n(g) No Agency. Each party enters as principal.",
    6: "4. Agreements\nEach party will furnish information, maintain authorisations, comply with laws, notify tax-representation failures and pay applicable Stamp Tax.",
    7: "5. Events of Default and Termination Events\nEvents include failure to pay or deliver, breach or repudiation, Credit Support Default, misrepresentation, default under a Specified Transaction, Cross-Default, Bankruptcy and Merger Without Assumption.",
    8: "Misrepresentation, Default Under Specified Transaction, Cross-Default, Bankruptcy and Merger Without Assumption have the consequences specified in Section 5 and the Schedule.",
    9: "(b) Termination Events\nIllegality, Force Majeure Event, Tax Event and Tax Event Upon Merger apply as specified in this Agreement and Schedule.",
    10: "Credit Event Upon Merger and Additional Termination Event apply where specified. The Agreement sets the event hierarchy and waiting-period deferrals.",
    11: "6. Early Termination; Close-Out Netting\nFollowing an Event of Default or Termination Event, the applicable party may designate an Early Termination Date subject to the notice and transfer requirements.",
    12: "A party may designate an Early Termination Date if a required transfer or agreement is not effected. On designation, no further payments or deliveries for Terminated Transactions are required, subject to the Agreement.",
    13: "(d) Calculations; Payment Date\nEach party provides calculations, any Early Termination Amount and the relevant payment account. The amount is payable on the applicable Payment Date.",
    14: "(e) Termination Events. The Early Termination Amount is determined by the applicable party and valuation method.\n(f) Set-Off. It may be reduced by set-off without creating a security interest.",
    15: "7. Transfer\nInterests and obligations may not be transferred without consent, subject to permitted transfers.\n8. Contractual Currency\nPayments are made in the relevant Contractual Currency.",
    16: "8. Contractual Currency (continued)\nA judgment in another currency is converted using commercially reasonable procedures.\n9. Miscellaneous\nThe Agreement addresses amendments, survival, remedies, counterparts and confirmations.",
    17: "(h) Interest and Compensation\nDefaulted payments bear interest at the Default Rate. A defaulted delivery may require compensation. Deferred payments accrue interest at the Applicable Deferral Rate.",
    18: "Interest and compensation continue for deferred deliveries and are calculated in the relevant currency, subject to the Confirmation and this Agreement.",
    19: "10. Offices; Multibranch Parties\nThe Schedule identifies Offices through which Transactions may be entered, booked and settled.\n11. Expenses\nA Defaulting Party indemnifies reasonable expenses.\n12. Notices\nNotices use the specified addresses and methods.",
    20: "12. Notices (continued)\nA notice is effective when delivered by the specified method and address.\n13. Governing Law and Jurisdiction\nThe Schedule specifies governing law, jurisdiction and any Process Agent.",
    21: "14. Definitions\nAdditional Representation, Additional Termination Event, Affected Party, Affected Transactions, Affiliate, Agreement and Applicable Close-out Rate have the meanings specified in the relevant Sections and Schedule.",
    22: "Applicable Deferral Rate, Automatic Early Termination, Burdened Party, Change in Tax Law, Close-out Amount and Contractual Currency have the meanings specified in this Agreement.",
    23: "Close-out Amount is determined in good faith using commercially reasonable procedures. Confirmation, consent, Credit Event Upon Merger and Credit Support Document have the meanings specified in this Agreement.",
    24: "Credit Support Provider, Cross-Default, Default Rate, Defaulting Party, Designated Event, Determining Party, Early Termination Amount, Early Termination Date and Illegality have the meanings specified in the Agreement.",
    25: "Indemnifiable Tax, Law, Local Business Day, Loss and Market Quotation are defined for tax allocation, business-day timing and close-out valuation.",
    26: "Non-defaulting Party, Notice, Office, Potential Event of Default and Proceedings identify the parties, communications, branches and proceedings used by the Agreement.",
    27: "Specified Entity, Specified Indebtedness, Tax, Termination Event, Transaction and Unpaid Amounts have the meanings assigned in the Agreement, Schedule and Confirmation.",
    28: "EXECUTION\nIN WITNESS WHEREOF the parties have executed this Agreement as of the date specified above. Each signatory confirms due authorisation.",
    29: "SCHEDULE to the 2002 Master Agreement\nThe Schedule supplements and forms part of the Agreement between {{party_x}} and {{party_y}}.\n\nPART 1. TERMINATION PROVISIONS\nSpecified Entity and Specified Transaction details are recorded for each party.",
    30: "PART 1. TERMINATION PROVISIONS (continued)\nThe parties specify Cross-Default thresholds, grace periods, Credit Event Upon Merger, Automatic Early Termination and Additional Termination Events.",
    31: "PART 2. TAX REPRESENTATIONS\nPayer and Payee Tax Representations are selected by party. The Schedule records tax forms, certificates, delivery dates and jurisdictions.",
    32: "PART 3. AGREEMENTS\nThe parties identify documents to be delivered, Credit Support Providers, Credit Support Documents and additional representations or agreements.",
    34: "PART 4. PROCESS AGENT AND OFFICES\nParty A process agent: {{party_x}}. Party B process agent: {{party_y}}. The parties record process agents, Offices and notice details.",
    35: "PART 5. PAYMENT NETTING\nThe parties specify whether Multiple Transaction Payment Netting applies and identify Transactions, currencies, Offices and limitations.",
    36: "EXECUTION SIGNATURES\nIN WITNESS WHEREOF the parties have executed this Agreement.\n\n{{party_x}}\nBy: ____________________   Name: ____________________   Title: ____________________\nDate: ____________________\n\n{{party_y}}\nBy: ____________________   Name: ____________________   Title: ____________________\nDate: ____________________",
}


def editable_isda_blocks() -> list[dict]:
    blocks = []
    for page_number, (heading, fallback) in enumerate(PAGE_SECTIONS, start=1):
        if page_number >= 25:
            blocks.extend(_definitions_and_schedule_blocks(page_number))
            continue
        if page_number <= 8:
            blocks.extend(_section_one_to_five_blocks(page_number))
            continue
        if page_number <= 16:
            blocks.extend(_section_five_to_eight_blocks(page_number))
            continue
        if page_number >= 17:
            blocks.extend(_section_nine_to_definitions_blocks(page_number))
            continue
        block = {"type": "text", "text": SOURCE_PAGE_OVERRIDES.get(page_number, fallback), "font_family": "Times New Roman", "font_size": 11, "color": "#171717", "align": "left", "bold": heading in {"2002 MASTER AGREEMENT", "Execution", "SCHEDULE - General", "Execution signatures"}, "line_height": 1.15, "paragraph_spacing_after": 7, "keep_with_next": page_number < len(PAGE_SECTIONS), "break_before": page_number > 1, "page_number": page_number, "position_mode": "flow", "position_unit": "mm", "anchor_id": f"isda-page-{page_number}", "toc_label": heading, "toc_level": 1 if page_number in {1, 29, 36} else 2, "semantic_kind": "clause", "semantic_id": f"isda-page-clause-{page_number}"}
        if page_number == 33:
            block.update({"type": "table", "text": heading, "items": "schedule_documents", "columns": [{"header": "Party required", "path": "party_required", "format": "text", "width": 20}, {"header": "Form/Document/Certificate", "path": "form_document", "format": "text", "width": 45}, {"header": "Delivery date", "path": "delivery_date", "format": "date", "width": 20}, {"header": "Section 3(d)", "path": "covered_by_section_3d", "format": "text", "width": 15}]})
        blocks.append(block)
    return blocks


def _section_one_to_five_blocks(page_number: int) -> list[dict]:
    """Split the opening source-aligned pages without inventing new legal text."""
    clauses: dict[int, list[dict]] = {
        1: [
            _isda_text(1, "agreement-opening", "ISDA 2002 Master Agreement", heading=True),
            _isda_text(1, "agreement-opening-date", "dated as of {{agreement_date}}", kind="field", field_path="agreement_date", field_role="Agreement date"),
            _isda_text(1, "agreement-opening-party-x", "{{party_x}}", kind="field", field_path="party_x", field_role="Party A legal name"),
            _isda_text(1, "agreement-opening-party-y", "{{party_y}}", kind="field", field_path="party_y", field_role="Party B legal name"),
            _isda_text(1, "agreement-opening-parties-context", "have entered into Transactions governed by this Master Agreement, the Schedule and Confirmations."),
            _isda_text(1, "section-1-interpretation", "1. Interpretation", heading=True),
            _isda_text(1, "section-1-definitions", "(a) Definitions. Terms defined in Section 14 have the specified meanings.", kind="clause"),
            _isda_text(1, "section-1-inconsistency", "(b) Inconsistency. The Schedule prevails over this Agreement and a Confirmation prevails for its Transaction.", kind="clause"),
            _isda_text(1, "section-1-single-agreement", "(c) Single Agreement. All Transactions and Confirmations form a single agreement.", kind="clause"),
        ],
        2: [
            _isda_text(2, "section-2-obligations", "2. Obligations", heading=True, break_before=True),
            _isda_text(2, "section-2-general-conditions", "(a) General Conditions", heading=True),
            _isda_text(2, "section-2-payment-obligations", "Each party will make each payment specified in each Confirmation, subject to the applicable conditions precedent.", kind="clause"),
            _isda_text(2, "section-2-delivery-obligations", "Each party will make each delivery specified in each Confirmation, subject to the applicable conditions precedent.", kind="clause"),
        ],
        3: [
            _isda_text(3, "section-2-change-account", "(b) Change of Account. Either party may change its receiving account by notice.", heading=True, break_before=True),
            _isda_text(3, "section-2-netting-tax", "(c) Netting of Payments; (d) Deduction or Withholding for Tax", heading=True),
            _isda_text(3, "section-2-netting-payments", "(c) Netting of Payments. Amounts in the same currency payable on the same date may be netted.", kind="clause"),
            _isda_text(3, "section-2-tax-withholding", "(d) Deduction or Withholding for Tax. Payments are made without withholding unless required by law.", kind="clause"),
            _isda_text(3, "section-3-representations-opening", "3. Representations\nEach party makes the representations specified in this Agreement and Schedule."),
        ],
        4: [
            _isda_text(4, "section-3-basic-representations", "(a) Basic Representations", heading=True, break_before=True),
            _isda_text(4, "section-3-status", "Each party represents that it has the status required to enter into the Agreement.", kind="clause"),
            _isda_text(4, "section-3-powers", "Each party represents that it has the powers to enter into and perform the Agreement.", kind="clause"),
            _isda_text(4, "section-3-authorisations", "Each party represents that all authorisations required for its execution and performance are in effect.", kind="clause"),
            _isda_text(4, "section-3-no-conflict", "Each party represents that execution and performance do not conflict with its obligations or constitutive documents.", kind="clause"),
            _isda_text(4, "section-3-binding-obligations", "Each party represents that its obligations are legal, valid and binding obligations.", kind="clause"),
            _isda_text(4, "section-3-absence-events", "(b) Absence of Certain Events. No Event of Default, Potential Event of Default or Termination Event has occurred and is continuing."),
        ],
        5: [
            _isda_text(5, "section-3-litigation-information", "(c) Absence of Litigation; (d) Accuracy of Specified Information", heading=True, break_before=True),
            _isda_text(5, "section-3-tax-no-agency", "(e) Payer Tax Representation; (f) Payee Tax Representations; (g) No Agency", heading=True),
        ],
        6: [
            _isda_text(5, "section-3-absence-litigation", "(c) Absence of Litigation. No proceeding materially affects performance.", kind="clause"),
            _isda_text(5, "section-3-specified-information", "(d) Accuracy of Specified Information. Information identified in the Schedule is true and complete.", kind="clause"),
            _isda_text(5, "section-3-payer-tax", "(e) Payer Tax Representation. Each specified representation is accurate.", kind="clause"),
            _isda_text(5, "section-3-payee-tax", "(f) Payee Tax Representations. Each specified representation is accurate.", kind="clause"),
            _isda_text(5, "section-3-no-agency", "(g) No Agency. Each party enters as principal.", kind="clause"),
            _isda_text(6, "section-4-agreements", "4. Agreements", heading=True, break_before=True),
            _isda_text(6, "section-4-ongoing-agreements", "Ongoing information, authorisation, legal-compliance, tax-notice and Stamp Tax duties.", heading=True),
        ],
        7: [
            _isda_text(6, "section-4-furnish-information", "Each party will furnish information required under the Agreement.", kind="clause"),
            _isda_text(6, "section-4-maintain-authorisations", "Each party will maintain the authorisations required for performance.", kind="clause"),
            _isda_text(6, "section-4-comply-laws", "Each party will comply with applicable laws.", kind="clause"),
            _isda_text(6, "section-4-notify-tax-failure", "Each party will notify the other of a failure of a tax representation.", kind="clause"),
            _isda_text(6, "section-4-stamp-tax", "Each party will pay applicable Stamp Tax.", kind="clause"),
            _isda_text(7, "section-5-events", "5. Events of Default and Termination Events", heading=True, break_before=True),
            _isda_text(7, "section-5-event-categories", "Event of Default categories", heading=True),
        ],
        8: [
            _isda_text(7, "section-5-failure-pay-deliver", "Failure to Pay or Deliver is an Event of Default subject to the Agreement.", kind="clause"),
            _isda_text(7, "section-5-breach-repudiation", "Breach or Repudiation is an Event of Default subject to the Agreement.", kind="clause"),
            _isda_text(7, "section-5-credit-support-default", "Credit Support Default is an Event of Default subject to the Agreement.", kind="clause"),
            _isda_text(7, "section-5-misrepresentation", "Misrepresentation is an Event of Default subject to the Agreement.", kind="clause"),
            _isda_text(7, "section-5-default-specified-transaction", "Default Under Specified Transaction is an Event of Default subject to the Agreement.", kind="clause"),
            _isda_text(7, "section-5-cross-default", "Cross-Default is an Event of Default subject to the Agreement and Schedule.", kind="clause"),
            _isda_text(7, "section-5-bankruptcy", "Bankruptcy is an Event of Default subject to the Agreement.", kind="clause"),
            _isda_text(7, "section-5-merger-without-assumption", "Merger Without Assumption is an Event of Default subject to the Agreement.", kind="clause"),
            _isda_text(8, "section-5-consequences", "Consequences for specified Events of Default", heading=True, break_before=True),
            _isda_text(8, "section-5-misrepresentation-consequence", "Misrepresentation has the consequences specified in Section 5 and the Schedule.", kind="clause"),
            _isda_text(8, "section-5-specified-transaction-consequence", "Default Under Specified Transaction has the consequences specified in Section 5 and the Schedule.", kind="clause"),
            _isda_text(8, "section-5-cross-default-consequence", "Cross-Default has the consequences specified in Section 5 and the Schedule.", kind="clause"),
            _isda_text(8, "section-5-bankruptcy-consequence", "Bankruptcy has the consequences specified in Section 5 and the Schedule.", kind="clause"),
            _isda_text(8, "section-5-merger-consequence", "Merger Without Assumption has the consequences specified in Section 5 and the Schedule.", kind="clause"),
        ],
    }
    return clauses[page_number]


def _section_five_to_eight_blocks(page_number: int) -> list[dict]:
    """Split the remaining termination, transfer and currency pages."""
    clauses: dict[int, list[dict]] = {
        9: [
            _isda_text(9, "section-5-illegality", "(b) Termination Events\nIllegality applies as specified in this Agreement and Schedule.", heading=True, break_before=True),
            _isda_text(9, "section-5-force-majeure", "Force Majeure Event applies as specified in this Agreement and Schedule."),
            _isda_text(9, "section-5-tax-event", "Tax Event applies as specified in this Agreement and Schedule."),
            _isda_text(9, "section-5-tax-event-upon-merger", "Tax Event Upon Merger applies as specified in this Agreement and Schedule."),
            _isda_text(9, "section-5-waiting-period-deferrals", "The Agreement sets event waiting periods and deferrals before termination rights arise.", kind="clause"),
        ],
        10: [
            _isda_text(10, "section-5-credit-event-merger", "Credit Event Upon Merger applies where specified.", heading=True, break_before=True),
            _isda_text(10, "section-5-additional-termination-event", "Additional Termination Event applies where specified.", heading=False),
            _isda_text(10, "section-5-designated-event", "A Designated Event may occur when a party, Credit Support Provider or applicable Specified Entity undergoes a specified change and the resulting creditworthiness is materially weaker.", kind="clause"),
            _isda_text(10, "section-5-designated-event-consolidation", "A Designated Event includes consolidation, amalgamation, merger, transfer of all or substantially all relevant assets, or reorganisation into another entity.", kind="clause"),
            _isda_text(10, "section-5-designated-event-control", "A Designated Event includes a person, related group or entity acquiring beneficial ownership or another ownership interest that enables control.", kind="clause"),
            _isda_text(10, "section-5-designated-event-capital-structure", "A Designated Event includes a substantial change in capital structure through debt, guarantees, preferred stock, convertible or exchangeable securities, or another ownership interest.", kind="clause"),
            _isda_text(10, "section-5-hierarchy-illegality-default", "An event giving rise to an Illegality or Force Majeure Event does not also constitute the specified Event of Default for so long as the applicable condition continues.", kind="clause"),
            _isda_text(10, "section-5-hierarchy-other-termination-event", "Except in the stated circumstances, an event that also constitutes an Event of Default or another Termination Event is treated as that Event of Default or other Termination Event.", kind="clause"),
            _isda_text(10, "section-5-hierarchy-force-majeure-illegality", "If a Force Majeure Event also constitutes an Illegality, it is treated as an Illegality except where the other hierarchy rule applies.", kind="clause"),
            _isda_text(10, "section-5-deferral-waiting-period", "During an Illegality or Force Majeure Event, a payment or delivery otherwise due is deferred until the first applicable Local Business Day or Local Delivery Day after the Waiting Period.", kind="clause"),
            _isda_text(10, "section-5-deferral-event-ceases", "If earlier, the deferred payment or delivery becomes due when the event or circumstance ceases, subject to the applicable Local Business Day or Local Delivery Day.", kind="clause"),
            _isda_text(10, "section-5-head-home-office-obligations", "The Agreement separately addresses an affected branch Office's obligations where the relevant Office is not the affected party's head or home office and the specified conditions apply.", kind="clause"),
        ],
        11: [
            _isda_text(11, "section-6-early-termination", "6. Early Termination; Close-Out Netting", heading=True, break_before=True),
            _isda_text(11, "section-6-termination-event-notice", "For a Termination Event other than a Force Majeure Event, the Affected Party promptly notifies the other party, specifying the nature of the event and each Affected Transaction, with additional information as reasonably required."),
            _isda_text(11, "section-6-force-majeure-notice", "For a Force Majeure Event, each party uses reasonable efforts to notify the other party, specifying the nature of the event and providing additional information as reasonably required."),
            _isda_text(11, "section-6-transfer-to-avoid-event", "A Tax Event or Tax Event Upon Merger may require reasonable efforts to transfer rights and obligations before termination."),
            _isda_text(11, "section-6-designation", "Designation mechanics", heading=True),
            _isda_text(11, "section-6-designation-notice", "The designation of an Early Termination Date is made in accordance with the applicable notice requirements.", kind="clause"),
        ],
        12: [
            _isda_text(12, "section-6-transfer-failure", "A party may designate an Early Termination Date if a required transfer or agreement is not effected.", heading=True, break_before=True),
            _isda_text(12, "section-6-right-to-terminate", "If the applicable transfer or agreement has not been effected, or a specified Credit Event Upon Merger, Additional Termination Event or Tax Event Upon Merger continues, the applicable party may designate an Early Termination Date for the Affected Transactions."),
            _isda_text(12, "section-6-right-to-terminate-illegality", "After an applicable Waiting Period for an Illegality or Force Majeure Event, either party may designate an Early Termination Date for all or specified Affected Transactions, subject to the stated prior-designation condition for certain Credit Support obligations.", kind="clause"),
            _isda_text(12, "section-6-effect-designation", "If notice designating an Early Termination Date is given under Section 6(a) or 6(b), the date occurs on the date designated whether or not the relevant Event of Default or Termination Event continues."),
            _isda_text(12, "section-6-effect-designation-due-amount", "Following the occurrence or effective designation of an Early Termination Date, no further payments or deliveries for Terminated Transactions are required, subject to the Agreement and the amount determined under Sections 6(e) and 9(h)(ii).", kind="clause"),
            _isda_text(12, "section-6-terminated-transactions", "Effects for Terminated Transactions", heading=True),
            _isda_text(12, "section-6-no-further-payments", "On designation, no further payments or deliveries for Terminated Transactions are required, subject to the Agreement.", kind="clause"),
        ],
        13: [
            _isda_text(13, "section-6-calculations", "(d) Calculations; Payment Date", heading=True, break_before=True),
            _isda_text(13, "section-6-payment-date", "The amount is payable on the applicable Payment Date."),
            _isda_text(13, "section-6-calculation-delivery", "Each party provides a statement showing its Section 6(e) calculations, any quotations or market data used, any Early Termination Amount payable and the relevant payment account.", kind="clause"),
            _isda_text(13, "section-6-payments-early-termination", "(e) Payments on Early Termination. The Early Termination Amount is determined under Section 6 and remains subject to the Set-Off provisions."),
            _isda_text(13, "section-6-early-termination-default-amount", "For an Event of Default, the Early Termination Amount reflects the Termination Currency Equivalent of Close-out Amounts and Unpaid Amounts owing to each party.", kind="clause"),
            _isda_text(13, "section-6-early-termination-one-affected-party", "For a Termination Event with one Affected Party, the Early Termination Amount uses the Event of Default calculation with the Affected Party and Non-affected Party substitutions.", kind="clause"),
            _isda_text(13, "section-6-early-termination-two-affected-parties", "For a Termination Event with two Affected Parties, each party determines the relevant Close-out Amounts and the Early Termination Amount reflects the difference and applicable Unpaid Amounts.", kind="clause"),
        ],
        14: [
            _isda_text(14, "section-6-termination-events", "(e) Termination Events. The Early Termination Amount is determined by the applicable party and valuation method.", heading=True, break_before=True),
            _isda_text(14, "section-6-mid-market-events", "For an Illegality or Force Majeure Event, a Determining Party seeking quotations asks third parties or Affiliates for mid-market quotations without taking account of its creditworthiness or existing Credit Support Document."),
            _isda_text(14, "section-6-mid-market-values", "Where quotations are not obtained, the Determining Party uses mid-market values without regard to its creditworthiness.", kind="clause"),
            _isda_text(14, "section-6-adjustments", "Where Automatic Early Termination applies, the Early Termination Amount is subject to appropriate adjustments for payments or deliveries retained during the period before payment."),
            _isda_text(14, "section-6-adjustment-illegality-force-majeure", "A failure to pay an Early Termination Amount caused by an Illegality or Force Majeure Event is treated under the stated interest and Unpaid Amount provisions rather than as the specified Event of Default.", kind="clause"),
            _isda_text(14, "section-6-pre-estimate", "The parties treat an amount recoverable under Section 6 as a reasonable pre-estimate of loss and not a penalty."),
            _isda_text(14, "section-6-set-off", "(f) Set-Off", heading=True, break_before=True),
            _isda_text(14, "section-6-set-off-right", "An Early Termination Amount payable by one party may, in the stated circumstances, be reduced by set-off against other amounts payable by the Payee to the Payer.", kind="clause"),
            _isda_text(14, "section-6-set-off-other-amounts", "Other Amounts may be matured or contingent, arise under or outside the Agreement, and be in another currency or place of payment; amounts set off are discharged and notice is given.", kind="clause"),
            _isda_text(14, "section-6-set-off-conversion", "The Early Termination Amount or Other Amounts may be converted into the currency of the other amount at a rate obtained in good faith using commercially reasonable procedures.", kind="clause"),
        ],
        15: [
            _isda_text(15, "section-7-transfer", "7. Transfer\nInterests and obligations may not be transferred without consent, subject to permitted transfers.", heading=True, break_before=True),
            _isda_text(15, "section-7-transfer-exceptions", "Transfer exceptions", heading=True),
            _isda_text(15, "section-7-consent", "Interests and obligations may not be transferred without the required consent.", kind="clause"),
            _isda_text(15, "section-7-corporate-asset-transfers", "Section 7 permits a transfer of the Agreement in connection with a consolidation, amalgamation, merger or transfer of all or substantially all assets to another entity.", kind="clause"),
            _isda_text(15, "section-7-early-termination-interest-transfers", "Section 7 permits a transfer of all or part of an interest in an Early Termination Amount payable to a Defaulting Party, together with associated amounts and rights.", kind="clause"),
            _isda_text(15, "section-8-contractual-currency", "8. Contractual Currency\nPayments are made in the relevant Contractual Currency."),
            _isda_text(15, "section-8-payment-currency", "Payments in a currency other than the Contractual Currency are subject to the conversion and shortfall provisions of Section 8."),
        ],
        16: [
            _isda_text(16, "section-8-currency-judgment", "8. Contractual Currency (continued)", heading=True, break_before=True),
            _isda_text(16, "section-8-judgment-conversion", "A judgment in another currency is converted using commercially reasonable procedures.", kind="clause"),
            _isda_text(16, "section-8-separate-indemnities", "The indemnities in Section 8 are separate and independent obligations."),
            _isda_text(16, "section-8-evidence-of-loss", "For Section 8 purposes, a party may demonstrate that it would have suffered a loss had an actual exchange or purchase been made."),
            _isda_text(16, "section-9-miscellaneous", "9. Miscellaneous\nThe Agreement addresses amendments, survival, remedies, counterparts and confirmations."),
            _isda_text(16, "section-9-entire-agreement", "The Agreement constitutes the entire agreement and understanding of the parties with respect to its subject matter."),
            _isda_text(16, "section-9-amendments", "Amendments, modifications and waivers are effective only in the written and executed or otherwise confirmed manner specified in the Agreement."),
            _isda_text(16, "section-9-survival", "Applicable obligations and remedies survive termination as specified in the Agreement.", kind="clause"),
            _isda_text(16, "section-9-remedies", "The Agreement preserves the remedies available to the parties under its terms.", kind="clause"),
            _isda_text(16, "section-9-counterparts-confirmations", "The Agreement may be executed in counterparts and is supplemented by Confirmations.", kind="clause"),
        ],
    }
    return clauses[page_number]


def _section_nine_to_definitions_blocks(page_number: int) -> list[dict]:
    """Split the later agreement pages into stable, renderer-native clause objects.

    These objects deliberately remain clause text rather than inventing field
    bindings for legal prose whose Schedule choices are represented separately.
    Page ownership and the existing safe text vocabulary are unchanged.
    """
    clauses: dict[int, list[dict]] = {
        17: [
            _isda_text(17, "section-9-interest", "(h) Interest and Compensation", heading=True, break_before=True),
            _isda_text(17, "section-9-defaulted-payments", "Before Early Termination, a party that defaults on a payment obligation pays interest on the overdue amount, subject to applicable law and Section 6(c), from the original due date until actual payment at the Default Rate."),
            _isda_text(17, "section-9-defaulted-deliveries", "A party that defaults on an obligation settled by delivery compensates the other party as provided in the Confirmation or Agreement and may owe interest on the fair market value of the undelivered obligation at the Default Rate."),
            _isda_text(17, "section-9-deferred-delivery", "A party that does not pay an amount deferred under Section 2(a)(iii) or Section 5(d), or fails to pay because of an Illegality or Force Majeure Event, pays interest at the Applicable Deferral Rate for the applicable deferral period.", kind="clause"),
            _isda_text(17, "section-9-deferred-payments", "Interest on Deferred Payments applies where payment is deferred under the Agreement."),
            _isda_text(17, "section-9-illegality-force-majeure-interest", "A party that fails to make a payment because of an Illegality or Force Majeure Event owes interest from the applicable failure or deferral date until the event ceases or the stated default condition occurs.", kind="clause"),
        ],
        18: [
            _isda_text(18, "section-9-deferred-interest", "Compensation for Deferred Deliveries continues subject to the applicable Confirmation and Agreement provisions.", heading=True, break_before=True),
            _isda_text(18, "section-9-interest-calculation", "Interest under Section 9(h) is calculated using daily compounding and the actual number of days elapsed."),
            _isda_text(18, "section-9-early-termination-interest", "Upon an Early Termination Date, interest accrues on payment obligations or fair market values included in Unpaid Amounts at the Applicable Close-out Rate until the Early Termination Date."),
            _isda_text(18, "section-9-early-termination-amount-interest", "An Early Termination Amount due on an Early Termination Date is paid with interest in the Termination Currency at the Applicable Close-out Rate until payment.", kind="clause"),
            _isda_text(18, "section-9-unpaid-amounts", "Unpaid Amounts and Early Termination Amounts are treated in the applicable currency and at the applicable close-out rate."),
        ],
        19: [
            _isda_text(19, "section-10-offices", "10. Offices; Multibranch Parties", heading=True, break_before=True),
            _isda_text(19, "section-10-office-recourse", "An Office election preserves the applicable recourse and obligations of a party as specified in Section 10."),
            _isda_text(19, "section-10-office-selection", "The Office through which a Transaction is entered is identified in the Confirmation or as agreed by the parties; absent that identification, the head or home office applies."),
            _isda_text(19, "section-10-multibranch-offices", "A party specified as a Multibranch Party may enter into, book and make or receive payments and deliveries through an Office listed for it in the Schedule, subject to the stated conditions.", kind="clause"),
            _isda_text(19, "section-10-office-booking-consent", "Unless otherwise agreed in writing, the entering Office also books and settles the Transaction, and changing that Office requires the other party's prior written consent subject to Section 6(b)(ii).", kind="clause"),
            _isda_text(19, "section-11-expenses", "11. Expenses\nA Defaulting Party indemnifies reasonable expenses incurred in connection with an Event of Default."),
            _isda_text(19, "section-12-notices", "12. Notices\nNotices use the specified addresses, numbers and electronic methods, with effectiveness determined by the delivery method."),
            _isda_text(19, "section-12-notice-methods", "Written delivery, telex, facsimile, certified or registered mail, electronic messaging and e-mail have the stated notice-effectiveness conditions; Section 5 or 6 notices cannot use electronic messaging or e-mail.", kind="clause"),
        ],
        20: [
            _isda_text(20, "section-12-notice-effectiveness", "12. Notices (continued)\nA notice is effective when delivered or received by the specified method and address.", heading=True, break_before=True),
            _isda_text(20, "section-12-notice-local-business-day", "If delivery, attempted delivery or receipt occurs after close of business or on a non-Local Business Day, the notice is effective on the first following Local Business Day.", kind="clause"),
            _isda_text(20, "section-12-change-details", "The parties may change notice addresses, numbers or electronic messaging and e-mail details by notice."),
            _isda_text(20, "section-13-jurisdiction", "13. Governing Law and Jurisdiction\nThe Schedule specifies governing law and jurisdiction."),
            _isda_text(20, "section-13-jurisdiction-submission", "Each party submits to the applicable courts specified for the governing law, waives objections to venue or inconvenient forum and accepts the court's jurisdiction, subject to the Agreement.", kind="clause"),
            _isda_text(20, "section-13-jurisdiction-multiple", "Proceedings in one jurisdiction do not preclude Proceedings in another jurisdiction to the extent permitted by applicable law.", kind="clause"),
            _isda_text(20, "section-13-service-process", "Each party appoints any Process Agent specified in the Schedule for service of process."),
            _isda_text(20, "section-13-process-agent-replacement", "If a Process Agent cannot act, the party promptly notifies the other party and appoints an acceptable substitute within 30 days; service may also be made by the stated notice methods or as permitted by law.", kind="clause"),
        ],
        21: [
            _isda_text(21, "definitions-opening", "14. Definitions", heading=True, break_before=True),
            _isda_text(21, "definitions-additional-representation", "Additional Representation has the meaning specified in the relevant Section and Schedule.", kind="clause"),
            _isda_text(21, "definitions-additional-termination-event", "Additional Termination Event has the meaning specified in the relevant Section and Schedule.", kind="clause"),
            _isda_text(21, "definitions-affected-party", "Affected Party identifies the party subject to a Termination Event or Event of Default.", kind="clause"),
            _isda_text(21, "definitions-applicable-close-out-rate", "For an Unpaid Amount, the Applicable Close-out Rate uses the Default Rate, Non-default Rate or Applicable Deferral Rate according to the applicable party, deferral and Termination Event circumstances.", kind="clause"),
            _isda_text(21, "definitions-applicable-close-out-rate-early-termination", "For an Early Termination Amount before its payment date, the Applicable Close-out Rate uses the Default Rate, Non-default Rate or Applicable Deferral Rate according to which party owes the amount.", kind="clause"),
            _isda_text(21, "definitions-applicable-close-out-rate-post-payment", "After the payment date, the applicable rate depends on an Illegality or Force Majeure Event, a Defaulting Party, a Non-defaulting Party or the remaining Termination Rate condition.", kind="clause"),
            _isda_text(21, "definitions-affected-transactions", "For an Illegality, Force Majeure Event, Tax Event or Tax Event Upon Merger, Affected Transactions are the Transactions affected by that Termination Event, subject to the Credit Support Document qualification."),
            _isda_text(21, "definitions-affected-transactions-other", "For another Termination Event, Affected Transactions are all Transactions.", kind="clause"),
            _isda_text(21, "definitions-affiliate-agreement", "Affiliate means an entity controlled by, controlling or under common control with a person, subject to the Schedule; control means majority voting ownership."),
            _isda_text(21, "definitions-agreement", "Agreement has the meaning specified in Section 1(c).", kind="clause"),
        ],
        22: [
            _isda_text(22, "definitions-deferral-currency", "Applicable Deferral Rate; Automatic Early Termination; Burdened Party; Change in Tax Law; Close-out Amount; Contractual Currency", heading=True, break_before=True),
            _isda_text(22, "definitions-applicable-deferral-rate", "For Section 9(h)(i)(3)(A), the Applicable Deferral Rate is the rate certified by the payer as offered by a major bank for overnight deposits in the applicable currency.", kind="clause"),
            _isda_text(22, "definitions-applicable-deferral-rate-prime", "For Section 9(h)(i)(3)(B), the Applicable Deferral Rate is the rate certified by the payer as offered to prime banks, selected in good faith after consultation where practicable.", kind="clause"),
            _isda_text(22, "definitions-applicable-deferral-rate-mean", "For Section 9(h)(i)(3)(C) and the stated Applicable Close-out Rate clauses, the Applicable Deferral Rate uses the arithmetic mean of the relevant overnight rate and the certified funding-cost rate.", kind="clause"),
            _isda_text(22, "definitions-burdened-party", "Burdened Party identifies the party affected by the applicable tax or termination provision.", kind="clause"),
            _isda_text(22, "definitions-change-tax-law", "Change in Tax Law has the meaning specified in the Agreement.", kind="clause"),
            _isda_text(22, "definitions-contractual-currency", "Contractual Currency identifies the currency applicable to payment and valuation.", kind="clause"),
            _isda_text(22, "definitions-automatic-early-termination", "Automatic Early Termination has the meaning specified in the Schedule and Section 6."),
            _isda_text(22, "definitions-close-out-amount", "Close-out Amount means the Determining Party's losses or costs, or gains, in replacing or providing the economic equivalent of the material terms of Terminated Transactions and their option rights."),
            _isda_text(22, "definitions-close-out-amount-scope", "Close-out Amounts exclude Unpaid Amounts, legal fees and Section 11 out-of-pocket expenses, and are determined for all Terminated Transactions in the aggregate, subject to the stated grouping conditions.", kind="clause"),
            _isda_text(22, "definitions-close-out-amount-determination", "The Determining Party determines each Close-out Amount in good faith using commercially reasonable procedures as of the Early Termination Date or another commercially reasonable date.", kind="clause"),
            _isda_text(22, "definitions-close-out-amount-information", "The Determining Party may consider third-party quotations, relevant market data, qualifying internal information, funding costs and relevant hedge termination costs without duplication.", kind="clause"),
        ],
        23: [
            _isda_text(23, "definitions-close-out-confirmation", "Close-out Amount; Confirmation; Consent; Credit Event Upon Merger; Credit Support Document", heading=True, break_before=True),
            _isda_text(23, "definitions-close-out-good-faith", "Close-out Amount is determined in good faith using commercially reasonable procedures.", kind="clause"),
            _isda_text(23, "definitions-close-out-market-information", "A Determining Party may consider third-party replacement quotations, relevant market data and qualifying internal information when determining a Close-out Amount.", kind="clause"),
            _isda_text(23, "definitions-close-out-valuation-methods", "Commercially reasonable procedures may include regular-course pricing models and different valuation methods for Terminated Transactions based on their type, complexity, size or number.", kind="clause"),
            _isda_text(23, "definitions-confirmation", "Confirmation identifies the transaction record contemplated by the Agreement.", kind="clause"),
            _isda_text(23, "definitions-confirmation-consent", "Confirmation identifies the transaction record contemplated by the Agreement."),
            _isda_text(23, "definitions-consent", "Consent includes a consent, approval, action, authorisation, exemption, notice, filing, registration or exchange-control consent.", kind="clause"),
            _isda_text(23, "definitions-credit-event-merger", "Credit Event Upon Merger has the meaning specified in Section 5 and the Schedule."),
            _isda_text(23, "definitions-credit-support-document", "Credit Support Document has the meaning specified in the Agreement and applicable Schedule provisions."),
        ],
        24: [
            _isda_text(24, "definitions-credit-support", "Credit Support Provider; Cross-Default; Default Rate; Defaulting Party; Designated Event; Determining Party; Early Termination Amount; Early Termination Date; Illegality", heading=True, break_before=True),
            _isda_text(24, "definitions-default-rate", "Default Rate means the relevant payee's certified funding cost for the applicable amount plus 1% per annum, subject to the Agreement.", kind="clause"),
            _isda_text(24, "definitions-defaulting-party", "Defaulting Party identifies the party subject to an Event of Default.", kind="clause"),
            _isda_text(24, "definitions-designated-event", "Designated Event has the meaning specified in the default and termination provisions.", kind="clause"),
            _isda_text(24, "definitions-determining-party", "Determining Party identifies the party making the applicable valuation determination.", kind="clause"),
            _isda_text(24, "definitions-early-termination-amount", "Early Termination Amount supports the payment due following an Early Termination Date.", kind="clause"),
            _isda_text(24, "definitions-early-termination-date", "Early Termination Date identifies the date on which Terminated Transactions are closed out.", kind="clause"),
            _isda_text(24, "definitions-illegality", "Illegality has the meaning specified in Section 5 and related provisions.", kind="clause"),
            _isda_text(24, "definitions-cross-default", "Cross-Default means the event specified in Section 5(a)(vi).", kind="clause"),
            _isda_text(24, "definitions-electronic-messages", "Electronic messages exclude e-mails and include documents expressed in markup languages; electronic messaging system is construed accordingly.", kind="clause"),
            _isda_text(24, "definitions-english-law", "English law means the law of England and Wales, and English is construed accordingly.", kind="clause"),
            _isda_text(24, "definitions-event-of-default", "Event of Default has the meaning specified in Section 5(a) and, if applicable, in the Schedule.", kind="clause"),
            _isda_text(24, "definitions-force-majeure-event", "Force Majeure Event has the meaning specified in Section 5(b).", kind="clause"),
            _isda_text(24, "definitions-general-business-day", "General Business Day means a day on which commercial banks are open for general business, including foreign exchange and foreign currency deposits.", kind="clause"),
            _isda_text(24, "definitions-credit-support-provider", "Credit Support Provider and Cross-Default identify support and default relationships under the Agreement."),
            _isda_text(24, "definitions-default-and-determining-party", "Default Rate, Defaulting Party, Designated Event and Determining Party support the default and valuation provisions."),
            _isda_text(24, "definitions-early-termination-illegality", "Early Termination Amount, Early Termination Date and Illegality have the meanings specified in Section 6 and related provisions."),
        ],
    }
    return clauses[page_number]


def _isda_text(page_number: int, semantic_id: str, text: str, *, kind: str = "clause",
               field_path: str | None = None, field_role: str | None = None,
               heading: bool = False, break_before: bool = False) -> dict:
    """Create a renderer-native text block with bounded ISDA semantics.

    ``semantic_kind`` is metadata, not a new renderer instruction. The safe renderer
    still receives only its existing text block vocabulary and ignores these labels.
    """
    block = {
        "type": "text", "text": text, "font_family": "Times New Roman", "font_size": 11,
        "color": "#171717", "align": "left", "bold": heading, "line_height": 1.15,
        "paragraph_spacing_after": 7, "keep_with_next": True, "break_before": break_before,
        "page_number": page_number, "position_mode": "flow", "position_unit": "mm",
        "anchor_id": f"isda-{semantic_id}", "toc_label": semantic_id.replace("-", " "),
        "toc_level": 2, "semantic_kind": kind, "semantic_id": semantic_id,
    }
    if field_path:
        block["field_path"] = field_path
    if field_role:
        block["field_role"] = field_role
    return block


def _isda_table(page_number: int, semantic_id: str, label: str, items: str,
                columns: list[dict]) -> dict:
    """Create a page-owned, declarative Schedule table with stable semantics."""
    return {
        "type": "table", "text": label, "items": items, "columns": columns,
        "page_number": page_number, "position_mode": "flow", "position_unit": "mm",
        "anchor_id": f"isda-{semantic_id}", "toc_label": label,
        "toc_level": 2, "semantic_kind": "schedule", "semantic_id": semantic_id,
        "break_before": False,
    }


def _schedule_and_execution_blocks(page_number: int) -> list[dict]:
    """Return semantic, page-owned objects for Schedule and execution pages.

    This is intentionally a bounded first decomposition. It does not assert that the
    supplied PDF has been transcribed or that these coordinates are source-calibrated.
    """
    page: dict[int, list[dict]] = {
        29: [
            _isda_text(29, "schedule-intro", "SCHEDULE to the 2002 Master Agreement", kind="schedule", heading=True, break_before=True),
            _isda_text(29, "schedule-agreement-date", "{{agreement_date}}", kind="field", field_path="agreement_date", field_role="Schedule agreement date"),
            _isda_text(29, "schedule-party-x", "{{schedule.party_x}}", kind="field", field_path="schedule.party_x", field_role="Schedule party A"),
            _isda_text(29, "schedule-party-y", "{{schedule.party_y}}", kind="field", field_path="schedule.party_y", field_role="Schedule party B"),
            _isda_text(29, "schedule-part-1", "PART 1. TERMINATION PROVISIONS", kind="schedule", heading=True),
        ],
        30: [
            _isda_text(29, "schedule-part1-termination-purpose", "Part 1 records the parties' termination elections and related thresholds.", kind="clause"),
            _isda_text(30, "schedule-cross-default", "PART 1. TERMINATION PROVISIONS (continued)", kind="clause", heading=True, break_before=True),
            _isda_text(30, "schedule-cross-default-purpose", "Cross-Default elections record thresholds and grace periods for each party.", kind="clause"),
            _isda_text(30, "termination-threshold-party-x", "{{schedule.termination.cross_default.threshold_party_x}}", kind="field", field_path="schedule.termination.cross_default.threshold_party_x", field_role="Cross-Default threshold — Party A"),
            _isda_text(30, "termination-threshold-party-y", "{{schedule.termination.cross_default.threshold_party_y}}", kind="field", field_path="schedule.termination.cross_default.threshold_party_y", field_role="Cross-Default threshold — Party B"),
            _isda_text(30, "automatic-early-termination", "{{schedule.termination.automatic_early_termination}}", kind="field", field_path="schedule.termination.automatic_early_termination", field_role="Automatic Early Termination election"),
            _isda_text(30, "specified-indebtedness", "{{schedule.elections.specified_indebtedness}}", kind="field", field_path="schedule.elections.specified_indebtedness", field_role="Specified Indebtedness election"),
            _isda_text(30, "specified-transaction-detail", "{{schedule.elections.specified_transaction_detail}}", kind="field", field_path="schedule.elections.specified_transaction_detail", field_role="Specified Transaction detail"),
            _isda_text(30, "specified-indebtedness-detail", "{{schedule.elections.specified_indebtedness_detail}}", kind="field", field_path="schedule.elections.specified_indebtedness_detail", field_role="Specified Indebtedness detail"),
            _isda_text(30, "additional-termination-event", "{{schedule.elections.additional_termination_event}}", kind="field", field_path="schedule.elections.additional_termination_event", field_role="Additional Termination Event election"),
            _isda_text(30, "additional-termination-event-detail", "{{schedule.elections.additional_termination_event_detail}}", kind="field", field_path="schedule.elections.additional_termination_event_detail", field_role="Additional Termination Event detail"),
            _isda_text(30, "termination-currency-detail", "{{schedule.elections.termination_currency_detail}}", kind="field", field_path="schedule.elections.termination_currency_detail", field_role="Termination Currency detail"),
        ],
        31: [
            _isda_text(31, "schedule-tax", "PART 2. TAX REPRESENTATIONS", kind="schedule", heading=True, break_before=True),
            _isda_text(31, "schedule-tax-purpose", "Part 2 records tax representations, jurisdictions and treaty elections.", kind="clause"),
            _isda_text(31, "tax-payer-party-x", "{{schedule.tax.payer_representation_party_x}}", kind="field", field_path="schedule.tax.payer_representation_party_x", field_role="Payer Tax Representation — Party A"),
            _isda_text(31, "tax-payee-party-x", "{{schedule.tax.payee_representation_party_x}}", kind="field", field_path="schedule.tax.payee_representation_party_x", field_role="Payee Tax Representation — Party A"),
            _isda_text(31, "tax-jurisdiction-party-x", "{{schedule.tax.jurisdiction_party_x}}", kind="field", field_path="schedule.tax.jurisdiction_party_x", field_role="Tax jurisdiction — Party A"),
        ],
        32: [
            _isda_text(32, "schedule-agreements", "PART 3. AGREEMENTS", kind="schedule", heading=True, break_before=True),
            _isda_text(32, "schedule-agreements-purpose", "Part 3 records delivery, credit support and additional agreement elections.", kind="clause"),
            _isda_table(32, "schedule-tax-documents", "Schedule tax documents", "schedule_tax_documents", [{"header": "Party required", "path": "party_required", "format": "text", "width": 20}, {"header": "Form/Document/Certificate", "path": "form_document", "format": "text", "width": 50}, {"header": "Delivery date", "path": "delivery_date", "format": "date", "width": 30}]),
        ],
        33: [
            _isda_text(33, "schedule-documents-heading", "DOCUMENTS TO BE DELIVERED", kind="schedule", heading=True, break_before=True),
            _isda_table(33, "schedule-documents", "Schedule documents", "schedule_documents", [{"header": "Party required", "path": "party_required", "format": "text", "width": 20}, {"header": "Form/Document/Certificate", "path": "form_document", "format": "text", "width": 45}, {"header": "Delivery date", "path": "delivery_date", "format": "date", "width": 20}, {"header": "Section 3(d)", "path": "covered_by_section_3d", "format": "text", "width": 15}]),
            _isda_text(33, "schedule-notice-party-x", "{{schedule.notices.party_x}}", kind="field", field_path="schedule.notices.party_x", field_role="Notice address — Party A"),
            _isda_text(33, "schedule-notice-party-y", "{{schedule.notices.party_y}}", kind="field", field_path="schedule.notices.party_y", field_role="Notice address — Party B"),
            _isda_text(33, "notice-telex-party-x", "{{schedule.notices.telex_party_x}}", kind="field", field_path="schedule.notices.telex_party_x", field_role="Notice Telex number — Party A"),
            _isda_text(33, "notice-answerback-party-x", "{{schedule.notices.answerback_party_x}}", kind="field", field_path="schedule.notices.answerback_party_x", field_role="Notice Answerback — Party A"),
            _isda_text(33, "notice-facsimile-party-x", "{{schedule.notices.facsimile_party_x}}", kind="field", field_path="schedule.notices.facsimile_party_x", field_role="Notice Facsimile number — Party A"),
            _isda_text(33, "notice-telephone-party-x", "{{schedule.notices.telephone_party_x}}", kind="field", field_path="schedule.notices.telephone_party_x", field_role="Notice Telephone number — Party A"),
            _isda_text(33, "notice-telex-party-y", "{{schedule.notices.telex_party_y}}", kind="field", field_path="schedule.notices.telex_party_y", field_role="Notice Telex number — Party B"),
            _isda_text(33, "notice-answerback-party-y", "{{schedule.notices.answerback_party_y}}", kind="field", field_path="schedule.notices.answerback_party_y", field_role="Notice Answerback — Party B"),
            _isda_text(33, "notice-facsimile-party-y", "{{schedule.notices.facsimile_party_y}}", kind="field", field_path="schedule.notices.facsimile_party_y", field_role="Notice Facsimile number — Party B"),
            _isda_text(33, "notice-telephone-party-y", "{{schedule.notices.telephone_party_y}}", kind="field", field_path="schedule.notices.telephone_party_y", field_role="Notice Telephone number — Party B"),
        ],
        34: [
            _isda_text(34, "schedule-process-agent", "PART 4. PROCESS AGENT AND OFFICES", kind="schedule", heading=True, break_before=True),
            _isda_text(34, "schedule-process-agent-purpose", "Part 4 records Process Agent, Office and Credit Support elections.", kind="clause"),
            _isda_text(34, "process-agent-party-x", "{{schedule.process_agent.party_x}}", kind="field", field_path="schedule.process_agent.party_x", field_role="Process Agent — Party A"),
            _isda_text(34, "process-agent-party-y", "{{schedule.process_agent.party_y}}", kind="field", field_path="schedule.process_agent.party_y", field_role="Process Agent — Party B"),
            _isda_text(34, "office-party-x", "{{schedule.offices.party_x}}", kind="field", field_path="schedule.offices.party_x", field_role="Office — Party A"),
            _isda_text(34, "office-party-y", "{{schedule.offices.party_y}}", kind="field", field_path="schedule.offices.party_y", field_role="Office — Party B"),
            _isda_text(34, "credit-support-provider-party-x", "{{schedule.agreements.credit_support_provider_party_x}}", kind="field", field_path="schedule.agreements.credit_support_provider_party_x", field_role="Credit Support Provider — Party A"),
            _isda_text(34, "credit-support-document-party-x", "{{schedule.agreements.credit_support_document_party_x}}", kind="field", field_path="schedule.agreements.credit_support_document_party_x", field_role="Credit Support Document — Party A"),
            _isda_text(34, "multibranch-offices-party-x", "{{schedule.offices.multibranch_offices_party_x}}", kind="field", field_path="schedule.offices.multibranch_offices_party_x", field_role="Multibranch Offices — Party A"),
            _isda_text(34, "multibranch-offices-party-y", "{{schedule.offices.multibranch_offices_party_y}}", kind="field", field_path="schedule.offices.multibranch_offices_party_y", field_role="Multibranch Offices — Party B"),
        ],
        35: [
            _isda_text(35, "schedule-payment-netting", "PART 5. PAYMENT NETTING", kind="schedule", heading=True, break_before=True),
            _isda_text(35, "schedule-payment-netting-purpose", "Part 5 records payment-netting elections and other Schedule provisions.", kind="clause"),
            _isda_text(35, "payment-netting-election", "{{schedule.payment_netting.multiple_transaction}}", kind="field", field_path="schedule.payment_netting.multiple_transaction", field_role="Multiple Transaction Payment Netting election"),
        ],
        36: [
            _isda_text(36, "schedule-other-provisions", "Part 5. Other Provisions.", kind="schedule", heading=True, break_before=True),
            _isda_text(36, "schedule-other-provisions-purpose", "Other provisions and execution details complete the Schedule.", kind="clause"),
            _isda_text(36, "execution-clause", "IN WITNESS WHEREOF the parties have executed this Agreement.", kind="signature", heading=True, break_before=False),
            _isda_text(36, "signature-attestation", "Each signatory confirms due authorisation to execute the Schedule.", kind="signature"),
            _isda_text(36, "signature-party-x-name-of-party", "{{signatures.party_x.name_of_party}}", kind="field", field_path="signatures.party_x.name_of_party", field_role="Party A legal name"),
            _isda_text(36, "signature-party-x-by", "{{signatures.party_x.by}}", kind="signature", field_path="signatures.party_x.by", field_role="Party A signature"),
            _isda_text(36, "signature-party-x-name", "{{signatures.party_x.name}}", kind="field", field_path="signatures.party_x.name", field_role="Party A name"),
            _isda_text(36, "signature-party-x-title", "{{signatures.party_x.title}}", kind="field", field_path="signatures.party_x.title", field_role="Party A title"),
            _isda_text(36, "signature-party-x-date", "{{signatures.party_x.date}}", kind="field", field_path="signatures.party_x.date", field_role="Party A execution date"),
            _isda_text(36, "signature-party-y-by", "{{signatures.party_y.by}}", kind="signature", field_path="signatures.party_y.by", field_role="Party B signature"),
            _isda_text(36, "signature-party-y-name-of-party", "{{signatures.party_y.name_of_party}}", kind="field", field_path="signatures.party_y.name_of_party", field_role="Party B legal name"),
            _isda_text(36, "signature-party-y-name", "{{signatures.party_y.name}}", kind="field", field_path="signatures.party_y.name", field_role="Party B name"),
            _isda_text(36, "signature-party-y-title", "{{signatures.party_y.title}}", kind="field", field_path="signatures.party_y.title", field_role="Party B title"),
            _isda_text(36, "signature-party-y-date", "{{signatures.party_y.date}}", kind="field", field_path="signatures.party_y.date", field_role="Party B execution date"),
        ],
    }
    measured_fields = {
        29: [
            ("counterparty-type-party-x", "schedule.elections.counterparty_type_party_x", "Counterparty type — Party A"),
            ("company-number-party-x", "schedule.elections.company_number_party_x", "Company number — Party A"),
            ("jurisdiction-party-x", "schedule.elections.jurisdiction_party_x", "Jurisdiction — Party A"),
            ("branch-party-x", "schedule.elections.branch_party_x", "Branch — Party A"),
            ("counterparty-type-party-y", "schedule.elections.counterparty_type_party_y", "Counterparty type — Party B"),
            ("company-number-party-y", "schedule.elections.company_number_party_y", "Company number — Party B"),
            ("jurisdiction-party-y", "schedule.elections.jurisdiction_party_y", "Jurisdiction — Party B"),
            ("branch-party-y", "schedule.elections.branch_party_y", "Branch — Party B"),
            ("specified-entity-5a-v-party-x", "schedule.elections.specified_entity_5a_v_party_x", "Specified Entity for Section 5(a)(v) — Party A"),
            ("specified-entity-5a-vi-party-x", "schedule.elections.specified_entity_5a_vi_party_x", "Specified Entity for Section 5(a)(vi) — Party A"),
            ("specified-entity-5a-vii-party-x", "schedule.elections.specified_entity_5a_vii_party_x", "Specified Entity for Section 5(a)(vii) — Party A"),
            ("specified-entity-5b-v-party-x", "schedule.elections.specified_entity_5b_v_party_x", "Specified Entity for Section 5(b)(v) — Party A"),
            ("specified-entity-5a-v-party-y", "schedule.elections.specified_entity_5a_v_party_y", "Specified Entity for Section 5(a)(v) — Party B"),
            ("specified-entity-5a-vi-party-y", "schedule.elections.specified_entity_5a_vi_party_y", "Specified Entity for Section 5(a)(vi) — Party B"),
            ("specified-entity-5a-vii-party-y", "schedule.elections.specified_entity_5a_vii_party_y", "Specified Entity for Section 5(a)(vii) — Party B"),
            ("specified-entity-5b-v-party-y", "schedule.elections.specified_entity_5b_v_party_y", "Specified Entity for Section 5(b)(v) — Party B"),
        ],
        30: [
            ("specified-transaction", "schedule.elections.specified_transaction", "Specified Transaction election"),
            ("cross-default-party-x", "schedule.elections.cross_default_party_x", "Cross-Default election — Party A"),
            ("cross-default-party-y", "schedule.elections.cross_default_party_y", "Cross-Default election — Party B"),
            ("grace-period-party-x", "schedule.termination.cross_default.grace_period_party_x", "Cross-Default grace period — Party A"),
            ("grace-period-party-y", "schedule.termination.cross_default.grace_period_party_y", "Cross-Default grace period — Party B"),
            ("credit-event-merger-party-x", "schedule.elections.credit_event_upon_merger_party_x", "Credit Event Upon Merger — Party A"),
            ("credit-event-merger-party-y", "schedule.elections.credit_event_upon_merger_party_y", "Credit Event Upon Merger — Party B"),
            ("automatic-early-termination-party-x", "schedule.elections.automatic_early_termination_party_x", "Automatic Early Termination — Party A"),
            ("automatic-early-termination-party-y", "schedule.elections.automatic_early_termination_party_y", "Automatic Early Termination — Party B"),
            ("termination-currency", "schedule.elections.termination_currency", "Termination Currency"),
        ],
        31: [
            ("payer-tax-party-x", "schedule.tax.payer_party_x", "Payer Tax Representation — Party A"),
            ("payer-tax-party-y", "schedule.tax.payer_party_y", "Payer Tax Representation — Party B"),
            ("payee-tax-party-x", "schedule.tax.payee_party_x", "Payee Tax Representation — Party A"),
            ("payee-tax-party-y", "schedule.tax.payee_party_y", "Payee Tax Representation — Party B"),
            ("tax-jurisdiction-party-y", "schedule.tax.jurisdiction_party_y", "Tax jurisdiction — Party B"),
            ("specified-treaty-party-x", "schedule.tax.specified_treaty_party_x", "Specified Treaty — Party A"),
            ("specified-treaty-party-y", "schedule.tax.specified_treaty_party_y", "Specified Treaty — Party B"),
            ("specified-jurisdiction-party-x", "schedule.tax.specified_jurisdiction_party_x", "Specified Jurisdiction — Party A"),
            ("specified-jurisdiction-party-y", "schedule.tax.specified_jurisdiction_party_y", "Specified Jurisdiction — Party B"),
            ("payer-representation-choice-party-x", "schedule.tax.payer_representation_choice_party_x", "Payer Representation choice — Party A"),
            ("payer-representation-choice-party-y", "schedule.tax.payer_representation_choice_party_y", "Payer Representation choice — Party B"),
            ("payee-representation-choice-party-x", "schedule.tax.payee_representation_choice_party_x", "Payee Representation choice — Party A"),
            ("payee-representation-choice-party-y", "schedule.tax.payee_representation_choice_party_y", "Payee Representation choice — Party B"),
            ("payer-representation-detail-party-x", "schedule.tax.payer_representation_detail_party_x", "Payer Representation detail — Party A"),
            ("payer-representation-detail-party-y", "schedule.tax.payer_representation_detail_party_y", "Payer Representation detail — Party B"),
            ("payee-representation-detail-party-x", "schedule.tax.payee_representation_detail_party_x", "Payee Representation detail — Party A"),
            ("payee-representation-detail-party-y", "schedule.tax.payee_representation_detail_party_y", "Payee Representation detail — Party B"),
        ],
        32: [
            ("tax-representation-party-x", "schedule.tax.additional_representation_party_x", "Additional tax representation — Party A"),
            ("tax-representation-party-y", "schedule.tax.additional_representation_party_y", "Additional tax representation — Party B"),
            ("document-delivery-party-x", "schedule.agreements.document_delivery_party_x", "Document delivery agreement — Party A"),
            ("document-delivery-party-y", "schedule.agreements.document_delivery_party_y", "Document delivery agreement — Party B"),
        ],
        33: [
            ("notice-address-party-x", "schedule.notices.address_party_x", "Notice address — Party A"),
            ("notice-address-party-y", "schedule.notices.address_party_y", "Notice address — Party B"),
            ("notice-attention-party-x", "schedule.notices.attention_party_x", "Notice attention — Party A"),
            ("notice-attention-party-y", "schedule.notices.attention_party_y", "Notice attention — Party B"),
            ("notice-email-party-x", "schedule.notices.email_party_x", "Notice E-mail — Party A"),
            ("notice-email-party-y", "schedule.notices.email_party_y", "Notice E-mail — Party B"),
            ("notice-messaging-party-x", "schedule.notices.electronic_messaging_party_x", "Electronic Messaging System Details — Party A"),
            ("notice-messaging-party-y", "schedule.notices.electronic_messaging_party_y", "Electronic Messaging System Details — Party B"),
            ("notice-instructions-party-x", "schedule.notices.specific_instructions_party_x", "Specific Instructions — Party A"),
            ("notice-instructions-party-y", "schedule.notices.specific_instructions_party_y", "Specific Instructions — Party B"),
        ],
        34: [
            ("multibranch-party-x", "schedule.offices.multibranch_party_x", "Multibranch Party election — Party A"),
            ("multibranch-party-y", "schedule.offices.multibranch_party_y", "Multibranch Party election — Party B"),
            ("offices-application", "schedule.offices.application", "Offices provision election"),
            ("calculation-agent", "schedule.offices.calculation_agent", "Calculation Agent"),
            ("credit-support-document", "schedule.agreements.credit_support_document", "Credit Support Document"),
            ("credit-support-provider-party-y", "schedule.agreements.credit_support_provider_party_y", "Credit Support Provider — Party B"),
            ("governing-law", "schedule.additional_provisions.governing_law", "Governing Law"),
        ],
        35: [
            ("netting-transactions", "schedule.payment_netting.transactions", "Payment-netting Transactions"),
            ("netting-start-date", "schedule.payment_netting.start_date", "Payment-netting start date"),
            ("affiliate", "schedule.additional_provisions.affiliate", "Affiliate definition election"),
            ("absence-litigation-specified-entity-party-x", "schedule.additional_provisions.absence_of_litigation_party_x", "Absence of Litigation Specified Entity — Party A"),
            ("absence-litigation-specified-entity-party-y", "schedule.additional_provisions.absence_of_litigation_party_y", "Absence of Litigation Specified Entity — Party B"),
            ("no-agency", "schedule.additional_provisions.no_agency", "No Agency election"),
            ("additional-representation", "schedule.additional_provisions.additional_representation", "Additional Representation election"),
            ("additional-representation-detail", "schedule.additional_provisions.additional_representation_detail", "Additional Representation detail"),
            ("recording-conversations", "schedule.additional_provisions.recording_conversations", "Recording of Conversations election"),
        ],
    }
    source_positions_mm = {
        "counterparty-type-party-x": (36, 120), "company-number-party-x": (42, 127), "jurisdiction-party-x": (42, 133), "branch-party-x": (45, 140),
        "counterparty-type-party-y": (118, 120), "company-number-party-y": (124, 127), "jurisdiction-party-y": (124, 133), "branch-party-y": (126, 140),
        "specified-transaction": (72, 35), "cross-default-party-x": (67, 57), "cross-default-party-y": (110, 62), "credit-event-merger-party-x": (86, 101), "termination-currency": (75, 122),
        "notice-address-party-x": (55, 118), "notice-attention-party-x": (55, 124), "process-agent-party-x": (65, 43), "process-agent-party-y": (65, 50),
        "netting-transactions": (133, 48), "netting-start-date": (40, 60), "signature-party-x-by": (25, 184), "signature-party-x-name": (25, 190), "signature-party-x-title": (25, 196), "signature-party-x-date": (32, 202),
        "signature-party-y-by": (116, 184), "signature-party-y-name": (116, 190), "signature-party-y-title": (116, 196), "signature-party-y-date": (123, 202),
    }
    for semantic_id, field_path, field_role in measured_fields.get(page_number, []):
        field = _isda_text(page_number, semantic_id, "{{" + field_path + "}}", kind="field", field_path=field_path, field_role=field_role)
        if semantic_id in source_positions_mm:
            field.update({"position_mode": "absolute", "position_unit": "mm", "position_x": source_positions_mm[semantic_id][0], "position_y": source_positions_mm[semantic_id][1], "position_provenance": "provisional-source-region", "calibration_source": "isda-source-measurements"})
        page[page_number].append(field)
    for block in page[page_number]:
        semantic_id = block.get("semantic_id")
        if semantic_id in source_positions_mm:
            block.update({"position_mode": "absolute", "position_unit": "mm", "position_x": source_positions_mm[semantic_id][0], "position_y": source_positions_mm[semantic_id][1], "position_provenance": "provisional-source-region", "calibration_source": "isda-source-measurements"})
    return page[page_number]


def _definitions_and_schedule_blocks(page_number: int) -> list[dict]:
    if page_number <= 28:
        definitions = {
            25: [
                _isda_text(25, "definitions-tax-loss-market", "Indemnifiable Tax; Law; Local Business Day; Loss; Market Quotation", kind="clause", heading=True, break_before=True),
                _isda_text(25, "definitions-indemnifiable-tax", "Indemnifiable Tax means a Tax other than a Tax imposed on overall net income, subject to the Agreement's stated exclusions.", kind="clause"),
                _isda_text(25, "definitions-law", "Law includes any statute, regulation, rule, order or other legally binding requirement applicable to a party or Transaction.", kind="clause"),
                _isda_text(25, "definitions-local-business-day", "Local Business Day means a day on which commercial banks are open for business in the relevant location.", kind="clause"),
                _isda_text(25, "definitions-loss", "Loss means the amount of a party's losses, costs or expenses, including a loss of bargain, resulting from a Termination Event or related close-out.", kind="clause"),
                _isda_text(25, "definitions-market-quotation", "Market Quotation means the amount quoted by a Reference Market-maker for replacing or providing the economic equivalent of a Terminated Transaction.", kind="clause"),
                _isda_text(25, "definition-indemnifiable-tax", "{{definitions.indemnifiable_tax}}", kind="field", field_path="definitions.indemnifiable_tax", field_role="Indemnifiable Tax definition"),
                _isda_text(25, "definition-law", "{{definitions.law}}", kind="field", field_path="definitions.law", field_role="Law definition"),
                _isda_text(25, "definition-local-business-day", "{{definitions.local_business_day}}", kind="field", field_path="definitions.local_business_day", field_role="Local Business Day definition"),
                _isda_text(25, "definition-loss", "{{definitions.loss}}", kind="field", field_path="definitions.loss", field_role="Loss definition"),
                _isda_text(25, "definition-market-quotation", "{{definitions.market_quotation}}", kind="field", field_path="definitions.market_quotation", field_role="Market Quotation definition"),
            ],
            26: [
                _isda_text(26, "definitions-notice-office", "Non-defaulting Party; Notice; Office; Potential Event of Default; Proceedings", kind="clause", heading=True, break_before=True),
                _isda_text(26, "definitions-non-defaulting-party", "Non-defaulting Party identifies the party that is not the Defaulting Party for the relevant Event of Default.", kind="clause"),
                _isda_text(26, "definitions-notice", "Notice means a notice given in accordance with the Agreement's notice provisions.", kind="clause"),
                _isda_text(26, "definitions-office", "Office means an office or branch through which a party enters into or performs a Transaction, as specified in the Agreement or Schedule.", kind="clause"),
                _isda_text(26, "definitions-potential-event-of-default", "Potential Event of Default means an event which, with the giving of notice, lapse of time or both, would become an Event of Default.", kind="clause"),
                _isda_text(26, "definitions-proceedings", "Proceedings means proceedings before a court, tribunal, regulator or other authority, including insolvency or reorganisation proceedings.", kind="clause"),
                _isda_text(26, "definition-non-defaulting-party", "{{definitions.non_defaulting_party}}", kind="field", field_path="definitions.non_defaulting_party", field_role="Non-defaulting Party definition"),
                _isda_text(26, "definition-notice", "{{definitions.notice}}", kind="field", field_path="definitions.notice", field_role="Notice definition"),
                _isda_text(26, "definition-office", "{{definitions.office}}", kind="field", field_path="definitions.office", field_role="Office definition"),
                _isda_text(26, "definition-potential-event-of-default", "{{definitions.potential_event_of_default}}", kind="field", field_path="definitions.potential_event_of_default", field_role="Potential Event of Default definition"),
                _isda_text(26, "definition-proceedings", "{{definitions.proceedings}}", kind="field", field_path="definitions.proceedings", field_role="Proceedings definition"),
            ],
            27: [
                _isda_text(27, "definitions-transaction", "Specified Entity; Specified Indebtedness; Tax; Termination Event; Transaction; Unpaid Amounts", kind="clause", heading=True, break_before=True),
                _isda_text(27, "definitions-specified-entity", "Specified Entity means an entity identified as such in the Schedule or otherwise specified for the relevant provision.", kind="clause"),
                _isda_text(27, "definitions-specified-indebtedness", "Specified Indebtedness means indebtedness of the type and scope specified in the Schedule or relevant provision.", kind="clause"),
                _isda_text(27, "definitions-tax", "Tax includes any present or future tax, levy, impost, duty, charge, fee, deduction or withholding imposed by a taxing authority.", kind="clause"),
                _isda_text(27, "definitions-termination-event", "Termination Event means an event or circumstance specified in Section 5 or the Schedule that permits termination of affected Transactions.", kind="clause"),
                _isda_text(27, "definitions-transaction-term", "Transaction means a transaction entered into under the Agreement, including each transaction evidenced by a Confirmation.", kind="clause"),
                _isda_text(27, "definitions-unpaid-amounts", "Unpaid Amounts means amounts due and payable under the Agreement that remain unpaid after their due date.", kind="clause"),
                _isda_text(27, "definition-specified-entity", "{{definitions.specified_entity}}", kind="field", field_path="definitions.specified_entity", field_role="Specified Entity definition"),
                _isda_text(27, "definition-specified-indebtedness", "{{definitions.specified_indebtedness}}", kind="field", field_path="definitions.specified_indebtedness", field_role="Specified Indebtedness definition"),
                _isda_text(27, "definition-tax", "{{definitions.tax}}", kind="field", field_path="definitions.tax", field_role="Tax definition"),
                _isda_text(27, "definition-termination-event", "{{definitions.termination_event}}", kind="field", field_path="definitions.termination_event", field_role="Termination Event definition"),
                _isda_text(27, "definition-transaction", "{{definitions.transaction}}", kind="field", field_path="definitions.transaction", field_role="Transaction definition"),
                _isda_text(27, "definition-unpaid-amounts", "{{definitions.unpaid_amounts}}", kind="field", field_path="definitions.unpaid_amounts", field_role="Unpaid Amounts definition"),
            ],
            28: [
                _isda_text(28, "execution-intro", "EXECUTION", kind="clause", heading=True, break_before=True),
                _isda_text(28, "master-execution-clause", "IN WITNESS WHEREOF the parties have executed this Agreement as of the date specified above.", kind="signature"),
                _isda_text(28, "execution-attestation", "Each signatory confirms due authorisation to execute the Agreement.", kind="signature"),
                _isda_text(28, "execution-agreement-date", "{{agreement_date}}", kind="field", field_path="agreement_date", field_role="Agreement execution date"),
                _isda_text(28, "master-signature-party-x-name-of-party", "{{master_signatures.party_x.name_of_party}}", kind="field", field_path="master_signatures.party_x.name_of_party", field_role="Master Agreement Party A legal name"),
                _isda_text(28, "master-signature-party-x-by", "{{master_signatures.party_x.by}}", kind="signature", field_path="master_signatures.party_x.by", field_role="Master Agreement Party A signature"),
                _isda_text(28, "master-signature-party-x-name", "{{master_signatures.party_x.name}}", kind="field", field_path="master_signatures.party_x.name", field_role="Master Agreement Party A name"),
                _isda_text(28, "master-signature-party-x-title", "{{master_signatures.party_x.title}}", kind="field", field_path="master_signatures.party_x.title", field_role="Master Agreement Party A title"),
                _isda_text(28, "master-signature-party-x-date", "{{master_signatures.party_x.date}}", kind="field", field_path="master_signatures.party_x.date", field_role="Master Agreement Party A execution date"),
                _isda_text(28, "master-signature-party-y-by", "{{master_signatures.party_y.by}}", kind="signature", field_path="master_signatures.party_y.by", field_role="Master Agreement Party B signature"),
                _isda_text(28, "master-signature-party-y-name-of-party", "{{master_signatures.party_y.name_of_party}}", kind="field", field_path="master_signatures.party_y.name_of_party", field_role="Master Agreement Party B legal name"),
                _isda_text(28, "master-signature-party-y-name", "{{master_signatures.party_y.name}}", kind="field", field_path="master_signatures.party_y.name", field_role="Master Agreement Party B name"),
                _isda_text(28, "master-signature-party-y-title", "{{master_signatures.party_y.title}}", kind="field", field_path="master_signatures.party_y.title", field_role="Master Agreement Party B title"),
                _isda_text(28, "master-signature-party-y-date", "{{master_signatures.party_y.date}}", kind="field", field_path="master_signatures.party_y.date", field_role="Master Agreement Party B execution date"),
            ],
        }
        return definitions[page_number]
    return _schedule_and_execution_blocks(page_number)


def isda_sample_data() -> dict:
    return {"agreement_date": "31 December 2002", "party_x": "Party X", "party_y": "Party Y", "schedule_documents": [{"document": "Tax form", "delivery_date": "2002-12-31", "covered_by_section_3d": "Yes"}, {"document": "Authorisation evidence", "delivery_date": "2002-12-31", "covered_by_section_3d": "No"}], "definitions": {"market_quotation": "Commercially reasonable quotation", "office": "Designated branch", "proceedings": "Court proceedings", "termination_event": "Termination Event", "transaction": "A transaction under a Confirmation"}, "schedule": {"party_x": "Party X", "party_y": "Party Y", "termination": {"cross_default": {"threshold_party_x": "USD 10,000,000", "threshold_party_y": "USD 10,000,000"}, "automatic_early_termination": "Not applicable"}, "tax": {"payer_representation_party_x": "Specified", "payee_representation_party_x": "Specified", "jurisdiction_party_x": "New York"}, "agreements": {"credit_support_provider_party_x": "None", "credit_support_document_party_x": "None"}, "process_agent": {"party_x": "Process Agent A", "party_y": "Process Agent B"}, "offices": {"party_x": "New York", "party_y": "London"}, "payment_netting": {"multiple_transaction": "Applicable"}, "notices": {"party_x": "Party X notice address", "party_y": "Party Y notice address"}}, "signatures": {"party_x": {"by": "____________________", "name": "Authorised signatory A", "title": "Director", "date": "31 December 2002"}, "party_y": {"by": "____________________", "name": "Authorised signatory B", "title": "Director", "date": "31 December 2002"}}}


_BASE_ISDA_SAMPLE_DATA = isda_sample_data


def isda_sample_data() -> dict:
    sample = _BASE_ISDA_SAMPLE_DATA()
    sample["definitions"].update({"indemnifiable_tax": "An indemnifiable tax under Section 7", "law": "Applicable law", "local_business_day": "A day on which commercial banks are open", "loss": "Loss determined under the Agreement", "non_defaulting_party": "The party that is not the Defaulting Party", "notice": "A notice under Section 12", "potential_event_of_default": "An event that may become an Event of Default", "specified_entity": "A Specified Entity under the Schedule", "specified_indebtedness": "Indebtedness specified in the Schedule", "tax": "A tax described in Section 14", "unpaid_amounts": "Amounts unpaid when due"})
    sample["schedule_documents"][0].update({"party_required": "Party X", "form_document": "Tax form"})
    sample["schedule_documents"][1].update({"party_required": "Party Y", "form_document": "Authorisation evidence"})
    sample["schedule_tax_documents"] = [{"party_required": "Party X", "form_document": "Tax form", "delivery_date": "2002-12-31"}, {"party_required": "Party Y", "form_document": "Tax residency certificate", "delivery_date": "2002-12-31"}]
    sample["schedule"]["termination"]["cross_default"].update({"grace_period_party_x": "30 days", "grace_period_party_y": "30 days"})
    sample["schedule"]["elections"] = {"counterparty_type_party_x": "Corporation", "company_number_party_x": "X-123", "jurisdiction_party_x": "New York", "branch_party_x": "New York", "counterparty_type_party_y": "Corporation", "company_number_party_y": "Y-456", "jurisdiction_party_y": "England", "branch_party_y": "London", "specified_entity_5a_v_party_x": "None", "specified_entity_5a_vi_party_x": "None", "specified_entity_5a_vii_party_x": "None", "specified_entity_5b_v_party_x": "None", "specified_entity_5a_v_party_y": "None", "specified_entity_5a_vi_party_y": "None", "specified_entity_5a_vii_party_y": "None", "specified_entity_5b_v_party_y": "None", "specified_transaction": "Specified Transactions", "specified_indebtedness": "Specified Indebtedness", "additional_termination_event": "None", "cross_default_party_x": "Applicable", "cross_default_party_y": "Applicable", "grace_period_party_x": "30 days", "grace_period_party_y": "30 days", "automatic_early_termination_party_x": "Not applicable", "automatic_early_termination_party_y": "Not applicable", "credit_event_upon_merger_party_x": "Not applicable", "credit_event_upon_merger_party_y": "Not applicable", "termination_currency": "United States Dollars"}
    sample["schedule"]["elections"].update({"specified_transaction_detail": "Transactions designated in the applicable Confirmation", "specified_indebtedness_detail": "Indebtedness above the agreed Threshold Amount", "additional_termination_event_detail": "None", "termination_currency_detail": "United States Dollars"})
    sample["schedule"]["tax"].update({"payer_party_x": "Specified", "payer_party_y": "Specified", "payee_party_x": "Specified", "payee_party_y": "Specified", "jurisdiction_party_y": "England", "specified_treaty_party_x": "United States treaty", "specified_treaty_party_y": "United Kingdom treaty", "specified_jurisdiction_party_x": "New York", "specified_jurisdiction_party_y": "England", "payer_representation_choice_party_x": "Option (i)", "payer_representation_choice_party_y": "Option (i)", "payee_representation_choice_party_x": "Option (i)", "payee_representation_choice_party_y": "Option (i)", "payer_representation_detail_party_x": "No additional payer representation", "payer_representation_detail_party_y": "No additional payer representation", "payee_representation_detail_party_x": "No additional payee representation", "payee_representation_detail_party_y": "No additional payee representation", "additional_representation_party_x": "None", "additional_representation_party_y": "None"})
    sample["schedule"]["agreements"].update({"document_delivery_party_x": "Applicable", "document_delivery_party_y": "Applicable", "credit_support_document": "None", "credit_support_provider_party_y": "None"})
    sample["schedule"]["notices"].update({"address_party_x": "Party X notice address", "address_party_y": "Party Y notice address", "attention_party_x": "Legal", "attention_party_y": "Legal", "telex_party_x": "TELEX-A", "telex_party_y": "TELEX-B", "answerback_party_x": "ANSWER-A", "answerback_party_y": "ANSWER-B", "facsimile_party_x": "+1 212 555 0101", "facsimile_party_y": "+44 20 5555 0102", "telephone_party_x": "+1 212 555 0103", "telephone_party_y": "+44 20 5555 0104", "email_party_x": "legal@partya.example", "email_party_y": "legal@partyb.example", "electronic_messaging_party_x": "System A", "electronic_messaging_party_y": "System B", "specific_instructions_party_x": "None", "specific_instructions_party_y": "None"})
    sample["schedule"]["offices"].update({"multibranch_party_x": "Not applicable", "multibranch_party_y": "Not applicable", "multibranch_offices_party_x": "New York", "multibranch_offices_party_y": "London", "application": "Applicable", "calculation_agent": "Party X"})
    sample["schedule"]["payment_netting"].update({"transactions": "All Transactions", "start_date": "2002-12-31"})
    sample["schedule"]["additional_provisions"] = {"affiliate": "Specified in Section 14", "absence_of_litigation_party_x": "None", "absence_of_litigation_party_y": "None", "no_agency": "Applicable", "governing_law": "New York law", "additional_representation": "Not applicable", "additional_representation_detail": "None", "recording_conversations": "Applicable"}
    sample["master_signatures"] = {"party_x": {"name_of_party": "Party X", "by": "____________________", "name": "Master signatory A", "title": "Director", "date": "31 December 2002"}, "party_y": {"name_of_party": "Party Y", "by": "____________________", "name": "Master signatory B", "title": "Director", "date": "31 December 2002"}}
    sample["signatures"]["party_x"]["name_of_party"] = "Party X"
    sample["signatures"]["party_y"]["name_of_party"] = "Party Y"
    return sample


def _base_isda_data_schema() -> dict:
    string = lambda title: {"title": title, "type": "string"}
    date = lambda title: {"title": title, "type": "string", "format": "date"}
    party = lambda title: {"title": title, "type": "object", "properties": {"party_x": string(f"{title} — Party A"), "party_y": string(f"{title} — Party B")}}
    return {"$id": "isda-master-agreement", "type": "object", "x-docplatform-schema-version": 3, "properties": {
        "agreement_date": date("Agreement date"), "party_x": string("Party X"), "party_y": string("Party Y"),
        "definitions": {"title": "Defined terms", "type": "object", "properties": {"indemnifiable_tax": string("Indemnifiable Tax definition"), "law": string("Law definition"), "local_business_day": string("Local Business Day definition"), "loss": string("Loss definition"), "market_quotation": string("Market Quotation definition"), "non_defaulting_party": string("Non-defaulting Party definition"), "notice": string("Notice definition"), "office": string("Office definition"), "potential_event_of_default": string("Potential Event of Default definition"), "proceedings": string("Proceedings definition"), "specified_entity": string("Specified Entity definition"), "specified_indebtedness": string("Specified Indebtedness definition"), "tax": string("Tax definition"), "termination_event": string("Termination Event definition"), "transaction": string("Transaction definition"), "unpaid_amounts": string("Unpaid Amounts definition")}},
        "schedule_documents": {"title": "Schedule documents", "type": "array", "items": {"type": "object", "properties": {"party_required": string("Party required to deliver"), "form_document": string("Form, Document or Certificate"), "document": string("Document"), "delivery_date": date("Date by which to be delivered"), "covered_by_section_3d": string("Covered by Section 3(d) Representation")}}},
        "schedule_tax_documents": {"title": "Schedule tax documents", "type": "array", "items": {"type": "object", "properties": {"party_required": string("Party required to deliver"), "form_document": string("Form, Document or Certificate"), "delivery_date": date("Date by which to be delivered")}}},
        "schedule": {"title": "Schedule elections", "type": "object", "properties": {
            "party_x": string("Schedule Party A"), "party_y": string("Schedule Party B"),
            "elections": {"title": "Schedule elections", "type": "object", "properties": {"counterparty_type_party_x": string("Counterparty type — Party A"), "company_number_party_x": string("Company number — Party A"), "jurisdiction_party_x": string("Jurisdiction — Party A"), "branch_party_x": string("Branch — Party A"), "counterparty_type_party_y": string("Counterparty type — Party B"), "company_number_party_y": string("Company number — Party B"), "jurisdiction_party_y": string("Jurisdiction — Party B"), "branch_party_y": string("Branch — Party B"), "specified_entity_5a_v_party_x": string("Specified Entity for Section 5(a)(v) — Party A"), "specified_entity_5a_vi_party_x": string("Specified Entity for Section 5(a)(vi) — Party A"), "specified_entity_5a_vii_party_x": string("Specified Entity for Section 5(a)(vii) — Party A"), "specified_entity_5b_v_party_x": string("Specified Entity for Section 5(b)(v) — Party A"), "specified_entity_5a_v_party_y": string("Specified Entity for Section 5(a)(v) — Party B"), "specified_entity_5a_vi_party_y": string("Specified Entity for Section 5(a)(vi) — Party B"), "specified_entity_5a_vii_party_y": string("Specified Entity for Section 5(a)(vii) — Party B"), "specified_entity_5b_v_party_y": string("Specified Entity for Section 5(b)(v) — Party B"), "specified_transaction": string("Specified Transaction election"), "specified_indebtedness": string("Specified Indebtedness election"), "additional_termination_event": string("Additional Termination Event election"), "cross_default_party_x": string("Cross-Default election — Party A"), "cross_default_party_y": string("Cross-Default election — Party B"), "automatic_early_termination_party_x": string("Automatic Early Termination — Party A"), "automatic_early_termination_party_y": string("Automatic Early Termination — Party B"), "credit_event_upon_merger_party_x": string("Credit Event Upon Merger — Party A"), "credit_event_upon_merger_party_y": string("Credit Event Upon Merger — Party B"), "termination_currency": string("Termination Currency")}},
            "termination": {"title": "Termination provisions", "type": "object", "properties": {"cross_default": {"title": "Cross-Default", "type": "object", "properties": {"threshold_party_x": string("Cross-Default threshold — Party A"), "threshold_party_y": string("Cross-Default threshold — Party B"), "grace_period_party_x": string("Cross-Default grace period — Party A"), "grace_period_party_y": string("Cross-Default grace period — Party B")}}, "automatic_early_termination": string("Automatic Early Termination election")}},
            "tax": {"title": "Tax representations", "type": "object", "properties": {"payer_representation_party_x": string("Payer Tax Representation — Party A"), "payee_representation_party_x": string("Payee Tax Representation — Party A"), "jurisdiction_party_x": string("Tax jurisdiction — Party A"), "jurisdiction_party_y": string("Tax jurisdiction — Party B"), "specified_treaty_party_x": string("Specified Treaty — Party A"), "specified_treaty_party_y": string("Specified Treaty — Party B"), "specified_jurisdiction_party_x": string("Specified Jurisdiction — Party A"), "specified_jurisdiction_party_y": string("Specified Jurisdiction — Party B"), "payer_representation_choice_party_x": string("Payer Representation choice — Party A"), "payer_representation_choice_party_y": string("Payer Representation choice — Party B"), "payee_representation_choice_party_x": string("Payee Representation choice — Party A"), "payee_representation_choice_party_y": string("Payee Representation choice — Party B"), "payer_party_x": string("Payer Tax Representation — Party A"), "payer_party_y": string("Payer Tax Representation — Party B"), "payee_party_x": string("Payee Tax Representation — Party A"), "payee_party_y": string("Payee Tax Representation — Party B"), "additional_representation_party_x": string("Additional tax representation — Party A"), "additional_representation_party_y": string("Additional tax representation — Party B")}},
            "agreements": {"title": "Additional agreements", "type": "object", "properties": {"credit_support_provider_party_x": string("Credit Support Provider — Party A"), "credit_support_provider_party_y": string("Credit Support Provider — Party B"), "credit_support_document_party_x": string("Credit Support Document — Party A"), "document_delivery_party_x": string("Document delivery agreement — Party A"), "document_delivery_party_y": string("Document delivery agreement — Party B"), "credit_support_document": string("Credit Support Document")}},
            "process_agent": party("Process Agent"),
            "offices": {"title": "Offices and calculation agent", "type": "object", "properties": {
                "party_x": string("Office — Party A"), "party_y": string("Office — Party B"),
                "multibranch_party_x": string("Multibranch Party election — Party A"),
                "multibranch_party_y": string("Multibranch Party election — Party B"),
                "application": string("Offices provision election"),
                "calculation_agent": string("Calculation Agent"),
            }},
            "payment_netting": {"title": "Payment netting", "type": "object", "properties": {"multiple_transaction": string("Multiple Transaction Payment Netting election"), "transactions": string("Payment-netting Transactions"), "start_date": date("Payment-netting start date")}},
            "additional_provisions": {"title": "Additional provisions", "type": "object", "properties": {"affiliate": string("Affiliate definition election"), "absence_of_litigation_party_x": string("Absence of Litigation — Party A"), "absence_of_litigation_party_y": string("Absence of Litigation — Party B"), "no_agency": string("No Agency election"), "governing_law": string("Governing Law"), "additional_representation": string("Additional Representation election"), "additional_representation_detail": string("Additional Representation detail"), "recording_conversations": string("Recording of Conversations election")}},
            "notices": {"title": "Notice addresses and attention lines", "type": "object", "properties": {
                "party_x": string("Notice address — Party A"), "party_y": string("Notice address — Party B"),
                "address_party_x": string("Notice address — Party A"), "address_party_y": string("Notice address — Party B"),
                "attention_party_x": string("Notice attention — Party A"), "attention_party_y": string("Notice attention — Party B"),
                "telex_party_x": string("Notice Telex number — Party A"), "telex_party_y": string("Notice Telex number — Party B"),
                "answerback_party_x": string("Notice Answerback — Party A"), "answerback_party_y": string("Notice Answerback — Party B"),
                "facsimile_party_x": string("Notice Facsimile number — Party A"), "facsimile_party_y": string("Notice Facsimile number — Party B"),
                "telephone_party_x": string("Notice Telephone number — Party A"), "telephone_party_y": string("Notice Telephone number — Party B"),
                "email_party_x": string("Notice E-mail — Party A"), "email_party_y": string("Notice E-mail — Party B"),
                "electronic_messaging_party_x": string("Electronic Messaging System Details — Party A"), "electronic_messaging_party_y": string("Electronic Messaging System Details — Party B"),
                "specific_instructions_party_x": string("Specific Instructions — Party A"), "specific_instructions_party_y": string("Specific Instructions — Party B"),
            }},
        }},
        "master_signatures": {"title": "Master Agreement signatures", "type": "object", "properties": {"party_x": {"title": "Master Agreement Party A signature", "type": "object", "properties": {"name_of_party": string("Master Agreement Party A legal name"), "by": string("Master Agreement Party A signature"), "name": string("Master Agreement Party A name"), "title": string("Master Agreement Party A title"), "date": date("Master Agreement Party A execution date")}}, "party_y": {"title": "Master Agreement Party B signature", "type": "object", "properties": {"name_of_party": string("Master Agreement Party B legal name"), "by": string("Master Agreement Party B signature"), "name": string("Master Agreement Party B name"), "title": string("Master Agreement Party B title"), "date": date("Master Agreement Party B execution date")}}}},
        "signatures": {"title": "Schedule signatures", "type": "object", "properties": {"party_x": {"title": "Schedule Party A signature", "type": "object", "properties": {"name_of_party": string("Schedule Party A legal name"), "by": string("Schedule Party A signature"), "name": string("Schedule Party A name"), "title": string("Schedule Party A title"), "date": date("Schedule Party A execution date")}}, "party_y": {"title": "Schedule Party B signature", "type": "object", "properties": {"name_of_party": string("Schedule Party B legal name"), "by": string("Schedule Party B signature"), "name": string("Schedule Party B name"), "title": string("Schedule Party B title"), "date": date("Schedule Party B execution date")}}}},
    }}


def isda_data_schema() -> dict:
    schema = _base_isda_data_schema()
    elections = schema["properties"]["schedule"]["properties"]["elections"]["properties"]
    elections.update({
        "specified_transaction_detail": {"title": "Specified Transaction detail", "type": "string"},
        "specified_indebtedness_detail": {"title": "Specified Indebtedness detail", "type": "string"},
        "additional_termination_event_detail": {"title": "Additional Termination Event detail", "type": "string"},
        "termination_currency_detail": {"title": "Termination Currency detail", "type": "string"},
    })
    tax = schema["properties"]["schedule"]["properties"]["tax"]["properties"]
    tax.update({
        "payer_representation_detail_party_x": {"title": "Payer Representation detail — Party A", "type": "string"},
        "payer_representation_detail_party_y": {"title": "Payer Representation detail — Party B", "type": "string"},
        "payee_representation_detail_party_x": {"title": "Payee Representation detail — Party A", "type": "string"},
        "payee_representation_detail_party_y": {"title": "Payee Representation detail — Party B", "type": "string"},
    })
    offices = schema["properties"]["schedule"]["properties"]["offices"]["properties"]
    offices.update({
        "multibranch_offices_party_x": {"title": "Multibranch Offices — Party A", "type": "string"},
        "multibranch_offices_party_y": {"title": "Multibranch Offices — Party B", "type": "string"},
    })
    return schema


def is_placeholder_isda(definition: dict) -> bool:
    blocks = definition.get("blocks") if isinstance(definition, dict) else None
    if not isinstance(blocks, list) or not blocks:
        return True
    texts = [str(block.get("text", "")) for block in blocks if isinstance(block, dict)]
    return bool(texts) and all(text.strip() in {"", "u{200B}", "\\u200B"} for text in texts)
