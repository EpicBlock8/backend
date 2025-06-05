# Cryptographic File Sharing Server

A FastAPI server for secure file sharing with cryptographic operations.

This project is set up using Python, FastAPI, and UV for package management.

## Project Structure

```
.
├── .gitignore
├── app/
│   ├── __init__.py
│   ├── main.py         # Main FastAPI application
│   ├── core/           # Core logic (e.g., cryptography, business logic)
│   │   └── __init__.py
│   ├── routers/        # API routers/endpoints
│   │   └── __init__.py
│   └── models/         # Pydantic models (for request/response and data)
│       └── __init__.py
├── tests/              # Unit and integration tests
│   └── __init__.py
├── pyproject.toml      # Project metadata and dependencies (for UV)
└── README.md
```

## Setup and Installation

1.  **Clone the repository (if you haven't already):**
    ```bash
    git clone <your-repo-url>
    cd cryptographic-file-sharing-server
    ```

2.  **Create a virtual environment and install dependencies using UV:**

    *   First, ensure you have `uv` installed. If not, follow the instructions at [https://github.com/astral-sh/uv](https://github.com/astral-sh/uv).
    *   Create and activate a virtual environment:
        ```bash
        # Using Python's built-in venv
        python -m venv .venv
        source .venv/bin/activate  # On Windows: .venv\Scripts\activate
        ```
        OR
        ```bash
        # Uv can also create and manage the venv for you
        uv venv
        source .venv/bin/activate # On Windows: .venv\Scripts\activate
        ```

    *   Install dependencies:
        ```bash
        uv pip install -e .[dev]
        ```
        This installs the project in editable mode (`-e .`) along with the development dependencies (`[dev]`).

3.  **Configure Environment Variables (Optional):**
    If your application requires specific configurations (e.g., API keys for external services, database URLs), you can create a `.env` file in the project root (it's ignored by Git).
    Example:
    ```env
    # .env
    # DATABASE_URL="your_database_url_here"
    # API_KEY_SOME_SERVICE="your_api_key"
    ```
    You would then need to load these variables into your application (e.g., using `python-dotenv` or Pydantic's settings management).

## Running the Application (Development)

Once the dependencies are installed and the virtual environment is active, you can run the FastAPI application using Uvicorn:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

*   `app.main:app`: Points to the `app` instance in your `app/main.py` file.
*   `--reload`: Enables auto-reloading when code changes are detected (useful for development).
*   `--host 0.0.0.0`: Makes the server accessible on your network.
*   `--port 8000`: Specifies the port to run on.

You can then access the API at `http://localhost:8000` and the auto-generated documentation at `http://localhost:8000/docs` or `http://localhost:8000/redoc`.

## Running Tests

To run tests (once you've written some in the `tests/` directory):

```bash
pytest
```

## Linting and Formatting

This project is set up with `flake8` for linting and `black` for formatting, `isort` for import sorting and `mypy` for type checking.

*   **Check formatting (black):**
    ```bash
    black --check .
    ```
*   **Apply formatting (black):**
    ```bash
    black .
    ```
*   **Check import sorting (isort):**
    ```bash
    isort --check-only .
    ```
*   **Apply import sorting (isort):**
    ```bash
    isort .
    ```
*   **Run linter (flake8):**
    ```bash
    flake8 .
    ```
*   **Run type checker (mypy):**
    ```bash
    mypy .
    ```

## Next Steps & Security Considerations

*   **Authentication/Authorization:** If your application requires protecting endpoints, implement a suitable authentication and authorization mechanism.
*   **HTTPS:** Always use HTTPS in production (typically handled by a reverse proxy like Nginx or Traefik).
*   **Input Validation:** FastAPI and Pydantic provide excellent input validation. Use it thoroughly.
*   **Cryptography:** Implement your cryptographic file operations in `app/core/crypto.py` (you'll need to create this file and add the `cryptography` library to `pyproject.toml`).
*   **File Storage:** Decide on and implement secure file storage (e.g., local filesystem with proper permissions, cloud storage like S3).
*   **Error Handling:** Customize error handling to prevent leaking sensitive information.
*   **Security Headers:** Implement security headers (e.g., CSP, X-Content-Type-Options).
*   **Rate Limiting:** Protect against brute-force and DoS attacks.
*   **Logging & Monitoring:** Set up robust logging and monitoring.

Refer to the [FastAPI Security Documentation](https://fastapi.tiangolo.com/advanced/security/) and the [LoadForge article on FastAPI Security](https://loadforge.com/guides/securing-your-fastapi-web-service-best-practices-and-techniques) for more details.
