import os
from datetime import datetime, timedelta
from urllib.parse import quote_plus
from urllib.request import urlopen, Request
import xml.etree.ElementTree as ET

import pandas as pd
import fastf1
import streamlit as st
import matplotlib.pyplot as plt
import plotly.express as px # upgrade from matplot as I wanted a more complex in-depth graph
import plotly.graph_objects as go


# -----------------------------
# Helper Functions
# -----------------------------

def format_lap_time(time):
    if time is None or str(time) == "NaT":
        return "No Time"

    try:
        total_seconds = time.total_seconds()
        minutes = int(total_seconds // 60)
        seconds = total_seconds % 60
        return f"{minutes}:{seconds:06.3f}"
    except:
        return "No Time"

def format_sector_time(time):
    if time is None or str(time) == "NaT":
        return "No Time"

    try:
        return f"{time.total_seconds():.3f}"
    except:
        return "No Time"

@st.cache_data(ttl=3600)
def get_race_news(year, grand_prix, race_date, max_articles=4):

    # Search from two days before the race
    # until two days after the race
    start_date = race_date - timedelta(days=2)
    end_date = race_date + timedelta(days=3)

    query = (
        f'"{grand_prix}" Formula 1 {year} '
        f'after:{start_date.strftime("%Y-%m-%d")} '
        f'before:{end_date.strftime("%Y-%m-%d")}'
    )

    encoded_query = quote_plus(query)

    url = (
        "https://news.google.com/rss/search?"
        f"q={encoded_query}"
        "&hl=en-GB"
        "&gl=GB"
        "&ceid=GB:en"
    )

    try:
        request = Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        with urlopen(request, timeout=10) as response:
            xml_data = response.read()

        root = ET.fromstring(xml_data)

        articles = []

        for item in root.findall("./channel/item"):

            title = item.findtext("title", "").strip()
            link = item.findtext("link", "").strip()
            published = item.findtext("pubDate", "").strip()

            source_element = item.find("source")

            if source_element is not None:
                source = source_element.text or "Unknown Source"
            else:
                source = "Unknown Source"

            # Google News often adds " - Source" to the title
            source_suffix = f" - {source}"

            if title.endswith(source_suffix):
                title = title[:-len(source_suffix)]

            articles.append(
                {
                    "title": title,
                    "source": source,
                    "published": published,
                    "link": link
                }
            )

            if len(articles) >= max_articles:
                break

        return articles

    except Exception:
        return []

def get_lap_event(row):
    events = []

    # Pit events
    if str(row["PitInTime"]) != "NaT":
        events.append("PIT IN")

    if str(row["PitOutTime"]) != "NaT":
        events.append("PIT OUT")
    
    # Track status events
    track_status = str(row["TrackStatus"])

    if "5" in track_status:
        events.append("RED FLAG")
    
    if "4" in track_status:
        events.append("SAFETY CAR")
    
    if "6" in track_status:
        events.append("VSC")

    if "7" in track_status:
        events.append("VSC ENDING")
    
    if events:
        return "  •  ".join(events)
    
    return ""

def get_lap_reason(row, typical_lap_time):

    # Known events always take priority
    if str(row["PitOutTime"]) != "NaT":
        return "PIT OUT / OUT LAP"

    if str(row["PitInTime"]) != "NaT":
        return "PIT IN"

    track_status = str(row["TrackStatus"])

    if "5" in track_status:
        return "RED FLAG"

    if "4" in track_status:
        return "SAFETY CAR"

    if "6" in track_status:
        return "VSC"

    # No known event - check whether the lap is unusually slow
    if row["LapTimeSeconds"] > typical_lap_time * 1.12:
        return "Unusually Slow Lap"

    return "Normal Racing Lap"

def create_race_events(session):
    race_events = []

    track_status = session.track_status.copy()
    laps = session.laps.copy()

    status_types = {
        "4": "SAFETY CAR",
        "5": "RED FLAG",
        "6": "VSC"
    }

    def get_lap_number(event_time):
        active_laps = laps[
            (laps["LapStartTime"] <= event_time)
            & (laps["Time"] >= event_time)
        ]

        if not active_laps.empty:
            return int(active_laps["LapNumber"].max())

            return None

    for i, row in track_status.iterrows():
        status_code = str(row["Status"])

        if status_code not in status_types:
            continue

        start_time = row["Time"]
        start_lap = get_lap_number(start_time)

        # Find the next track-status change
        next_rows = track_status[
            track_status["Time"] > start_time
        ]

        if not next_rows.empty:
            end_time = next_rows.iloc[0]["Time"]
            end_lap = get_lap_number(end_time)
        else:
            end_lap = int(laps["LapNumber"],max())
        
        if start_lap is None:
            continue
        
        if end_lap is None:
            end_lap = start_lap

        race_events.append(
            {
                "start_lap": start_lap,
                "end_lap": end_lap,
                "event": status_types[status_code]
            }
        )

    return race_events

def create_timing_table(laps, session):
    timing_table = (
        laps[["Driver", "Team", "Compound", "LapTime", "LapNumber"]]
        .groupby("Driver")
        .agg(
            Team=("Team", "first"),
            Fastest_Lap=("LapTime", "min"),
            Average_Lap=("LapTime", "mean"),
            Total_Laps=("LapNumber", "count"),
            Most_Used_Tyre=(
                "Compound",
                lambda x: x.mode()[0] if not x.mode().empty else "Unknown"
            ),
        )
        .reset_index()
        .sort_values("Fastest_Lap")
    )

    driver_names = dict(
        zip(
            session.results["Abbreviation"],
            session.results["FullName"]
        )
    )

    timing_table["Driver"] = timing_table["Driver"].map(driver_names)

    timing_table["Fastest_Lap"] = timing_table["Fastest_Lap"].apply(format_lap_time)
    timing_table["Average_Lap"] = timing_table["Average_Lap"].apply(format_lap_time)
    timing_table["Most_Used_Tyre"] = timing_table["Most_Used_Tyre"].str.title()

    timing_table.columns = [
        "Driver",
        "Team",
        "Fastest Lap",
        "Average Lap",
        "Total Laps",
        "Most Used Tyre",
    ]

    return timing_table

def create_race_results(session):
    results = session.results.copy()

    race_results = results[
        ["FullName", "TeamName", "GridPosition", "Position", "Status"]
    ].copy()

    race_results["PositionsGained"] = (
        race_results["GridPosition"] - race_results["Position"]
    )

    race_results.columns = [
        "Driver",
        "Team",
        "Grid",
        "Finish",
        "Status",
        "Positions Gained"
    ]

    return race_results

def create_qualifying_results(session):
    results = session.results.copy()

    qualifying_results = results[
        [
            "Position",
            "Abbreviation",
            "TeamName",
            "Q1",
            "Q2",
            "Q3"
        ]
    ].copy()

    qualifying_results["Q1"] = qualifying_results["Q1"].apply(format_lap_time)
    qualifying_results["Q2"] = qualifying_results["Q2"].apply(format_lap_time)
    qualifying_results["Q3"] = qualifying_results["Q3"].apply(format_lap_time)

    qualifying_results.columns = [
        "Position",
        "Driver",
        "Team",
        "Q1",
        "Q2",
        "Q3"
    ]

    return qualifying_results

def create_comparison_graph(laps, driver_1, driver_2, driver_names):
    comparison_laps = laps[
        (laps["Driver"].isin([driver_1, driver_2]))
        & (laps["LapTime"].notna())
    ].copy()

    comparison_laps["LapTimeSeconds"] = (
        comparison_laps["LapTime"].dt.total_seconds()
    )

    comparison_laps["Lap Time"] = (
        comparison_laps["LapTime"].apply(format_lap_time)
    )

    comparison_laps["Sector 1"] = (
        comparison_laps["Sector1Time"].apply(format_sector_time)
    )

    comparison_laps["Sector 2"] = (
        comparison_laps["Sector2Time"].apply(format_sector_time)
    )

    comparison_laps["Sector 3"] = (
        comparison_laps["Sector3Time"].apply(format_sector_time)
    )

    comparison_laps["Tyre"] = (
        comparison_laps["Compound"].fillna("Unknown")
    )

    comparison_laps["Tyre Life"] = (
        comparison_laps["TyreLife"].fillna(0)
    )

    comparison_laps["Driver Name"] = (
        comparison_laps["Driver"].map(driver_names)
    )

    fig = px.line(
        comparison_laps,
        x="LapNumber",
        y="LapTimeSeconds",
        color="Driver Name",
        markers=True,
        title=(
            f"{driver_names.get(driver_1, driver_1)} vs "
            f"{driver_names.get(driver_2, driver_2)}"
        ),
        labels={
            "LapNumber": "Lap",
            "LapTimeSeconds": "Lap Time",
            "Driver Name": "Driver"
        },
        custom_data=[
            "Driver Name",
            "Lap Time",
            "Tyre",
            "Tyre Life",
            "Sector 1",
            "Sector 2",
            "Sector 3"
        ]
    )

    fig.update_traces(
        hovertemplate=
            "<b>%{customdata[0]}</b><br>"
            "Lap %{x}<br>"
            "Lap Time: %{customdata[1]}<br>"
            "Tyre: %{customdata[2]}<br>"
            "Tyre Life: %{customdata[3]} laps<br>"
            "Sector 1: %{customdata[4]}<br>"
            "Sector 2: %{customdata[5]}<br>"
            "Sector 3: %{customdata[6]}"
            "<extra></extra>"
    )

    fig.update_layout(
        hovermode="closest",
        xaxis_title="Lap",
        yaxis_title="Lap Time",
        height=550,
        legend_title="Driver",
        margin=dict(
            l=60,
            r=30,
            t=70,
            b=60
        )
    )

    # Format Y-axis as minutes:seconds
    min_time = comparison_laps["LapTimeSeconds"].min()
    max_time = comparison_laps["LapTimeSeconds"].max()

    tick_start = int(min_time // 5) * 5
    tick_end = int(max_time // 5 + 1) * 5

    tick_values = list(
        range(tick_start, tick_end + 1, 5)
    )

    tick_labels = [
        f"{int(seconds // 60)}:{int(seconds % 60):02d}"
        for seconds in tick_values
    ]

    fig.update_yaxes(
        tickmode="array",
        tickvals=tick_values,
        ticktext=tick_labels
    )

    return fig


# -----------------------------
# App Setup
# -----------------------------

st.set_page_config(
    page_title="F1 Timing Dashboard",
    layout="wide"
)

st.title("F1 Timing Dashboard")

os.makedirs("cache", exist_ok=True)
fastf1.Cache.enable_cache("cache")


# -----------------------------
# User Inputs
# -----------------------------

current_year = datetime.now().year

year = st.selectbox(
    "Season",
    list(range(current_year, 2021, -1))
)

grand_prix = None

if year is not None:
    schedule = fastf1.get_event_schedule(year)

    race_schedule = schedule[
        schedule["RoundNumber"] > 0
    ].copy()

    if year == datetime.now().year:
        today = datetime.now().date()

        race_schedule = race_schedule[
            race_schedule["EventDate"].dt.date <= today
        ]

    grand_prix = st.selectbox(
        "Grand Prix",
        race_schedule["EventName"].tolist(),
        index=None,
        placeholder="Select Grand Prix"
    )
session_type = None

if grand_prix is not None:
    session_type = st.selectbox(
        "Session",
        ["Race", "Qualifying", "FP1", "FP2", "FP3"],
        index=None,
        placeholder="Select Session"
    )




# -----------------------------
# Load F1 Data
# -----------------------------

if grand_prix is not None and session_type is not None:
    session = fastf1.get_session(
        year,
        grand_prix,
        session_type
    )

    session.load()

    race_date = session.event["EventDate"].date()

    laps = session.laps

    overview_tab, lap_tab, tyre_tab, comparison_tab = st.tabs([
        "Overview",
        "Lap Analysis",
        "Tyres & Stints",
        "Driver Comparison"
    ])

    # -----------------------------
    # Timing Table
    # -----------------------------

    with overview_tab:
        timing_table = create_timing_table(laps, session)

        st.subheader(
            f"{year} {grand_prix} - {session_type}"
        )

        if session_type == "Race":
            race_results = create_race_results(session)

            # ---------------------------------
            # Race Headline Stats
            # ---------------------------------

            results = session.results.copy()

            # Race Winner
            winner = results.loc[
                results["Position"] == 1
            ].iloc[0]

            winner_name = winner["FullName"]
            winner_team = winner["TeamName"]

            # Fastest Lap
            fastest_lap = laps.pick_fastest()

            driver_names = dict(
                zip(
                    session.results["Abbreviation"],
                    session.results["FullName"]
                )
            )

            fastest_driver = driver_names.get(
                fastest_lap["Driver"],
                fastest_lap["Driver"]
            )

            fastest_lap_time = format_lap_time(
                fastest_lap["LapTime"]
            )

            # Pole Sitter
            pole = results.loc[
                results["GridPosition"] == 1
            ].iloc[0]

            pole_name = pole["FullName"]
            pole_team = pole["TeamName"]

            # Biggest Gainer
            biggest_gainer = race_results.loc[
                race_results["Positions Gained"].idxmax()
            ]

            gainer_name = biggest_gainer["Driver"]
            gainer_grid = int(biggest_gainer["Grid"])
            gainer_finish = int(biggest_gainer["Finish"])
            gainer_positions = int(
                biggest_gainer["Positions Gained"]
            )

            # Retirements
            retirements = results[
                results["Status"] == "Retired"
            ].shape[0]

            # -----------------------------
            # Display Race Headline Stats
            # -----------------------------

            stats = [
                ("🏆 Race Winner", winner_name, winner_team),
                ("⚡ Fastest Lap", fastest_driver, fastest_lap_time),
                ("🥇 Pole Sitter", pole_name, pole_team),
                (
                    "📈 Biggest Gainer",
                    gainer_name,
                    f"P{gainer_grid} → P{gainer_finish} (+{gainer_positions})"
                ),
                ("🚫 Retirements", str(retirements), "")
            ]

            columns = st.columns(5)

            for column, stat in zip(columns, stats):
                label, main_value, sub_value = stat

                with column:
                    st.markdown(
                        f"""<div style="border:1px solid #343434; border-radius:12px; padding:14px 16px; background-color:#161616; min-height:105px;">
                <div style="font-size:12px; color:#b5b5b5; margin-bottom:8px; white-space:nowrap;">{label}</div>
                <div style="font-size:20px; font-weight:700; line-height:1.2; margin-bottom:7px;">{main_value}</div>
                <div style="font-size:12px; color:#8fd19e;">{sub_value}</div>
                </div>""",
                        unsafe_allow_html=True
                    )

            st.markdown(
                "<hr style='margin: 20px 0; border: none; border-top: 1px solid #343434;'>",
                unsafe_allow_html=True
            )

            overview_table = race_results.merge(
                timing_table,
                on=["Driver", "Team"],
                how="left"
            )

            overview_table = overview_table[
                [
                    "Finish",
                    "Driver",
                    "Team",
                    "Grid",
                    "Positions Gained",
                    "Fastest Lap",
                    "Average Lap",
                    "Most Used Tyre",
                    "Status"
                ]
            ]

            st.dataframe(
                overview_table,
                use_container_width=True,
                hide_index=True,
                height=(len(overview_table) + 1) * 35 + 3
            )

            # Race Events
            st.subheader("Race Events")

            race_events = create_race_events(session)

            events_per_row = 4

            for i in range(0, len(race_events), events_per_row):
                row_events = race_events[i:i + events_per_row]

                columns = st.columns(len(row_events))

                for column, event in zip(columns, row_events):
                    start_lap = event["start_lap"]
                    end_lap = event["end_lap"]
                    event_name = event["event"]

                    event_descriptions = {
                        "SAFETY CAR": "Safety Car Deployed",
                        "RED FLAG": "Session suspended",
                        "VSC": "Race neutralised under Virtual Safety Car"
                    }

                    event_description = event_descriptions.get(
                        event_name,
                        ""
                    )

                    event_duration = end_lap - start_lap + 1

                    if event_duration == 1:
                        duration_text = ""
                    else:
                        duration_text = f"  •  {event_duration} laps"

                    if start_lap == end_lap:
                        lap_text = f"LAP {start_lap}"
                    else:
                        lap_text = f"LAPS {start_lap}-{end_lap}"

                    event_colours = {
                        "SAFETY CAR": "#FFD700",
                        "RED FLAG": "#FF4B4B",
                        "VSC": "#FFB000"
                    }

                    event_colour = event_colours.get(
                        event_name,
                        "#FFFFFF"
                    )

                    with column:
                        st.markdown(
                            f"""
                    <div style="border:1px solid #3a3a3a; border-radius:12px; padding:16px; margin-bottom:12px; background-color:#161616;">
                        <div style="font-size:12px; color:#9a9a9a; margin-bottom:5px;">
                            {lap_text}{duration_text}
                        </div>
                        <div style="font-size:18px; font-weight:700; color:{event_colour}; margin-bottom:6px;">
                            {event_name}
                        </div>
                        <div style="font-size:13px; color:#c7c7c7;">
                            {event_description}
                        </div>
                    </div>
                            """,
                            unsafe_allow_html=True
                        )
    
            # -----------------------------
            # Race Headlines
            # -----------------------------

            st.markdown(
                "<hr style='margin: 25px 0; border: none; border-top: 1px solid #343434;'>",
                unsafe_allow_html=True
            )

            st.subheader("Race Headlines")

            race_news = get_race_news(
                year,
                grand_prix,
                race_date
            )

            if race_news:

                news_columns = st.columns(len(race_news))

                for column, article in zip(news_columns, race_news):

                    with column:

                        with st.container(border=True):

                            # Headline
                            st.markdown(
                                f"""
                                <div style="
                                    min-height: 95px;
                                    font-size: 16px;
                                    font-weight: 700;
                                    line-height: 1.45;
                                ">
                                    {article['title']}
                                </div>
                                """,
                                unsafe_allow_html=True
                            )

                            # Publisher
                            st.markdown(
                                f"""
                                <div style="
                                    min-height: 32px;
                                    font-size: 13px;
                                    color: #9a9a9a;
                                    margin-top: 10px;
                                ">
                                    📰 &nbsp; {article['source']}
                                </div>
                                """,
                                unsafe_allow_html=True
                            )

                            # Spacer so every card lines up
                            st.markdown(
                                "<div style='height: 8px;'></div>",
                                unsafe_allow_html=True
                            )

                            st.link_button(
                                "Read Article",
                                article["link"],
                                use_container_width=True
                            )

            else:

                st.info(
                    "No race headlines were found for this event."
                )
            
        elif session_type == "Qualifying":
            qualifying_results = create_qualifying_results(session)

            st.dataframe(
                qualifying_results,
                use_container_width=True,
                hide_index=True
            )

        else:
            st.dataframe(
                timing_table,
                use_container_width=True,
                hide_index=True
            )


    # -----------------------------
    # Driver Comparison
    # -----------------------------

    with lap_tab:
        st.subheader("Lap Analysis")

        driver_names = dict(
            zip(
                session.results["Abbreviation"],
                session.results["FullName"]
            )
        )

        drivers = sorted(
            laps["Driver"].dropna().unique()
        )

        selected_driver = st.selectbox(
            "Driver",
            drivers,
            format_func=lambda x: driver_names.get(x, x),
            key="lap_analysis_driver"
        )

        driver_laps = laps[
            (laps["Driver"] == selected_driver)
            & (laps["LapTime"].notna())
        ].copy()

        driver_laps["LapTimeSeconds"] = (
            driver_laps["LapTime"].dt.total_seconds()
        )

        driver_laps["Lap Time"] = driver_laps["LapTime"].apply(format_lap_time)
        driver_laps["Sector 1"] = driver_laps["Sector1Time"].apply(format_sector_time)
        driver_laps["Sector 2"] = driver_laps["Sector2Time"].apply(format_sector_time)
        driver_laps["Sector 3"] = driver_laps["Sector3Time"].apply(format_sector_time)

        driver_laps["Tyre"] = driver_laps["Compound"].fillna("Unknown")
        driver_laps["Tyre Life"] = driver_laps["TyreLife"].fillna(0)
        driver_laps["Stint Number"] = driver_laps["Stint"].fillna(0)
        typical_lap_time = driver_laps["LapTimeSeconds"].median()

        driver_laps["Reason"] = driver_laps.apply(
            lambda row: get_lap_reason(row, typical_lap_time),
            axis=1
        )
        

        fig = px.line(
            driver_laps,
            x="LapNumber",
            y="LapTimeSeconds",
            markers=True,
            title=f"{driver_names.get(selected_driver, selected_driver)} Lap Times",
            labels={
                "LapNumber": "Lap",
                "LapTimeSeconds": "Lap Time"
            },
            custom_data=[
                "Lap Time",
                "Tyre",
                "Tyre Life",
                "Stint Number",
                "Sector 1",
                "Sector 2",
                "Sector 3",
                "Reason"
            ]
        )

        fig.update_traces(
            hovertemplate=
                "<b>Lap %{x}</b><br>"
                "Lap Time: %{customdata[0]}<br>"
                "Tyre: %{customdata[1]}<br>"
                "Tyre Life: %{customdata[2]} laps<br>"
                "Stint: %{customdata[3]}<br>"
                "Sector 1: %{customdata[4]}<br>"
                "Sector 2: %{customdata[5]}<br>"
                "Sector 3: %{customdata[6]}<br>"
                "<br>"
                "<b>Reason: %{customdata[7]}</b>"
                "<extra></extra>"
        )

        fig.update_layout(
            hovermode="closest",
            xaxis_title="Lap",
            yaxis_title="Lap Time",
            height=500,
            margin=dict(
                l=60,
                r=30,
                t=70,
                b=60
            )
        )

        # Format Y-axis as minutes:seconds
        min_time = driver_laps["LapTimeSeconds"].min()
        max_time = driver_laps["LapTimeSeconds"].max()

        # Only format the Y-axis if valid lap times exist
        if not driver_laps.empty and pd.notna(min_time) and pd.notna(max_time):

            tick_start = int(min_time // 5) * 5
            tick_end = int(max_time // 5 + 1) * 5

            tick_values = list(
                range(tick_start, tick_end + 1, 5)
            )

            tick_labels = [
                f"{int(seconds // 60)}:{int(seconds % 60):02d}"
                for seconds in tick_values
            ]

            fig.update_yaxes(
                tickmode="array",
                tickvals=tick_values,
                ticktext=tick_labels
            )

        # All of this above is driver selection and graph

        st.subheader("Lap Breakdown")

        all_driver_laps = laps[
            laps["Driver"] == selected_driver
        ].copy()

        lap_breakdown = all_driver_laps[
            [
                "LapNumber",
                "LapTime",
                "Sector1Time",
                "Sector2Time",
                "Sector3Time",
                "Compound",
                "TyreLife",
                "Stint",
                "PitInTime",
                "PitOutTime",
                "TrackStatus"
            ]
        ].copy()

        lap_breakdown["Event"] = lap_breakdown.apply(
            get_lap_event,
            axis=1
        )

        previous_compound = lap_breakdown["Compound"].shift(1)

        tyre_changed = (
            lap_breakdown["Compound"].notna()
            & previous_compound.notna()
            & (lap_breakdown["Compound"] != previous_compound)
        )

        lap_breakdown.loc[tyre_changed, "Event"] = (
             lap_breakdown.loc[tyre_changed, "Event"]
             + "  •  TYRE CHANGE: "
             + previous_compound[tyre_changed]
             + " → "
             + lap_breakdown.loc[tyre_changed, "Compound"]
        )

        lap_breakdown["LapNumber"] = lap_breakdown["LapNumber"].astype(int)

        lap_breakdown["LapTime"] = lap_breakdown["LapTime"].apply(format_lap_time)
        lap_breakdown["Sector1Time"] = lap_breakdown["Sector1Time"].apply(format_sector_time)
        lap_breakdown["Sector2Time"] = lap_breakdown["Sector2Time"].apply(format_sector_time)
        lap_breakdown["Sector3Time"] = lap_breakdown["Sector3Time"].apply(format_sector_time)

        lap_breakdown = lap_breakdown[
            [
                "LapNumber",
                "LapTime",
                "Sector1Time",
                "Sector2Time",
                "Sector3Time",
                "Compound",
                "TyreLife",
                "Stint",
                "Event"
            ]
        ]

        lap_breakdown.columns = [
            "Lap",
            "Lap Time",
            "Sector 1",
            "Sector 2",
            "Sector 3",
            "Tyre",
            "Tyre Life",
            "Stint",
            "Event"
        ]

        st.dataframe(
            lap_breakdown,
            use_container_width=True,
            hide_index=True,
            height=(len(lap_breakdown) + 1) * 35 + 3,
            column_config={
                "Lap": st.column_config.NumberColumn(
                    "Lap",
                    width="small"
                ),
                "Tyre Life": st.column_config.NumberColumn(
                    "Tyre Life",
                    width="small"
                ),
                "Stint": st.column_config.NumberColumn(
                    "Stint",
                    width="small"
                ),
                "Event": st.column_config.TextColumn(
                    "Event",
                    width="large"
                ),                
            }
        )

        st.markdown(
            "<hr style='margin: 25px 0; border: none; border-top: 1px solid #343434;'>",
            unsafe_allow_html=True
        )

        st.subheader("Lap Time Graph")

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    with tyre_tab:
        st.subheader("Tyres & Stints")

        tyre_driver = st.selectbox(
            "Driver",
            drivers,
            format_func=lambda x: driver_names.get(x, x),
            key="tyre_driver"
        )

        tyre_driver_laps = laps[
            laps["Driver"] == tyre_driver
        ].copy()

        stint_summary = (
            tyre_driver_laps
            .dropna(subset=["Stint", "Compound"])
            .groupby("Stint")
            .agg(
                Compound=("Compound", "first"),
                Start_Lap=("LapNumber", "min"),
                End_Lap=("LapNumber", "max"),
                Laps=("LapNumber", "count"),
                Average_Lap=("LapTime", "mean"),
                Fastest_Lap=("LapTime", "min"),
                Start_Tyre_Life=("TyreLife", "min"),
                End_Tyre_Life=("TyreLife", "max")
            )
            .reset_index()
        )

        stint_summary["Average_Lap"] = (
            stint_summary["Average_Lap"].apply(format_lap_time)
        )

        stint_summary["Fastest_Lap"] = (
            stint_summary["Fastest_Lap"].apply(format_lap_time)
        )

        stint_summary["Start_Lap"] = (
            stint_summary["Start_Lap"].astype(int)
        )

        stint_summary["End_Lap"] = (
            stint_summary["End_Lap"].astype(int)
        )

        stint_summary["Laps"] = (
            stint_summary["Laps"].astype(int)
        )

        stint_summary.columns = [
            "Stint",
            "Compound",
            "Start Lap",
            "End Lap",
            "Laps",
            "Average Lap",
            "Fastest Lap",
            "Starting Tyre Life",
            "Ending Tyre Life"
        ]

        st.dataframe(
            stint_summary,
            use_container_width=True,
            hide_index=True
        )

        st.markdown(
            "<hr style='margin: 25px 0; border: none; border-top: 1px solid #343434;'>",
            unsafe_allow_html=True
        )

        st.subheader("Race Strategy")

        # F1 tyre compound colours
        compound_colours = {
            "SOFT": "#FF3333",
            "MEDIUM": "#FFD700",
            "HARD": "#F2F2F2",
            "INTERMEDIATE": "#39B54A",
            "WET": "#2D7DD2"
        }

        strategy_fig = go.Figure()

        compound_colours = {
            "SOFT": "#FF3333",
            "MEDIUM": "#FFD700",
            "HARD": "#F2F2F2",
            "INTERMEDIATE": "#39B54A",
            "WET": "#2D7DD2"
        }

        stint_labels = []

        for _, stint in stint_summary.iterrows():

            stint_number = int(stint["Stint"])
            compound = str(stint["Compound"]).upper()

            start_lap = int(stint["Start Lap"])
            end_lap = int(stint["End Lap"])

            stint_label = f"Stint {stint_number} · {compound}"
            stint_labels.append(stint_label)

            colour = compound_colours.get(
                compound,
                "#888888"
            )

            strategy_fig.add_trace(
                go.Scatter(
                    x=[start_lap, end_lap],
                    y=[stint_label, stint_label],

                    mode="lines+markers+text",

                    line=dict(
                        width=12,
                        color=colour
                    ),

                    marker=dict(
                        size=9,
                        color=colour
                    ),

                    text=[
                        f"L{start_lap}",
                        f"L{end_lap}"
                    ],

                    textposition=[
                        "middle left",
                        "middle right"
                    ],

                    name=compound,

                    customdata=[
                        [
                            stint_number,
                            compound,
                            start_lap,
                            end_lap,
                            int(stint["Laps"]),
                            stint["Average Lap"],
                            stint["Fastest Lap"]
                        ],
                        [
                            stint_number,
                            compound,
                            start_lap,
                            end_lap,
                            int(stint["Laps"]),
                            stint["Average Lap"],
                            stint["Fastest Lap"]
                        ]
                    ],

                    hovertemplate=
                        "<b>Stint %{customdata[0]}</b><br>"
                        "Compound: %{customdata[1]}<br>"
                        "Laps: %{customdata[2]} - %{customdata[3]}<br>"
                        "Stint Length: %{customdata[4]} laps<br>"
                        "Average Lap: %{customdata[5]}<br>"
                        "Fastest Lap: %{customdata[6]}"
                        "<extra></extra>",

                    showlegend=False
                )
            )

        strategy_fig.update_layout(
            height=360,

            title=dict(
                text=driver_names.get(
                    tyre_driver,
                    tyre_driver
                ),
                x=0.01
            ),

            xaxis_title="Lap",
            yaxis_title="",

            margin=dict(
                l=130,
                r=60,
                t=70,
                b=60
            )
        )

        strategy_fig.update_xaxes(
            dtick=5,
            range=[
                0,
                int(stint_summary["End Lap"].max()) + 2
            ],
            showgrid=True,
            gridcolor="rgba(255,255,255,0.08)"
        )

        strategy_fig.update_yaxes(
            categoryorder="array",
            categoryarray=stint_labels,
            autorange="reversed",
            showgrid=False
        )

        st.plotly_chart(
            strategy_fig,
            use_container_width=True
        )

    with comparison_tab:
        st.subheader("Driver Lap Time Comparison")

        drivers = sorted(
            laps["Driver"].dropna().unique()
        )

        driver_1 = st.selectbox(
            "Driver 1",
            drivers,
            format_func=lambda x: driver_names.get(x, x)
        )

        driver_2 = st.selectbox(
            "Driver 2",
            drivers,
            index=1,
            format_func=lambda x: driver_names.get(x, x)
        )

        fig = create_comparison_graph(
            laps,
            driver_1,
            driver_2,
            driver_names
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )
    
    