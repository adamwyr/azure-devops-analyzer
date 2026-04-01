from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseAnalyzer(ABC):
    """
    Abstract base class for all language analyzers.
    Each analyzer must implement the `analyze` method.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the language this analyzer handles."""
        pass
        
    @abstractmethod
    async def analyze(self, ado_client: Any, project_id: str, repo_id: str, file_tree: List[Dict]) -> List[Dict]:
        """
        Analyze the repository file tree and extract modules.
        
        :param ado_client: The AdoClient instance, used to fetch file contents.
        :param project_id: ID of the ADO project.
        :param repo_id: ID of the ADO repository.
        :param file_tree: List of file dictionaries (from the ADO items API) where each item has e.g. 'path'.
        :return: A list of dictionaries, one per discovered module in this repo.
                 Each dictionary format is up to the specific analyzer, but usually includes:
                 'module_path', 'is_api', and language-specific details.
        """
        pass
