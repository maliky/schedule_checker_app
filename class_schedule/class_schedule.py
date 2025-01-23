"""Fonction pour nettoyer un fichier de schedule de TU."""

import pandas as pd  # read_csv, timedelta, timestamp, conv__dt, DataFrame
from class_schedule.utilities import (
    time_filter,
    clean,
    split_time_interval,
    get_datetimes,
    build_date,
    get_week_days,
)
from class_schedule.settings import course_colleged, course_code_mapping

import logging


logger = logging.getLogger(__name__)
# logging.basicConfig(level=logging.INFO, format=logfmt)


def general_cleaning(df, logger=logger):
    """Supprime les espaces en trop, harmonize la casse."""
    logger.info("Supprime les espaces en trop, harmonize la casse.")
    #    l2.info("Supprime les espaces en trop, harmonize la casse.")
    df.columns = [
        c.strip().lower().replace(" ", "_").strip().strip(".") for c in df.columns
    ]
    cols = ["days", "time"]
    df.loc[:, cols] = df.loc[:, cols].apply(lambda r: r.str.lower())

    # assert "college" in df.columns, f"'college' should be df.columns={df.columns}"
    # df.loc[:, "college"] = df.college.str.upper()

    for c in df:
        if isinstance(df[c].iloc[0], str):
            df[c] = df[c].str.strip().replace(r"  +", " ", regex=True)
    return df


def clean_and_harmonize_times(df):
    """cleaning and harmonizing times."""
    logger.info("cleaning and harmonizing times.")

    df.time = df.time.str.lower()
    df.time = df.time.str.replace("noon", "pm")

    #  df.loc[354, 'time'] = df.loc[354].time.split('/')[1]
    # replacing  time separators space '-'
    df.time = df.time.str.replace(
        r"(\d) (\d)", lambda m: f"{m.groups()[0]}-{m.groups()[1]}", regex=True
    )

    df.time = df.time.str.replace(" ", "")
    # common typos
    df.time = df.time.str.replace(".", ":")
    df.time = df.time.str.replace(";", ":")

    # if time is not set, set it to a default time
    default_time = "01:01-02:02am"
    df.loc[:, "time"] = df.time.fillna(default_time)
    df.loc[:, "time"] = df.time.str.replace("tba", default_time)

    no_meridium = ~df.time.apply(time_filter)
    df.loc[no_meridium, "time"] = df.loc[no_meridium, "time"].apply(lambda x: x + "pm")

    return df


def getting_start_end_times(df):
    """Spliting time intervales on the dataframe to add cols = ("stime", "etime", "meridium")."""
    logger.debug(
        "Spliting time intervales on the dataframe to add cols = ('stime', 'etime', 'meridium')."
    )

    split_interval = df.time.apply(split_time_interval)
    time_cols = ("stime", "etime", "meridium")
    df.loc[:, time_cols] = split_interval

    df.loc[:, "stime"] = df.stime.apply(clean)
    df.loc[:, "etime"] = df.etime.apply(clean)
    return df


def add_duration(df):
    """Convert str times to time objects."""
    logger.debug("Convert str times to time objects.")
    time_cols = ("stime", "etime", "meridium")
    _tmp = df.loc[:, time_cols].apply(get_datetimes, axis=1, result_type="expand")
    _tmp.columns = ("sts", "ets")
    df.loc[:, ("sts", "ets")] = _tmp
    df.loc[:, "duration_td"] = df.ets - df.sts
    df.loc[:, "duration_sec"] = df.duration_td.dt.seconds
    df.loc[:, "duration_str"] = df.duration_sec.apply(
        lambda s: f"{s //3600:02}:{s%3600 // 60 :02}"
    )
    return df


def add_course_id_year_college(df):
    """Crée et ajoute un identifiant avec ou sans sess no et le level du cours."""
    logger.info("Crée et ajoute un identifiant et l'année pour chaque cours.")

    course_id = ["course_code", "course_no", "section"]

    df.loc[:, "cid"] = df.loc[:, course_id].apply(
        lambda x: f"{x[0]}_{x[1]}_s{x[2]:.0f}", axis=1
    )
    # keeping a id without sessname
    df.loc[:, "cidno_sess"] = df.cid.str.split("_s").apply(lambda x: x[0])

    years = {
        "1": "Freshmen",
        "2": "Sophomore",
        "3": "Junior",
        "4": "Senior",
        "5": "Senior",
    }

    df.loc[:, "year"] = df.course_no.apply(lambda x: years[str(x)[0]])

    college_cols = ["cidno_sess", "course_title", "year"]

    try:
        df.loc[:, "college"] = df.loc[:, college_cols].apply(
            lambda s: course_colleged[tuple(s)], axis=1
        )

    except KeyError as ke:
        msg = f">> {ke} is not a course that was seen before.  We need to update the course_colleged variable in file settings.py <<"
        logger.warning(msg)
        pass
    return df


def expand_days(df):
    """Crée une ligne de cours par jour."""
    logger.info("Crée une ligne de cours par jour.")

    tdf = pd.concat([expand_row(row) for _, row in df.iterrows()]).reset_index(
        drop=True
    )

    return tdf


def expand_row(row):
    """
    Transform a single row with a days combined into.
    a dataframe with potentialy two rows where two new columns show
    start and end times for one specific days"""
    try:
        days = get_week_days(row.days)
    except Exception:
        # in case of error is no days attributed then put them on sunday
        # so it's obvious
        days = ["S", "S"]

    start_times = [build_date(day, row.sts) for day in days]
    end_times = [build_date(day, row.ets) for day in days]

    # drop this to avoid confusion
    row = row.drop(["sts", "ets"])

    data = {"sts": start_times, "ets": end_times}
    n = len(start_times)
    for i in row.index:
        data[i] = [row[i]] * n
    data["oldidx"] = row.name

    tdf = pd.DataFrame(data)

    return tdf


def add_weekname(tdf):
    """Ajoute une colone avec le nom du jour de la semaine."""
    logger.info("Ajoute une colone avec le nom du jour de la semaine.")
    tdf.loc[:, "weekday"] = tdf.sts.dt.day_name()
    tdf.loc[:, "time_start"] = tdf.sts.apply(lambda ts: ts.strftime("%H:%M"))
    tdf.loc[:, "time_end"] = tdf.ets.apply(lambda ts: ts.strftime("%H:%M"))
    return tdf


def special_applied_epidemiology_course(df: pd.DataFrame):
    """
    Adjusts a DataFrame of course offerings to handle special cases where
    a course has a total of 5 credits but is taught across 2 sessions.

    Specifically, this function identifies courses that are listed with a
    time string containing a "/", splits these courses into two new entries,
    assigning one entry 3 credits and the other 2 credits. The modifications
    include ensuring that the newly created courses retain relevant attributes
    while updating the index appropriately. The resulting DataFrame is returned
    with the new courses added.

    Parameters:
        df (pd.DataFrame): The DataFrame containing course offerings, which
                           must include 'time', 'days', and 'credit' columns.

    Returns:
        pd.DataFrame: The updated DataFrame with the special case courses added.
    """
    special_course = df.loc[df.time.str.contains("/"), :].reset_index()
    logger.debug(
        "we are hardcoding some harmonization rules pertaining to this course.  Should be on tuesday and saturday"
    )
    special_course.loc[0, "days"] = special_course.days.values[0] + "/ts"

    if len(special_course) == 1:
        new_course = pd.concat([special_course, special_course])
        new_course.iloc[1, 0] = df.index[-1] + 1
        new_course = new_course.set_index("no")
        new_course.loc[:, "time"] = new_course.time.str.split("/").iloc[0]
        new_course.loc[:, "days"] = new_course.days.str.split("/").iloc[0]
        new_course.loc[:, "credit"] = [3, 2]
        df.loc[new_course.index[0]] = new_course.iloc[0]

        _tmp = pd.DataFrame(new_course.iloc[1]).T
        df = pd.concat([df, _tmp])
    else:
        logger.debug("no course are containing '/' ")

    return df


def harmonize_course_codes(df, mapping=course_code_mapping):
    """
    Given the mapping harmonize the course code to 4 letters codes

    update the course_code_mapping if need to add other courses traduction
    """
    df.loc[:, "course_code"] = df.course_code.apply(
        lambda x: course_code_mapping.get(x, x)
    )

    return df
