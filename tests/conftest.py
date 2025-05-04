import pytest
import pytest_asyncio
from httpx import AsyncClient
from typing import AsyncGenerator

# Import the FastAPI app instance
# Adjust the import path based on your project structure
from src.app.main import app 

@pytest_asyncio.fixture(scope="function") # Use function scope for isolation
async def test_client() -> AsyncGenerator[AsyncClient, None]:
    """Fixture to create an httpx AsyncClient for testing the FastAPI app."""
    # Base URL for the test client
    base_url = "http://testserver" 
    async with AsyncClient(app=app, base_url=base_url) as client:
        yield client
    # Teardown logic can go here if needed after yield

# Add other fixtures here later (e.g., mocked Tufin client, database connections) 