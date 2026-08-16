TC Explorer 2.0 is a web-based platform for loading, validating, analysing and visualising tropical cyclone (TC) datasets from multiple climate models and tracking methods. The project is designed to make it easier to compare cyclone behaviour across datasets, including differences in frequency, intensity, lifetime, tracks and other derived characteristics.

The current implementation combines a Dash/Plotly interactive dashboard with a FastAPI backend and a reusable Python data-ingestion pipeline.

Features
- Load tropical cyclone data from CSV, TXT and NetCDF files.
- Support for regional climate model datasets including BARPA and CCAM.
- Support for CDD and TE cyclone tracking methods.
- Support for best-track style observational datasets.
- Automatically select an appropriate dataset loader from the filename or file type.
- Standardise data into a common TCRecord / TCPoint structure.
- Validate cyclone tracks using scientific and data-quality checks.
- Derive cyclone characteristics including:
    - genesis time and location
    - cyclone lifetime
    - maximum wind speed
    - minimum pressure
    - cyclone category
    - mean translation speed
    - landfall information where available
- Filter records by dataset/model, region, scenario, tracking method, year and minimum category.
- View cyclone frequency and intensity distributions.
- View strongest cyclone records and individual cyclone tracks on a map.
- Export filtered cyclone records as CSV.
- Access datasets, tracks and summary statistics through a FastAPI interface.
- Project Structure

ITProject2-main/
├── app/
│   ├── api/
│   │   └── routes.py              # FastAPI endpoints
│   ├── assets/
│   │   └── style.css              # Dashboard styling
│   ├── db/
│   │   └── schema.sql             # Database schema
│   ├── models/
│   │   └── tc_record.py           # Standard TCPoint and TCRecord models
│   ├── pipeline/
│   │   ├── loaders/
│   │   │   ├── base.py            # Base loader interface
│   │   │   ├── barpa_loader.py    # BARPA CSV loader
│   │   │   ├── ccam_loader.py     # CCAM CSV loader
│   │   │   ├── cdd_tracker_loader.py
│   │   │   ├── te_tracker_loader.py
│   │   │   ├── besttrack_loader.py
│   │   │   └── netcdf_loader.py
│   │   ├── ingest.py              # Loader selection and ingestion pipeline
│   │   ├── standardize.py         # Record standardisation
│   │   └── validators.py          # Data-quality validation
│   ├── services/
│   │   ├── cache_manager.py       # In-memory cache
│   │   ├── data_manager.py        # Dataset loading and access
│   │   ├── filter_service.py      # Cyclone filtering
│   │   ├── geo_service.py         # GeoJSON generation
│   │   └── stats_engine.py        # Summary statistics
│   ├── config.py                  # Application configuration
│   ├── dashboard.py               # Dash dashboard
│   └── main.py                    # FastAPI application
├── data/                           # Tropical cyclone datasets
├── TC_Explorer_Pipeline_Demo.ipynb
├── requirements.txt
└── README.md

Data Pipeline -> The core processing flow is:

Dataset file
    ↓
DataManager
    ↓
Ingestor
    ↓
Appropriate Loader
(BARPA / CCAM / CDD / TE / Best Track / NetCDF)
    ↓
TCPoint + TCRecord models
    ↓
Standardisation
    ↓
Validation
    ↓
Filtering / Statistics / GeoJSON
    ↓
FastAPI or Dash Dashboard

Ingestor can identify the correct loader using an explicitly supplied dataset type, the filename, or the file extension. Valid records are then retained by DataManager for use by the dashboard and API.

Requirements -> The project is written in Python. Python 3.10 or newer is recommended because the code uses modern Python type-hint syntax.

Major dependencies include:
- FastAPI
- Uvicorn
- Pydantic
- Pandas
- NumPy
- Xarray
- NetCDF4 / h5netcdf
- SciPy
- Plotly
- Dash
- GeoPandas
- Shapely
- PyProj
- SQLAlchemy
- Pytest

Important: app/config.py imports pydantic-settings. If it is not already installed in your environment, install it with pip install pydantic-settings. It should also be added to requirements.txt for a clean fresh installation.

Installation

1. Clone or download the repository

git clone <repository-url>
cd ITProject2-main

Alternatively, extract the project ZIP and open a terminal in the project root.

2. Create a virtual environment

Windows:

python -m venv .venv
.venv\Scripts\activate

macOS/Linux:

python3 -m venv .venv
source .venv/bin/activate

3. Install dependencies

pip install -r requirements.txt
pip install pydantic-settings

Running the Dashboard

From the project root, run:

python -m app.dashboard

The dashboard will start on:

http://localhost:8050

The dashboard loads supported files from the data/ directory. If a file cannot be parsed or does not pass validation, the error is reported in the terminal and the dashboard continues where possible.

Running the FastAPI Backend

From the project root, run:

uvicorn app.main:app --reload

By default, the API is available at:

http://127.0.0.1:8000

Interactive API documentation is available at:

http://127.0.0.1:8000/docs

A basic application health check is available at:
- GET /health

API Functions -> The API router provides operations for:

Method -> Endpoint -> Purpose

GET -> /health -> Application health check

GET -> /datasets -> List available dataset files

POST -> /tracks/{filename} -> Load and filter cyclone tracks from a dataset

GET -> /stats/{filename} -> Return summary statistics for a dataset

Track filters can include model, tracker, scenario, minimum year and maximum year.

Current development note: app/api/routes.py currently defines an /api router prefix and app/main.py also mounts the router using the configured /api prefix. As written, the router endpoints may therefore appear under /api/api/.... Removing one of the two prefixes will give the intended /api/... routes.

Supported Dataset Types
 - BARPA:
BARPA regional climate model files are handled by BARPALoader. The loader groups cyclone observations into individual tracks, converts supported wind-speed values into the standard units used by the application, and builds standard TCRecord objects.

 - CCAM:
CCAM data is handled by CCAMLoader. Tracks are grouped and split where large temporal gaps occur so that unrelated or discontinuous observations are not treated as one continuous cyclone.

- CDD and TE Trackers:
CDDTrackerLoader and TETrackerLoader use the underlying BARPA or CCAM loader and assign the appropriate tracking method to each resulting record.

- Best-Track Data
BestTrackLoader supports CSV-style observational cyclone datasets with common fields such as storm ID, date/time, latitude, longitude, wind speed and pressure.

- NetCDF
NetCDFLoader uses Xarray to locate common track, time, latitude and longitude variables and convert NetCDF cyclone data into the same standard record format used throughout the project.

Cyclone Data Model

All supported source datasets are converted into two main Pydantic models.

TCPoint -> Represents a single observation along a cyclone track and can contain:
- timestamp
- latitude and longitude
- wind speed
- pressure
- cyclone category
- land status

TCRecord -> Represents a complete cyclone track and contains both its sequence of points and derived summary information such as:
- dataset and track identifiers
- regional model
- tracker
- scenario
- ensemble / driving GCM information where available
- genesis location and time
- landfall information
- lifetime
- maximum wind speed
- minimum pressure
- maximum category
- mean translation speed
- year
- source file metadata
- Validation

The validation pipeline checks records before they are returned to the dashboard. Current checks include:
- minimum number of points per track
- chronological track ordering
- duplicate or non-increasing timestamps
- excessive time gaps between track points
- implausibly long cyclone lifetimes
- unreasonable wind speeds
- pressure outside the accepted range
- invalid category values
- unreasonable translation speeds
- missing genesis information

Invalid records are retained in the validation report for traceability but are excluded from the records returned to the dashboard by DataManager.

Dashboard -> The Dash application provides an interactive interface for exploring the loaded cyclone datasets.
Current controls include:
- dataset selection
- region selection
- scenario selection
- tracking-method selection
- year range
- minimum cyclone category
- apply/reset filters

Current visualisations include:
- cyclone summary statistics
- cyclones per year
- intensity/category distribution
- strongest cyclone records
- selected-cyclone track map
- CSV export of filtered records

Configuration
Application settings are defined in app/config.py and can be overridden through environment variables or a .env file.

Default settings include:

APP_NAME=TC-Explorer API
APP_VERSION=0.1.0
ENVIRONMENT=development
API_PREFIX=/api
HOST=127.0.0.1
PORT=8000
DATABASE_URL=sqlite:///./tc_records.db
CACHE_ENABLED=true
MAX_RECORDS_PER_RESPONSE=10000

For production deployment, update configuration as required and restrict the CORS policy in app/main.py; the current configuration permits all origins for development.

Adding a New Dataset ->
To add another dataset type:
1. Create a loader in app/pipeline/loaders/ that inherits from BaseTCLoader.
2. Implement the load() method.
3. Convert each source cyclone into TCPoint and TCRecord objects.
4. Register the loader in Ingestor.loader_map in app/pipeline/ingest.py.
5. Add filename/file-type detection if automatic loader selection is required.
6. Validate the output against the existing standardisation and validation pipeline.

This design allows additional datasets to be added without changing the dashboard's internal cyclone representation.

Testing ->
Pytest and HTTPX are included in the project dependencies for automated testing.
Run tests from the project root with:

pytest

At present, the supplied repository does not contain a dedicated automated test suite, so this command will only execute tests once test files are added.

Development Status

TC Explorer 2.0 is currently under active development. The existing repository contains the core ingestion pipeline, standard cyclone data model, validation logic, API structure and interactive dashboard. Additional dataset compatibility, analysis functions, testing, security hardening and deployment configuration can be added as the project progresses.

Team : IT Project II – Group 2 | Team Susanoo 
