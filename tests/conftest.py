import pytest
from unittest.mock import AsyncMock
import sys
import os

# Ensure the parent directory is in the path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture
def mock_ado_client():
    from src.ado_client import AdoClient
    client = AsyncMock(spec=AdoClient)
    # Default behaviors
    client.get_projects.return_value = []
    client.get_repositories.return_value = []
    client.get_file_tree.return_value = []
    client.get_file_content.return_value = ""
    return client
