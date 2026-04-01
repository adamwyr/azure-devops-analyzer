import pytest
from src.analyzers.python import PythonAnalyzer

@pytest.fixture
def python_analyzer():
    return PythonAnalyzer()

@pytest.mark.asyncio
async def test_no_config_files(python_analyzer, mock_ado_client):
    file_tree = [{'path': 'main.py'}]
    result = await python_analyzer.analyze(mock_ado_client, "proj1", "repo1", file_tree)
    assert result == []

@pytest.mark.asyncio
async def test_requirements_not_api(python_analyzer, mock_ado_client):
    file_tree = [{'path': 'requirements.txt'}]
    mock_ado_client.get_file_content.return_value = "requests==2.31.0\nnumpy==1.25.0"
    
    result = await python_analyzer.analyze(mock_ado_client, "proj", "repo", file_tree)
    assert len(result) == 1
    assert result[0]['is_api'] is False
    assert result[0]['module_path'] == '/'

@pytest.mark.asyncio
async def test_detects_api(python_analyzer, mock_ado_client):
    file_tree = [{'path': 'src/pyproject.toml'}]
    mock_ado_client.get_file_content.return_value = """
    [tool.poetry.dependencies]
    python = "^3.10"
    fastapi = "^0.103.0"
    uvicorn = "^0.23.0"
    """
    
    result = await python_analyzer.analyze(mock_ado_client, "proj", "repo", file_tree)
    assert len(result) == 1
    assert result[0]['is_api'] is True
    assert result[0]['module_path'] == 'src'

@pytest.mark.asyncio
async def test_deduplicates_modules(python_analyzer, mock_ado_client):
    # Same directory has multiple config files
    file_tree = [
        {'path': 'src/pyproject.toml'},
        {'path': 'src/requirements.txt'}
    ]
    
    async def mock_get_content(project, repo, path):
        if path == 'src/requirements.txt':
            return "flask"
        return "requests"
        
    mock_ado_client.get_file_content.side_effect = mock_get_content
    
    result = await python_analyzer.analyze(mock_ado_client, "proj", "repo", file_tree)
    assert len(result) == 1
    # One file had flask, so it should be true overall
    assert result[0]['is_api'] is True
    assert result[0]['module_path'] == 'src'
