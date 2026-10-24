# Reports: what the user takes away

## Plain words
Plain words: three downloads: a filing sheet for the 1930 helpline / cybercrime.gov.in with the full identifiers, a
redacted summary safe to share (accounts as last 4 digits), and a structured incident card (JSON). Blanks stay blank:
VERIQ never invents a transaction ID or a phone number. Links from the chat are made unclickable.

| | |
|---|---|
| Code | `report/` |
| Goes in | the case and anything the user typed |
| Comes out | Markdown, HTML and JSON files |
| Can do | carry every payee, the evidence, the timeline and file fingerprints |
| Cannot say | file a complaint (the user does that); it is not an official NCRP format |
| Tests / numbers | `report/tests/`, `app/tests/test_finale_features.py::test_incident_card_json` |
| Known limit | English only for the reports. |
