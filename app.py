import os
from datetime import datetime

import fastf1
import streamlit as st
import matplotlib.pyplot as plt


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

def create_race_events(laps):
    race_events = []

    status_types = {
        "4": "SAFETY CAR",
        "5": "RED FLAG",
        "6": "VSC"
    }

    for status_code, event_name in status_types.items():
        event_laps = []

        for lap_number in sorted(laps["LapNumber"].dropna().unique()):
            lap_statuses = laps[
                laps["LapNumber"] == lap_number
            ]["TrackStatus"].astype(str)

            if lap_statuses.str.contains(status_code).any():
                event_laps.append(int(lap_number))

        if not event_laps:
            continue
        
        start_lap = event_laps[0]
        previous_lap = event_laps[0]

        for lap_number in event_laps[1:]:
            if lap_number == previous_lap + 1:
                previous_lap = lap_number
            else:
                race_events.append(
                    (start_lap, previous_lap, event_name)
                )

                start_lap = lap_number
                previous_lap = lap_number

        race_events.append(
            (start_lap, previous_lap, event_name)
        )
    
    race_events.sort(key=lambda event: event[0])

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

def create_comparison_graph(laps, driver_1, driver_2):
    comparison_laps = laps.pick_quicklaps()

    comparison_laps = comparison_laps[
        (comparison_laps["Driver"].isin([driver_1, driver_2]))
        & (comparison_laps["LapTime"].notna())
    ].copy()

    comparison_laps["LapTimeSeconds"] = (
        comparison_laps["LapTime"].dt.total_seconds()
    )

    fig, ax = plt.subplots(figsize=(10, 5))

    for driver in [driver_1, driver_2]:
        driver_laps = comparison_laps[
            comparison_laps["Driver"] == driver
        ]

        ax.plot(
            driver_laps["LapNumber"],
            driver_laps["LapTimeSeconds"],
            marker="o",
            label=driver,
        )

    ax.set_ylim(
        comparison_laps["LapTimeSeconds"].min() - 2,
        comparison_laps["LapTimeSeconds"].max() + 2,
    )

    ax.set_title(f"{driver_1} vs {driver_2} Lap Times")
    ax.set_xlabel("Lap Number")
    ax.set_ylabel("Lap Time (seconds)")
    ax.legend()

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
                hide_index=True
            )

            # Race Events
            st.subheader("Race Events")

            race_events = create_race_events(laps)

            events_per_row = 4

            for i in range(0, len(race_events), events_per_row):
                row_events = race_events[i:i + events_per_row]

                columns = st.columns(events_per_row)

                for column, event in zip (columns, row_events):
                    start_lap, end_lap, event_name = event

                    if start_lap == end_lap:
                        lap_text = f"LAP {start_lap}"
                    else:
                        lap_text = f"LAPS {start_lap}-{end_lap}"
                    
                    with column:
                        st.caption(lap_text)
                        st.markdown(f"**{event_name}**")
            
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

        fig, ax = plt.subplots(figsize=(8, 4))

        ax.plot(
            driver_laps["LapNumber"],
            driver_laps["LapTimeSeconds"],
            marker="o"
        )

        ax.set_title(
            f"{driver_names.get(selected_driver, selected_driver)} Lap Times"
        )

        ax.set_xlabel("Lap Number")
        ax.set_ylabel("Lap Time (seconds)")

        col1, col2, col3 = st.columns([1, 2, 1])

        with col2:
            st.pyplot(fig, use_container_width=True)
    
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

    with tyre_tab:
        st.info("Tyre and stint analysis coming next.")

    with comparison_tab:
        st.subheader("Driver Lap Time Comparison")

        drivers = sorted(
            laps["Driver"].dropna().unique()
        )

        driver_1 = st.selectbox(
            "Driver 1",
            drivers
        )

        driver_2 = st.selectbox(
            "Driver 2",
            drivers,
            index=1
        )

        fig = create_comparison_graph(
            laps,
            driver_1,
            driver_2
        )

        col1, col2, col3 = st.columns([1, 3, 1])

        with col2:
            st.pyplot(fig)
    
    