"""Traite le fichier excel des schedule et affiche des infos à son sujet."""

import logging
import argparse
import pandas as pd
from class_schedule.class_schedule import (
    general_cleaning,
    clean_and_harmonize_times,
    getting_start_end_times,
    add_duration,
    add_course_id_year_college,
    expand_days,
    add_weekname,
    special_applied_epidemiology_course,
)

from class_schedule.helper import process_schedule

# from utilities import setup_logger


LOGFMT = "%(asctime)s %(threadName)s~%(levelno)s /%(filename)s@%(lineno)s@%(funcName)s/ %(message)s"
LEVEL = "INFO"

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format=LOGFMT)

# logger = logging.getLogger(__name__)
# setup_logger()


def main_prg():
    """Récupère les arguments et lance l'application principale."""
    args = get_args()
    logger.setLevel(args.logLevel)
    main(args.fname, args.sname, args.fout)
    return None


def main(
    fname="FINAL SCHEDULE SEMESTEWR II 2024-2025_v2.xlsx",
    sheet_name="GENERAL SCHEDULE",
    fout="./Data/class_schedule_v3_cleaned.xlsx",
):
    """Application principale."""
    tdf = process_schedule(fname, sheet_name)

    col_reorder = [
        "college",
        "cid",
        "instructor",
        "course_title",
        "weekday",
        "start_time",
        "end_time",
        "location",
        "credit",
        "ets",
        "sts",
        "oldidx",
    ]
    tdf = tdf.loc[:, col_reorder]
    logger.info(f">>> Saving the df:\n{tdf.head(5)}\nto  {fout}")

    tdf.to_excel(fout)
    return tdf


def get_args():
    """Parse the function's arguments."""
    description = (
        """Un fichier pour executer traiter les schedules de TU dans le format std."""
    )
    parser = argparse.ArgumentParser(description=description)

    logLevel_def = "INFO"
    logLevel_doc = f"Le Log Leve {logLevel_def}"
    parser.add_argument(
        "--logLevel", "-l", type=str, default=logLevel_def, help=logLevel_doc
    )

    fname_def = "./Data/Book1_v4.xlsx"
    fname_doc = f"name of the file to update.  ({fname_def})"
    parser.add_argument(
        "--fname",
        "-f",
        help=fname_doc,
        default=fname_def,
    )

    sname_def = "GENERAL SCHEDULE"
    sname_doc = f"Name of the sheet in the excel doc. ({sname_def})"
    parser.add_argument(
        "--sname",
        "-s",
        help=sname_doc,
        default=sname_def,
    )

    fout_def = f"{fname_def.split('.xlsx')[0]}_cleaned.xlsx"
    fout_doc = f"Name of the output file. ({fout_def})"
    parser.add_argument(
        "--fout",
        "-o",
        help=fout_doc,
        default=fout_def,
    )

    return parser.parse_args()


if __name__ == "__main__":
    main_prg()
