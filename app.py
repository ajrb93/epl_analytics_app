import streamlit as st
import pandas as pd
import plotly.express as px
import os

# --- 1. CONFIG & COMPACT STYLING ---
st.set_page_config(layout="wide", page_title="English Premier League")

# CUSTOM CSS: Shrinks headers, table padding, and overall container gaps
st.markdown("""
<style>

/* -------------------- */
/* TABS = 12px */
/* -------------------- */
button[data-baseweb="tab"] {
    font-size: 12px !important;
    font-weight: 600 !important;
}

/* -------------------- */
/* SELECTBOXES = 10px */
/* -------------------- */

/* Selected value */
div[data-baseweb="select"] > div {
    font-size: 10px !important;
    min-height: 28px !important;
}

/* Dropdown menu items */
div[role="listbox"] li {
    font-size: 10px !important;
}

/* -------------------- */
/* DATAFRAMES = 8px */
/* -------------------- */

/* Entire dataframe container */
div[data-testid="stDataFrame"] {
    font-size: 8px !important;
}

/* Header cells */
div[data-testid="stDataFrame"] [role="columnheader"] {
    font-size: 8px !important;
    padding: 2px 4px !important;
}

/* Data cells */
div[data-testid="stDataFrame"] [role="gridcell"] {
    font-size: 8px !important;
    padding: 2px 4px !important;
}

/* Remove extra row height */
div[data-testid="stDataFrame"] div[role="row"] {
    min-height: 20px !important;
}

/* Remove excessive padding around dataframe */
div[data-testid="stDataFrame"] > div {
    padding: 0px !important;
}

</style>
""", unsafe_allow_html=True)

# Load All Data
def credible_range_str(row, level=0.9):
    probs = row.sort_values(ascending=False)
    cumsum = probs.cumsum()
    included = probs.index[cumsum <= level]
    if len(included) < len(probs):
        included = included.append(pd.Index([cumsum.index[len(included)]]))
    nums = [int(float(p)) for p in included]
    lo, hi = min(nums), max(nums)
    return f"{lo}" if lo == hi else f"{lo} to {hi}"

def load_standings_sims():
    files = os.listdir('data/Sim_States/')
    files = list(filter(lambda k: '.ftr' in k, files))

    standings_files = list(filter(lambda k: '_matches' not in k, files))
    match_files = list(filter(lambda k: '_matches' in k, files))

    standings_sims = []
    for file in standings_files:
        temp = pd.read_feather('data/Sim_States/'+file)
        date = file.replace('.ftr','')
        temp['Sim_Date'] = date
        standings_sims.append(temp)
    standings_sims = pd.concat((standings_sims)).reset_index()
    standings_sims.Sim_Date = pd.to_datetime(standings_sims.Sim_Date).dt.date
    standings_sims = standings_sims.fillna(0)
    standings_sims['Champ'] = standings_sims['1']
    standings_sims['CL'] = standings_sims[['1','2','3','4','5']].sum(axis=1)
    standings_sims['Rel'] = standings_sims[['18','19','20']].sum(axis=1)

    standings_sims['range'] = standings_sims[['1','2','3','4','5','6','7','8','9','10','11','12','13','14','15','16','17','18','19','20']].apply(credible_range_str, axis=1)
    standings_sims['season'] = (pd.to_datetime(standings_sims.Sim_Date).dt.year + (pd.to_datetime(standings_sims.Sim_Date).dt.month >= 8).astype('int')).astype('str').str[2:]
    return standings_sims

def create_standings_file(standings,standings_sims,team_ratings,season,max_date,min_date):
    temp = standings[standings.season == season][['season','F','F_score','A_score','F_P','F_xg','A_xg','F_xPts','oRTG','dRTG','nRTG']].reset_index(drop=True)
    temp['GD'] = temp.F_score - temp.A_score
    temp['xGD'] = temp.F_xg - temp.A_xg
    temp_sim = standings_sims[standings_sims.Sim_Date == max_date].set_index('index')[['Points','Champ','CL','Rel','range']]
    temp_sim2 = standings_sims[standings_sims.Sim_Date == min_date].set_index('index')[['Points','Champ','CL','Rel']]
    temp_sim2 = temp_sim - temp_sim2
    temp_sim3 = team_ratings[team_ratings.Date == max_date].set_index('Team')[['Date','A','B','C']]
    temp_sim4 = team_ratings[team_ratings.Date == min_date].set_index('Team')[['A','B','C']]
    temp_sim4 = temp_sim3 - temp_sim4
    temp = temp.merge(temp_sim.reset_index(),left_on='F',right_on='index').merge(temp_sim2.reset_index(),left_on='F',right_on='index',suffixes=['','_c']).merge(
        temp_sim3.reset_index(),left_on='F',right_on='Team').merge(temp_sim4.reset_index(),left_on='F',right_on='Team',suffixes=['','_c'])
    temp = temp[['season','Team','C','C_c','A','A_c','B','B_c','nRTG','oRTG','dRTG','Points','Points_c','F_P','F_xPts','GD','xGD','Champ','Champ_c','CL','CL_c','Rel',
                 'Rel_c','range']].rename(
                     columns={'A':'oPRE','A_c':'oPREΔ','B':'dPRE','B_c':'dPREΔ','F_P':'P','F_xPts':'xPts','Points':'Proj','Points_c':'ProjΔ','C':'nPRE','C_c':'nPREΔ',
                               'Champ':'Win','Champ_c':'WinΔ','CL_c':'CLΔ','Rel_c':'RelΔ'})
    return temp

standings = pd.read_feather('data/standings.ftr')
#color_map = pd.read_feather('data/color_map.ftr')
#matches = pd.read_feather('data/matches.ftr')
#player_stats = pd.read_feather('data/player_stats.ftr')
team_ratings = pd.read_feather('data/team_ratings.ftr')
team_ratings = team_ratings[['Season','Date']].drop_duplicates().merge(team_ratings[['Season','Team']].drop_duplicates()).merge(
    team_ratings,how='outer').sort_values(['Team','Date'])
team_ratings[['A','B','C']] = team_ratings.groupby(['Season','Team'])[['A','B','C']].ffill()
standings_sims = load_standings_sims()

# Formatting Helper: 1 decimal for FPoints, 0 for the rest
fmt_dict = {'nPRE': '{:.1%}', 'nPREΔ': '{:.1%}', 'oPRE': '{:.2f}','oPREΔ':'{:.0%}', 'dPRE': '{:.2f}','dPREΔ':'{:.0%}','nRTG':'{:.2f}','oRTG':'{:.2f}','dRTG':'{:.2f}',
            'Proj':'{:.1f}','ProjΔ':'{:.1f}','xGD': '{:.1f}', 'xPts': '{:.1f}','Win':'{:.0%}','WinΔ':'{:.0%}','CL':'{:.0%}','CLΔ':'{:.0%}','Rel':'{:.0%}','RelΔ':'{:.0%}'}

# --- MAIN DASHBOARD ---
tab_standings, tab_team = st.tabs([f"Standings", "Team Profile"])

with tab_standings:
    col1, col2 = st.columns([2,3])
    # --- COLUMN 1: LEFT ---
    with col1:
        subcol1, subcol2, subcol3 = st.columns([1,1,1])
        with subcol1:
            season = sorted(standings_sims['season'].unique(), reverse=True)
            selected_season = st.selectbox("Select Year", options=season, index=0, key="season_picker",label_visibility="collapsed")
        with subcol2:
            dates = sorted(standings_sims[standings_sims['season'] == selected_season]['Sim_Date'].unique(),reverse=True)
            selected_end_date = st.selectbox("Select Date",options=dates,index=0, key="end_date_picker",label_visibility='collapsed')
        with subcol3:
            start_dates = sorted(standings_sims[(standings_sims['season'] == selected_season) & (standings_sims['Sim_Date'] < selected_end_date)]['Sim_Date'].unique(),reverse=True)
            selected_start_date = st.selectbox("Select Relative Date",options=start_dates,index=len(start_dates)-1, key='start_date_picker',label_visibility='collapsed')

    with col2:
        standings_df = create_standings_file(standings,standings_sims,team_ratings,selected_season,selected_end_date,selected_start_date).sort_values(['P','GD'],ascending=False)
        st.dataframe(standings_df.drop(columns='season').style.format(fmt_dict),hide_index=True, use_container_width=True, height=520)