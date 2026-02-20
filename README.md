<h1 align="center">GuideWire</h1>

<p align="center">
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.11%2B-blue?logo=python&logoColor=white" alt="Python 3.11+"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green" alt="MIT License"></a>
  <a href="https://www.anthropic.com/"><img src="https://img.shields.io/badge/AI-Claude%20(Anthropic)-blueviolet?logo=anthropic&logoColor=white" alt="Claude AI"></a>
  <a href="https://pyinstaller.org/"><img src="https://img.shields.io/badge/packaged%20with-PyInstaller-orange?logo=pyinstaller&logoColor=white" alt="PyInstaller"></a>
  <img src="https://img.shields.io/badge/platform-Windows-0078D6?logo=windows&logoColor=white" alt="Windows">
</p>

<p align="center"><em>Follow the wire. Resolve the issue.</em></p>

<p align="center">
  An AI-powered troubleshooting tool that converts support documentation into branded, offline decision-tree viewers for IT teams — no Python required on the end-user's machine.
</p>

---

## What GuidWire Does

GuidWire has two modes:

**Single Document mode** — upload one `.pdf`, `.docx`, `.html`, or `.txt` file, let
Claude generate a decision tree, preview and edit it, then export a branded
standalone `.exe` viewer.

**Bulk Library mode** — point GuidWire at a folder tree containing 10 GB+ of DOCX
documentation, let it ingest and index everything (hash-based, incremental),
generate a full library of troubleshooting trees grouped by category, and export
an offline Library Viewer `.exe` for service-desk analysts.

---

## Prerequisites

- Python 3.11 or later
- An [Anthropic API key](https://console.anthropic.com/) (required only during the **Analyze** step)
- Windows, macOS, or Linux for running the Builder
- Windows target for the packaged Viewer `.exe`

---

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/careed23/GuideWire.git
cd GuideWire

# 2. Create and activate a virtual environment (recommended)
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
```

---

## How to Run the Builder

```bash
python builder/main.py
```

---

## Single Document Mode — Step by Step

### Step 1 — Upload Document
Click **Browse File** (or drag-and-drop) and select the support document you want to convert. Accepted formats: `.pdf`, `.docx`, `.html`, `.txt`.

### Step 2 — Analyze
Enter your Anthropic API key (it is never stored to disk). Click **Analyze Document**. GuidWire extracts the document text and sends it to Claude, which returns a fully structured decision tree. A success message will confirm the number of nodes extracted.

### Step 3 — Preview Tree
Review the extracted nodes. Each node shows its **ID**, **type** (`question`, `step`, or `resolution`), and a text preview. Click **Edit** on any node to fine-tune the wording before packaging.

### Step 4 — Brand & Export
- Enter the **Company Name** (used in the exe filename and window title).
- Upload the **Company Logo** (PNG, JPG, or similar; automatically resized to 300×300).
- Choose an **Output Directory**.
- Click **Build .exe**.

GuidWire will run PyInstaller in the background and move the finished `GuidWire_<CompanyName>.exe` to your chosen output directory.

---

## Bulk Library Mode — Step by Step

Click **Bulk Library** in the sidebar to switch modes.

### Step 1 — Select Knowledge Base Folder
- Click **Browse Folder…** and choose the root folder of your documentation tree
  (e.g. `D:\ForgedFiber37_KB\`).  GuidWire immediately scans and shows the DOCX
  file count and total size.
- Click **Output Base Folder…** and choose (or create) the content directory
  (e.g. `D:\ForgedFiber37_Content\`).

### Step 2 — Ingest & Index
- Click **Start Ingest**.
- GuidWire copies every DOCX file into
  `<OutputBase>/docs/<same folder tree as source>/` and extracts its text.
- A SHA-256 hash manifest (`manifest.json`) is written inside the output base.
  Re-running skips unchanged files automatically.

### Step 3 — Generate Tree Library
- Enter your Anthropic API key.
- Click **Generate Trees**.
- Documents are grouped by top-level sub-folder (= category).  Claude generates
  one decision-tree JSON per document.
- Outputs:
  - `<OutputBase>/trees/*.json` — one tree per document
  - `<OutputBase>/library.json` — catalog with title, description, category,
    tree file path, and source doc link for every tree

### Step 4 — Export Offline Package
- Enter the **Company Name** (e.g. `ForgedFiber37`).
- Choose an **Output Directory** for the executable.
- Click **Build Library Viewer .exe**.
- GuidWire builds `GuidWire_<CompanyName>_LibraryViewer.exe`.

Distribute to analysts by copying both the EXE and the content folder
(e.g. `ForgedFiber37_Content/`) to the same directory.  The viewer reads
directly from the folder — documents are never embedded in the EXE.

---

## Offline Library Viewer

The Library Viewer provides:

| Feature | Detail |
|---|---|
| **Category browser** | Sidebar listing all top-level-folder categories |
| **Fast metadata search** | Search by title, description, or symptom tags |
| **Tree navigator** | Step-by-step decision tree for any selected entry |
| **Open Source Doc** | Launches the original DOCX in Word (or default app) |

---

## Distributing the Viewer

**Single-doc viewer:** send only `GuidWire_<CompanyName>.exe` — tree and branding are embedded.

**Library viewer:** send both:
```
GuidWire_<CompanyName>_LibraryViewer.exe
<CompanyName>_Content/          ← the content folder from Step 2–3
  ├── library.json
  ├── manifest.json
  ├── trees/
  │     └── *.json
  └── docs/
        └── <mirrored source folder tree>
              └── *.docx
```

---

## Notes on API Key Usage

- Your Anthropic API key is used **only** during the Analyze step (Single mode) or
  the Generate Trees step (Bulk mode).
- It is sent directly from your machine to the Anthropic API over HTTPS.
- It is **never** written to disk, logged, or embedded in any packaged viewer.

---

## Project Structure

```
guidewire/
│
├── builder/
│   ├── main.py              # Builder entry point
│   ├── ingestor.py          # DocumentIngestor — extracts text from a single file
│   ├── bulk_ingestor.py     # BulkIngestor — folder scan, copy, hash manifest
│   ├── analyzer.py          # DocumentAnalyzer — Claude AI integration
│   ├── tree_builder.py      # TreeBuilder — validates & saves tree JSON
│   ├── library_builder.py   # LibraryBuilder — generates library.json from manifest
│   ├── packager.py          # Packager — single-doc & library-viewer PyInstaller builds
│   └── ui/
│       └── builder_ui.py    # CustomTkinter Builder GUI (Single + Bulk modes)
│
├── viewer/
│   ├── main.py              # Single-doc viewer entry point
│   ├── library_main.py      # Library viewer entry point
│   ├── tree_engine.py       # TreeEngine — loads & navigates a decision tree
│   ├── library_engine.py    # LibraryEngine — loads library.json, search, open doc
│   ├── ui/
│   │   ├── viewer_ui.py     # Single-doc viewer GUI
│   │   └── library_viewer_ui.py  # Library viewer GUI
│   └── assets/              # Injected at build time by Packager
│       ├── logo.png
│       ├── tree.json        # (single-doc builds)
│       ├── config.json      # (single-doc builds)
│       └── viewer_config.json  # (library builds — content folder name)
│
├── requirements.txt
└── README.md
```

---

## License

MIT — see [LICENSE](LICENSE) for details.
