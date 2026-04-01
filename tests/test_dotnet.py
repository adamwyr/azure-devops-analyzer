import pytest
from src.analyzers.dotnet import DotNetAnalyzer

@pytest.fixture
def dotnet_analyzer():
    return DotNetAnalyzer()

@pytest.mark.asyncio
async def test_analyzer_name(dotnet_analyzer):
    assert dotnet_analyzer.name == ".NET"

@pytest.mark.asyncio
async def test_no_csproj_returns_empty(dotnet_analyzer, mock_ado_client):
    file_tree = [{'path': 'README.md'}]
    result = await dotnet_analyzer.analyze(mock_ado_client, "proj1", "repo1", file_tree)
    assert result == []

@pytest.mark.asyncio
async def test_basic_csproj_not_api(dotnet_analyzer, mock_ado_client):
    file_tree = [{'path': 'src/MyLibrary/MyLibrary.csproj'}]
    mock_ado_client.get_file_content.return_value = """
    <Project Sdk="Microsoft.NET.Sdk">
        <PropertyGroup>
            <TargetFramework>net8.0</TargetFramework>
        </PropertyGroup>
        <ItemGroup>
            <PackageReference Include="Newtonsoft.Json" Version="13.0.1" />
        </ItemGroup>
    </Project>
    """
    
    result = await dotnet_analyzer.analyze(mock_ado_client, "proj1", "repo1", file_tree)
    
    assert len(result) == 1
    module = result[0]
    assert module['module_path'] == 'src/MyLibrary/MyLibrary.csproj'
    assert module['framework_version'] == 'net8.0'
    assert module['is_api'] is False
    assert len(module['dependencies']) == 1
    assert module['dependencies'][0] == {'name': 'Newtonsoft.Json', 'version': '13.0.1'}

@pytest.mark.asyncio
async def test_cpm_directory_packages_props(dotnet_analyzer, mock_ado_client):
    file_tree = [
        {'path': 'Directory.Packages.props'},
        {'path': 'src/Api/Api.csproj'}
    ]
    
    # We need a dynamic mock side effect based on file path
    async def mock_get_content(project, repo, path):
        if path == 'Directory.Packages.props':
            return """
            <Project>
                <ItemGroup>
                    <PackageVersion Include="Microsoft.AspNetCore.Mvc" Version="8.0.0" />
                </ItemGroup>
            </Project>
            """
        elif path == 'src/Api/Api.csproj':
            return """
            <Project Sdk="Microsoft.NET.Sdk.Web">
                <ItemGroup>
                    <PackageReference Include="Microsoft.AspNetCore.Mvc" />
                </ItemGroup>
            </Project>
            """
        return ""
        
    mock_ado_client.get_file_content.side_effect = mock_get_content
    
    result = await dotnet_analyzer.analyze(mock_ado_client, "proj1", "repo1", file_tree)
    
    assert len(result) == 1
    module = result[0]
    assert module['is_api'] is True # triggered by Sdk.Web and Mvc
    assert len(module['dependencies']) == 1
    assert module['dependencies'][0] == {'name': 'Microsoft.AspNetCore.Mvc', 'version': '8.0.0'}

@pytest.mark.asyncio
async def test_directory_build_props(dotnet_analyzer, mock_ado_client):
    file_tree = [
        {'path': 'Directory.Build.props'},
        {'path': 'src/Lib/Lib.csproj'}
    ]
    
    async def mock_get_content(project, repo, path):
        if path == 'Directory.Build.props':
            return """
            <Project>
                <ItemGroup>
                    <PackageReference Include="StyleCop.Analyzers" Version="1.1.118" />
                </ItemGroup>
            </Project>
            """
        elif path == 'src/Lib/Lib.csproj':
            return "<Project Sdk=\"Microsoft.NET.Sdk\"></Project>"
        return ""
        
    mock_ado_client.get_file_content.side_effect = mock_get_content
    result = await dotnet_analyzer.analyze(mock_ado_client, "proj1", "repo1", file_tree)
    
    assert len(result) == 1
    module = result[0]
    assert module['is_api'] is False
    assert len(module['dependencies']) == 1
    assert module['dependencies'][0] == {'name': 'StyleCop.Analyzers', 'version': '1.1.118'}
