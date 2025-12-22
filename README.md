# TDD Process Safety Report Generation

[English](./README_en.md) | [中文](./README_zh.md)

## Title/Caption

- **Title:** DSC Report Generation Tool (Python)
- **Date Generated / Last Updated:** 2025-12-15
- **Produced For:** Process Safety / Materials reporting workflow (professional ePortfolio artifact)
- **Artifact Type:** Automation tool + report template pipeline (TXT/PDF → Word report)

## Project Structure

```shell
.
├── main.py                      # Application entry point
├── requirements.txt             # Python dependencies
├── README.md                    # Project documentation
├── log.md                       # Development notes / logs
├── problems.md                  # Known issues / TODOs
│
├── src/                         # Source code
│   ├── config/                  # Configuration (paths, defaults, constants)
│   │   └── config.py
│   ├── models/                  # Data models / typed structures for parsed results
│   │   └── models.py
│   ├── utils/                   # Core utilities: parsing, templating, text generation
│   │   ├── parser_dsc.py
│   │   ├── templating.py
│   │   └── dsc_text.py
│   ├── ui/                      # UI layer (PyQt)
│   │   └── ui_main.py
│   └── test/                    # Unit tests
│       └── test_segments.py
│
├── data/                        # Report templates (Word .docx)
│   ├── DSC Report-Empty-2511.docx
│   └── DSC Report-Empty-2512.docx
│
└── CF130G/                      # Sample input assets (example dataset)
    ├── PrnRes_CF130G_2025-05-06.txt
    ├── CF130G.pdf
    └── DSC test for CF130G.docx
```

## Description/Explanation

### Context

- **Goal / Purpose:** Automate the creation of standardized DSC (Differential Scanning Calorimetry) reports to reduce manual copy-paste work and improve report consistency and traceability.
- **Timeline / Scope:** Built as a focused prototype covering parsing, structured data modeling, and Word template report generation, with a pathway for UI-driven operation.
- **Where / When / For Whom:** Developed for an internal process safety reporting workflow where DSC results must be documented in a consistent format for review and recordkeeping.
- **My Role / Responsibilities:** Sole developer—responsible for project structure design, parsing logic, data models, template mapping, and end-to-end report generation.
- **Artifact History:** New build with iterative refinement using sample datasets (e.g., CF130G) and report templates stored under data/.
  
### Development Details

#### Resources Used

- python-docx for Word template editing and placeholder replacement
- PyMuPDF (fitz) for handling PDF content when needed (e.g., figures/screenshots)
- Modular code organization under src/ (config, models, utils, UI, tests)

#### Key Implementation Decisions

- Introduced typed models to represent parsed DSC results (improves maintainability and validation).
- Separated parsing, text generation, and templating to minimize coupling and simplify testing.
- Used templates in data/ to ensure report layout remains consistent while content is automated.

#### Constraints / Challenges

- Instrument output text can vary across methods/runs; required resilient parsing and edge-case handling.
- Word placeholder replacement can be affected by run splitting and formatting, requiring careful replacement logic.
- Managing repository hygiene (excluding sample data, temporary Word files like ~$*, and virtual environments).

#### Skills Applied / Developed

- Python engineering (modular design, typed modeling, parsing)
- Document automation (Word templating, structured text generation)
- QA mindset (basic unit tests under src/test, reproducible sample inputs)

### Outcome

- **Current Status:** Working prototype that parses DSC TXT outputs and generates a structured Word report using templates; includes sample input assets for validation and a test scaffold for parsing segments.
- **Feedback / Validation:** Verified generation correctness by running against sample datasets and ensuring report fields populate as expected; issues captured and tracked in problems.md.
- **Impact:** Reduces reporting time, standardizes report formatting, and decreases the risk of missing key thermal parameters due to manual transcription.

### Reflection

- **What I Learned:** Small variations in input formatting and document templating behaviors can cause disproportionate errors; robust parsing and validation are as important as core functionality.
- **What I Would Improve Next:**
  
  - Add stronger validation and clearer user-facing error messages (e.g., missing fields, parsing failures).
  - Make parsing rules configurable per instrument method/output format.
  - Improve PDF/image insertion sizing and layout control in generated reports.
  - Add CI to run tests automatically and enforce code quality gates.
  
