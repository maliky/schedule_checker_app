import altair as alt
from class_schedule.helper import process_schedule
import pandas as pd

domain = {"start": {}, "end": {}}

room_order = alt.EncodingSortField(field="location", order="ascending")
instructor_order = alt.EncodingSortField(field="instructor", order="ascending")


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
    day_gps = data.groupby(["weekday"]).groups

    instructor_order_college = (
        data.sort_values(by=["college", "instructor"])
    ).instructor
    colleges = list(data.college.unique())
    weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

    clg_instructor_charts = []
    day_room_charts = []

    for day in weekdays:

        day_df = data.loc[day_gps[day]]

        time_scale = alt.Scale(domain=[day_df.sts.min(), day_df.ets.max()])

        day_room_chart = make_day_room_chart(
            day_df, time_scale, title=day, sort=instructor_order_college
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

        clg_instructor_chart = alt.vconcat(*clg_day_charts).properties(title=day)
        clg_instructor_charts.append(clg_instructor_chart)
        # college_chart.save(f"{day}-colleges_chart.html")

        instructor_final_chart = alt.hconcat(*clg_instructor_charts)

    instructor_final_chart.save(f"{dout}/instructor_final_chart.html")

    room_final_chart = alt.hconcat(*day_room_charts)
    room_final_chart.save(f"{dout}/room_final_chart.html")

    pass


def make_day_room_chart(
    day_data_df: pd.DataFrame, time_scale: alt.Scale, title: str, sort
):
    # A chart layer for the room occupation
    chart_rooms = (
        alt.Chart(day_data_df)
        .mark_bar(opacity=0.5)
        .encode(
            x=alt.X("sts:T", scale=time_scale),
            x2="ets:T",
            y=alt.Y("instructor:N", title=None, sort=sort),
            size="credit:N",
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
        alt.layer(chart_rooms)
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
            size="credit:N",
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
