import pytest
from src.analyzers.java import JavaAnalyzer

@pytest.fixture
def java_analyzer():
    return JavaAnalyzer()

@pytest.mark.asyncio
async def test_no_build_files(java_analyzer, mock_ado_client):
    file_tree = [{'path': 'src/Main.java'}]
    result = await java_analyzer.analyze(mock_ado_client, "proj1", "repo1", file_tree)
    assert result == []

@pytest.mark.asyncio
async def test_maven_not_api(java_analyzer, mock_ado_client):
    file_tree = [{'path': 'pom.xml'}]
    mock_ado_client.get_file_content.return_value = """
    <project>
        <dependencies>
            <dependency>
                <groupId>org.apache.commons</groupId>
                <artifactId>commons-lang3</artifactId>
            </dependency>
        </dependencies>
    </project>
    """
    
    result = await java_analyzer.analyze(mock_ado_client, "proj", "repo", file_tree)
    assert len(result) == 1
    assert result[0]['is_api'] is False
    assert result[0]['build_tool'] == 'maven'

@pytest.mark.asyncio
async def test_gradle_detects_api(java_analyzer, mock_ado_client):
    file_tree = [{'path': 'build.gradle.kts'}]
    mock_ado_client.get_file_content.return_value = """
    dependencies {
        implementation("org.springframework.boot:spring-boot-starter-web")
    }
    """
    
    result = await java_analyzer.analyze(mock_ado_client, "proj", "repo", file_tree)
    assert len(result) == 1
    assert result[0]['is_api'] is True
    assert result[0]['build_tool'] == 'gradle'
