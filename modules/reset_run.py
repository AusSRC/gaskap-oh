#!/usr/bin/env python3

"""
A script to reset the classification of detections for a GASKAP-OH
source finding run. This can be used to "undo" the categorisation done in the
sidelobe rejection workflow.
"""

import os
import sys
import asyncio
import asyncpg
import logging
from configparser import ConfigParser


logging.basicConfig(level=logging.INFO)


async def main(argv):
    if len(argv) != 1:
        logging.error("sidelobe_rejection.py <config_file>")
        return
    config_file = argv[0]
    if not os.path.exists(config_file):
        raise FileNotFoundError("Config file does not exist")

    # Database connection
    parser = ConfigParser()
    parser.read(config_file)
    config = parser["SoFiAX"]
    run_name = config["run_name"]
    creds = {
        "host": config["db_hostname"],
        "database": config["db_name"],
        "user": config["db_username"],
        "password": config["db_password"],
        "port": config["db_port"],
    }
    schema = config["db_schema"]
    pool = await asyncpg.create_pool(**creds, server_settings={"search_path": schema})
    async with pool.acquire() as conn:
        async with conn.transaction():
            run = await conn.fetchrow("SELECT * FROM run WHERE name=$1", run_name)
            logging.info(
                "Resetting detection status in run %s (id=%i)"
                % (run["name"], run["id"])
            )
            if run is None:
                raise Exception("Run does not exist")

            # remove accepted and rejected flags
            await conn.execute(
                "UPDATE detection SET rejected=false WHERE run_id=$1", int(run["id"])
            )
            await conn.execute(
                "UPDATE detection SET accepted=false WHERE run_id=$1", int(run["id"])
            )
            logging.info("Detections for run %s reset" % run_name)
    return


if __name__ == "__main__":
    argv = sys.argv[1:]
    asyncio.run(main(argv))
