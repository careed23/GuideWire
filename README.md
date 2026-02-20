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

1. **Ingest** — Upload a `.pdf`, `.docx`, `.html`, or `.txt` support document.
2. **Analyze** — Claude AI (claude-opus-4-5) reads the document and extracts every troubleshooting branch into a structured JSON decision tree.
3. **Brand & Export** — Provide your company name and logo; GuidWire compiles a fully self-contained `GuidWire_<CompanyName>.exe` viewer that runs offline on any Windows machine — no Python required.

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

## Using the Builder — Step by Step

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

## Distributing the Viewer

Simply send the `GuidWire_<CompanyName>.exe` to your end-users. It runs completely offline — no Python, no API keys, no installation required. The decision tree and company branding are embedded inside the executable.

---

## Notes on API Key Usage

- Your Anthropic API key is used **only** during Step 2 (Analyze).
- It is sent directly from your machine to the Anthropic API over HTTPS.
- It is **never** written to disk, logged, or embedded in the packaged viewer.

---

## Project Structure

```
guidewire/
│
├── builder/
│   ├── main.py              # Builder entry point
│   ├── ingestor.py          # DocumentIngestor — extracts text from files
│   ├── analyzer.py          # DocumentAnalyzer — Claude AI integration
│   ├── tree_builder.py      # TreeBuilder — validates & saves tree JSON
│   ├── packager.py          # Packager — PyInstaller build pipeline
│   └── ui/
│       └── builder_ui.py    # CustomTkinter Builder GUI
│
├── viewer/
│   ├── main.py              # Viewer entry point
│   ├── tree_engine.py       # TreeEngine — loads & navigates the tree
│   ├── ui/
│   │   └── viewer_ui.py     # CustomTkinter Viewer GUI
│   └── assets/              # Injected at build time by Packager
│       ├── logo.png
│       ├── tree.json
│       └── config.json
│
├── requirements.txt
└── README.md
```

---

## License

MIT — see [LICENSE](LICENSE) for details.
