"""Development runner for Shoptegrity.

Starts the FastAPI server with auto-reload and static assets mounted.
Access in browser:
  - Hub Portal: http://127.0.0.1:8000
  - Food Chain Partner Site: http://127.0.0.1:8000/food
  - Brand Integrity Partner Site: http://127.0.0.1:8000/brands
  - Local Directory & PE Rollup Detector: http://127.0.0.1:8000/local
  - Swap Guides: http://127.0.0.1:8000/swaps
  - Dollar Flow Maps: http://127.0.0.1:8000/flows
  - Methodology: http://127.0.0.1:8000/methodology
  - Interactive API Docs: http://127.0.0.1:8000/docs
"""

import uvicorn

if __name__ == "__main__":
    print("Starting Shoptegrity Platform...")
    print("Visit http://127.0.0.1:8000 in your browser.")
    uvicorn.run("api.app.main:app", host="127.0.0.1", port=8000, reload=True)
