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
        for company in config.get("greenhouse_boards", []):
            jobs, ok = fetch_greenhouse_jobs(company=company, rules=rules, session=session)
            if not ok:
                failed_boards.append(f"Greenhouse:{company}")
                continue
            new_for_company = sum(1 for job in jobs if save_job(job=job))
            total_discovered += len(jobs)
            total_new += new_for_company
            logger.info(f"[Greenhouse] {company:<18} | Matched: {len(jobs):<3} | New Saved: {new_for_company}")
        
        for company in config.get("lever_boards", []):
            jobs, ok = fetch_lever_jobs(company=company, rules=rules, session=session)
            if not ok:
                failed_boards.append(f"Lever:{company}")
                continue

            new_for_company = sum(1 for job in jobs if save_job(job=job))
            total_discovered += len(jobs)
            total_new += new_for_company
            logger.info(f"[Lever]      {company:<18} | Matched: {len(jobs):<3} | New Saved: {new_for_company}")

        # clean teardown
        session.close()

        # Step 6: Pipeline Telemetry
        logger.info("--- Pipeline Run Summary ---")
        logger.info(f"Total Target Roles Discovered: {total_discovered}")
        logger.info(f"New Requisitions Saved:        {total_new}")
        logger.info(f"Duplicates Filtered Out:       {total_discovered - total_new}")
        if failed_boards:
            logger.warning(f"Failed Boards ({len(failed_boards)}): {', '.join(failed_boards)}")
        else:
            logger.info("All configured ATS boards responded with HTTP 200 OK.")

    except Exception as e:
        logger.critical(f"Pipeline suffered a fatal crash: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()

