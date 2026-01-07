# DSC Report Generation Tool - Technical Documentation

## Overview

The DSC Report Generation Tool is a Python-based desktop application designed to automate the creation of standardized Differential Scanning Calorimetry (DSC) reports. The tool parses raw instrument output files (TXT and PDF), extracts thermal analysis data, and generates formatted Word documents using template-based document generation.

## System Requirements

- **Operating System**: Windows, macOS, or Linux
- **Python**: Python 3.8 or higher
- **Memory**: Minimum 4GB RAM (8GB recommended)
- **Disk Space**: ~500MB for application and dependencies
- **Display**: Minimum 1280x720 resolution

## Installation & Deployment

### Prerequisites

1. **Python Installation**
   - Download and install Python 3.8+ from [python.org](https://www.python.org/downloads/)
   - Ensure Python is added to system PATH
   - Verify installation: `python --version`

2. **Git** (Optional, for cloning repository)
   - Download from [git-scm.com](https://git-scm.com/downloads)

### Installation Methods

#### Method 1: Standard Installation

1. **Clone or Download the Repository**
   ```shell
   git clone https://github.com/MegumiKat/SSD-Process-Safety-Report-Generation.git
   cd SSD-Process-Safety-Report-Generation
   ```
   Or download and extract the ZIP archive.

2. **Create Virtual Environment** (Recommended)
   ```shell
   # Windows
   python -m venv venv
   venv\Scripts\activate

   # macOS/Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install Dependencies**
   ```shell
   pip install -r requirements.txt
   ```

4. **Verify Installation**
   ```shell
   python main.py
   ```

#### Method 2: Development Installation

For developers who want to modify the code:

```shell
# Clone repository
git clone <repository-url>
cd DSC_Report_Tool

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Install in editable mode (if setup.py exists)
pip install -e .
```

### Configuration

1. **Template Setup**
   - Place your Word template files in the `data/` directory
   - Default template path: `data/DSC Report-Empty-2512.docx`
   - Modify `src/config/config.py` to change default template:
     ```python
     DEFAULT_TEMPLATE_PATH = DATA_DIR / "your_template.docx"
     ```

2. **Logo Configuration** (Optional)
   - Place logo image in `src/assets/logo.png`
   - Supported formats: PNG, JPG, ICO
   - Logo will appear in application header

3. **Stylesheet Customization** (Optional)
   - Edit `src/assets/app.qss` for dark theme customization
   - Edit `src/assets/app_light.qss` for light theme customization
   - Qt stylesheet syntax applies
   - Changes take effect after application restart (or use theme toggle)

### Deployment Options

#### Option 1: Standalone Executable (PyInstaller)

Create a standalone executable for distribution:

```shell
# Install PyInstaller
pip install pyinstaller

# Create executable
# Windows
pyinstaller --name="DSC_Report_Tool" ^
            --windowed ^
            --icon=src/assets/app.ico ^
            --add-data "src/assets;assets" ^
            --add-data "data;data" ^
            main.py

# macOS/Linux
pyinstaller --name="DSC_Report_Tool" \
            --windowed \
            --icon=src/assets/app.ico \
            --add-data "src/assets:assets" \
            --add-data "data:data" \
            main.py

# Executable will be in dist/DSC_Report_Tool/
# Note: Use semicolon (;) for Windows, colon (:) for macOS/Linux in --add-data
```

#### Option 2: Portable Installation

1. Copy entire project directory to target machine
2. Ensure Python 3.8+ is installed
3. Run `pip install -r requirements.txt` in project directory
4. Execute `python main.py`

#### Option 3: Docker Deployment (Advanced)

Create a `Dockerfile`:

```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
```

Build and run:
```shell
docker build -t dsc-report-tool .
docker run -it --rm -e DISPLAY=$DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix dsc-report-tool
```

## Technology Stack

- **Language**: Python 3.8+
- **GUI Framework**: PyQt6 (6.10.1) - Cross-platform desktop application framework
- **Document Processing**:
  - `python-docx` (1.2.0) - Word document manipulation and template processing
  - `PyMuPDF` (1.26.7) - PDF parsing, text extraction, and image conversion
- **Data Models**: Python `dataclasses` for structured data representation with type hints
- **Text Processing**: Regular expressions for pattern matching and extraction
- **XML Processing**: `lxml` (6.0.2) - For document structure manipulation

## Architecture

### Project Structure

```shell
DSC_Report_Tool/
├── main.py                      # Application entry point
├── requirements.txt             # Python dependencies
├── README.md                    # Project overview (this file)
├── README_en.md                 # Detailed technical documentation (English)
├── README_zh.md                 # Detailed technical documentation (Chinese)
├── Placeholders.md              # Template placeholder reference guide
├── log.md                       # Development notes and logs
├── problems.md                  # Known issues and TODOs
│
├── src/                         # Source code
│   ├── config/                  # Configuration management
│   │   └── config.py            # Paths, defaults, constants
│   ├── models/                  # Data models (typed structures)
│   │   └── models.py            # DscBasicInfo, DscSegment, DscPeakPart, SampleItem, etc.
│   ├── utils/                   # Core utilities
│   │   ├── parser_dsc.py        # TXT/PDF parsing logic
│   │   ├── templating.py        # Word template processing
│   │   └── dsc_text.py          # Discussion text generation
│   ├── tools/                   # Business logic controllers (MVC pattern)
│   │   ├── dsc_services.py      # Core services (DscParseService, ReportService)
│   │   ├── workflow_controller.py # Workflow step management
│   │   ├── sample_controller.py  # Sample management logic
│   │   ├── segments_controller.py # Segment editing logic
│   │   ├── report_controller.py  # Report generation coordination
│   │   ├── form_controller.py    # Form data management
│   │   ├── theme_controller.py   # Theme switching (dark/light)
│   │   └── make_logo_transparent.py # Logo processing utility
│   ├── ui/                      # UI layer (PyQt6)
│   │   ├── ui_main.py           # Main window
│   │   ├── dialog_add_sample.py # Sample addition dialog
│   │   └── widgets/             # Custom UI widgets
│   │       └── toggle_switch.py # Theme toggle switch widget
│   ├── assets/                  # UI resources
│   │   ├── app.qss              # Dark theme stylesheet
│   │   ├── app_light.qss        # Light theme stylesheet
│   │   ├── app.ico              # Application icon (Windows)
│   │   ├── app.png              # Application icon
│   │   ├── logo.png             # Application logo
│   │   └── logo.jpg             # Application logo (alternative)
│   └── test/                    # Unit tests
│       └── test_segments.py     # Segment parsing tests
│
└── data/                        # Report templates
    ├── DSC Report-Empty-2511.docx
    └── DSC Report-Empty-2512.docx
```

## Core Components

### 1. Data Models (`src/models/models.py`)

The application uses typed dataclasses to represent parsed DSC data:

- **`DscBasicInfo`**: Extracted metadata from instrument output
  - `sample_name`: Sample identifier from TXT file
  - `sample_mass_mg`: Sample mass in milligrams
  - `operator`: Operator name
  - `instrument`: Instrument identifier
  - `atmosphere`: Atmosphere type (e.g., N₂, Air)
  - `crucible`: Crucible type (e.g., "Concavus Al, pierced lid")
  - `temp_calib`: Temperature calibration date (format: YYYY/MM/DD)
  - `end_date`: Test end date (format: YYYY/MM/DD)

- **`DscPeakPart`**: Individual thermal event data
  - `value_dsc`: Value (DSC) magnitude in mW/mg
  - `value_temp_c`: Value (DSC) corresponding temperature in °C
  - `onset_c`: Onset temperature in °C
  - `peak_c`: Peak temperature in °C
  - `area_raw`: Raw area (enthalpy change) in J/g
  - `area_report`: Processed area (sign-inverted for reporting)
  - `comment`: Endothermic/Exothermic classification

- **`DscSegment`**: Temperature program segment
  - `index`: Segment number (1, 2, 3, ...)
  - `total`: Total number of segments
  - `raw_desc`: Raw description string (e.g., "-20°C/10.0(K/min)/150°C")
  - `desc_display`: Formatted description (e.g., "-20°C ➜ 150°C@10K/min")
  - `parts`: List of `DscPeakPart` objects for this segment

- **`AutoFields`**: UI-editable auto-identified fields
  - Stores user-modified values to prevent overwriting on sample switch
  - Fields: sample_name, sample_mass, operator, instrument, atmosphere, crucible, temp_calib, end_date

- **`SampleManualFields`**: Per-sample manual input fields
  - `sample_id`: Sample identifier
  - `nature`: Sample nature/type (e.g., powder, liquid)
  - `assign_to`: Assignment information

- **`SampleItem`**: Complete sample representation
  - `id`: Unique sample ID
  - `name`: Display name for UI
  - `txt_path`: Path to TXT file
  - `pdf_path`: Optional path to PDF file
  - `basic_info`: Parsed `DscBasicInfo` object
  - `segments`: List of `DscSegment` objects
  - `auto_fields`: `AutoFields` instance
  - `manual_fields`: `SampleManualFields` instance

### 2. Parsing Engine (`src/utils/parser_dsc.py`)

#### TXT File Parsing

The parser extracts structured data from NETZSCH DSC instrument output files:

- **Encoding Detection**: Handles UTF-16 and UTF-8 encodings with fallback
- **Basic Information Extraction**: Regex-based pattern matching for:
  - Sample identity and mass
  - Instrument metadata
  - Date/time fields with format normalization

- **Segment Parsing**: Multi-stage extraction:
  1. Segment header detection: `Segments: X/Y : -20°C/10.0(K/min)/150°C`
  2. Complex Peak block extraction (Area, Peak, Onset temperatures)
  3. Value (DSC) line extraction
  4. Part pairing and data association

#### PDF Range Extraction

- Uses PyMuPDF to extract text from PDF pages
- Identifies "Range" sections containing temperature program information
- Merges PDF-derived segments with TXT-parsed data
- Handles cases where PDF contains additional segments not present in TXT

#### Segment Normalization

- Converts raw format (`-20°C/10.0(K/min)/150°C`) to display format (`-20°C ➜ 150°C@10K/min`)
- Handles heating/cooling cycle classification
- Manages segment indexing and total count synchronization

### 3. Template System (`src/utils/templating.py`)

#### Placeholder Replacement

- **Global Replacement**: Processes placeholders in:
  - Document body paragraphs
  - Tables (cells and nested paragraphs)
  - Headers and footers across all sections

- **Run-Level Preservation**: Maintains formatting by replacing at the `Run` level when possible, falling back to paragraph-level replacement for split placeholders

#### Dynamic Table Generation

- **Result Table**: Generates multi-row tables from segment data
  - Template row cloning for multiple segments
  - Cell merging for identical sample/method values
  - Vertical and horizontal alignment control

- **Sample Information Table**: Handles multiple samples
  - Template row duplication per sample
  - Field mapping from `SampleItem.manual_fields`

#### Discussion Text Insertion

- Multi-paragraph insertion replacing `{{Discussion}}` placeholder
- Font inheritance from template paragraph
- Automatic bold formatting for cycle headers ("heating cycle:", "cooling cycle:")

#### Figure Insertion

- PDF to image conversion (250 DPI) using PyMuPDF
- PNG/JPG direct insertion support
- Automatic figure numbering
- Page width calculation for responsive sizing
- Caption generation with sample name

### 4. Text Generation (`src/utils/dsc_text.py`)

Generates natural language descriptions of DSC results:

- **Cycle Classification**: Determines heating vs. cooling cycles from temperature ranges
- **Event Detection**: Identifies thermal events with complete data (onset, peak, area)
- **Summary Generation**: Creates structured English text:
  - Opening statement with cycle count
  - Ordinal numbering for multiple cycles
  - Event descriptions with temperature and enthalpy data
  - Endothermic/Exothermic classification

### 5. Service Layer (`src/tools/dsc_services.py`)

#### DscParseService

Encapsulates parsing logic for TXT and PDF files:

- **`parse_one(txt_path, pdf_path=None)`**: Parses a single sample
  - Returns `ParseResult` containing `basic` (DscBasicInfo) and `segments` (List[DscSegment])
  - Handles encoding detection and error propagation
  - Merges PDF range data with TXT parsed data

#### ReportService

Handles report generation and discussion text:

- **`build_discussion(samples)`**: Generates discussion text for multiple samples
  - Combines text from all samples with proper formatting
  - Uses `generate_dsc_summary()` for each sample
  - Returns concatenated discussion text

- **`generate_report(...)`**: Orchestrates report generation
  - Takes template path, output path, mapping dictionary
  - Handles segments, discussion text, PDF figures, and sample data
  - Delegates to `fill_template_with_mapping()` for actual document generation

### 6. Controller Layer (`src/tools/`)

The application follows an MVC (Model-View-Controller) pattern with dedicated controllers:

- **`WorkflowController`**: Manages multi-step workflow (Step 0: Setup → Step 1: Edit → Step 2: Confirm)
  - Step navigation and validation
  - Step completion tracking
  - Button state management

- **`SampleController`**: Handles sample list management
  - Sample addition/removal
  - Sample selection and navigation
  - Auto-save on sample switch

- **`SegmentsController`**: Manages segment editing
  - Segment display and modification
  - Part editing within segments
  - Data validation

- **`ReportController`**: Coordinates report generation
  - Data confirmation dialog
  - Mapping dictionary construction
  - Report generation orchestration

- **`FormController`**: Manages form data
  - Request information fields
  - Sample information fields
  - Field validation and synchronization

- **`ThemeController`**: Handles theme switching
  - Dark/light theme application
  - QSS stylesheet loading and caching
  - Theme persistence

### 7. UI Architecture (`src/ui/ui_main.py`)

#### Multi-Sample Management

- **Sample List**: Scrollable card-based interface
  - File status indicators (TXT/PDF presence)
  - Sample selection and navigation
  - Add/remove operations
  - Current sample highlighting

- **State Management**: 
  - Current sample tracking
  - UI-to-model synchronization via controllers
  - Auto-save on sample switch
  - Workflow step tracking

#### Layout Structure

- **Header Section**: 
  - Logo display
  - Application title
  - Template selection (with "Change" button)
  - Output file selection (with "Choose" button)
  - Theme toggle switch (dark/light)

- **Left Panel**: 
  - Sample list (scrollable cards)
  - Action buttons (Confirm Data, Generate Report)
  - Manual input forms:
    - Request Information section
    - Sample Information section (per-sample)

- **Right Panel**: 
  - Tabbed interface:
    - **Auto Tab**: Auto-identified fields (editable)
      - Sample name, mass, operator, instrument, etc.
      - Segments display with expandable parts
    - **Log Tab**: Operation log with HTML formatting
      - Parsing results
      - Confirmation summary
      - Error messages

#### Custom Widgets

- **`ToggleSwitch`** (`src/ui/widgets/toggle_switch.py`): Custom theme toggle widget
  - Animated switch with smooth transitions
  - PyQt6 property-based animation
  - Signal-based communication

#### Data Flow

1. **File Selection**: User adds samples via `AddSampleDialog`
2. **Parsing**: `DscParseService` automatically parses TXT/PDF on sample addition
3. **UI Population**: `SampleController` populates auto-fields from parsed data
4. **Editing**: User modifies values via controllers (changes saved to model)
5. **Confirmation**: `ReportController` validates and confirms data
6. **Generation**: `ReportService` generates discussion and fills template

## Key Implementation Details

### Architecture Patterns

- **MVC Pattern**: Clear separation between Models (data structures), Views (UI components), and Controllers (business logic)
- **Service Layer**: Core functionality encapsulated in services (`DscParseService`, `ReportService`) for reusability
- **Controller Pattern**: Dedicated controllers for different aspects (workflow, samples, segments, reports, forms, themes)
- **Dependency Injection**: Controllers receive view references for loose coupling

### Parsing Robustness

- **Error Handling**: Graceful degradation when parsing fails, with error messages logged to UI
- **Encoding Detection**: Multiple encoding attempts (UTF-16 → UTF-8) with fallback handling
- **Partial Data Support**: Handles missing fields without crashing; uses empty strings or None as defaults
- **PDF-TXT Merging**: Combines data from both sources when available; PDF provides range information, TXT provides detailed measurements
- **Regex Pattern Matching**: Robust pattern matching for various instrument output formats

### Template Processing

- **Format Preservation**: Maintains Word document formatting during placeholder replacement
- **Run-Level Replacement**: Replaces placeholders at the `Run` level when possible to preserve formatting
- **Paragraph-Level Fallback**: Falls back to paragraph-level replacement for split placeholders
- **Table Manipulation**: Deep cloning of table rows for dynamic content generation
- **Cell Merging**: Intelligent merging of identical adjacent cells in result tables
- **Figure Insertion**: PDF to image conversion with automatic sizing and caption generation

### Multi-Sample Workflow

- **Sample Isolation**: Each sample maintains independent data structures (`SampleItem`)
- **State Persistence**: Auto-fields preserve user modifications across sample switches
- **Batch Processing**: Generates single unified report with multiple samples
- **Latest Date Selection**: Automatically selects most recent end date from all samples for report header
- **Unified Discussion**: Combines discussion text from all samples with proper formatting
- **Sequential Figure Numbering**: Figures numbered sequentially across all samples (Figure 1, Figure 2, ...)

### Theme System

- **Dynamic Theme Switching**: Real-time theme switching without application restart
- **QSS Stylesheets**: Separate stylesheets for dark (`app.qss`) and light (`app_light.qss`) themes
- **Caching**: Light theme stylesheet cached after first load for performance
- **Custom Widgets**: Theme-aware custom widgets (e.g., `ToggleSwitch`)

## Configuration

### Path Management (`src/config/config.py`)

- **Base Directory Resolution**: 
  - Uses `Path.parents` for relative path calculation
  - Supports both source code execution and PyInstaller packaged execution
  - Automatically detects `sys._MEIPASS` for packaged applications
  
- **Directory Structure**:
  - `BASE_DIR`: Project root directory
  - `SRC_DIR`: Source code directory (`src/`)
  - `DATA_DIR`: Template directory (`data/`)
  - `ASSETS_DIR`: UI resources directory (`src/assets/`)

- **Template Path**: 
  - Default: `data/DSC Report-Empty-2512.docx`
  - Configurable via `DEFAULT_TEMPLATE_PATH` constant
  - Can be changed at runtime via UI

- **Asset Paths**: 
  - Logo: `src/assets/logo.png` (fallback to `logo.jpg`)
  - Dark theme: `src/assets/app.qss`
  - Light theme: `src/assets/app_light.qss`
  - Icons: `src/assets/app.ico` (Windows) or `app.png` (fallback)

## Dependencies

Key dependencies (see `requirements.txt` for complete list):

- `PyQt6==6.10.1` - GUI framework and widgets
- `PyQt6-Qt6==6.10.1` - Qt6 core libraries
- `PyQt6_sip==13.10.3` - Python bindings for Qt
- `python-docx==1.2.0` - Word document manipulation
- `PyMuPDF==1.26.7` - PDF parsing and image extraction
- `lxml==6.0.2` - XML/HTML processing for document manipulation
- `typing_extensions==4.15.0` - Extended type hints support
- Standard library: `dataclasses`, `re`, `pathlib`, `typing`

## Usage Guide

### Quick Start

1. **Launch the Application**
   ```shell
   python main.py
   ```
   The application window will open maximized.

2. **Select Template** (Optional)
   - Default template (`DSC Report-Empty-2512.docx`) is automatically loaded
   - Click "Change" button in header to select different template
   - Template must be a `.docx` file with placeholder fields (see `Placeholders.md` for reference)

3. **Choose Output Location**
   - Click "Choose" button next to Output field
   - Select or create destination `.docx` file
   - File will be created/overwritten during generation
   - Green text indicates valid output path

4. **Theme Selection** (Optional)
   - Use the toggle switch in the header to switch between dark and light themes
   - Theme preference is applied immediately

### Detailed Workflow

#### Step 1: Add Samples

1. Click the **"+ Add Sample"** button in the left panel
2. In the dialog:
   - Enter a sample name (e.g., "CF130G")
   - Select TXT file (required): Instrument output text file
   - Select PDF file (optional): DSC curve plot PDF
3. Click "OK" to add the sample
4. The application automatically parses the TXT file and displays results

**Sample File Requirements:**
- TXT file: NETZSCH DSC instrument output format
- PDF file: Should contain "Range" information at the bottom
- File encoding: UTF-16 or UTF-8

#### Step 2: Review Auto-Identified Data

1. Select a sample from the list (click on sample card)
2. View auto-extracted fields in the right panel ("Auto" tab):
   - Sample Name
   - Sample Mass
   - Operator
   - Instrument
   - Atmosphere
   - Crucible
   - Temp.Calib. (Temperature calibration date)
   - End Date

3. Review Segments section:
   - Each segment shows temperature program (e.g., "-20°C ➜ 150°C@10K/min")
   - Part data includes: Value, Onset, Peak, Area, Comment
   - Edit values directly if needed

#### Step 3: Edit Data (Optional)

1. **Modify Auto-Identified Fields**
   - Click on any field in the "Auto" tab
   - Edit values directly
   - Changes are saved automatically when switching samples

2. **Edit Segment Data**
   - Modify temperature values, areas, or comments
   - Changes apply to the current sample

3. **Switch Between Samples**
   - Click sample cards to switch
   - Use navigation arrows (◀ ▶) in top-right corner
   - Current sample: "Sample X / N"

#### Step 4: Fill Manual Input Fields

**Request Information** (Left panel, top section):
- Test Code: e.g., "LSMP-21 F01v04"
- Request Id: Request identifier
- Customer Information: Customer details
- Request Name: Request name
- Submission Date: Format YYYY/MM/DD
- Request Number: Request number
- Project Account: Project account code
- Deadline: Format YYYY/MM/DD
- Receive Date: Format YYYY/MM/DD
- Test Date: Format YYYY/MM/DD
- Report Date: Format YYYY/MM/DD
- Request Description: Multi-line text field

**Sample Information** (Left panel, bottom section):
For each sample, fill:
- Sample Id: Sample identifier
- Nature: Sample nature/type
- Assign To: Assignment information

#### Step 5: Confirm Data

1. Click **"Confirm Data"** button
2. Review compiled information in the "Log" tab:
   - Automatically identified fields (all samples)
   - Manual input fields
   - Final End Date (latest from all samples)
3. Verify all data is correct
4. Switch back to "Auto" tab if corrections needed

#### Step 6: Generate Report

1. Ensure output path is selected (green text indicates valid path)
2. Click **"Generate Report"** button
3. Wait for generation to complete
4. Success message will appear
5. Open the generated Word document to review

### Multi-Sample Workflow

The application supports processing multiple samples in a single report:

1. **Add Multiple Samples**
   - Click "+ Add Sample" multiple times
   - Each sample is parsed independently

2. **Navigate Between Samples**
   - Use sample cards or navigation arrows
   - Edit data for each sample separately

3. **Generate Unified Report**
   - All samples appear in the same report
   - Result table includes all samples
   - Discussion text combines all samples
   - Figures are numbered sequentially (Figure 1, Figure 2, ...)

### Template Placeholders

The Word template should contain the following placeholders. For a detailed reference, see `Placeholders.md`.

**Basic Fields:**
- `{{LSMP_code}}` - Test code (manual input)
- `{{Request_id}}` - Request identifier (manual input)
- `{{Customer_information}}` - Customer info (manual input)
- `{{Request_Name}}` - Request name (manual input, default: "DSC test for {{Sample_name}}")
- `{{Sample_name}}` - Sample name (auto from TXT: `Sample identity` or `Sample name`)
- `{{Sample_mass}}` - Sample mass (auto from TXT)
- `{{Operator}}` - Operator name (auto from TXT)
- `{{Instrument}}` - Instrument name (auto from TXT)
- `{{Atmosphere}}` - Atmosphere type (auto from TXT)
- `{{Crucible}}` - Crucible type (auto from TXT: `Crucible:` line)
- `{{Temp.Calib}}` - Temperature calibration date (auto from TXT: `Temp.Calib.:` line)
- `{{End_Date}}` - End date (auto from TXT: `nd Date/Time:` line, or latest from all samples)

**Date Fields (Manual Input):**
- `{{Submission_Date}}` - Submission date (format: YYYY/MM/DD)
- `{{Test_Date}}` - Test date (format: YYYY/MM/DD)
- `{{Receive_Date}}` - Receive date (format: YYYY/MM/DD)
- `{{Report_Date}}` - Report date (format: YYYY/MM/DD, default: current date)
- `{{Deadline}}` - Deadline (format: YYYY/MM/DD)

**Request Fields (Manual Input):**
- `{{Request_Number}}` - Request number
- `{{Project_Account}}` - Project account code
- `{{Request_desc}}` - Request description (multi-line)

**Sample Fields (in Sample Information Table):**
- `{{Sample_id}}` - Sample identifier (manual input per sample)
- `{{Sample_name}}` - Sample name (in sample table)
- `{{Nature}}` - Sample nature/type (manual input, e.g., powder, liquid)
- `{{Assign_to}}` - Assignment (manual input, default: Operator from TXT)

**Result Table Placeholders (Auto-generated from Segments):**
- `{{SEG_SAMPLE}}` - Sample name in result table
- `{{SEG_METHOD}}` - Test method/segment description (e.g., "1st heating / cooling / 2nd heating")
- `{{SEG_VALUE}}` - Value (DSC) temperature (°C)
- `{{SEG_ONSET}}` - Onset temperature (°C)
- `{{SEG_PEAK}}` - Peak temperature (°C)
- `{{SEG_AREA}}` - Area (enthalpy change, J/g)
- `{{SEG_COMMENT}}` - Comment (Endothermic/Exothermic)

**Discussion:**
- `{{Discussion}}` - Multi-paragraph discussion text (auto-generated, replaced with formatted paragraphs)

**Note**: Placeholders are case-sensitive and must match exactly. Some placeholders contain special characters (e.g., `{{Temp.Calib}}` with a dot). See `Placeholders.md` for complete reference and usage notes.

### Keyboard Shortcuts

- **Tab**: Navigate between input fields
- **Enter**: Confirm dialog actions
- **Esc**: Cancel dialogs
- **Arrow Keys**: Navigate between samples (when sample list is focused)

### Tips & Best Practices

1. **File Organization**
   - Keep TXT and PDF files together
   - Use descriptive sample names
   - Organize files by project/date

2. **Template Preparation**
   - Ensure all placeholders are correctly spelled
   - Test template with sample data first
   - Keep backup of original template

3. **Data Validation**
   - Always review auto-extracted data
   - Check segment data completeness
   - Verify dates are in correct format (YYYY/MM/DD)

4. **Error Handling**
   - Check Log tab for parsing errors
   - Verify file paths are accessible
   - Ensure template file exists and is valid

5. **Performance**
   - Large PDF files may take longer to process
   - Multiple samples increase generation time
   - Close unnecessary applications for better performance

## Technical Highlights

- **Type Safety**: Extensive use of Python type hints, dataclasses, and `typing_extensions` for robust type checking
- **MVC Architecture**: Clear separation between Models, Views, and Controllers for maintainability
- **Service Layer**: Core functionality encapsulated in reusable services
- **Separation of Concerns**: Modular design with distinct layers (config, models, utils, tools, ui)
- **Extensibility**: Easy addition of new parsers, templates, or UI components
- **Error Recovery**: Robust error handling with graceful degradation and user-friendly error messages
- **Performance**: Efficient parsing with minimal memory overhead, stylesheet caching
- **User Experience**: Real-time feedback, validation, logging, theme switching, and intuitive workflow
- **Cross-Platform**: Works on Windows, macOS, and Linux with proper path handling

## Troubleshooting

### Common Issues

#### 1. Application Won't Start

**Problem**: Error when running `python main.py`

**Solutions**:
- Verify Python version: `python --version` (should be 3.8+)
- Check dependencies: `pip install -r requirements.txt`
- Verify PyQt6 installation: `pip show PyQt6`
- Check for missing files (template, assets)

#### 2. Template Not Found

**Problem**: Warning message about missing template

**Solutions**:
- Ensure template file exists in `data/` directory
- Check file name matches `DEFAULT_TEMPLATE_PATH` in `config.py`
- Verify file is not corrupted (try opening in Word)
- Use "Change Template" button to select correct file

#### 3. Parsing Fails

**Problem**: Sample data not extracted correctly

**Solutions**:
- Verify TXT file is from NETZSCH DSC instrument
- Check file encoding (should be UTF-16 or UTF-8)
- Review Log tab for specific error messages
- Ensure file is not corrupted or incomplete
- Try opening TXT file in text editor to verify format

#### 4. PDF Not Processing

**Problem**: PDF file not recognized or Range not extracted

**Solutions**:
- Verify PDF is not password-protected
- Check PDF contains "Range" text at bottom
- Ensure PyMuPDF is installed: `pip install PyMuPDF`
- Try converting PDF to image format (PNG/JPG) as alternative

#### 5. Report Generation Fails

**Problem**: Error during report generation

**Solutions**:
- Ensure output path is writable
- Check disk space availability
- Verify template file is not open in Word
- Review error message in Log tab
- Ensure all required placeholders exist in template

#### 6. UI Display Issues

**Problem**: Interface looks incorrect or elements missing

**Solutions**:
- Check `src/assets/app.qss` and `src/assets/app_light.qss` exist
- Verify screen resolution (minimum 1280x720)
- Try switching themes using the toggle switch
- Try restarting application
- Check PyQt6 version compatibility: `pip show PyQt6`
- Verify all asset files are present (icons, logos, stylesheets)

#### 7. Sample Data Not Saving

**Problem**: Changes lost when switching samples

**Solutions**:
- Ensure you click on sample card to switch (not just navigation arrows)
- Changes are auto-saved when switching samples via `SampleController`
- Use "Confirm Data" before generating report to validate all data
- Check Log tab for any error messages or parsing issues
- Verify that auto-fields are properly populated from parsed data

#### 8. Theme Not Switching

**Problem**: Theme toggle doesn't work or stylesheet not loading

**Solutions**:
- Verify `src/assets/app_light.qss` exists
- Check file permissions for stylesheet files
- Try restarting the application
- Check Log tab for stylesheet loading errors
- Verify `ThemeController` is properly initialized in `main.py`

### Debug Mode

Enable verbose logging for troubleshooting:

```python
# In main.py, add before app.exec():
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Getting Help

1. **Check Log Tab**: Review operation logs for error messages and parsing results
2. **Verify File Formats**: Ensure files match expected formats (NETZSCH DSC TXT, PDF with Range info)
3. **Review Placeholders**: Check `Placeholders.md` for template placeholder reference
4. **Review Configuration**: Check `src/config/config.py` for path and default settings
5. **Check Problems Log**: Review `problems.md` for known issues and workarounds
6. **Development Logs**: Check `log.md` for development notes and changes

## Future Enhancements

- **Configurable Parsing Rules**: Per-instrument type configuration files for parsing rules
- **Enhanced Validation**: More comprehensive validation with actionable error messages
- **Improved PDF/Image Layout**: User-configurable sizing and positioning options
- **CI/CD Integration**: Automated testing pipeline with code quality gates
- **Export Formats**: Additional export formats (PDF, HTML, Excel)
- **Command-Line Interface**: Batch processing mode for automation scenarios
- **Template Editor**: Built-in template editor with placeholder validation and preview
- **Data Persistence**: Project save/load functionality for configurations and sample data
- **Multi-Language Support**: Internationalization (i18n) for UI and reports
- **Advanced Theme Customization**: User-defined color schemes and styles
- **Undo/Redo**: History management for data editing operations
- **Keyboard Shortcuts**: Expanded keyboard navigation and shortcuts
- **Plugin System**: Extensible architecture for custom parsers and exporters
