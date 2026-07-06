# Heroes of the Storm Draft Helper

A desktop draft helper for Heroes of the Storm that reads screen data (via OpenCV) or accepts manual inputs, processes drafts, and recommends draft choices based on data from Icy Veins.

## Quick Start

### 1. Start Python Backend
```bash
cd backend
# Note: Do NOT use --reload on Windows during draft/play, as Torch/EasyOCR touching files triggers uvicorn reload loops.
uv run uvicorn app.main:app --host 0.0.0.0
```

### 2. Start Svelte Frontend
```bash
cd frontend
npm install
npm run dev -- --host
```

## Documentation

For detailed installation, testing, and web scraper pipeline instructions, see [docs/setup.md](docs/setup.md).
