import altair as alt
from class_schedule.helper import process_schedule
import pandas as pd

domain = {"start": {}, "end": {}}

room_order = alt.EncodingSortField(field="location", order="ascending")
instructor_order = alt.EncodingSortField(field="instructor", order="ascending")


def _detect_location_conflicts(day_df: pd.DataFrame) -> pd.DataFrame:
    """Return a DataFrame summarising conflicts per location for the day.

    Columns: location, conflict_start, conflict_end, conflicts (list of dicts)
    """

    rows = []
    for location, group in day_df.groupby("location"):
        group_sorted = group.sort_values("sts")
        overlaps = []
        prev = None
        for _, row in group_sorted.iterrows():
            if prev is not None and row.sts < prev.ets:
                overlaps.append(prev)
                overlaps.append(row)
            prev = row
        if overlaps:
            uniq = pd.DataFrame(overlaps).drop_duplicates()
            rows.append(
                {
                    "location": location,
                    "conflict_start": uniq.sts.min(),
                    "conflict_end": uniq.ets.max(),
                    "conflicts": uniq.to_dict(orient="records"),
                }
            )

    return pd.DataFrame(rows)


def create_visualizations(data, dout="templates"):
    """
    Generates visualizations for class schedules based on instructors, rooms, and weekdays.

    Parameters:
    ----------
    data : pandas.DataFrame
        The processed schedule data containing columns such as 'weekday', 'college', 'instructor',
        'sts' (start time), and 'ets' (end time).

    dout : str
        The output directory where the generated visualization files will be saved.

    Outputs:
    -------
    - Saves two HTML files:
        1. `instructor_final_chart.html` (Instructor-based schedules)
        2. `room_final_chart.html` (Room-based schedules)
    """
    data = data.copy()
    data.loc[:, "college"] = data.college.fillna("Unknown")

    day_gps = data.groupby(["weekday"]).groups

    colleges = sorted(data.college.unique())
    weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

    clg_instructor_charts = []
    day_room_charts = []

    college_param = alt.param(
        "College",
        bind=alt.binding_select(options=["All"] + colleges),
        value="All",
    )

    for day in weekdays:

        day_df = data.loc[day_gps[day]]

        time_scale = alt.Scale(domain=[day_df.sts.min(), day_df.ets.max()], nice=False)
        conflict_df = _detect_location_conflicts(day_df)

        day_room_chart = make_day_room_chart(
            day_df, time_scale, title=day, conflict_df=conflict_df
        )
        day_room_charts.append(day_room_chart)

        clg_day_charts = []
        clg_day_gps = day_df.groupby("college").groups

        for cllg in colleges:

            gp_idx = clg_day_gps.get(cllg, [])
            if len(gp_idx) != 0:
                clg_day_df = data.loc[gp_idx]

                clg_day_chart = make_clg_day_instructor_chart(
                    clg_day_df, time_scale, title=cllg
                )
                clg_day_charts.append(clg_day_chart)

        clg_instructor_chart = (
            alt.vconcat(*clg_day_charts)
            .properties(title=day)
            .resolve_scale(x="independent")
        )
        clg_instructor_charts.append(clg_instructor_chart)
        # college_chart.save(f"{day}-colleges_chart.html")
        instructor_final_chart = alt.hconcat(*clg_instructor_charts)

    instructor_final_chart = (
        instructor_final_chart
        .add_params(college_param)
        .transform_filter(
            (college_param == "All") | (alt.datum.college == college_param)
        )
        .resolve_scale(x="independent")
    )

    instructor_final_chart.save(f"{dout}/instructor_final_chart.html")

    room_final_chart = alt.hconcat(*day_room_charts).resolve_scale(x="independent")
    room_final_chart.save(f"{dout}/room_final_chart.html")

    pass


def make_day_room_chart(
    day_data_df: pd.DataFrame,
    time_scale: alt.Scale,
    title: str,
    conflict_df: pd.DataFrame | None = None,
):
    # A chart layer for the room occupation
    chart_rooms = (
        alt.Chart(day_data_df)
        .mark_bar(opacity=0.5)
        .encode(
            x=alt.X("sts:T", scale=time_scale),
            x2="ets:T",
            y=alt.Y("instructor:N", title=None, sort=instructor_order),
            size=alt.Size("credit:Q", title="Credit", scale=alt.Scale(range=[2, 15])),
            color="college:N",
            tooltip=[
                "cid",
                "college",
                "credit",
                "course_title",
                "start_time",
                "end_time",
            ],
        )
    )
    layers = []

    if conflict_df is not None and not conflict_df.empty:
        conflict_df = conflict_df.copy()
        conflict_df.loc[:, "conflict_start"] = conflict_df["conflict_start"].astype(str)
        conflict_df.loc[:, "conflict_end"] = conflict_df["conflict_end"].astype(str)
        conflict_df.loc[:, "conflicts"] = conflict_df["conflicts"].apply(str)
        conflict_layer = (
            alt.Chart(conflict_df)
            .mark_rect(color="rgba(255,0,0,0.15)")
            .encode(
                x=alt.X("conflict_start:T", scale=time_scale),
                x2=alt.X2("conflict_end:T"),
                tooltip=[
                    alt.Tooltip("location:N", title="Location"),
                    alt.Tooltip("conflict_start:T", title="First overlap"),
                    alt.Tooltip("conflict_end:T", title="Last overlap"),
                    alt.Tooltip("conflicts:N", title="Conflicting sessions"),
                ],
            )
        )
        layers.append(conflict_layer)

    layers.append(chart_rooms)

    layered_chart = (
        alt.layer(*layers, data=day_data_df)
        .facet(
            row=alt.Facet(
                "location:N",
                sort=room_order,
                header=alt.Header(
                    labelAngle=0, labelAnchor="start", labelBaseline="middle"
                ),
                title=None,
            )
        )
        .resolve_scale(y="independent")
        .properties(title=title)
    )
    return layered_chart


def make_clg_day_instructor_chart(
    data: pd.DataFrame,
    time_scale: alt.Scale,
    title: str,
):
    """
    Build and return the layered facet chart for a single day.
     Args:
      day (str): Name of the weekday, e.g. "Monday"
      college (str): Name of the college, e.g. "COET"
      data (pd.DataFrame): DataFrame
      time_scale: Earliest and Latest start time and end_time  for this day's data
    """
    # 2) A chart layer for the instructor’s time-blocks
    chart_instructor = (
        alt.Chart(data)
        .mark_bar(opacity=0.5)  # highlight color for the chosen instructor
        .encode(
            x=alt.X("sts:T", scale=time_scale),
            x2="ets:T",
            y=alt.Y(
                "location:N",
                title=None,
                sort=room_order,
            ),
            size=alt.Size("credit:Q", title="Credit", scale=alt.Scale(range=[2, 15])),
            color="college:N",
            tooltip=[
                "cid",
                "college",
                "credit",
                "course_title",
                "start_time",
                "end_time",
            ],
        )
    )
    layered_chart = (
        alt.layer(chart_instructor)
        .facet(
            row=alt.Facet(
                "instructor:N",
                sort=instructor_order,
                header=alt.Header(
                    labelAngle=0,
                    labelAnchor="start",
                    labelBaseline="middle",
                    title=None,
                ),
            ),
        )
        .resolve_scale(y="independent")
        .properties(title=title)
    )
    return layered_chart
