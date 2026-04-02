import re
import xml.etree.ElementTree as ET
import logging
from typing import List, Dict, Any
from src.analyzers.base import BaseAnalyzer

logger = logging.getLogger(__name__)

class DotNetAnalyzer(BaseAnalyzer):
    """Analyzer for extracting .NET modules and their dependencies."""
    
    @property
    def name(self) -> str:
        return ".NET"

    def _strip_ns(self, tag: str) -> str:
        """Removes namespace from XML tag to simplify parsing."""
        if '}' in tag:
            return tag.split('}', 1)[1]
        return tag

    def _resolve_variables(self, value: str, properties: Dict[str, str]) -> str:
        """Resolves MSBuild variables like $(VarName) using the properties dict."""
        if not value or '$(' not in value:
            return value
        return re.sub(r'\$\(([^)]+)\)', lambda m: properties.get(m.group(1), m.group(0)), value)

    def _parse_name_and_version(self, elem: ET.Element, global_versions: Dict[str, str] = None, properties: Dict[str, str] = None) -> tuple:
        """Helper to extract package name and version from an element."""
        if global_versions is None:
            global_versions = {}
        if properties is None:
            properties = {}
            
        pkg_name = elem.attrib.get('Include', '')
        if not pkg_name:
            pkg_name = elem.attrib.get('Update', '')
            
        pkg_ver = elem.attrib.get('Version', '')

        # Check if version is specified as a child element
        if not pkg_ver:
            for child in elem:
                if self._strip_ns(child.tag) == 'Version' and child.text:
                    pkg_ver = child.text
                    break

        # Check if Name and Version are both in the Include/Update attribute
        # Example: Include="Newtonsoft.Json, Version=12.0.0, Culture=neutral"
        if pkg_name and ',' in pkg_name:
            parts = [p.strip() for p in pkg_name.split(',')]
            pkg_name = parts[0]
            if not pkg_ver:
                for part in parts[1:]:
                    if part.lower().startswith("version="):
                        pkg_ver = part[8:]
                        break

        # Check Central Package Management
        if not pkg_ver and pkg_name in global_versions:
            pkg_ver = global_versions[pkg_name]

        pkg_name = self._resolve_variables(pkg_name, properties)
        pkg_ver = self._resolve_variables(pkg_ver, properties)

        return pkg_name, pkg_ver

    async def analyze(self, ado_client: Any, project_id: str, repo_id: str, file_tree: List[Dict]) -> List[Dict]:
        csproj_files = [f for f in file_tree if f['path'].endswith('.csproj')]
        if not csproj_files:
            return []

        # Find central packages and build props
        dir_packages_props = [f for f in file_tree if f['path'].endswith('Directory.Packages.props')]
        dir_build_props = [f for f in file_tree if f['path'].endswith('Directory.Build.props')]

        global_versions = {}
        global_deps = []
        global_properties = {}

        # Parse Directory.Packages.props (Central Package Management)
        for dp_file in dir_packages_props:
            content = await ado_client.get_file_content(project_id, repo_id, dp_file['path'])
            if content:
                try:
                    root = ET.fromstring(content)
                    for elem in root.iter():
                        tag = self._strip_ns(elem.tag)
                        if tag == 'PropertyGroup':
                            for child in elem:
                                child_tag = self._strip_ns(child.tag)
                                if child.text:
                                    global_properties[child_tag] = child.text.strip()
                        elif tag == 'PackageVersion':
                            pkg_name, pkg_ver = self._parse_name_and_version(elem, properties=global_properties)
                            if pkg_name:
                                global_versions[pkg_name] = pkg_ver
                except ET.ParseError:
                    logger.debug(f"Failed to parse XML in {dp_file['path']}")

        # Parse Directory.Build.props
        for db_file in dir_build_props:
            content = await ado_client.get_file_content(project_id, repo_id, db_file['path'])
            if content:
                try:
                    root = ET.fromstring(content)
                    for elem in root.iter():
                        tag = self._strip_ns(elem.tag)
                        if tag == 'PropertyGroup':
                            for child in elem:
                                child_tag = self._strip_ns(child.tag)
                                if child.text:
                                    global_properties[child_tag] = child.text.strip()
                        elif tag == 'PackageReference':
                            pkg_name, pkg_ver = self._parse_name_and_version(elem, global_versions, global_properties)
                            if pkg_name:
                                global_deps.append({'name': pkg_name, 'version': pkg_ver})
                except ET.ParseError:
                    logger.debug(f"Failed to parse XML in {db_file['path']}")

        modules = []
        for csproj in csproj_files:
            content = await ado_client.get_file_content(project_id, repo_id, csproj['path'])
            if not content:
                continue

            # Need to copy to prevent mutating the global list across modules
            dependencies = list(global_deps)
            framework_version = None
            is_api = False

            project_properties = global_properties.copy()

            try:
                root = ET.fromstring(content)
                
                # First pass: collect properties
                for elem in root.iter():
                    tag = self._strip_ns(elem.tag)
                    if tag == 'PropertyGroup':
                        for child in elem:
                            child_tag = self._strip_ns(child.tag)
                            if child.text:
                                project_properties[child_tag] = child.text.strip()
                
                # 1. Check SDK
                sdk = root.attrib.get('Sdk', '')
                if 'Microsoft.NET.Sdk.Web' in sdk:
                    is_api = True
                    
                for elem in root.iter():
                    tag = self._strip_ns(elem.tag)
                    
                    if tag == 'TargetFramework' and elem.text:
                        framework_version = self._resolve_variables(elem.text, project_properties)
                        
                    elif tag in ('PackageReference', 'Reference'):
                        pkg_name, pkg_ver = self._parse_name_and_version(elem, global_versions, project_properties)
                            
                        if pkg_name:
                            # Heuristics for ASP.NET / API
                            lower_name = pkg_name.lower()
                            if 'microsoft.aspnetcore' in lower_name or 'swashbuckle.aspnetcore' in lower_name:
                                is_api = True
                            if 'system.web.mvc' in lower_name or 'system.web.http' in lower_name:
                                is_api = True
                                
                            dependencies.append({'name': pkg_name, 'version': pkg_ver})
                            
                    elif tag == 'FrameworkReference':
                        fw_name = elem.attrib.get('Include', '')
                        if fw_name == 'Microsoft.AspNetCore.App':
                            is_api = True

            except ET.ParseError:
                logger.warning(f"Failed to parse XML for {csproj['path']}")
                
            modules.append({
                'module_path': csproj['path'],
                'framework_version': framework_version,
                'dependencies': dependencies,
                'is_api': is_api
            })

        return modules
