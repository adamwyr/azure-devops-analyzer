import argparse
import asyncio
import os
import json
import logging
import sys

from src.ado_client import AdoClient
from src.crawler import Crawler
from src.analyzers.dotnet import DotNetAnalyzer
from src.analyzers.python import PythonAnalyzer
from src.analyzers.java import JavaAnalyzer

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def run(org_url: str, pat: str, output_file: str, max_retries: int, backoff_factor: float):
    logger.info(f"Starting crawl for {org_url}")
    
    analyzers = [
        DotNetAnalyzer(),
        PythonAnalyzer(),
        JavaAnalyzer()
    ]
    
    async with AdoClient(org_url, pat, max_retries=max_retries, backoff_factor=backoff_factor) as client:
        crawler = Crawler(client, analyzers)
        results = await crawler.crawl_all()
        
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=4, ensure_ascii=False)
        
    logger.info(f"Crawl finished. Results saved to {output_file}")

def main():
    parser = argparse.ArgumentParser(description="Crawl Azure DevOps to identify APIs across languages.")
    parser.add_argument("--org", help="Azure DevOps Organization URL (e.g. https://dev.azure.com/myorg)", required=False)
    parser.add_argument("--pat", help="Personal Access Token for ADO", required=False)
    parser.add_argument("--output", help="Path to output JSON file", default="report_results.json")
    parser.add_argument("--max-retries", help="Maximum number of retries for API requests", type=int, default=3)
    parser.add_argument("--backoff-factor", help="Exponential backoff factor for retries", type=float, default=1.0)
    
    args = parser.parse_args()
    
    # Let environment variables override args
    org_url = os.environ.get("ADO_ORG_URL", args.org)
    pat = os.environ.get("ADO_PAT", args.pat)
    max_retries = int(os.environ.get("ADO_MAX_RETRIES", args.max_retries))
    backoff_factor = float(os.environ.get("ADO_BACKOFF_FACTOR", args.backoff_factor))
    
    if not org_url or not pat:
        logger.error("ADO_ORG_URL and ADO_PAT must be provided via environment variables or CLI arguments.")
        sys.exit(1)
        
    asyncio.run(run(org_url, pat, args.output, max_retries, backoff_factor))

if __name__ == "__main__":
    main()
