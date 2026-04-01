import logging
from typing import List, Dict, Any
import os
from src.analyzers.base import BaseAnalyzer

logger = logging.getLogger(__name__)

class PythonAnalyzer(BaseAnalyzer):
    """Analyzer for identifying Python modules and their API status."""
    
    API_INDICATORS = [
        'fastapi', 'flask', 'django', 'starlette', 'aiohttp', 'tornado', 'sanic', 'bottle'
    ]

    @property
    def name(self) -> str:
        return "Python"

    async def analyze(self, ado_client: Any, project_id: str, repo_id: str, file_tree: List[Dict]) -> List[Dict]:
        target_files = [f for f in file_tree if os.path.basename(f['path']) in ['requirements.txt', 'pyproject.toml', 'setup.py']]
        
        # If no explicit config files are found, there still might be Python code.
        # But for module discovery, it's safer to rely on config files.
        if not target_files:
            return []

        modules = []
        for pf in target_files:
            content = await ado_client.get_file_content(project_id, repo_id, pf['path'])
            if not content:
                continue

            content_lower = content.lower()
            is_api = any(indicator in content_lower for indicator in self.API_INDICATORS)
            
            modules.append({
                'module_path': os.path.dirname(pf['path']) or '/',
                'config_file': os.path.basename(pf['path']),
                'is_api': is_api
            })
            
        # Deduplicate modules since there could be both requirements.txt and pyproject.toml in the same directory
        unique_modules = {}
        for m in modules:
            path = m['module_path']
            if path not in unique_modules:
                unique_modules[path] = m
            else:
                # If either says it's an API, keep it
                if m['is_api']:
                    unique_modules[path]['is_api'] = True
                    
        return list(unique_modules.values())
