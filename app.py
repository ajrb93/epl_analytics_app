import streamlit as st
import pandas as pd
import plotly.express as px
import os
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import Rectangle
import matplotlib.colors as mcolors

# --- 1. CONFIG & COMPACT STYLING ---
st.set_page_config(layout="wide", page_title="English Premier League")

# CUSTOM CSS: Shrinks headers, table padding, and overall container gaps
st.markdown("""
    <style>
    /* Page margins */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 0rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }
    
    /* Tab labels */
    button[data-baseweb="tab"] {
        font-size: 14px !important;
    }
    button[data-baseweb="tab"] div {
        font-size: 14px !important;
    }

    /* Expander headers */
    div[data-testid="stExpander"] div[role="button"] p { 
        font-size: 12px !important; 
        font-weight: bold !important; 
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

def hex_to_rgb(value):
    value = value.lstrip('#')
    lv = len(value)
    return tuple(int(value[i:i + lv // 3],16) for i in range(0,lv,lv//3))

def rgb_to_hex(rgb):
    return '%02x%02x%02x' % rgb

def mean_color(color1,color2):
    rgb1 = hex_to_rgb(color1)
    rgb2 = hex_to_rgb(color2)
    
    avg = lambda x,y: round((x+y)/2)
    new_rgb = ()
    for i in range(len(rgb1)):
        new_rgb += (avg(rgb1[i],rgb2[i]),)
    
    return '#' + rgb_to_hex(new_rgb)

#colormap
colors = [(0.75,0,0),(1,1,1),(0,0.75,0)]
colors_r = [(0,0.75,0),(1,1,1),(0.75,0,0),]
n_bins = 100
cmap = mcolors.LinearSegmentedColormap.from_list('redwhitegreen',colors,N=n_bins)
cmap_r = mcolors.LinearSegmentedColormap.from_list('redwhitegreen_r',colors_r,N=n_bins)
norm_o = mcolors.TwoSlopeNorm(vmin=0,vcenter=1.3,vmax=2.6)
norm_r = mcolors.TwoSlopeNorm(vmin=0,vcenter=1,vmax=3)
norm_p = mcolors.TwoSlopeNorm(vmin=0,vcenter=1.5,vmax=3)
norm_w = mcolors.TwoSlopeNorm(vmin=0,vcenter=1/3,vmax=1)
norm_perf = mcolors.TwoSlopeNorm(vmin=-1.5, vcenter=0, vmax=1.5)

def plot_standings_table(standings_df):
    fig, ax = plt.subplots(figsize=(14,6))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')

    # --- HEADERS ---
    ax.annotate('Team',       (0.01,  0.97), va='center', ha='left',   size=10, weight='bold')
    ax.annotate('Skill',      (1.65/10, 0.97), va='center', ha='center', size=10, weight='bold')
    ax.annotate('Off',        (2.65/10, 0.97), va='center', ha='center', size=10, weight='bold')
    ax.annotate('Def',        (3.65/10, 0.97), va='center', ha='center', size=10, weight='bold')
    ax.annotate('Performance',(4.65/10, 0.97), va='center', ha='center', size=10, weight='bold')
    ax.annotate('Proj',       (5.5/10,  0.97), va='center', ha='center', size=10, weight='bold')
    ax.annotate('Points',     (6.15/10, 0.97), va='center', ha='center', size=10, weight='bold')
    ax.annotate('GD',         (6.7/10,  0.97), va='center', ha='center', size=10, weight='bold')
    ax.annotate('Champ',      (7.45/10, 0.97), va='center', ha='center', size=10, weight='bold')
    ax.annotate('CL',         (8.3/10,  0.97), va='center', ha='center', size=10, weight='bold')
    ax.annotate('Rele.',      (9.1/10,  0.97), va='center', ha='center', size=10, weight='bold')
    ax.annotate('Range',      (9.75/10, 0.97), va='center', ha='center', size=10, weight='bold')

    # --- VERTICAL DIVIDERS ---
    for x in [1.15, 2.15, 3.15, 4.15, 5.15, 5.85, 6.45, 7.05, 7.85, 8.65, 9.50]:
        ax.axvline(x/10, color='black', linewidth=0.5)

    # --- ROWS ---
    n_teams = len(standings_df)
    top = 0.93
    bottom_margin = 0.01
    total_height = top - bottom_margin
    space = total_height / n_teams
    i_loc = top - space / 2

    ax.vlines(4.483/10, bottom_margin, top, color='black', linewidth=0.3, linestyle='--')
    ax.vlines(4.816/10, bottom_margin, top, color='black', linewidth=0.3, linestyle='--')

    for _, row in standings_df.iterrows():
        team = row['Team']

        # Team name
        ax.annotate(team, (0.01, i_loc), va='center', ha='left', size=9, fontweight='bold')

        # Background placeholder (replace with team colors later)
        ax.add_patch(Rectangle((0, i_loc - space/2), 1.15/10, space, facecolor='lightgray'))
        ax.add_patch(Rectangle((1.15/10, i_loc - space/2), 1, space, facecolor='whitesmoke'))

        # Skill (nPRE)
        ax.annotate(f"{row['nPRE']:.0%}", (1.4/10, i_loc), va='center', ha='center', size=9)
        delta_color = 'darkgreen' if row['nPREΔ'] > 0 else 'darkred'
        ax.annotate(f"({'+' if row['nPREΔ'] > 0 else ''}{row['nPREΔ']:.0%})", (1.9/10, i_loc), va='center', ha='center', size=9, color=delta_color)
        ax.add_patch(Rectangle((1.15/10, i_loc - space/2), 0.5/10, space,facecolor=cmap(row['nPRE'])))

        # Offensive (oPRE)
        ax.annotate(f"{row['oPRE']:.2f}", (2.4/10, i_loc), va='center', ha='center', size=9)
        delta_color = 'darkgreen' if row['oPREΔ'] > 0 else 'darkred'
        ax.annotate(f"({'+' if row['oPREΔ'] > 0 else ''}{row['oPREΔ']:.0%})", (2.9/10, i_loc), va='center', ha='center', size=9, color=delta_color)
        ax.add_patch(Rectangle((2.15/10, i_loc - space/2), 0.5/10, space,facecolor=cmap(norm_o(row['oPRE']))))

        # Defensive (dPRE)
        ax.annotate(f"{row['dPRE']:.2f}", (3.4/10, i_loc), va='center', ha='center', size=9)
        delta_color = 'darkgreen' if row['dPREΔ'] < 0 else 'darkred'
        ax.annotate(f"({'+' if row['dPREΔ'] < 0 else ''}{row['dPREΔ']*-1:.0%})", (3.9/10, i_loc), va='center', ha='center', size=9, color=delta_color)
        ax.add_patch(Rectangle((3.15/10, i_loc - space/2), 0.5/10, space,facecolor=cmap(1 - norm_o(row['dPRE']))))

        # Performance (nRTG, oRTG, dRTG)
        ax.annotate(f"{row['nRTG']:.2f}", (4.35/10, i_loc), va='center', ha='center', size=9)
        ax.annotate(f"{row['oRTG']:.2f}", (4.65/10, i_loc), va='center', ha='center', size=9)
        ax.annotate(f"{row['dRTG']:.2f}", (4.95/10, i_loc), va='center', ha='center', size=9)
        ax.add_patch(Rectangle((4.15/10, i_loc - space/2), (1/3)/10, space,facecolor=cmap(norm_perf(row['nRTG']))))
        ax.add_patch(Rectangle((4.483/10, i_loc - space/2), (1/3)/10, space,facecolor=cmap(norm_o(row['oRTG']))))
        ax.add_patch(Rectangle((4.816/10, i_loc - space/2), (1/3)/10, space,facecolor=cmap(1 - norm_o(row['dRTG']))))

        # Proj + ProjΔ
        ax.annotate(f"{row['Proj']:.0f}", (5.3/10, i_loc), va='center', ha='center', size=9)
        delta_color = 'darkgreen' if row['ProjΔ'] > 0 else 'darkred'
        ax.annotate(f"({'+' if row['ProjΔ'] > 0 else ''}{row['ProjΔ']:.0f})", (5.65/10, i_loc), va='center', ha='center', size=9, color=delta_color)

        # Points + xPts
        ax.annotate(f"{int(row['P'])}", (6.0/10, i_loc), va='center', ha='center', size=9)
        ax.annotate(f"{row['xPts']:.1f}", (6.25/10, i_loc), va='center', ha='center', size=9)

        # GD + xGD
        ax.annotate(f"{int(row['GD'])}", (6.6/10, i_loc), va='center', ha='center', size=9)
        ax.annotate(f"{row['xGD']:.1f}", (6.85/10, i_loc), va='center', ha='center', size=9)

        # Champ + WinΔ
        ax.annotate(f"{row['Win']:.0%}", (7.25/10, i_loc), va='center', ha='center', size=9)
        delta_color = 'darkgreen' if row['WinΔ'] > 0 else 'darkred'
        ax.annotate(f"({'+' if row['WinΔ'] > 0 else ''}{row['WinΔ']:.0%})", (7.65/10, i_loc), va='center', ha='center', size=9, color=delta_color)

        # CL + CLΔ
        ax.annotate(f"{row['CL']:.0%}", (8.05/10, i_loc), va='center', ha='center', size=9)
        delta_color = 'darkgreen' if row['CLΔ'] > 0 else 'darkred'
        ax.annotate(f"({'+' if row['CLΔ'] > 0 else ''}{row['CLΔ']:.0%})", (8.45/10, i_loc), va='center', ha='center', size=9, color=delta_color)

        # Rel + RelΔ
        ax.annotate(f"{row['Rel']:.0%}", (8.85/10, i_loc), va='center', ha='center', size=9)
        delta_color = 'darkgreen' if row['RelΔ'] < 0 else 'darkred'
        ax.annotate(f"({'+' if row['RelΔ'] < 0 else ''}{row['RelΔ']*-1:.0%})", (9.25/10, i_loc), va='center', ha='center', size=9, color=delta_color)

        # Range
        ax.annotate(row['range'], (9.75/10, i_loc), va='center', ha='center', size=9)

        # Row divider
        ax.axhline(i_loc - space/2, color='black', linewidth=0.5)

        i_loc -= space

    # Top border
    ax.axhline(0.935, color='black', linewidth=0.5)

    plt.tight_layout()
    return fig

standings = pd.read_feather('data/standings.ftr')
#color_map = pd.read_feather('data/color_map.ftr')
#matches = pd.read_feather('data/matches.ftr')
#player_stats = pd.read_feather('data/player_stats.ftr')
team_ratings = pd.read_feather('data/team_ratings.ftr')
team_ratings = team_ratings[['Season','Date']].drop_duplicates().merge(team_ratings[['Season','Team']].drop_duplicates()).merge(
    team_ratings,how='outer').sort_values(['Team','Date'])
team_ratings[['A','B','C']] = team_ratings.groupby(['Season','Team'])[['A','B','C']].ffill()
standings_sims = load_standings_sims()

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
        fig = plot_standings_table(standings_df.drop(columns='season'))
        st.pyplot(fig, use_container_width=True)