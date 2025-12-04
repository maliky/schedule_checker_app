"""Helpers to transform exam schedule workbooks into Vega-friendly frames."""

from __future__ import annotations

import logging
import re
from typing import Iterable, Optional

import pandas as pd

try:  # pragma: no cover - defensive dependency check
    import openpyxl  # noqa: F401
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("openpyxl is required to parse exam schedule workbooks") from exc

from class_schedule.class_schedule import clean_and_harmonize_times
from class_schedule.utilities import split_time_interval, get_datetimes


logger = logging.getLogger(__name__)

COLUMN_MAP = {
    "n0.": "no",
    "course code": "course_code",
    "course n0.": "course_no",
    "course title": "course_title",
    "sec": "section",
    "day & time": "day_time",
    "location/room": "location",
    "instructor/ proctor": "instructor",
    "exam day": "exam_date",
    "exam date": "exam_date",
    "remedial program schedule": "program",
    "time": "time",
}


def _normalize_string_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Apply strip + whitespace normalization to every string column."""

    string_cols = df.select_dtypes(include="object").columns
    if not len(string_cols):
        return df

    df = df.copy()
    df.loc[:, string_cols] = df.loc[:, string_cols].apply(
        lambda s: s.str.strip().str.replace(r"\s+", " ", regex=True)
    )
    return df


def get_no_index(raw: pd.DataFrame) -> pd.Series:
    """Return a boolean index indicating rows containing the "N0." header marker."""

    def _contains_marker(row: pd.Series) -> bool:
        return row.astype(str).str.contains("N0.", case=False, na=False).any()

    return raw.apply(_contains_marker, axis=1)


def load_exam_sheet(xl: pd.ExcelFile, sheet: str) -> pd.DataFrame:
    """Load a sheet and slice the table that starts at the "N0." marker."""

    raw = xl.parse(sheet, header=None)
    raw = _normalize_string_columns(raw)

    header_mask = get_no_index(raw)
    if not header_mask.any():
        raise ValueError(f"Unable to locate N0. header row in sheet {sheet!r}")

    header_idx = header_mask[header_mask].index[0]
    header = raw.iloc[header_idx].ffill()
    df = (
        raw.iloc[header_idx + 2 :]
        .dropna(how="all")
        .reset_index(drop=True)
    )
    df.columns = header
    df = df.loc[:, ~df.columns.duplicated()]
    df = _normalize_string_columns(df)
    logger.info("Loaded %s rows from sheet %s", len(df), sheet)
    return df


def normalize_columns(df: pd.DataFrame, sheet: str) -> pd.DataFrame:
    """Rename columns using COLUMN_MAP and attach the sheet name as the college."""

    rename_map = {}
    for col in df.columns:
        normalized = col.strip().lower()
        target = COLUMN_MAP.get(normalized, normalized.replace(" ", "_"))
        rename_map[col] = target
    df = df.rename(columns=rename_map)
    df.loc[:, "college"] = sheet
    df = df.drop(columns=[c for c in df.columns if c.lower().startswith("unnamed")], errors="ignore")
    df = df.dropna(subset=["course_code", "course_no"], how="all")
    return df


def parse_exam_times(df: pd.DataFrame) -> pd.DataFrame:
    """Split "Day & Time" into weekday/time and derive timestamp columns."""

    time_pattern = re.compile(
        r"(\d{1,2}(?::\d{2})?\s*(?:am|pm)?\s*(?:-|to)\s*\d{1,2}(?::\d{2})?\s*(?:am|pm))",
        re.IGNORECASE,
    )

    def _split_day_time(value: Optional[str]) -> tuple[Optional[str], Optional[str]]:
        if not isinstance(value, str):
            return None, None
        match = time_pattern.search(value)
        if not match:
            return value.strip(), None
        day = value[: match.start()].strip(" ,") or None
        time_str = match.group(1).strip().strip("()").replace(" ", "")
        return day, time_str

    df = df.copy()
    df = df.drop(columns=["time"], errors="ignore")

    day_time_parts = df.loc[:, "day_time"].apply(
        lambda v: pd.Series(_split_day_time(v))
    )
    day_time_parts.columns = ["weekday_text", "time"]
    df = pd.concat([df, day_time_parts], axis=1)
    df = df[df.loc[:, "time"].notna()].reset_index(drop=True)

    df = clean_and_harmonize_times(df)

    time_parts = df.loc[:, "time"].apply(split_time_interval).apply(pd.Series)
    time_parts.columns = ["stime", "etime", "meridium"]
    df.loc[:, ["stime", "etime", "meridium"]] = time_parts

    datetimes = df.loc[:, ["stime", "etime", "meridium"]].apply(
        get_datetimes, axis=1, result_type="expand"
    )
    datetimes.columns = ["sts", "ets"]
    df.loc[:, ["sts", "ets"]] = datetimes

    df.loc[:, "exam_date"] = pd.to_datetime(df.loc[:, "exam_date"], errors="coerce").dt.date
    df.loc[:, "sts"] = df.apply(
        lambda row: pd.Timestamp.combine(row["exam_date"], row["sts"].time())
        if pd.notna(row["exam_date"]) and pd.notna(row["sts"])
        else row["sts"],
        axis=1,
    )
    df.loc[:, "ets"] = df.apply(
        lambda row: pd.Timestamp.combine(row["exam_date"], row["ets"].time())
        if pd.notna(row["exam_date"]) and pd.notna(row["ets"])
        else row["ets"],
        axis=1,
    )
    return df


def build_exam_records(df: pd.DataFrame) -> pd.DataFrame:
    """Produce the Vega-friendly subset of columns for visualisation."""

    df = df.copy()
    df.loc[:, "start_time"] = df.loc[:, "sts"].dt.strftime("%H:%M")
    df.loc[:, "end_time"] = df.loc[:, "ets"].dt.strftime("%H:%M")
    df.loc[:, "weekday"] = df.loc[:, "sts"].dt.day_name()
    df.loc[:, "cid"] = df.apply(
        lambda row: f"{row.course_code}_{row.course_no}_exam_{row.section}".lower(),
        axis=1,
    )
    return df.loc[
        :,
        [
            "sts",
            "ets",
            "weekday",
            "course_code",
            "course_no",
            "course_title",
            "section",
            "instructor",
            "location",
            "college",
            "start_time",
            "end_time",
            "exam_date",
            "cid",
        ],
    ]


def process_exam_workbook(path: str, sheets: Optional[Iterable[str]] = None) -> pd.DataFrame:
    """End-to-end processing entry point for exam workbook parsing."""

    xl = pd.ExcelFile(path)
    selected = list(sheets or ["FINAL EXAM SCHEDULE", "GENERAL SCHEDULE"])
    logger.info("Processing sheets: %s", ", ".join(selected))

    frames = []
    for sheet in selected:
        df = load_exam_sheet(xl, sheet)
        df = normalize_columns(df, sheet)
        df = parse_exam_times(df)
        frames.append(build_exam_records(df))

    if not frames:
        return pd.DataFrame()

    return pd.concat(frames, ignore_index=True)
