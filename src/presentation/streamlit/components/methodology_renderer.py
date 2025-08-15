# src/presentation/streamlit/components/methodology_renderer.py - Methodology documentation component

import streamlit as st
from ....domain.metrics import NFLMetrics


class MethodologyRenderer:
    """Renders detailed methodology documentation for all statistics."""
    
    def __init__(self):
        self.analysis_response = None
    
    def render_methodology_page(self, analysis_response=None):
        """Render the complete methodology documentation."""
        self.analysis_response = analysis_response
        st.header("Statistical Methodology")
        st.markdown("This page documents how each statistic is calculated, including data sources, filters, and formulas.")
        
        # Create tabs for different sections
        tab1, tab2, tab3, tab4 = st.tabs(["Core Metrics", "Efficiency Metrics", "Situational Stats", "Data Sources"])
        
        with tab1:
            self._render_core_metrics()
        
        with tab2:
            self._render_efficiency_metrics()
        
        with tab3:
            self._render_situational_stats()
        
        with tab4:
            self._render_data_sources()
    
    def _render_core_metrics(self):
        """Render core offensive metrics methodology."""
        st.subheader("Core Offensive Metrics")
        
        # Get actual team data if available
        team_name = self.analysis_response.team.name if self.analysis_response else "Example Team"
        season_year = self.analysis_response.season.year if self.analysis_response else 2024
        
        # Yards Per Play
        if self.analysis_response:
            ypp_value = self.analysis_response.season_stats.avg_yards_per_play
            total_yards = self.analysis_response.season_stats.total_yards
            total_plays = self.analysis_response.season_stats.total_plays
            
            self._render_stat_card(
                "Yards Per Play",
                "Average yards gained per offensive play",
                f"**What's Included:** Every offensive snap - all rushes, passes, and sacks. Excludes punts, kicks, penalties with no play, and two-point conversions (scoring plays, not offensive plays).",
                f"**Formula:** Total Yards ÷ Total Plays",
                f"**{team_name} {season_year}:** {total_yards:,} yards ÷ {total_plays:,} plays = **{ypp_value:.2f} YPP**"
            )
        else:
            self._render_stat_card(
                "Yards Per Play",
                "Average yards gained per offensive play",
                "**What's Included:** Every offensive snap - all rushes, passes, and sacks. Excludes punts, kicks, penalties with no play, and two-point conversions (scoring plays, not offensive plays).",
                "**Formula:** Total Yards ÷ Total Plays",
                "**Example:** 6,218 yards ÷ 1,120 plays = 5.55 YPP"
            )
        
        # Completion Percentage
        if self.analysis_response:
            stats = self.analysis_response.season_stats
            comp_pct = stats.completion_pct
            completions = stats.total_pass_completions
            attempts = stats.total_pass_attempts
            
            self._render_stat_card(
                "Completion Percentage",
                "Percentage of pass attempts that were completed",
                f"**What's Included:** Forward pass attempts only - completions, incompletions, and spikes. Excludes sacks (not pass attempts).",
                f"**Formula:** Completions ÷ Pass Attempts × 100",
                f"**{team_name} {season_year}:** {completions:,} completions ÷ {attempts:,} attempts × 100 = **{comp_pct:.2f}%**"
            )
        else:
            self._render_stat_card(
                "Completion Percentage",
                "Percentage of pass attempts that were completed",
                "**What's Included:** Forward pass attempts only - completions, incompletions, and spikes. Excludes sacks (not pass attempts).",
                "**Formula:** Completions ÷ Pass Attempts × 100",
                "**Example:** 399 completions ÷ 552 attempts × 100 = 72.28%"
            )
        
        # Rushing YPC
        if self.analysis_response:
            stats = self.analysis_response.season_stats
            rush_ypc = stats.rush_ypc
            rush_yards = stats.total_rush_yards
            rush_attempts = stats.total_rush_attempts
            
            self._render_stat_card(
                "Rushing Yards Per Carry",
                "Average yards gained per rushing attempt",
                f"**What's Included:** Any play where a player carries the ball - handoffs, QB runs, scrambles, kneels. Excludes sacks (pass plays).",
                f"**Formula:** Total Rushing Yards ÷ Total Rush Attempts",
                f"**{team_name} {season_year}:** {rush_yards:,} yards ÷ {rush_attempts:,} attempts = **{rush_ypc:.2f} YPC**"
            )
        else:
            self._render_stat_card(
                "Rushing Yards Per Carry",
                "Average yards gained per rushing attempt",
                "**What's Included:** Any play where a player carries the ball - handoffs, QB runs, scrambles, kneels. Excludes sacks (pass plays).",
                "**Formula:** Total Rushing Yards ÷ Total Rush Attempts",
                "**Example:** 2,500 yards ÷ 520 attempts = 4.81 YPC"
            )
        
        # Points Per Drive
        if self.analysis_response:
            stats = self.analysis_response.season_stats
            ppd = stats.points_per_drive
            total_points = stats.total_offensive_points
            total_drives = stats.total_drives
            
            # Get scoring breakdown
            touchdowns = stats.total_touchdowns
            extra_points = stats.total_extra_points
            two_point_convs = stats.total_two_point_conversions
            field_goals = stats.total_field_goals
            
            self._render_stat_card(
                "Points Per Drive",
                "Average points scored per offensive possession",
                f"**What's Included:** Points scored by the offense during their possessions. Excludes defensive and special teams touchdowns.",
                f"**Formula:** Total Offensive Points ÷ Total Offensive Drives",
                f"**{team_name} {season_year}:** Touchdowns: {touchdowns} × 6 = {touchdowns * 6} pts, Extra Points: {extra_points} × 1 = {extra_points} pts, 2-Point Conversions: {two_point_convs} × 2 = {two_point_convs * 2} pts, Field Goals: {field_goals} × 3 = {field_goals * 3} pts. Total: {total_points:,} points ÷ {total_drives:,} drives = **{ppd:.2f} PPD**"
            )
        else:
            self._render_stat_card(
                "Points Per Drive",
                "Average points scored per offensive possession",
                "**What's Included:** All points scored by the offense",
                "**Formula:** Total Points Scored ÷ Total Drives",
                "**Scoring:** Touchdowns (6), Extra Points (1), 2-Point Conversions (2), Field Goals (3)"
            )
    
    def _render_efficiency_metrics(self):
        """Render efficiency metrics methodology."""
        st.subheader("Efficiency & Advanced Metrics")
        
        # Success Rate
        if self.analysis_response:
            stats = self.analysis_response.season_stats
            success_rate = stats.success_rate
            total_plays = stats.total_plays
            # Calculate actual successful plays from breakdown
            successful_plays = (stats.first_down_successful_plays + 
                              stats.second_down_successful_plays + 
                              stats.third_down_successful_plays)
            team_name = self.analysis_response.team.name
            season_year = self.analysis_response.season.year
            
            # Get breakdown by down
            first_success = stats.first_down_successful_plays
            first_total = stats.first_down_total_plays
            second_success = stats.second_down_successful_plays  
            second_total = stats.second_down_total_plays
            third_success = stats.third_down_successful_plays
            third_total = stats.third_down_total_plays
            
            self._render_stat_card(
                "Play Success Rate", 
                "Percentage of plays that gained 'enough' yards based on down and distance",
                f"**Success Criteria:** 1st down (≥40% of yards needed), 2nd down (≥60% of yards needed), 3rd/4th down (must gain all yards needed).",
                f"**Formula:** Successful Plays ÷ Total Plays × 100",
                f"**{team_name} {season_year}:** 1st down: {first_success}/{first_total} successful, 2nd down: {second_success}/{second_total} successful, 3rd/4th down: {third_success}/{third_total} successful. Total: {successful_plays:,} ÷ {total_plays:,} × 100 = **{success_rate:.2f}%**"
            )
        else:
            self._render_stat_card(
                "Play Success Rate",
                "Percentage of plays that gained 'enough' yards based on down and distance", 
                "**Success Criteria:** 1st down (≥40% of yards needed), 2nd down (≥60% of yards needed), 3rd/4th down (must gain all yards needed).",
                "**Formula:** Successful Plays ÷ Total Plays × 100",
                "**Example:** 53.76% means 53.76% of plays gained enough yards to stay 'on schedule'",
                "Each play judged by different standards based on down and distance"
            )
        
        # Third Down Conversion
        if self.analysis_response:
            stats = self.analysis_response.season_stats
            third_down_pct = stats.third_down_pct
            total_third_downs = stats.total_third_downs
            total_conversions = stats.total_third_down_conversions
            team_name = self.analysis_response.team.name
            season_year = self.analysis_response.season.year
            
            # Get conversion breakdown
            rush_conversions = stats.total_third_down_rush_conversions
            pass_conversions = stats.total_third_down_pass_conversions
            
            self._render_stat_card(
                "Third Down Conversion Rate",
                "Percentage of 3rd down attempts that resulted in a first down or touchdown",
                f"**What's Included:** 3rd down offensive plays only. Success = achieving first down or touchdown.",
                f"**Formula:** (First Downs + Touchdowns) ÷ 3rd Down Attempts × 100",
                f"**{team_name} {season_year}:** Rushing conversions: {rush_conversions}, Passing conversions: {pass_conversions}. Total: {total_conversions:,} conversions ÷ {total_third_downs:,} attempts × 100 = **{third_down_pct:.2f}%**"
            )
        else:
            self._render_stat_card(
                "Third Down Conversion Rate",
                "Percentage of 3rd down attempts that resulted in a first down or touchdown",
                "**What's Included:** 3rd down offensive plays only. Success = achieving first down or touchdown.",
                "**Formula:** (First Downs + Touchdowns) ÷ 3rd Down Attempts × 100",
                "**Example:** 48.06% means the offense converted 48.06% of their 3rd down attempts"
            )
        
        # Red Zone TD%
        if self.analysis_response:
            stats = self.analysis_response.season_stats
            redzone_td_pct = stats.redzone_td_pct
            total_rz_trips = stats.total_redzone_trips
            total_rz_tds = stats.total_redzone_tds
            team_name = self.analysis_response.team.name
            season_year = self.analysis_response.season.year
            
            # Get red zone outcome breakdown
            total_rz_fgs = stats.total_redzone_field_goals
            total_rz_failed = stats.total_redzone_failed
            
            self._render_stat_card(
                "Red Zone Touchdown Rate",
                "Percentage of red zone drives that ended in touchdowns",
                f"**What's Included:** Offensive drives reaching the red zone (20-yard line or closer to goal line). Success = scoring touchdown, not field goal.",
                f"**Formula:** Red Zone TDs ÷ Red Zone Trips × 100",
                f"**{team_name} {season_year}:** Touchdowns: {total_rz_tds}, Field Goals: {total_rz_fgs}, Failed: {total_rz_failed}. Red Zone Efficiency: {total_rz_tds:,} TDs ÷ {total_rz_trips:,} trips × 100 = **{redzone_td_pct:.2f}%**"
            )
        else:
            self._render_stat_card(
                "Red Zone Touchdown Rate",
                "Percentage of red zone drives that ended in touchdowns",
                "**What's Included:** Offensive drives reaching the red zone (20-yard line or closer to goal line). Success = scoring touchdown, not field goal.",
                "**Formula:** Red Zone TDs ÷ Red Zone Trips × 100",
                "**Example:** 91.3% means the offense scored touchdowns on 91.3% of their red zone drives"
            )
    
    def _render_situational_stats(self):
        """Render situational statistics methodology."""
        st.subheader("Situational Statistics")
        
        # Turnovers
        if self.analysis_response:
            stats = self.analysis_response.season_stats
            turnovers_per_game = stats.turnovers_per_game
            total_turnovers = stats.total_turnovers
            games_played = stats.games_played
            team_name = self.analysis_response.team.name
            season_year = self.analysis_response.season.year
            
            # Get turnover breakdown
            interceptions = stats.total_interceptions
            fumbles_lost = stats.total_fumbles_lost
            
            self._render_stat_card(
                "Turnovers Per Game",
                "Average turnovers committed per game",
                f"**What's Included:** Possessions lost to defense - interceptions thrown and fumbles lost. Excludes fumbles recovered by offense.",
                f"**Formula:** Total Turnovers ÷ Games Played",
                f"**{team_name} {season_year}:** Interceptions: {interceptions}, Fumbles Lost: {fumbles_lost}. Total: {total_turnovers:,} turnovers ÷ {games_played:,} games = **{turnovers_per_game:.2f}** per game"
            )
        else:
            self._render_stat_card(
                "Turnovers Per Game",
                "Average turnovers committed per game",
                "**What's Included:** Possessions lost to defense - interceptions thrown and fumbles lost. Excludes fumbles recovered by offense.",
                "**Formula:** Total Turnovers ÷ Games Played",
                "**Example:** 0.71 means the offense turns the ball over 0.71 times per game"
            )
        
        # Sacks Allowed
        if self.analysis_response:
            stats = self.analysis_response.season_stats
            sacks_per_game = stats.sacks_per_game
            total_sacks = stats.total_sacks
            games_played = stats.games_played
            team_name = self.analysis_response.team.name
            season_year = self.analysis_response.season.year
            
            self._render_stat_card(
                "Sacks Allowed Per Game",
                "Average sacks allowed per game",
                f"**What's Included:** QB tackled behind line of scrimmage while attempting to pass. Excludes designed runs.",
                f"**Formula:** Total Sacks ÷ Games Played",
                f"**{team_name} {season_year}:** {total_sacks:,} sacks ÷ {games_played:,} games = **{sacks_per_game:.2f}** per game"
            )
        else:
            self._render_stat_card(
                "Sacks Allowed Per Game",
                "Average sacks allowed per game",
                "**What's Included:** QB tackled behind line of scrimmage while attempting to pass. Excludes designed runs.",
                "**Formula:** Total Sacks ÷ Games Played",
                "**Example:** 2.24 means the offense allows 2.24 sacks per game"
            )
        
        # First Downs
        if self.analysis_response:
            stats = self.analysis_response.season_stats
            first_downs_per_game = stats.first_downs_per_game
            total_first_downs = stats.total_first_downs
            games_played = stats.games_played
            team_name = self.analysis_response.team.name
            season_year = self.analysis_response.season.year
            
            # Get first down breakdown
            rush_first_downs = stats.total_first_downs_rush
            pass_first_downs = stats.total_first_downs_pass
            penalty_first_downs = stats.total_first_downs_penalty
            
            self._render_stat_card(
                "First Downs Per Game",
                "Average first downs gained per game",
                f"**What's Included:** New sets of downs earned - by rush, pass, or defensive penalty. Excludes touchdowns.",
                f"**Formula:** Total First Downs ÷ Games Played",
                f"**{team_name} {season_year}:** Rushing: {rush_first_downs}, Passing: {pass_first_downs}, Penalty: {penalty_first_downs}. Total: {total_first_downs:,} first downs ÷ {games_played:,} games = **{first_downs_per_game:.2f}** per game"
            )
        else:
            self._render_stat_card(
                "First Downs Per Game",
                "Average first downs gained per game",
                "**What's Included:** New sets of downs earned - by rush, pass, or defensive penalty. Excludes touchdowns.",
                "**Formula:** Total First Downs ÷ Games Played",
                "**Example:** 18.35 means the offense earns 18.35 first downs per game"
            )
        
        # Penalty Yards
        if self.analysis_response:
            stats = self.analysis_response.season_stats
            penalty_yards_per_game = stats.penalty_yards_per_game
            total_penalty_yards = stats.total_penalty_yards
            games_played = stats.games_played
            team_name = self.analysis_response.team.name
            season_year = self.analysis_response.season.year
            
            penalty_metric = NFLMetrics.PENALTY_YARDS_PER_GAME
            self._render_stat_card(
                penalty_metric.display_name,
                penalty_metric.description,
                f"**What's Included:** Infractions committed by offense while they have the ball. Excludes penalties that benefit the offense.",
                f"**Formula:** Total Penalty Yards ÷ Games Played",
                f"**{team_name} {season_year}:** {total_penalty_yards:,} penalty yards ÷ {games_played:,} games = **{penalty_yards_per_game:.2f}** per game"
            )
        else:
            penalty_metric = NFLMetrics.PENALTY_YARDS_PER_GAME
            self._render_stat_card(
                penalty_metric.display_name,
                penalty_metric.description,
                "**What's Included:** Infractions committed by offense while they have the ball. Excludes penalties that benefit the offense.",
                "**Formula:** Total Penalty Yards ÷ Games Played",
                "**Example:** 5.59 means the offense commits 5.59 penalty yards per game"
            )
    
    def _render_data_sources(self):
        """Render data sources and technical information."""
        st.subheader("Data Sources & Technical Details")
        
        st.markdown("### Data Source")
        st.markdown("""
        **Primary Source:** `nfl_data_py` Python package
        - **Provider:** nflfastR project
        - **Coverage:** Play-by-play data for all NFL games
        - **Update Frequency:** Multiple times per week during season
        - **Data Quality:** Official NFL play-by-play with advanced analytics
        """)
        
        st.markdown("### Data Filtering")
        st.markdown("""
        **Season Type Options:**
        - **Regular Season:** `season_type = 'REG'` (varies by era: 17 games since 2021, 16 games 1978-2020)
        - **Playoffs:** `season_type = 'POST'` (varies by team)
        - **Combined:** Both regular season and playoffs
        
        **Play Exclusions:**
        - Special teams plays (kickoffs, punts, etc.)
        - No-play situations (some penalties)
        - Kneel downs in victory formation (included in rushing stats per NFL standard)
        """)
        
        st.markdown("### Technical Implementation")
        st.markdown("""
        **Key Data Columns Used:**
        - `rush_attempt = 1`: Official rushing attempts
        - `pass_attempt = 1`: Official passing attempts (includes spikes)
        - `sack = 1`: Quarterback sacked
        - `complete_pass = 1`: Pass completion
        - `yards_gained`: Yards gained/lost on play
        - `down`, `ydstogo`: Down and distance
        - `first_down = 1`: First down achieved
        - `touchdown = 1`: Touchdown scored
        - `penalty = 1`: Penalty on play
        """)
        
        st.markdown("### Accuracy & Validation")
        st.markdown("""
        **Validation Sources:**
        - NFL.com official statistics
        - Pro Football Reference
        - ESPN Stats & Info
        """)
        
        st.markdown("### Updates & Methodology Changes")
        st.markdown("""
        **Recent Improvements:**
        - None
        """)
    
    def _render_stat_card(self, title, description, input_data, formula, example):
        """Render a formatted statistics card."""
        st.markdown(f"#### {title}")
        
        with st.expander(f"View {title} Details", expanded=False):
            st.markdown(f"**Description:** {description}")
            st.markdown(f"{input_data}")
            st.markdown(f"{formula}")
            st.markdown(f"{example}")
