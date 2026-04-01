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

    async def analyze(self, ado_client: Any, project_id: str, repo_id: str, file_tree: List[Dict]) -> List[Dict]:
        csproj_files = [f for f in file_tree if f['path'].endswith('.csproj')]
        if not csproj_files:
            return []

        # Find central packages and build props
        dir_packages_props = [f for f in file_tree if f['path'].endswith('Directory.Packages.props')]
        dir_build_props = [f for f in file_tree if f['path'].endswith('Directory.Build.props')]

        global_versions = {}
        global_deps = []

        # Parse Directory.Packages.props (Central Package Management)
        for dp_file in dir_packages_props:
            content = await ado_client.get_file_content(project_id, repo_id, dp_file['path'])
            if content:
                try:
                    root = ET.fromstring(content)
                    for elem in root.iter():
                        tag = self._strip_ns(elem.tag)
                        if tag == 'PackageVersion':
                            pkg_name = elem.attrib.get('Include', '')
                            pkg_ver = elem.attrib.get('Version', '')
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
                        if tag == 'PackageReference':
                            pkg_name = elem.attrib.get('Include', '')
                            pkg_ver = elem.attrib.get('Version', '')
                            if not pkg_ver and pkg_name in global_versions:
                                pkg_ver = global_versions[pkg_name]
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

            try:
                root = ET.fromstring(content)
                
                # 1. Check SDK
                sdk = root.attrib.get('Sdk', '')
                if 'Microsoft.NET.Sdk.Web' in sdk:
                    is_api = True
                    
                for elem in root.iter():
                    tag = self._strip_ns(elem.tag)
                    
                    if tag == 'TargetFramework' and elem.text:
                        framework_version = elem.text
                        
                    elif tag == 'PackageReference':
                        pkg_name = elem.attrib.get('Include', '')
                        pkg_ver = elem.attrib.get('Version', '')
                        
                        # Apply CPM if version is empty
                        if not pkg_ver and pkg_name in global_versions:
                            pkg_ver = global_versions[pkg_name]
                            
                        if pkg_name:
                            # Heuristics for ASP.NET / API
                            lower_name = pkg_name.lower()
                            if 'microsoft.aspnetcore' in lower_name or 'swashbuckle.aspnetcore' in lower_name:
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
