"""
####################
# HELPER FUNCTIONS #
####################
"""

import logging
import re
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
    harmonize_course_codes,
)

LOGFMT = "%(asctime)s %(threadName)s~%(levelno)s /%(filename)s@%(lineno)s@%(funcName)s/ %(message)s"
LEVEL = "INFO"

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format=LOGFMT)


EXPECTED_SCHEDULE_COLUMNS = [
    "no",
    "course_code",
    "college",
    "course_no",
    "course_title",
    "credit",
    "section",
    "instructor",
    "location",
    "days",
    "time",
    "capacity",
]

COLUMN_ALIASES = {
    "n0": "no",
    "no": "no",
    "course_code": "course_code",
    "course_code_": "course_code",
    "course_code__": "course_code",
    "college": "college",
    "course_no": "course_no",
    "course_n0": "course_no",
    "course_title": "course_title",
    "credit": "credit",
    "section": "section",
    "sec": "section",
    "instructor": "instructor",
    "location": "location",
    "location_room": "location",
    "days": "days",
    "time": "time",
    "capacity": "capacity",
}


def _normalize_string_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Clean the value of the df."""

    def _clean_value(value):
        if isinstance(value, str):
            return re.sub(r"\s+", " ", value.strip())
        return value

    str_cols = df.columns[df.dtypes == "object"]
    if len(str_cols):
        for col in str_cols:
            df.loc[:, col] = df.loc[:, col].map(_clean_value)
    return df


def _canonical_column_name(value) -> str:
    if not isinstance(value, str):
        return value
    normalized = (
        value.strip().lower().replace("&", "and").replace("/", "_").replace(".", "")
    )
    normalized = normalized.replace(" ", "_")
    normalized = normalized.replace("-", "_")
    normalized = normalized.replace("__", "_")
    return COLUMN_ALIASES.get(normalized, normalized)


def load_general_schedule(fname, sheet_name):
    raw = pd.read_excel(fname, sheet_name=sheet_name, header=None)
    raw = raw.dropna(axis=0, thresh=2)
    raw = raw.dropna(axis=1, thresh=2)
    first_col = raw.iloc[:, 0].astype(str).str.strip().str.lower()
    mask = first_col.str.match(r"n[o0]\.?")
    if not mask.any():
        raise ValueError(
            f"Unable to locate header row labeled 'No.' in sheet {sheet_name!r}"
        )
    header_idx = mask[mask].index[0]
    header = raw.iloc[header_idx]
    data = raw.iloc[header_idx + 1 :,]
    data.columns = header
    data = _normalize_string_columns(data)
    rename_map = {col: _canonical_column_name(col) for col in data.columns}
    data = data.rename(columns=rename_map)
    missing = [col for col in EXPECTED_SCHEDULE_COLUMNS if col not in data.columns]
    if missing:
        logger.warning(
            "Missing columns %s in sheet %s; filling with NA",
            missing,
            sheet_name,
        )
        for col in missing:
            data.loc[:, col] = pd.NA
    data = data.loc[:, EXPECTED_SCHEDULE_COLUMNS]
    data = data.dropna(subset=["course_code"]).copy()
    data = data.set_index("no")
    data.index.name = "no"
    return data


def process_schedule(fname, sheet_name):

    df = load_general_schedule(fname, sheet_name)

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
