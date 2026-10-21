import os
import json
import logging
from pathlib import Path
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from pydantic import ValidationError

## Import data contract
from src.database import JobRequisition

## configuration & logging setup
# logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "configs" / "boards.json"
CONFIG_PATH = Path(os.environ.get("CONFIG_PATH", DEFAULT_CONFIG_PATH))

def load_config() -> dict:
    """Loads the filtering rules and company targets from boards.json."""
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Configuration file missing at: {CONFIG_PATH}")
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

## Networking layer
def get_resilinet_session() -> requests.Session:
    """
    Creates an HTTPS session with automatic retries for transient network failures.
    Prevents the pipeline form crashing if ATS API momentarily drops.
    """
    session = requests.Session()
    # retry strategy: 3 attempts, exponential backoff, retry on 5xx errors
    retries = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update({"User-Agent": "AutonomousJobEngine/2.0"})
    return session

## Filtering
def is_target_role(title: str, rules: dict) -> bool:
    """strict exclusion and inclusionary keyword filters"""
    if not title:
        return False

    title_lower = title.lower()

    # Exclusionary filter
    if any(exclude.lower() in title_lower for exclude in rules.get("exclude_titles", [])):
        return False

    # Inclusionary filter
    return any(include.lower() in title_lower for include in rules.get("include_titles", []))

## ATS Ingestion & validation
def fetch_greenhouse_jobs(company: str, rules: dict, session: requests.Session) -> tuple[list[JobRequisition], bool]:
    """
    Poll greenhouse API , filters by title, and immediately enforces pydantic schema.
    returns a list strictly validated JobRequisition objects.
    """
    endpoint = f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs?content=true"
    discovered = []

    try:
        response = session.get(endpoint, timeout=10)
        response.raise_for_status() # automatically throws erros for 4xx/5xx responses.

        payload = response.json()
        for job_node in payload.get("jobs", []):
            if is_target_role(job_node.get("title", ""), rules):
                # metadata
                job_node["company"] = company.capitalize()
                job_node["source"] = "Greenhouse_API"

                try:
                    # validate the edge: convert the dict to pydantic obj
                    validated_job = JobRequisition(**job_node)
                    discovered.append(validated_job)
                except ValidationError as e:
                    logger.debug(f"Data Validation failed for the {company} job: {e}")
        return discovered, True
    
    except requests.RequestException as e:
        status = e.response.status_code if e.response is not None else "CONN_ERR"
        logger.warning(f"[Greenhouse] {company:<18} | FAILED (HTTP {status})")
        return [], False

def fetch_lever_jobs(company: str, rules: dict, session: requests.Session) -> tuple[list[JobRequisition], bool]:
    """
    Polls Lever API, filters by title, and immediately enforces the Pydantic schema.
    Returns a list of strictly validated JobRequisition objects.
    """
    endpoint = f"https://api.lever.co/v0/postings/{company}?mode=json"
    discovered = []

    try:
        response = session.get(endpoint, timeout=10)
        response.raise_for_status()
        
        jobs = response.json()
        for job_node in jobs:
            if is_target_role(job_node.get("text", ""), rules):
                # Inject metadata missing from the individual Lever node
                job_node["company"] = company.capitalize()
                job_node["source"] = "Lever_API"
                
                try:
                    # Validate at the edge: Pydantic handles AliasChoices mapping 'text' -> 'title'
                    validated_job = JobRequisition(**job_node)
                    discovered.append(validated_job)
                except ValidationError as e:
                    logger.debug(f"Data validation failed for {company} job: {e}")
        return discovered, True

    except requests.RequestException as e:
        status = e.response.status_code if e.response is not None else "CONN_ERR"
        logger.warning(f"[Lever]      {company:<18} | FAILED (HTTP {status})")
        return [], False