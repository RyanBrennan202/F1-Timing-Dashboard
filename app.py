import os
import fastf1
import streamlit as st
import matplotlib.pyplot as plt

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

st.set_page_config(page_title="F1 Timing Dashboard", layout="wide")

st.title("F1 Timing Dashboard")

os.makedirs("cache", exist_ok=True)
fastf1.Cache.enable_cache("cache")

year = st.selectbox("Season", [2024, 2023, 2022])
grand_prix = st.text_input("Grand Prix", "Monaco")
session_type = st.selectbox("Session", ["Qualifying", "Race", "FP1", "FP2", "FP3"])

load_session = st.checkbox("Load Session")

if load_session:
    session = fastf1.get_session(year, grand_prix, session_type)
    session.load()

    laps = session.laps

    timing_table = (
        laps[["Driver", "Team", "Compound", "LapTime", "LapNumber"]]
        .groupby("Driver")
        .agg(
            Team=("Team", "first"),
            Fastest_Lap=("LapTime", "min"),
            Average_Lap=("LapTime", "mean"),
            Total_Laps=("LapNumber", "count"),
            Most_Used_Tyre=("Compound", lambda x: x.mode()[0] if not x.mode().empty else "Unknown"),
        )
        .reset_index()
        .sort_values("Fastest_Lap")
    )

    timing_table["Fastest_Lap"] = timing_table["Fastest_Lap"].apply(format_lap_time) # create correct time format
    timing_table["Average_Lap"] = timing_table["Average_Lap"].apply(format_lap_time) # create correct time format

    timing_table["Most_Used_Tyre"] = timing_table["Most_Used_Tyre"].str.title() # Changes the compound name to lowercase

    timing_table.columns = [
        "Driver",
        "Team",
        "Fastest Lap",
        "Average Lap",
        "Total Laps",
        "Most Used Tyre"
        ] # Naming convention for the column' titles

    st.subheader(f"{year} {grand_prix} - {session_type}")
    st.dataframe(timing_table, use_container_width=True)


    st.subheader("Driver Lap Time Comparison")

    drivers = sorted(laps["Driver"].dropna().unique())

    driver_1 = st.selectbox("Driver 1", drivers)
    driver_2 = st.selectbox("Driver 2", drivers, index=1)
   
    comparison_laps = laps.pick_quicklaps()

    comparison_laps = comparison_laps[
        (comparison_laps["Driver"].isin([driver_1, driver_2])) &
        (comparison_laps["LapTime"].notna())
    ].copy()

    comparison_laps["LapTimeSeconds"] = comparison_laps["LapTime"].dt.total_seconds()

    fig, ax = plt.subplots(figsize=(10, 5))

    for driver in [driver_1, driver_2]:
        driver_laps = comparison_laps[comparison_laps["Driver"] == driver]
        ax.plot(
            driver_laps["LapNumber"],
            driver_laps["LapTimeSeconds"],
            marker="o",
            label=driver
        )

    ax.set_ylim(
        comparison_laps["LapTimeSeconds"].min() - 2,
        comparison_laps["LapTimeSeconds"].max() + 2
    )

    ax.set_title(f"{driver_1} vs {driver_2} Lap Times")
    ax.set_xlabel("Lap Number")
    ax.set_ylabel("Lap Time (seconds)")
    ax.legend()

    col1, col2, col3 = st.columns([1, 3, 1])

    with col2:
        st.pyplot(fig)