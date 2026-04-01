import logging
from typing import List, Dict, Any
import os
from src.analyzers.base import BaseAnalyzer

logger = logging.getLogger(__name__)

class JavaAnalyzer(BaseAnalyzer):
    """Analyzer for identifying Java modules and their API status."""
    
    API_INDICATORS = [
        'spring-boot-starter-web', 'jakarta.ws.rs', 'javax.ws.rs', 'jax-rs',
        'quarkus-resteasy', 'micronaut-http-server'
    ]

    @property
    def name(self) -> str:
        return "Java"

    async def analyze(self, ado_client: Any, project_id: str, repo_id: str, file_tree: List[Dict]) -> List[Dict]:
        target_files = [
            f for f in file_tree 
            if os.path.basename(f['path']) in ['pom.xml', 'build.gradle', 'build.gradle.kts']
        ]
        
        if not target_files:
            return []

        modules = []
        for build_file in target_files:
            content = await ado_client.get_file_content(project_id, repo_id, build_file['path'])
            if not content:
                continue

            content_lower = content.lower()
            is_api = any(indicator in content_lower for indicator in self.API_INDICATORS)
            
            modules.append({
                'module_path': build_file['path'],
                'build_tool': 'maven' if 'pom.xml' in build_file['path'] else 'gradle',
                'is_api': is_api
            })
            
        return modules
