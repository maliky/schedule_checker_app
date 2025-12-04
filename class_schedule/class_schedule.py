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
    """
    Perform initial cleaning on the schedule DataFrame.

    Actions:
    - Removes extra spaces from column names.
    - Harmonizes column names to lowercase with underscores.
    - Strips excess spaces from string values in all columns.

    Logs:
    - Logs the start and completion of the cleaning process.

    Parameters:
    - df (pd.DataFrame): Raw schedule data.
    """
    logger.info("Starting general cleaning of the data.")

    #    l2.info("Supprime les espaces en trop, harmonize la casse.")
    df.columns = [
        c.strip().lower().replace(" ", "_").strip().strip(".") for c in df.columns
    ]
    cols = ["days", "time"]
    try:
        df.loc[:, cols] = df.loc[:, cols].apply(lambda r: r.str.lower())
    except AttributeError as ae:
        logger.exception(f"df.dtypes={df.dtypes}")

    # assert "college" in df.columns, f"'college' should be df.columns={df.columns}"
    # df.loc[:, "college"] = df.college.str.upper()

    for c in df:
        if isinstance(df[c].iloc[0], str):
            df[c] = df[c].str.strip().replace(r"  +", " ", regex=True)
    logger.info("Completed general cleaning.")
    return df


def clean_and_harmonize_times(df):
    """Clean and standardize the time column in the DataFrame.
        Actions:
    - Converts time to lowercase.
    - Replaces common typos and standardizes formats.
    Parameters:
    - df (pd.DataFrame): DataFrame containing a 'time' column.

    Returns:
    - pd.DataFrame: DataFrame with cleaned and standardized time values.
    """
    logger.info("cleaning and harmonizing times.")

    time_series = df.time.astype(str).str.lower()
    # normalize unicode dashes before further parsing
    time_series = time_series.str.replace("\u2013", "-", regex=False)
    time_series = time_series.str.replace("\u2014", "-", regex=False)

    # we replace "noon" with "pm" to later ease the convertion of time in dt.
    time_series = time_series.str.replace("no?o?n?", "pm", regex=True)

    # handle stray duplicates like "pmpm" or "ampm"
    time_series = time_series.str.replace("pmpm", "pm", regex=False)
    time_series = time_series.str.replace("ampm", "am", regex=False)

    time_series = time_series.str.replace(
        r"(\d) (\d)", lambda m: f"{m.groups()[0]}-{m.groups()[1]}", regex=True
    )

    rows_with_pm_repeated = time_series.str.contains(r"(?P<A>pm).*(?P=A)")
    logger.info(f"pm is repeating in rows {rows_with_pm_repeated}")

    time_series = time_series.str.replace(" ", "")
    rows_with_dots = time_series.str.contains(r"\.")
    logger.info(f"rows with . in the time {rows_with_dots}")
    time_series = time_series.str.replace(".", ":")

    rows_with_semicols = time_series.str.contains(r"\;")
    logger.info(f"rows with ; in the time {rows_with_semicols}")
    time_series = time_series.str.replace(";", ":")

    default_time = "01:01-02:02am"
    time_series = time_series.replace({"nan": pd.NA, "none": pd.NA})
    time_series = time_series.fillna(default_time)
    time_series = time_series.str.replace("tba", default_time)

    time_series = time_series.str.replace(
        "(.*)p$", lambda m: f"{m.groups()[0]}pm", regex=True
    )

    df.loc[:, "time"] = time_series

    no_meridium = ~df.time.apply(time_filter)
    df.loc[no_meridium, "time"] = df.loc[no_meridium, "time"].apply(lambda x: x + "pm")
    logger.info("Completed time cleaning and harmonization.")

    return df


def getting_start_end_times(df):
    """
    Extract start time, end time, and meridium from the 'time' column.
    Parameters:
    - df (pd.DataFrame): DataFrame containing a 'time' column.

    Returns:
    - pd.DataFrame: DataFrame with new columns: 'stime', 'etime', 'meridium'.
    """
    logger.info("Extracting start and end times from the time column.")

    split_interval = df.time.apply(split_time_interval)
    time_cols = ("stime", "etime", "meridium")
    df.loc[:, time_cols] = split_interval

    df.loc[:, "stime"] = df.stime.apply(clean)
    # no need of meridum in start time.  is deducted from etime meridum
    # and relative amplitude
    df.loc[:, "etime"] = df.etime.apply(clean)
    logger.info("Completed extraction of start and end times.")
    return df


def add_duration(df):
    """Calculate duration for each course based on start and end times.
    Parameters:
    - df (pd.DataFrame): DataFrame containing 'stime', 'etime', and 'meridium'.
    Returns:
    - pd.DataFrame: DataFrame with additional duration columns.
    """
    logger.info("Calculating course durations.")
    time_cols = ("stime", "etime", "meridium")
    _tmp = df.loc[:, time_cols].apply(get_datetimes, axis=1, result_type="expand")
    _tmp.columns = ("sts", "ets")
    df.loc[:, ("sts", "ets")] = _tmp
    df.loc[:, "duration_td"] = df.ets - df.sts
    df.loc[:, "duration_sec"] = df.duration_td.dt.seconds
    df.loc[:, "duration_str"] = df.duration_sec.apply(
        lambda s: f"{s //3600:02}:{s%3600 // 60 :02}"
    )
    logger.info("Completed calculation of course durations.")
    return df


def add_course_id_year_college(df, course_colleged=course_colleged):
    """Generate unique course IDs, determine year level, and assign college.
    Parameters:
    - df (pd.DataFrame): Schedule DataFrame.
    Returns:
    - pd.DataFrame: DataFrame with added columns for course ID, year, and college.
    """
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

    def _infer_year(course_no):
        """Map the first numeric digit of course_no to a year label."""
        if pd.isna(course_no):
            return "Unknown"
        digits = [ch for ch in str(course_no) if ch.isdigit()]
        if not digits:
            return "Unknown"
        return years.get(digits[0], "Unknown")

    df.loc[:, "year"] = df.course_no.apply(_infer_year)

    college_cols = ["cidno_sess", "course_title", "year"]
    not_in_curriculum_courses = []
    for k, s in df[college_cols].T.items():
        try:
            df.loc[k, "college"] = course_colleged[tuple(s)]
        except KeyError as ke:
            not_in_curriculum_courses.append(ke)
            pass

    if not_in_curriculum_courses:
        logger.warning(
            f"Unmapped course encountered: {not_in_curriculum_courses}\n>> It is not a course that was"
            " seen before.  We need to update the course_colleged variable in"
            " file settings.py <<"
        )

    logger.info("Completed generation of course IDs and assignment of colleges.")
    return df


def expand_days(df):
    """
    Expand days column into multiple rows, one for each weekday.
    Parameters:
    - df (pd.DataFrame): Schedule DataFrame.

    Returns:
    - pd.DataFrame: Expanded DataFrame with one row per day.
    """

    logger.info("Expanding days into separate rows.")

    tdf = pd.concat([expand_row(row) for _, row in df.iterrows()]).reset_index(drop=True)
    logger.info("Completed expansion of days.")
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
    """
    Add a column with the weekday name for each course.
    Parameters:
    - df (pd.DataFrame): Schedule DataFrame.

    Returns:
    - pd.DataFrame: DataFrame with the weekday name added.
    """
    logger.info("Adding weekday names.")

    tdf.loc[:, "weekday"] = tdf.sts.dt.day_name()
    tdf.loc[:, "time_start"] = tdf.sts.apply(lambda ts: ts.strftime("%H:%M"))
    tdf.loc[:, "time_end"] = tdf.ets.apply(lambda ts: ts.strftime("%H:%M"))
    logger.info("Completed expansion of days.")
    return tdf


def special_applied_epidemiology_course(df: pd.DataFrame):
    """
    Transform a single row with combined days into multiple rows, one per day.

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
    if special_course.empty:
        logger.debug("No course contains /, skipping special handling.")
        return df

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
    logger.info("Adding weekday names.")

    return df
