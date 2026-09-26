# Bounded Word merge contract

`backend.app.word_merge.merge_docx` accepts a DOCX package as bytes and returns a new DOCX package plus a report. It rejects malformed ZIPs, traversal/absolute paths, oversized decompressed packages, VBA macro parts, and external relationships before any XML is interpreted.

The current offline merge path replaces scalar `{{dot.path}}` tokens when each token is contained in one Word text node. A table row may repeat with `{{#items}} ... {{/items}}` and `{{item.field}}` tokens; arrays are capped at 1,000 items. Main document, header, and footer XML parts are processed. Existing images and other package parts are preserved byte-for-byte, but image placeholders, split-run tokens, arbitrary Word fields, nested loop composition, and Word layout fidelity are not interpreted by this bounded implementation.

`POST /api/word/convert` accepts the merged base64 DOCX and invokes the configured `word_converter_command` as `command input.docx output.pdf` inside the credential-free document worker. The command receives a reduced environment, bounded wall time, a temporary working directory, and a generated Python network guard when it is a Python adapter. Native executable network isolation remains a deployment responsibility. The returned artifact must begin with a PDF signature, stay within the output limit, and pass the existing active-content gate. An empty command returns 503; no converter is bundled or selected by default.

This is an E6-02 implementation enabler and a conversion boundary, not conversion fidelity evidence. E6-03 remains partial until an explicitly reviewed, isolated conversion engine is selected, licensed, and validated against Word-authored fixtures.
