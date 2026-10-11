# DataPulse Autonomous

**An intelligent data engineering platform for detecting, diagnosing, and responding to data pipeline failures.**

DataPulse Autonomous is a portfolio project exploring how data platforms can become more reliable through automated ingestion, data quality validation, schema evolution monitoring, statistical drift detection, and controlled recovery mechanisms.

The project uses historical New York City Taxi and Limousine Commission (TLC) trip records to simulate a data pipeline receiving monthly datasets over time.

## Project Objectives

- Build a reproducible data ingestion and batch processing workflow.
- Track incoming datasets through a batch manifest.
- Profile data quality, including missing values, duplicates, and invalid records.
- Detect schema changes and statistical data drift.
- Identify pipeline failures such as missing, corrupted, or unexpectedly empty batches.
- Explore intelligent failure diagnosis and risk prediction.
- Implement controlled recovery actions with validation and auditability.

## Project Approach

Instead of treating all historical datasets as available at once, DataPulse will replay them chronologically to simulate data arriving over time.

The initial development period begins with the available 2015 TLC Green Taxi records. Later datasets will be used to evaluate whether the platform can identify previously unseen schema changes, quality issues, and distribution shifts.

Historical data is used as a simulation of incoming batches; it is not a live TLC API integration.

## Planned Architecture

```text
Historical TLC Parquet Files
            |
            v
   Batch Inventory and Manifest
            |
            v
      Chronological Replay
            |
            v
   Ingestion and Raw Storage
            |
            v
   Data Quality and Profiling
            |
            v
   Schema and Drift Detection
            |
            v
   Diagnosis and Risk Analysis
            |
            v
   Controlled Recovery and Verification
```

Distributed processing and workflow orchestration will be introduced as the project evolves.

## Technology Stack

### Initial implementation

- Python
- Pandas
- PyArrow
- Apache Parquet
- CSV-based batch manifests
- Git and GitHub
- Pytest

### Planned extensions

- Apache Spark / PySpark for distributed processing
- Apache Airflow for orchestration
- Scikit-learn for pipeline risk prediction
- Ollama for local language-model-assisted diagnosis
- SQL and a database-backed metadata registry
- Docker and automated testing for reproducible deployment

Planned technologies are not yet claimed as implemented features.

## Repository Structure

```text
DataPulse/
├── TLC_Data/                   # Local source datasets; excluded from Git
├── src/
│   └── datapulse/
│       ├── __init__.py
│       └── inventory.py        # Parquet inventory and manifest generation
├── notebooks/                  # Exploratory analysis
├── tests/                      # Automated tests
├── reports/                    # Generated reports; excluded from Git
├── requirements.txt
├── .gitignore
└── README.md
```

The source dataset and generated reports are kept outside version control to avoid committing large files or machine-specific artifacts.

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/datapulse-autonomous.git
cd datapulse-autonomous
```

### 2. Create a virtual environment

Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### 4. Add the TLC data

Place the downloaded Parquet datasets in the local `TLC_Data/` directory.

The source files are not included in the repository and must be obtained separately from the NYC TLC trip record data source.

### 5. Generate the batch manifest

```powershell
python -m src.datapulse.inventory
```

The initial inventory module inspects Parquet metadata and records file information, row counts, schemas, schema fingerprints, and inspection status in `reports/batch_manifest.csv`.

The manifest is a local generated artifact and is excluded from Git by default.

## Development Roadmap

- [x] Establish the project structure and local development workflow
- [ ] Build the initial Parquet inventory and batch manifest
- [ ] Validate file coverage and inventory results
- [ ] Implement chronological batch replay
- [ ] Add reusable data profiling and quality rules
- [ ] Implement schema evolution detection
- [ ] Implement statistical drift detection
- [ ] Add distributed processing and workflow orchestration
- [ ] Explore pipeline failure risk prediction
- [ ] Add diagnosis, controlled remediation, and verification
- [ ] Expand automated tests and deployment support

Roadmap items will be marked complete as they are implemented and tested.

## Engineering Principles

- Preserve raw source data.
- Separate detection from remediation.
- Make batch processing observable and reproducible.
- Design ingestion and recovery operations for idempotency.
- Distinguish legitimate schema evolution from harmful changes.
- Evaluate drift chronologically to reduce data leakage.
- Validate automated actions before accepting their results.

## Data Source

The project uses NYC TLC trip record data. Refer to the official source for dataset documentation, formats, and available monthly records:

[https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page)

## Project Status

**Early development — inventory and manifest stage.**

DataPulse Autonomous is being developed incrementally, with each milestone adding tested functionality and documented engineering decisions.

## License

A license has not yet been selected. Add a license before distributing the project or inviting reuse under specific terms.
