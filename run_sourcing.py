import logging
import sys
from src.database import init_db, save_job
from src.sourcing import load_config, get_resilinet_session, fetch_greenhouse_jobs, fetch_lever_jobs

## logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("sourcing.log", mode="w", encoding="utf-8")
    ]
)
logger = logging.getLogger("PipelineRunner")

def main():
    logger.info("Starting Autonomous ATS Sourcing Pipeline...")

    try:
        # Initialize storage.
        # logger.info("Initializing  SQLite storage...")
        init_db()

        # Load Declerative configuration
        # logger.info("Loading configuration routing rules...")
        config = load_config()
        rules = config.get("filter_rules", [])

        # Initialize connection pool
        # this single session stays open, reusing TCP connection across all API calls
        session = get_resilinet_session()

        total_discovered = 0
        total_new = 0
        failed_boards = []

        # Execute polling
        greenhouse_targets = config.get("greenhouse_boards", [])
        if greenhouse_targets:
            logger.info(f"Polling {len(greenhouse_targets)} Greenhouse boards...")
            for company in greenhouse_targets:
                jobs = fetch_greenhouse_jobs(company=company, rules=rules, session=session)
                total_discovered += len(jobs)
                for job in jobs:
                    if save_job(job=job):
                        total_new += 1
                        logger.info(f"[+] NEW MATCH: [{job.company}] {job.title}")

        lever_targets = config.get("lever_boards", [])
        if lever_targets:
            logger.info(f"Polling {len(lever_targets)} Lever boards...")
            for company in lever_targets:
                jobs = fetch_lever_jobs(company=company, rules=rules, session=session)
                total_discovered += len(jobs)
                for job in jobs:
                    if save_job(job=job):
                        total_new += 1
                        logger.info(f"[+] NEW MATCH: [{job.company}] {job.title}")

        # clean teardown
        session.close()

        # Step 6: Pipeline Telemetry
        logger.info("--- Pipeline Run Summary ---")
        logger.info(f"Total Target Roles Discovered: {total_discovered}")
        logger.info(f"New Requisitions Saved:        {total_new}")
        logger.info(f"Duplicates Filtered Out:       {total_discovered - total_new}")

    except Exception as e:
        logger.critical(f"Pipeline suffered a fatal crash: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()

