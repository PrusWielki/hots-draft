# Heroes of the Storm Draft Helper

A desktop draft helper for Heroes of the Storm that reads screen data (via OpenCV) or accepts manual inputs, processes drafts, and recommends draft choices based on data from Icy Veins.

## Quick Start

### 1. Start Python Backend
```bash
cd backend
uv run uvicorn app.main:app --reload
```

### 2. Start Svelte Frontend
```bash
cd frontend
npm install
npm run dev
```

## Documentation

For detailed installation, testing, and web scraper pipeline instructions, see [docs/setup.md](docs/setup.md).
