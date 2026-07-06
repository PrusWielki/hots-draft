# Detailed Setup & Development Guide

This guide provides detailed setup, running, and development instructions for the Heroes of the Storm Draft Helper.

## Prerequisites

Ensure you have the following installed on your system:
*   **Python**: Version 3.10 or higher.
*   **uv**: Fast Python package installer and resolver.
*   **Node.js & npm**: For the frontend web application.

---

## Getting Started

### 1. Python Backend & Server

The backend runs a FastAPI server. To set up and launch it:

1.  Navigate to the `backend` directory:
    ```bash
    cd backend
    ```
2.  Validate the referential integrity of your database:
    ```bash
    uv run app/validate_data.py
    ```
3.  Start the FastAPI application:
    ```bash
    # Note: Do NOT use --reload on Windows during draft/play, as Torch/EasyOCR touching files triggers uvicorn reload loops.
    uv run uvicorn app.main:app --host 0.0.0.0
    ```
    The server will be available at `http://localhost:8000` (and accessible externally via your PC's IP).

### 2. Svelte Frontend

The frontend is a Vite + Svelte 5 application styled with Tailwind CSS and DaisyUI.

1.  Navigate to the `frontend` directory:
    ```bash
    cd frontend
    ```
2.  Install dependencies:
    ```bash
    npm install
    ```
3.  Start the development server (with network hosting active):
    ```bash
    npm run dev -- --host
    ```
    Open your browser and navigate to the printed URL (usually `http://localhost:5173`).

---

## Database & Scraper Pipeline

To re-scrape or compile data from Icy Veins:

1.  **Fetch Guide Pages**: Downloads and caches guide HTML locally:
    ```bash
    uv run --project backend python scraper/fetch_icyveins.py
    ```
2.  **Parse HTML**: Extracts map performance, synergies, counters, and talent builds:
    ```bash
    uv run --project backend python scraper/parse.py
    ```
3.  **Build Database**: Merges parsed raw data, skeleton metadata, and overrides to generate `data/heroes.json`:
    ```bash
    uv run --project backend python scraper/build_db.py
    ```
4.  **Download & Crop Portraits**: Downloads the sprite sheet and extracts individual portrait images:
    ```bash
    uv run --project backend python scraper/download_portraits.py
    ```

---

## Code Quality & Testing

### Running Tests

To run the mock draft scoring unit tests:
```bash
uv run --project backend pytest
```

### Formatting & Linting

Before submitting code, run the following commands to ensure clean formatting:

*   **Python (Ruff, isort, black, docformatter)**:
    ```bash
    uvx ruff check --fix .
    uvx isort .
    uvx black .
    uvx docformatter --in-place backend/app/main.py backend/app/models.py backend/app/draft.py backend/app/scoring.py scraper/parse.py scraper/fetch_icyveins.py scraper/build_db.py scraper/download_portraits.py
    ```
*   **Svelte/JS/CSS (Prettier & Svelte-Check)**:
    ```bash
    cd frontend
    npx svelte-check
    npx prettier --write .
    ```

### Pre-commit Hooks

To enable automated pre-commit linting:
```bash
pre-commit install
```
This runs validation and formatting checks automatically before each commit.

---

## OpenCV Screen Detection

The helper includes an automated screen reader that captures the primary display and matches the active pick/ban slot against the loaded hero portraits in real-time.

*   **Activation**: Ensure the backend python virtual environment has `opencv-python` and `mss` installed (automatically handled via `uv`).
*   **How it Works**: The background thread dynamically captures screenshots, scales predefined coordinate slots to match your monitor's display resolution (proportional scaling based on a base target of 1920x1080), crops the active draft slot, and compares it to all templates using template matching (`cv2.matchTemplate`).
*   **Debouncing**: Matches require 3 consecutive identical readings to transition into stable states, preventing transient hover frames or visual noise from triggering false picks/bans.
*   **Manual Overrides Cooldown**: When a draft action is taken manually via the Svelte frontend, the vision detector enters a **6-second cooldown** to prevent the automated screen reader from immediately overwriting your manual overrides.

