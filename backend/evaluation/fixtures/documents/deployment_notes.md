# Local Deployment Notes

The project includes Docker Compose source configuration for a local demo. The backend container exposes port 8000 and stores runtime data under /app/data. The frontend container builds the Vite app and serves static files through nginx on port 5173.

Docker Compose syntax is checked with docker compose config --quiet. Runtime build verification can be blocked by Docker Hub network or DNS issues. A trusted registry mirror may be needed on some networks.

The local development workflow still supports running the backend through the Python 3.12 virtual environment and running the frontend with npm.cmd.
