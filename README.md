# F1 Timing & Race Analysis Dashboard

An interactive Formula 1 race analysis application built with Python, Streamlit and FastF1.

The dashboard processes real Formula 1 timing data and presents it through interactive tools for analysing race performance, lap times, tyre strategy, race events and driver comparisons.

I started this project to develop my Python and data analysis skills using a subject I am genuinely interested in. As the project developed, I expanded it from a basic timing dashboard into a more complete race analysis tool, with a focus on turning raw session data into information that is useful and easy to interpret.

## Project Overview

Formula 1 produces a large amount of timing and telemetry-related data during every session. This project uses FastF1 to retrieve and process that data before presenting it through an interactive Streamlit interface.

Users can select a season, Grand Prix and session, with the dashboard automatically loading and analysing the appropriate data.

The application currently supports Formula 1 seasons from 2022 onwards.

## Features

### Race Overview

The race overview provides a quick summary of the selected Grand Prix, including:

- Race winner
- Pole sitter
- Fastest lap
- Biggest position gainer
- Retirements
- Starting and finishing positions
- Fastest and average lap times
- Most-used tyre compound
- Driver classification and status

The aim of the overview is to take a large amount of race data and present the most important information clearly before moving into more detailed analysis.

### Race Events

Track status data is processed to identify significant events during a race, including:

- Safety Cars
- Virtual Safety Cars
- Red Flags

The dashboard determines when these events occurred and displays their lap range and duration.

This provides additional context when analysing changes in lap time, strategy and race position.

### Race Headlines

Relevant news stories are automatically retrieved for the selected Grand Prix.

The news search is generated dynamically using the selected season, event and race date, allowing historical races to display headlines from around their original race weekend rather than current Formula 1 news.

### Lap Analysis

Drivers can be selected individually for detailed lap-by-lap analysis.

For each lap, the dashboard can display:

- Lap time
- Sector 1, Sector 2 and Sector 3 times
- Tyre compound
- Tyre life
- Stint number
- Pit-in and pit-out information
- Track status
- Race events

Interactive Plotly visualisations allow individual laps to be inspected in more detail.

The application also identifies unusually slow laps while prioritising known causes such as pit stops, Safety Cars, Virtual Safety Cars and Red Flags.

### Tyres and Stints

The tyre analysis section converts individual lap data into stint-level information.

For each stint it calculates:

- Tyre compound
- Start lap
- End lap
- Stint length
- Average lap time
- Fastest lap
- Starting and ending tyre life

An interactive strategy timeline provides a visual representation of how a driver's tyre strategy developed throughout the race.

### Driver Comparison

Two drivers can be compared across the same session using an interactive lap-time graph.

The comparison includes additional information for each lap such as:

- Lap time
- Sector times
- Tyre compound
- Tyre life

This makes it possible to investigate differences in pace and how those differences develop throughout a session.

## Technologies

The project currently uses:

- Python
- Streamlit
- FastF1
- Pandas
- Plotly
- Matplotlib
- Google News RSS
- Git and GitHub

## Technical Approach

FastF1 provides the underlying Formula 1 session data. The application processes this data using Python and Pandas before passing the required information to the dashboard and visualisation components.

Reusable functions are used for tasks including:

- Timing data processing
- Lap and sector time formatting
- Race result generation
- Race event detection
- Driver comparison
- News retrieval

Plotly is used for interactive visualisations where detailed inspection of individual data points is useful.

FastF1 session data is cached locally to reduce unnecessary downloads and improve loading performance. Cache files are excluded from version control because they are generated automatically and are not part of the application source.

The project has also required handling incomplete or unavailable session data so that individual missing values do not unnecessarily prevent the rest of the dashboard from operating.

## Example Analysis

The dashboard is designed to help answer questions such as:

- Where did a driver gain or lose time during a race?
- How did two drivers' pace compare throughout a session?
- How did tyre choice and stint length affect race pace?
- When did major race events occur?
- Was an unusually slow lap caused by a pit stop or track-status event?
- How did a driver's strategy develop throughout the race?

The intention is not simply to display timing data, but to provide context that makes the data easier to analyse.

## Running the Project

Clone the repository:

```bash
git clone https://github.com/RyanBrennan202/F1-Timing-Dashboard.git
```

Move into the project directory:

```bash
cd F1-Timing-Dashboard
```

Install the required packages:

```bash
pip install streamlit fastf1 pandas plotly matplotlib
```

Run the application:

```bash
python -m streamlit run app.py
```

Streamlit will then provide the local address for the dashboard.

## Project Structure

```text
F1-Timing-Dashboard/
|
|-- app.py
|-- README.md
|-- .gitignore
|
`-- cache/              Generated locally and excluded from Git
```

## Development

This is an ongoing personal project and has been developed incrementally as I have learned more about Formula 1 data analysis and software development.

During development I have worked through issues involving data cleaning, missing values, session differences, visualisation design, caching, Git version control and presenting large datasets in a useful format.

The project has also evolved based on analysing the usefulness of each feature rather than simply adding more data. For example, the lap analysis and tyre strategy sections are designed to provide different views of the same race: one focusing on individual lap performance and the other on the wider strategic picture.

## Future Development

Areas I would like to continue developing include:

- More detailed pit-stop and strategy analysis
- Tyre degradation analysis
- Weather data integration
- Additional race-event context
- Improved handling of unusual session conditions
- More detailed team and driver comparisons
- Circuit-specific analysis
- Further performance and usability improvements

## Screenshots

Overview Page
<img width="2387" height="1185" alt="image" src="https://github.com/user-attachments/assets/42f7f0a7-3063-4265-a600-bed8b4bb97f1" />

<img width="2467" height="1221" alt="image" src="https://github.com/user-attachments/assets/742ac913-da9c-42ac-ba8f-c751c58fadd6" />

Individual Lap Analysis
<img width="2460" height="1199" alt="image" src="https://github.com/user-attachments/assets/25c4ed08-95f7-4bbc-9ca9-4a04e1e60cf8" />

<img width="2398" height="1179" alt="image" src="https://github.com/user-attachments/assets/de08b7ad-8f00-4f71-9515-68bd574bb9e0" />

<img width="2417" height="1065" alt="image" src="https://github.com/user-attachments/assets/6d8d1dc0-6eff-4a4b-b597-ace461fd9fd3" />

Tyres & Stints Page

<img width="2380" height="1147" alt="image" src="https://github.com/user-attachments/assets/04a329d3-4da3-4732-8fc4-9a0388ca8217" />

Driver Comparison Graph

<img width="2425" height="1128" alt="image" src="https://github.com/user-attachments/assets/756e57d7-3b47-46dc-a748-e686725d084a" />



## Author

Ryan Brennan

Computer Science student.
