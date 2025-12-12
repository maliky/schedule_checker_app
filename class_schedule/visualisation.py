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
    data = data.copy()
    # > Do I have unknown college ?
    # > give me the cmd to list the lines with na or unknown
    data.loc[:, "college"] = data.college.fillna("Unknown")

    day_gps = data.groupby(["weekday"]).groups

    colleges = sorted(data.college.unique())
    weekdays = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]

    clg_instructor_charts = []
    day_room_charts = []

    # Reference: Altair parameter bindings allow dropdown filters (see official docs
    # https://altair-viz.github.io/user_guide/parameters.html#binding-parameters-to-input-elements)
    # college_param = alt.param(
    #     "College",
    #     bind=alt.binding_select(options=["All"] + colleges),
    #     value="All",
    # )

    for day in weekdays:

        day_df = data.loc[day_gps[day]]

        # Reference: Explicit time-scale domains keep per-day charts aligned
        # (Altair scale docs: https://altair-viz.github.io/user_guide/customization.html#scales)
        time_scale = alt.Scale(domain=[day_df.sts.min(), day_df.ets.max()], nice=False)

        day_room_chart = make_day_room_chart(day_df, time_scale, title=day)
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

    instructor_final_chart = instructor_final_chart.resolve_scale(x="independent")

    instructor_final_chart.save(f"{dout}/instructor_final_chart.html")

    room_final_chart = alt.hconcat(*day_room_charts).resolve_scale(x="independent")
    room_final_chart.save(f"{dout}/room_final_chart.html")

    pass


def make_day_room_chart(
    day_data_df: pd.DataFrame,
    time_scale: alt.Scale,
    title: str,
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
    ).properties(title=title)
    return chart_rooms


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
