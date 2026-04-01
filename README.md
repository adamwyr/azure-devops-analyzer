# Azure DevOps API Crawler

A high-performance, asynchronous Python tool designed to scan an entire Azure DevOps organization's projects and repositories. It identifies source code modules written in .NET, Python, and Java, extracts their dependencies, and checks whether they serve as an API.

## Features

- **Concurrent Execution**: Built on top of `asyncio` and `aiohttp` to ensure lightning-fast crawling across thousands of repositories.
- **Independent Analyzers**: Language-specific logic is cleanly separated into pluggable analyzer modules (`dotnet.py`, `python.py`, `java.py`).
- **.NET Central Package Management**: Can resolve dependencies correctly handling `Directory.Build.props` and `Directory.Packages.props`.
- **JSON Export**: Aggregates all repository data into a neat hierarchical JSON structure.

## Prerequisites

- Python 3.8+
- An Azure DevOps Personal Access Token (PAT) with at least **Code (Read)** and **Project and Team (Read)** permissions.

## Setup

1. Clone or navigate to the repository folder:
```bash
cd azuredevops_crawler
```

2. Create and activate a Virtual Environment (recommended):
```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# Linux / Mac
python3 -m venv venv
source venv/bin/activate
```

3. Install the dependencies:
```bash
pip install -r requirements.txt
```

## Running the Crawler

You need to provide your Azure DevOps Organization URL and your PAT. You can pass these either through environment variables (recommended) or as command-line arguments.

### Option 1: Using Environment Variables

```powershell
# Windows PowerShell
$env:ADO_ORG_URL="https://dev.azure.com/your-org-name"
$env:ADO_PAT="your-pat-token"

python main.py
```

```bash
# Linux / Mac
export ADO_ORG_URL="https://dev.azure.com/your-org-name"
export ADO_PAT="your-pat-token"

python main.py
```

### Option 2: Using CLI Arguments

```bash
python main.py --org https://dev.azure.com/your-org-name --pat your-pat-token
```

### Additional Parameters
- `--output` (Optional): Specify a custom output file path for the results. By default, the script outputs to `report_results.json`.

Example:
```bash
python main.py --output "c:\temp\my_ado_report.json"
```

## How to Extend

If you need to analyze a new language (e.g., Node.js or Go), simply:
1. Create a new analyzer file inside the `analyzers/` directory (e.g., `nodejs.py`).
2. Make your new class inherit from `BaseAnalyzer` (found in `analyzers/base.py`).
3. Implement the `analyze()` method which receives the repository's file tree and the `AdoClient` to pull individual file text.
4. Import and add your new analyzer to the `analyzers` list inside `main.py`.
