"""Des utilities pour gérer le passage du fichier schedule en format traitable et standardisé."""

from typing import List
import re
import datetime as dt
import pandas as pd
import logging

logger = logging.getLogger(__name__)

# def setup_logger(level=LEVEL, logfmt=LOGFMT):
#     logging.basicConfig(level=logging.INFO, format=logfmt)
#     return None


def conv__hours(tdelta):
    """Convert a tdelta in seconds to %H:%M:%S format."""
    return f"{tdelta // 3600:02}:{(tdelta % 3600) // 60 :02}:{tdelta % 60:02}"


def conv__dt(time_str):
    """Convert a time_str in datetime."""
    try:
        dt.datetime.strptime(time_str, "%H:%M")
        return True
    except Exception:
        return False


def clean(se_time):
    """
    Take care of common mistyped errors in times.

    t = df.time.apply(split_time_interval)

    >>> t.loc[check_ill_formated_time(t.stime).apply(clean).index]
         stime etime meridium
    286  8:00:   930       am
    311    12:  1:30       pm
    >>> t.loc[check_ill_formated_time(t.etime).apply(clean).index]
         stime etime meridium
    228   2:40   :40       pm
    229   8:00    30       am
    286  8:00:   930       am
    324   2:30    4:       pm
    >>>
    <<< This is sem 2 >>>
    >>> df.loc[df.time.str.contains('5:4'), ('stime', 'etime', 'meridium', 'time')]
    stime   etime meridium           time
    82   2:40  5:4:10       pm  2:40-5:4:10pm
    296  2:40  5:4:10       pm  2:40-5:4:10pm
    >>>
    >>> df.loc[df.time.str.contains('12pm'), ('stime', 'etime', 'meridium', 'time')]
    stime etime meridium       time
    290  9:00    12       pm  9:00-12pm
    """
    erratum = {
        "8:00:": "8:00",
        "12": "12:00",
        "12:": "12:00",
        "930": "9:30",
        "30": "9:30",
        ":40": "3:40",
        "4:": "4:00",
        "5:4:10": "4:10",
    }
    return erratum.get(se_time, se_time)


def split_time_interval(time_inter: str):
    """
    Split the time interval 6:00-7:00am in 3 parts.

    the start time the end time and the meridiam.
    """
    split = time_inter.split("-")

    assert len(split) == 2, f"split={split}"

    meridium = "am" if "am" in split[-1] else "pm"
    stime, etime = split
    assert stime is not None, f"Trying to split time_inter={time_inter}, stime={stime}"

    # sometime stime has a meridium attached to it, which is not correct.
    stime = stime.replace("am", "").replace("pm", "")    
    etime = etime.replace("am", "").replace("pm", "")
    data = {"stime": stime, "etime": etime, "meridium": meridium}

    return pd.Series(data)


def check_time_format(time_str):
    """Check if the time string is in the correct HH:MM format."""
    try:
        # Attempt to parse the time string in HH:MM format
        dt.datetime.strptime(time_str, "%H:%M")
        return True
    except ValueError:
        # If parsing fails, return False
        return False


def check_ill_formated_time(s: pd.Series):
    """Return the ill formated data in a time_serie of str times."""
    return s.where(~s.apply(check_time_format)).dropna()


def get_datetimes(row):
    """
    Given start end and meridium values.

    return 2 datetimes object one for the start time
    one for the end time
    take in account the meridium to compute the datetime objects correctly

    row should be ("stime", "etime", "meridium")
    """
    stime, etime, meridium = row

    shour = int(stime.split(":")[0])
    ehour = int(etime.split(":")[0])

    # need to report this errors
    if ehour > 8 and meridium == "pm":
        # this is an error we correct it
        # no courses allowed to finish after 9
        # it's probably a morning course
        meridium = "am"
    if ehour < 8 and meridium == "am":
        # this is an error we correct it
        # no courses allowed to finish before 8
        # it's probably an afternoon course ""
        #
        # make an exception for course starting at 01:01  which are tba
        # ending at 02:02
        if shour == 1 and int(stime.split(":")[1]) == 1:
            pass
        else:
            meridium = "pm"

    stimedt, etimedt = None, None
    try:
        if shour == 12:
            stimedt = dt.datetime.strptime(stime + "pm", "%I:%M%p")
            etimedt = dt.datetime.strptime(etime + "pm", "%I:%M%p")
        elif (ehour == 12 and shour < 12) or (shour > ehour):
            stimedt = dt.datetime.strptime(stime + "am", "%I:%M%p")
            etimedt = dt.datetime.strptime(etime + "pm", "%I:%M%p")
        elif shour < ehour:
            stimedt = dt.datetime.strptime(stime + meridium, "%I:%M%p")
            etimedt = dt.datetime.strptime(etime + meridium, "%I:%M%p")
    except ValueError as va:
        logger.exception(f">>>> 'row={row} not converted.'")
    
    return (stimedt, etimedt)


def get_week_days(days: str) -> list[str] | None:
    """Given the value of a Days column value return a list of weekdays."""
    # cleaning
    week_days = re.fullmatch(
        r"((m)|(t)|(w)|(th)|(f)|(s)|(S))+", days.strip(), flags=re.I
    )

    # removing some none and strange double counting stuff
    week_days = [d for d in set(week_days.groups()) if d]

    return week_days


# à finir
def build_date(week_day: str, ts: pd.Timestamp):
    """
    Build the date from the string week_day and a start_time.
    The date should start monday 2nd of september 2024
    """
    correspondance = {
        "m": "03",
        "t": "04",
        "w": "05",
        "th": "06",
        "f": "07",
        "s": "08",
        "S": "02",
    }
    time_str = ts.strftime("%H:%M")
    date = f"2025-02-{correspondance[week_day]} {time_str}"
    try:
        dtdate = dt.datetime.strptime(date, "%Y-%m-%d %H:%M")
    except ValueError as ve:
        print(f">>>> date='{date}' and time_str='{time_str}' and week_day='{week_day}'")
        raise ve

    return dtdate


def time_filter(atime: str):
    """Check if the time is am or pm
    if no time or tba set it to np.nan"""
    try:
        atime = atime.strip()

        # cond = 'am' in atime or 'pm' in atime
        cond = atime.endswith("am") or atime.endswith("pm")
        # except AttributeError as ae:
        #     # we are probably treating np.nan and whant it to pass
        #     print(ae)
        return True
    except Exception:
        cond = False

    return not cond


def print_org_table(table: pd.DataFrame, titles: str = None):
    """Print a df in org table."""
    if titles:
        print(f"|{'|'.join(titles)}|")
    print("|--")
    for k, v in table.iterrows():
        print(f"|{k} |{'|'.join([str(elt) for elt in v.values])} |")
