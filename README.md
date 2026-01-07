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
├── README.md                    # Project documentation (this file)
├── README_en.md                 # Detailed technical documentation (English)
├── README_zh.md                 # Detailed technical documentation (Chinese)
├── Placeholders.md              # Template placeholder reference
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
│   ├── tools/                   # Business logic controllers
│   │   ├── dsc_services.py      # Core parsing and report services
│   │   ├── workflow_controller.py
│   │   ├── sample_controller.py
│   │   ├── segments_controller.py
│   │   ├── report_controller.py
│   │   ├── form_controller.py
│   │   ├── theme_controller.py
│   │   └── make_logo_transparent.py
│   ├── ui/                      # UI layer (PyQt6)
│   │   ├── ui_main.py           # Main window
│   │   ├── dialog_add_sample.py # Sample addition dialog
│   │   └── widgets/             # Custom UI widgets
│   │       └── toggle_switch.py
│   ├── assets/                  # UI resources
│   │   ├── app.qss              # Dark theme stylesheet
│   │   ├── app_light.qss        # Light theme stylesheet
│   │   ├── app.ico              # Application icon (Windows)
│   │   ├── app.png              # Application icon
│   │   ├── logo.png             # Application logo
│   │   └── logo.jpg             # Application logo (alternative)
│   └── test/                    # Unit tests
│       └── test_segments.py
│
└── data/                        # Report templates (Word .docx)
    ├── DSC Report-Empty-2511.docx
    └── DSC Report-Empty-2512.docx
```

## Description/Explanation

### Context

- **Goal / Purpose:** Automate the creation of standardized DSC (Differential Scanning Calorimetry) reports to reduce manual copy-paste work and improve report consistency and traceability. The tool provides a graphical user interface for managing multiple samples, parsing instrument output files, and generating formatted Word documents.
- **Timeline / Scope:** Built as a complete desktop application with PyQt6 GUI, covering parsing, structured data modeling, multi-sample management, and Word template report generation. The application supports both dark and light themes, with a modular architecture for easy maintenance and extension.
- **Where / When / For Whom:** Developed for an internal process safety reporting workflow where DSC results must be documented in a consistent format for review and recordkeeping. The tool handles NETZSCH DSC instrument output files (TXT and PDF formats).
- **My Role / Responsibilities:** Sole developer—responsible for project structure design, parsing logic, data models, template mapping, UI/UX design, controller architecture, theme system, and end-to-end report generation.
- **Artifact History:** Evolved from a prototype to a full-featured desktop application with iterative refinement, including multi-sample support, enhanced UI, theme switching, and comprehensive error handling.
  
### Development Details

#### Resources Used

- **PyQt6** for cross-platform desktop GUI with modern styling (QSS stylesheets)
- **python-docx** for Word template editing and placeholder replacement
- **PyMuPDF (fitz)** for handling PDF content when needed (e.g., figures/screenshots, range extraction)
- **Modular code organization** under src/ with clear separation:
  - `config/` for configuration management
  - `models/` for typed data structures
  - `utils/` for core parsing and templating logic
  - `tools/` for business logic controllers (MVC pattern)
  - `ui/` for GUI components and dialogs
  - `assets/` for UI resources (icons, stylesheets, logos)
  - `test/` for unit tests

#### Key Implementation Decisions

- **Typed Data Models**: Introduced dataclasses (`DscBasicInfo`, `DscSegment`, `DscPeakPart`, `SampleItem`) to represent parsed DSC results, improving maintainability, validation, and type safety.
- **MVC Architecture**: Separated concerns with controller layer (`tools/`) managing business logic, UI layer handling presentation, and models representing data structures.
- **Modular Parsing**: Separated parsing, text generation, and templating into distinct utilities to minimize coupling and simplify testing.
- **Template-Based Generation**: Used Word templates in `data/` to ensure report layout remains consistent while content is automated through placeholder replacement.
- **Multi-Sample Support**: Designed architecture to handle multiple samples in a single report workflow, with independent parsing and unified report generation.
- **Theme System**: Implemented dark/light theme switching with QSS stylesheets for improved user experience.
- **Service Layer**: Created service classes (`DscParseService`, `ReportService`) to encapsulate core functionality and enable reuse.

#### Constraints / Challenges

- **Parsing Robustness**: Instrument output text can vary across methods/runs; required resilient parsing with encoding detection (UTF-16/UTF-8), regex pattern matching, and graceful error handling for missing fields.
- **Word Document Manipulation**: Placeholder replacement can be affected by run splitting and formatting; implemented careful replacement logic at both run and paragraph levels to preserve document formatting.
- **Multi-Sample State Management**: Managing state for multiple samples with independent parsing, editing, and unified report generation required careful synchronization between UI and data models.
- **PDF-TXT Data Merging**: Combining data from both PDF (range information) and TXT (detailed measurements) sources while handling cases where formats differ or data is incomplete.
- **Repository Hygiene**: Managing `.gitignore` to exclude sample data, temporary Word files (like `~$*`), virtual environments, and build artifacts.
- **Cross-Platform Compatibility**: Ensuring PyQt6 application works consistently across Windows, macOS, and Linux with proper path handling and resource management.

#### Skills Applied / Developed

- **Python Engineering**: Modular design, typed modeling with dataclasses, advanced parsing with regex, error handling, and service-oriented architecture
- **GUI Development**: PyQt6 application design, custom widgets, dialog management, event handling, and responsive layouts
- **Document Automation**: Word templating with python-docx, placeholder replacement, table manipulation, figure insertion, and formatted text generation
- **Software Architecture**: MVC pattern implementation, separation of concerns, controller design, and dependency management
- **User Experience**: Theme system implementation, intuitive UI design, real-time feedback, validation, and error messaging
- **QA Mindset**: Unit tests under `src/test`, reproducible sample inputs, logging, and error tracking in `problems.md`

### Outcome

- **Current Status:** Fully functional desktop application with PyQt6 GUI that parses DSC TXT/PDF outputs, manages multiple samples, and generates structured Word reports using templates. The application includes theme switching, comprehensive error handling, and a modular architecture for easy maintenance and extension.
- **Feedback / Validation:** Verified generation correctness by running against sample datasets and ensuring report fields populate as expected. The application handles edge cases gracefully, with issues captured and tracked in `problems.md`. Unit tests validate core parsing functionality.
- **Impact:** Significantly reduces reporting time (from hours to minutes), standardizes report formatting across all generated documents, decreases the risk of missing key thermal parameters due to manual transcription, and enables batch processing of multiple samples in a single workflow.

### Reflection

- **What I Learned:** 
  - Small variations in input formatting and document templating behaviors can cause disproportionate errors; robust parsing and validation are as important as core functionality.
  - GUI development requires careful state management, especially when handling multiple data sources and user interactions.
  - Modular architecture with clear separation of concerns significantly improves maintainability and testability.
  - User experience details (theme switching, real-time feedback, validation) greatly impact tool adoption and usability.

- **What I Would Improve Next:**
  
  - Add stronger validation and clearer user-facing error messages (e.g., missing fields, parsing failures) with actionable guidance.
  - Make parsing rules configurable per instrument method/output format through a configuration file or UI settings.
  - Improve PDF/image insertion sizing and layout control in generated reports with user-configurable options.
  - Add CI/CD pipeline to run tests automatically and enforce code quality gates.
  - Implement data export/import functionality for saving and loading project configurations.
  - Add batch processing mode with command-line interface for automation scenarios.
  - Enhance template editor with placeholder validation and preview functionality.
  
