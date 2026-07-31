from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_docker_deployment_files_exist_and_expose_expected_ports() -> None:
    backend_dockerfile = (ROOT / "backend" / "Dockerfile").read_text(encoding="utf-8")
    frontend_dockerfile = (ROOT / "frontend" / "Dockerfile").read_text(encoding="utf-8")
    compose_file = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert "python:3.12-slim" in backend_dockerfile
    assert "uvicorn" in backend_dockerfile
    assert "EXPOSE 8000" in backend_dockerfile
    assert "node:22-alpine" in frontend_dockerfile
    assert "nginx:alpine" in frontend_dockerfile
    assert "EXPOSE 80" in frontend_dockerfile
    assert "8000:8000" in compose_file
    assert "5173:80" in compose_file
    assert "rag_backend_data:/app/data" in compose_file
