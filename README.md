# SampleTrack

Environmental sample analytical results tracking. Centralized intake, storage, search, and reporting for lab analytical data across all CCC projects.

## Local setup

1. Create and activate a virtual environment (Python 3.10+):

```bash
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
```

2. Install requirements:

```bash
pip install -r requirements.txt
```

3. Copy environment file:

```bash
cp .env.example .env
```

4. Run the app:

```bash
python app.py
```

## Deployment target

- VPS: 72.62.97.199
- Hostname: sampletrack.ccctrainingonline.com
- Port: 6000
- Managed with PM2 (or your preferred process manager)
