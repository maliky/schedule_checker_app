"""
####################
# HELPER FUNCTIONS #
####################
"""

import logging
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
    harmonize_course_codes    
)

LOGFMT = "%(asctime)s %(threadName)s~%(levelno)s /%(filename)s@%(lineno)s@%(funcName)s/ %(message)s"
LEVEL = "INFO"

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format=LOGFMT)


def process_schedule(fname, sheet_name):

    
    df = pd.read_excel(
        fname,
        sheet_name,
        header=10,
        index_col=0,
        names=[
            "course_code",
            "course_no",
            "course_title",
            "credit",
            "section",
            "instructor",
            "location",
            "days",
            "time",
            "capacity",
        ],
    ).dropna()

    df.index.name = "no"

    df = general_cleaning(df)
    logger.info("Completed general cleaning")

    df = clean_and_harmonize_times(df)
    logger.info("Completed cleaning and harmonizing times")
    
    logger.info("Starting with applied epidemiology a special course to split in 2")
    df = special_applied_epidemiology_course(df)
    logger.info("Completed special applied epidemiology course")
    
    df = getting_start_end_times(df)
    logger.info("Completed getting start and end times")
    
    df = add_duration(df)
    logger.info("Completed adding duration")
    
    df = harmonize_course_codes(df)
    logger.info("Completed harmonizing course codes")
    
    df = add_course_id_year_college(df)
    logger.info("Completed adding course ID, year, and college")

    tdf = expand_days(df)
    tdf = add_weekname(tdf)

    data = tdf.loc[
        :,
        [
            "sts",
            "instructor",
            "location",
            "weekday",
            "cid",
            "credit",
            "course_title",
            "college",
            "oldidx",
            "ets",
        ],
    ]
    times = data.loc[:, ["sts", "ets"]]
    data.loc[:, "start_time"] = data.sts.apply(lambda t: t.strftime("%H:%M"))
    data.loc[:, "end_time"] = data.ets.apply(lambda t: t.strftime("%H:%M"))

    return data
