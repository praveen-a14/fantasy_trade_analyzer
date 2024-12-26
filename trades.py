import requests
import pandas as pd
import os
import json
import streamlit as st
from collections import defaultdict
import nfl_data_py as nfl

# Define file paths
player_data_file = "players_data.json"
transaction_data_file = "transactions_data.json"
stats_data_file = "stats_data.json"

urls = {
        2020: "https://api.sleeper.app/v1/league/634178924393340928/",
        2021: "https://api.sleeper.app/v1/league/649911222413668352/",
        2022: "https://api.sleeper.app/v1/league/784354886748897280/",
        2023: "https://api.sleeper.app/v1/league/928374253781659648/",
        2024: "https://api.sleeper.app/v1/league/1049429880049373184/",
}

picks_urls = {
    2021: "https://api.sleeper.app/v1/draft/649911222413668353/picks",
    2022: "https://api.sleeper.app/v1/draft/784354886748897281/picks",
    2023: "https://api.sleeper.app/v1/draft/928374253781659649/picks",
    2024: "https://api.sleeper.app/v1/draft/1049429880049373185/picks"
}

# Load or fetch player data
@st.cache_data
def load_player_data():
    if os.path.exists(player_data_file):
        with open(player_data_file, "r") as file:
            data = json.load(file)
        players = pd.DataFrame.from_dict(data, orient='index')
    else:
        url = "https://api.sleeper.app/v1/players/nfl"
        response = requests.get(url)
        data = response.json()
        players = pd.DataFrame.from_dict(data, orient='index')

        with open(player_data_file, "w") as file:
            json.dump(data, file)
    return players

@st.cache_data
def load_transaction_data():
    if os.path.exists(transaction_data_file):
        with open(transaction_data_file, "r") as file:
            data = json.load(file)
    else:
        data = defaultdict(list)
        for year in range(2020, 2025):
            for week in range(1, 19):
                url = f"{urls.get(year)}transactions/{week}"
                try:
                    response = requests.get(url)
                    response.raise_for_status()
                    data[str(year)].extend(response.json())
                except requests.RequestException as e:
                    st.error(f"An error occurred while fetching transactions for {year}, week {week}: {e}")
        
        with open(transaction_data_file, "w") as file:
            json.dump(data, file)
    return data

@st.cache_data
def load_stats_data():
    if os.path.exists(stats_data_file):
        with open(stats_data_file, "r") as file:
            data = json.load(file)
    else:
        # Load data from nfl_data_py
        stats = nfl.import_weekly_data(
            [2020, 2021, 2022, 2023, 2024],
            ['player_id', 'player_display_name', 'position', 'season', 'season_type', 'week', 'fantasy_points_ppr']
        )
        stats = stats[stats['season_type'] == 'REG']
        ids = nfl.import_ids(['gsis_id', 'sleeper_id'])
        data = pd.merge(
            stats, ids,
            left_on='player_id', right_on='gsis_id',
            how='inner'
        )[['player_id', 'position', 'player_display_name', 'season', 'week', 'fantasy_points_ppr', 'sleeper_id']]

        # Convert to a list of dictionaries
        data = data.to_dict(orient="records")

        # Write grouped_data to file
        with open(stats_data_file, "w") as file:
            json.dump(data, file)

    return data

@st.cache_data
def get_rosters(year):
    url = f"{urls.get(year)}rosters"
    response = requests.get(url)
    return response.json()

@st.cache_data
def get_users(year):
    url = f"{urls.get(year)}users"
    response = requests.get(url)
    return response.json()

@st.cache_data
def get_draft(year):
    url = f"{urls.get(year)}drafts"
    response = requests.get(url)
    drafts = response.json()
    return drafts[0] if drafts else None

@st.cache_data
def get_picks(year):
    url = f"{picks_urls.get(year)}"
    response = requests.get(url)
    return response.json()

drafts = {}
picks = {}
for i in range(2021, 2025):
    drafts[f"{i}"] = get_draft(i)
    picks[f"{i}"] = get_picks(i)

# Create a text area to display the logs
log_output = ""

# Streamlit app layout
st.title("Machiavelli Trade Viewer")

# Load player data
players = load_player_data()
transactions = load_transaction_data()
stats = load_stats_data()

# Get Year and Team from User
year = st.sidebar.selectbox("Select Year", [2020, 2021, 2022, 2023, 2024])
team = st.sidebar.selectbox("Select Team", ["Beckham", "Tyler", "Praveen", "Andre", "Jonny", "Gov", "Nick", "Cameron", "Joseph", "Kai/Arshon/Stathis", "Chase/Tin", "Robert/Ryan"])
names_dict = {"Beckham": ['brazybabybc', 'bc5934'], "Tyler": ['norris13', 'JoeBrownFanClub'], "Praveen": ['praveen14'], "Andre": ['sheluvgov', 'chicosman'], "Jonny": ['AndreRishel', 'TeamJonnyL'], "Gov":['GovsForeskin', 'Govvy'], "Nick": ['BucklingRelic12'], "Cameron": ['PuffDad'], "Joseph": ['SuperVUsters'], "Kai/Arshon/Stathis": ['RatchetRabies', 'guccigaropppp', 'TheStinkers'], "Chase/Tin": ['chade1', 'Matinnn'], "Robert/Ryan": ['GuapGetterz999', 'Br0wnsBunch', 'TheDanesh30']}

# Get Rosters and Users for that Year
rosters = get_rosters(year=year)
users = get_users(year=year)

user_dict = {user['user_id']: user['display_name'] for user in users if 'display_name' in user}

for transaction in transactions[str(year)]:
    if transaction['type'] == 'trade':
        transaction_year = year
        # Check if the selected team is involved in the transaction
        involved_teams = [roster['owner_id'] for roster in rosters if roster['roster_id'] in transaction['roster_ids']]
        involved_team_names = [user_dict.get(owner, f"Unknown User ({owner})") for owner in involved_teams]
        
        # Check if any of the names associated with the selected team are in the involved teams
        team_names = names_dict.get(team, [])
        if any(name in involved_team_names for name in team_names):
            log_output += f"Week {transaction['leg']} {year} - "
            
            log_output += "Teams Involved:  "
            for roster_id in transaction['roster_ids']:
                roster = next((r for r in rosters if r['roster_id'] == roster_id), None)  # find roster from id
                if roster:
                    owner_id = roster['owner_id']  # find owner_id from roster
                    display_name = user_dict.get(owner_id, f"Unknown User ({owner_id})")  # find display_name via owner_id and users dict
                    log_output += f"{display_name}  "
            log_output += "\n"
            
            # Combine players and draft picks into one structure per team
            trade_details = {}
            team_season_total = 0
            team_total = 0
            player_info = {}
            for player in stats:
                sleeper_id = player['sleeper_id']
                if sleeper_id not in player_info:
                    player_info[sleeper_id] = []
                player_info[sleeper_id].append(player)

            # Show added players and draft picks in the trade
            if transaction['adds']:
                # Assuming stats is a dictionary of lists of dictionaries
                for player_id, roster_id in transaction['adds'].items():
                    player_first_season_total = 0
                    not_first_season_total = 0
                    player_total = 0
                    first_season_weeks = 1
                    first_season_weeks = 0
                    not_first_season_weeks = 0
                    # stats is a list of dicts instead of a dict of lists of dicts
                    if player_id.isdigit(): 
                        # If player_id is numeric (indicating a player)
                        player = player_info.get(float(player_id), [])
                            
                    if player:
                        # Player found in stats, you can proceed with your logic here
                        for week in player:  # Assuming player_info contains a list of weeks
                            if (week['season'] == transaction_year) and (week['week'] >= transaction['leg']):
                                player_first_season_total += week['fantasy_points_ppr']
                                first_season_weeks += 1
                            elif week['season'] > transaction_year:
                                not_first_season_total += week['fantasy_points_ppr']
                                not_first_season_weeks += 1
                        
                        total_weeks = first_season_weeks + not_first_season_weeks
                        if total_weeks < 1:
                            total_weeks = 1
                        player_total = player_first_season_total + not_first_season_total
                        total_ppg = player_total / total_weeks
                        total_ppg = round(total_ppg, 2)
                        if first_season_weeks < 1:
                            first_season_weeks = 1
                        first_season_ppg = player_first_season_total / first_season_weeks
                        first_season_ppg = round(first_season_ppg, 2)
                        if not_first_season_weeks < 1:
                            not_first_season_weeks = 1
                        not_first_season_ppg = not_first_season_total / not_first_season_weeks
                        not_first_season_ppg = round(not_first_season_ppg, 2)
                        # Get the roster owner from the rosters list
                        roster = next((r for r in rosters if r['roster_id'] == roster_id), None)
                        if roster:
                            owner_id = roster['owner_id']
                            display_name = user_dict.get(owner_id, f"Unknown User ({owner_id})")
                            
                            # Update trade details for the roster
                            if roster_id not in trade_details:
                                trade_details[roster_id] = {"team": display_name, "items": []}
                            
                            trade_details[roster_id]["items"].append(f"{player[0].get('player_display_name')} ({player[0].get('position')}) - RoS: {first_season_ppg} PPG ({first_season_weeks} Gs), Future: {not_first_season_ppg} PPG ({not_first_season_weeks} Gs)")
                    else:
                        # Player not found in stats
                        log_output += f"Player ID {player_id} not found in player data.\n"

                                
            if transaction['draft_picks']:
                for pick in transaction['draft_picks']:
                    draft_pick_points = 0
                    draft_pick_weeks = 1
                    original = next((r for r in rosters if r['roster_id'] == pick['roster_id']), None)
                    reciever = next((r for r in rosters if r['roster_id'] == pick['owner_id']), None)
                
                    if original and reciever:
                        orig_owner_id = original['owner_id']
                        rec_owner_id = reciever['owner_id']

                        orig_display = user_dict.get(orig_owner_id, f"Unknown User ({orig_owner_id})")
                        rec_display = user_dict.get(rec_owner_id, f"Unknown User ({rec_owner_id})")

                        if pick['owner_id'] not in trade_details:
                            trade_details[pick['owner_id']] = {"team": rec_display, "items": []}
                        
                        if pick['season'] in drafts and drafts[pick['season']]:
                            position = drafts[pick['season']]['draft_order'].get(orig_owner_id, '?')
                            for player in picks[pick['season']]:
                                if player['round'] == pick['round'] and player['draft_slot'] == position:
                                    id = player['metadata']['player_id']
                                    not_played_info = players.loc[id]
                                    info = player_info.get(float(id), [])
                                    if info:
                                        for week in info: 
                                            draft_pick_points += week['fantasy_points_ppr']
                                            draft_pick_weeks += 1
                                            draft_pick_ppg = draft_pick_points / draft_pick_weeks
                                            draft_pick_ppg = round(draft_pick_ppg, 2)
                                            name = f"{week['player_display_name']} ({week['position']})"
                                        trade_details[pick['owner_id']]["items"].append(f"{pick['season']} RD {pick['round']} (Via {orig_display}) ({pick['round']}.{position} - {name}: {draft_pick_ppg} PPG ({draft_pick_weeks} Gs))")
                                    else:
                                        trade_details[pick['owner_id']]["items"].append(f"{pick['season']} RD {pick['round']} (Via {orig_display}) ({pick['round']}.{position} - {not_played_info['first_name']} {not_played_info['last_name']} ({not_played_info['position']}))")
                        else:
                            trade_details[pick['owner_id']]["items"].append(f"{pick['season']} RD {pick['round']} (Via {orig_display})")

            # Output the trade details for all involved teams
            for roster_id, data in trade_details.items():
                log_output += f"\nTeam {data['team']}:\n"
                for item in data["items"]:
                    log_output += f" - {item}\n"

            log_output += "-" * 104 + "\n"

# doing both .dr and .dd because its diff from 3.11 and 3.12
st.markdown(""" 
<style>
.st-dr {
    -webkit-text-fill-color: white !important;
}
.st-dd {
    -webkit-text-fill-color: white !important;
}
.st-d1 {
    color: white !important;
}
textarea {
    font-size: 20px !important;
    font-family: Goudy Bookletter 1911, sans-serif !important;
}
</style>
""", unsafe_allow_html=True)

# Display log in a scrollable text area
st.text_area("Transaction Log", value=log_output, height=400, max_chars=None, key="log", disabled=True)
