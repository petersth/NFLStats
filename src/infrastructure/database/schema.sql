


SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;


COMMENT ON SCHEMA "public" IS 'standard public schema';



CREATE EXTENSION IF NOT EXISTS "pg_graphql" WITH SCHEMA "graphql";






CREATE EXTENSION IF NOT EXISTS "pg_stat_statements" WITH SCHEMA "extensions";






CREATE EXTENSION IF NOT EXISTS "pgcrypto" WITH SCHEMA "extensions";






CREATE EXTENSION IF NOT EXISTS "supabase_vault" WITH SCHEMA "vault";






CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA "extensions";






CREATE OR REPLACE FUNCTION "public"."auto_refresh_aggregates_trigger"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
  DECLARE
      affected_season INTEGER;
      result RECORD;
  BEGIN
      -- Get the season from the new data
      IF TG_OP = 'INSERT' OR TG_OP = 'UPDATE' THEN
          -- For INSERT operations, we need to find the season from the inserted data
          SELECT DISTINCT season INTO affected_season
          FROM raw_play_data
          WHERE ctid = ANY(ARRAY(SELECT ctid FROM inserted_rows))
          LIMIT 1;
      ELSIF TG_OP = 'DELETE' THEN
          affected_season := OLD.season;
      END IF;

      -- Only refresh if we have a valid season
      IF affected_season IS NOT NULL THEN
          -- Log the refresh attempt
          RAISE NOTICE 'Auto-refreshing aggregates for season %',
  affected_season;

          -- Use the simple (non-concurrent) version for triggers
          SELECT * INTO result FROM
  refresh_season_aggregates_simple(affected_season);

          RAISE NOTICE 'Refresh result: %', result.message;
      END IF;

      RETURN NULL; -- For AFTER trigger
  EXCEPTION
      WHEN OTHERS THEN
          -- Log error but don't fail the transaction
          RAISE NOTICE 'Error in auto-refresh trigger: %', SQLERRM;
          RETURN NULL;
  END;
  $$;


ALTER FUNCTION "public"."auto_refresh_aggregates_trigger"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."refresh_all_aggregates"() RETURNS TABLE("views_refreshed" integer, "message" "text")
    LANGUAGE "plpgsql"
    AS $$
  DECLARE
      refresh_count INTEGER := 0;
      start_time TIMESTAMP;
      end_time TIMESTAMP;
      duration_ms INTEGER;
  BEGIN
      start_time := clock_timestamp();

      -- Refresh team game aggregates
      REFRESH MATERIALIZED VIEW team_game_aggregates;
      refresh_count := refresh_count + 1;

      -- Update refresh log
      INSERT INTO aggregate_refresh_log (view_name, last_refresh)
      VALUES ('team_game_aggregates', NOW())
      ON CONFLICT (view_name)
      DO UPDATE SET last_refresh = NOW();

      -- Refresh team season aggregates
      REFRESH MATERIALIZED VIEW team_season_aggregates;
      refresh_count := refresh_count + 1;

      end_time := clock_timestamp();
      duration_ms := EXTRACT(MILLISECONDS FROM (end_time -
  start_time))::INTEGER;

      -- Update refresh log
      INSERT INTO aggregate_refresh_log (view_name, last_refresh,
  refresh_duration_ms)
      VALUES ('team_season_aggregates', NOW(), duration_ms)
      ON CONFLICT (view_name)
      DO UPDATE SET
          last_refresh = NOW(),
          refresh_duration_ms = EXCLUDED.refresh_duration_ms;

      RETURN QUERY SELECT refresh_count,
          format('Successfully refreshed %s views in %s ms', refresh_count,
  duration_ms);
  EXCEPTION
      WHEN OTHERS THEN
          RETURN QUERY SELECT 0,
              format('Error refreshing views: %s', SQLERRM);
  END;
  $$;


ALTER FUNCTION "public"."refresh_all_aggregates"() OWNER TO "postgres";


COMMENT ON FUNCTION "public"."refresh_all_aggregates"() IS 'Refreshes all materialized views. Returns number of views refreshed and 
  status message.';



CREATE OR REPLACE FUNCTION "public"."refresh_combined_season_stats"() RETURNS TABLE("message" "text", "rows_affected" integer)
    LANGUAGE "plpgsql"
    AS $$
  DECLARE
      start_time TIMESTAMP;
      end_time TIMESTAMP;
      duration_ms INTEGER;
      total_rows INTEGER;
  BEGIN
      start_time := clock_timestamp();

      -- Clear existing combined stats
      DELETE FROM team_season_combined_stats;

      -- Insert combined 'ALL' season type records using numeric comparisons
      INSERT INTO team_season_combined_stats (
          season, season_type, posteam, games_played, total_plays, total_yards,
  total_drives,
          total_rush_attempts, total_rush_yards, total_pass_attempts,
  total_completions,
          total_offensive_tds, total_extra_points, total_two_point_conversions,
  total_field_goals,
          total_interceptions, total_fumbles_lost, total_first_downs,
  total_third_down_attempts,
          total_third_down_conversions, total_sacks, total_penalty_yards,
  total_redzone_trips,
          total_redzone_tds, avg_success_rate, completion_pct, rush_ypc,
  third_down_pct
      )
      SELECT
          season,
          'ALL' as season_type,
          posteam,
          COUNT(DISTINCT game_id) as games_played,
          COUNT(*) as total_plays,
          SUM(yards_gained) as total_yards,
          COUNT(DISTINCT drive) as total_drives,

          -- Use numeric comparisons (1.0 = true, 0.0 = false)
          SUM(CASE WHEN rush_attempt = 1 THEN 1 ELSE 0 END) as
  total_rush_attempts,
          SUM(CASE WHEN rush_attempt = 1 THEN yards_gained ELSE 0 END) as
  total_rush_yards,

          SUM(CASE WHEN pass_attempt = 1 THEN 1 ELSE 0 END) as
  total_pass_attempts,
          SUM(CASE WHEN complete_pass = 1 THEN 1 ELSE 0 END) as
  total_completions,

          SUM(CASE WHEN touchdown = 1 AND td_team = posteam THEN 1 ELSE 0 END)
  as total_offensive_tds,
          SUM(CASE WHEN extra_point_result = 'good' THEN 1 ELSE 0 END) as
  total_extra_points,
          SUM(CASE WHEN two_point_conv_result = 'success' THEN 1 ELSE 0 END) as
  total_two_point_conversions,
          SUM(CASE WHEN field_goal_result = 'good' THEN 1 ELSE 0 END) as
  total_field_goals,

          SUM(CASE WHEN interception = 1 THEN 1 ELSE 0 END) as
  total_interceptions,
          SUM(CASE WHEN fumble_lost = 1 THEN 1 ELSE 0 END) as
  total_fumbles_lost,

          SUM(CASE WHEN first_down = 1 THEN 1 ELSE 0 END) as total_first_downs,

          SUM(CASE WHEN down = 3 THEN 1 ELSE 0 END) as
  total_third_down_attempts,
          SUM(CASE WHEN down = 3 AND first_down = 1 THEN 1 ELSE 0 END) as
  total_third_down_conversions,

          SUM(CASE WHEN sack = 1 THEN 1 ELSE 0 END) as total_sacks,

          SUM(CASE WHEN penalty = 1 AND penalty_team = posteam THEN
  penalty_yards ELSE 0 END) as total_penalty_yards,

          SUM(CASE WHEN yardline_100 <= 20 AND yardline_100 > 0 THEN 1 ELSE 0
  END) as total_redzone_trips,
          SUM(CASE WHEN yardline_100 <= 20 AND touchdown = 1 AND td_team =
  posteam THEN 1 ELSE 0 END) as total_redzone_tds,

          -- Success rate calculation
          AVG(CASE WHEN success IS NOT NULL THEN success ELSE NULL END) * 100 as
   avg_success_rate,

          -- Completion percentage
          CASE
              WHEN SUM(CASE WHEN pass_attempt = 1 THEN 1 ELSE 0 END) > 0
              THEN (SUM(CASE WHEN complete_pass = 1 THEN 1 ELSE 0 END)::float /
                    SUM(CASE WHEN pass_attempt = 1 THEN 1 ELSE 0 END)) * 100
              ELSE 0
          END as completion_pct,

          -- Rush yards per carry
          CASE
              WHEN SUM(CASE WHEN rush_attempt = 1 THEN 1 ELSE 0 END) > 0
              THEN SUM(CASE WHEN rush_attempt = 1 THEN yards_gained ELSE 0
  END)::float /
                   SUM(CASE WHEN rush_attempt = 1 THEN 1 ELSE 0 END)
              ELSE 0
          END as rush_ypc,

          -- Third down percentage
          CASE
              WHEN SUM(CASE WHEN down = 3 THEN 1 ELSE 0 END) > 0
              THEN (SUM(CASE WHEN down = 3 AND first_down = 1 THEN 1 ELSE 0
  END)::float /
                    SUM(CASE WHEN down = 3 THEN 1 ELSE 0 END)) * 100
              ELSE 0
          END as third_down_pct

      FROM raw_play_data
      WHERE posteam IS NOT NULL
        AND season_type IN ('REG', 'POST')
        AND play_type NOT IN ('no_play', 'timeout', 'extra_point')
        AND (qb_kneel IS NULL OR qb_kneel = 0)
      GROUP BY season, posteam;

      GET DIAGNOSTICS total_rows = ROW_COUNT;

      end_time := clock_timestamp();
      duration_ms := EXTRACT(EPOCH FROM (end_time - start_time)) * 1000;

      -- Update refresh log
      INSERT INTO aggregate_refresh_log (view_name, last_refresh,
  refresh_duration_ms, rows_affected)
      VALUES ('team_season_combined_stats', end_time, duration_ms, total_rows)
      ON CONFLICT (view_name)
      DO UPDATE SET
          last_refresh = EXCLUDED.last_refresh,
          refresh_duration_ms = EXCLUDED.refresh_duration_ms,
          rows_affected = EXCLUDED.rows_affected;

      RETURN QUERY SELECT
          FORMAT('Successfully created %s combined season records with all stats
   recalculated from raw data', total_rows)::TEXT as message,
          total_rows as rows_affected;
  END;
  $$;


ALTER FUNCTION "public"."refresh_combined_season_stats"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."refresh_season_aggregates"("target_season" integer) RETURNS TABLE("views_refreshed" integer, "message" "text")
    LANGUAGE "plpgsql"
    AS $$
  DECLARE
      refresh_count INTEGER := 0;
      use_concurrent BOOLEAN := true;
  BEGIN
      -- Check if season has data
      IF EXISTS (SELECT 1 FROM raw_play_data WHERE season = target_season LIMIT
  1) THEN
          -- Try concurrent refresh first, fall back to regular if it fails
          BEGIN
              -- Refresh team game aggregates
              REFRESH MATERIALIZED VIEW CONCURRENTLY team_game_aggregates;
              refresh_count := refresh_count + 1;
          EXCEPTION
              WHEN OTHERS THEN
                  -- Fall back to non-concurrent refresh
                  use_concurrent := false;
                  REFRESH MATERIALIZED VIEW team_game_aggregates;
                  refresh_count := refresh_count + 1;
          END;

          BEGIN
              -- Refresh team season aggregates
              IF use_concurrent THEN
                  REFRESH MATERIALIZED VIEW CONCURRENTLY team_season_aggregates;
              ELSE
                  REFRESH MATERIALIZED VIEW team_season_aggregates;
              END IF;
              refresh_count := refresh_count + 1;
          EXCEPTION
              WHEN OTHERS THEN
                  -- Fall back to non-concurrent refresh
                  REFRESH MATERIALIZED VIEW team_season_aggregates;
                  refresh_count := refresh_count + 1;
          END;

          -- Update refresh log
          INSERT INTO aggregate_refresh_log (view_name, rows_affected)
          VALUES ('team_season_aggregates',
                  (SELECT COUNT(*) FROM team_season_aggregates WHERE season =
  target_season))
          ON CONFLICT (view_name)
          DO UPDATE SET
              last_refresh = NOW(),
              rows_affected = EXCLUDED.rows_affected;

          INSERT INTO aggregate_refresh_log (view_name, rows_affected)
          VALUES ('team_game_aggregates',
                  (SELECT COUNT(*) FROM team_game_aggregates WHERE season =
  target_season))
          ON CONFLICT (view_name)
          DO UPDATE SET
              last_refresh = NOW(),
              rows_affected = EXCLUDED.rows_affected;

          IF use_concurrent THEN
              RETURN QUERY SELECT refresh_count,
                  format('Successfully refreshed %s views for season %s 
  (concurrent)', refresh_count, target_season);
          ELSE
              RETURN QUERY SELECT refresh_count,
                  format('Successfully refreshed %s views for season %s 
  (blocking)', refresh_count, target_season);
          END IF;
      ELSE
          RETURN QUERY SELECT 0,
              format('No data found for season %s - skipping refresh',
  target_season);
      END IF;
  EXCEPTION
      WHEN OTHERS THEN
          RETURN QUERY SELECT 0,
              format('Error refreshing views: %s', SQLERRM);
  END;
  $$;


ALTER FUNCTION "public"."refresh_season_aggregates"("target_season" integer) OWNER TO "postgres";


COMMENT ON FUNCTION "public"."refresh_season_aggregates"("target_season" integer) IS 'Refreshes materialized views for a specific season with concurrent 
  refresh if possible. Returns number of views refreshed and status message.';



CREATE OR REPLACE FUNCTION "public"."refresh_season_aggregates_simple"("target_season" integer) RETURNS TABLE("views_refreshed" integer, "message" "text")
    LANGUAGE "plpgsql"
    AS $$
  DECLARE
      refresh_count INTEGER := 0;
      start_time TIMESTAMP;
      end_time TIMESTAMP;
      duration_ms INTEGER;
      row_count INTEGER;
  BEGIN
      -- Check if season has data
      IF EXISTS (SELECT 1 FROM raw_play_data WHERE season = target_season LIMIT
  1) THEN
          start_time := clock_timestamp();

          -- Refresh team game aggregates (non-concurrent)
          REFRESH MATERIALIZED VIEW team_game_aggregates;
          refresh_count := refresh_count + 1;

          -- Count rows for this season
          SELECT COUNT(*) INTO row_count
          FROM team_game_aggregates
          WHERE season = target_season;

          -- Update refresh log for game aggregates
          INSERT INTO aggregate_refresh_log (view_name, last_refresh,
  rows_affected)
          VALUES ('team_game_aggregates', NOW(), row_count)
          ON CONFLICT (view_name)
          DO UPDATE SET
              last_refresh = NOW(),
              rows_affected = EXCLUDED.rows_affected;

          -- Refresh team season aggregates (non-concurrent)
          REFRESH MATERIALIZED VIEW team_season_aggregates;
          refresh_count := refresh_count + 1;

          -- Count rows for this season
          SELECT COUNT(*) INTO row_count
          FROM team_season_aggregates
          WHERE season = target_season;

          end_time := clock_timestamp();
          duration_ms := EXTRACT(MILLISECONDS FROM (end_time -
  start_time))::INTEGER;

          -- Update refresh log for season aggregates
          INSERT INTO aggregate_refresh_log (view_name, last_refresh,
  rows_affected, refresh_duration_ms)
          VALUES ('team_season_aggregates', NOW(), row_count, duration_ms)
          ON CONFLICT (view_name)
          DO UPDATE SET
              last_refresh = NOW(),
              rows_affected = EXCLUDED.rows_affected,
              refresh_duration_ms = EXCLUDED.refresh_duration_ms;

          RETURN QUERY SELECT refresh_count,
              format('Successfully refreshed %s views for season %s (%s ms)',
  refresh_count, target_season, duration_ms);
      ELSE
          RETURN QUERY SELECT 0,
              format('No data found for season %s - skipping refresh',
  target_season);
      END IF;
  EXCEPTION
      WHEN OTHERS THEN
          RETURN QUERY SELECT 0,
              format('Error refreshing views: %s', SQLERRM);
  END;
  $$;


ALTER FUNCTION "public"."refresh_season_aggregates_simple"("target_season" integer) OWNER TO "postgres";


COMMENT ON FUNCTION "public"."refresh_season_aggregates_simple"("target_season" integer) IS 'Refreshes materialized views for a specific season. Returns number of 
  views refreshed and status message.';



CREATE OR REPLACE FUNCTION "public"."refresh_team_aggregates"() RETURNS "void"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
    -- Refresh both views
    REFRESH MATERIALIZED VIEW team_game_aggregates;
    REFRESH MATERIALIZED VIEW team_season_aggregates;
    
    -- Update refresh log
    UPDATE aggregate_refresh_log 
    SET last_refresh = NOW() 
    WHERE view_name IN ('team_game_aggregates', 'team_season_aggregates');
    
    RETURN;
END;
$$;


ALTER FUNCTION "public"."refresh_team_aggregates"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."refresh_team_season_aggregates_with_combined"() RETURNS TABLE("message" "text", "rows_affected" integer)
    LANGUAGE "plpgsql"
    AS $$
  DECLARE
      start_time TIMESTAMP;
      end_time TIMESTAMP;
      duration_ms INTEGER;
      total_rows INTEGER;
  BEGIN
      start_time := clock_timestamp();

      -- Refresh the base materialized view first
      REFRESH MATERIALIZED VIEW team_season_aggregates;

      -- Now add the combined 'ALL' season type records
      -- This combines REG and POST data with proper success rate calculation
      INSERT INTO team_season_aggregates (
          season, season_type, posteam, games_played, total_plays, total_yards,
  total_drives,
          total_rush_attempts, total_rush_yards, total_pass_attempts,
  total_completions,
          total_offensive_tds, total_extra_points, total_two_point_conversions,
  total_field_goals,
          total_interceptions, total_fumbles_lost, total_first_downs,
  total_third_down_attempts,
          total_third_down_conversions, total_sacks, total_penalty_yards,
  total_redzone_trips,
          total_redzone_tds, avg_success_rate, completion_pct, rush_ypc,
  third_down_pct
      )
      WITH combined_stats AS (
          -- Combine REG and POST data for each team/season
          SELECT
              season,
              'ALL' as season_type,
              posteam,
              SUM(games_played) as games_played,
              SUM(total_plays) as total_plays,
              SUM(total_yards) as total_yards,
              SUM(total_drives) as total_drives,
              SUM(total_rush_attempts) as total_rush_attempts,
              SUM(total_rush_yards) as total_rush_yards,
              SUM(total_pass_attempts) as total_pass_attempts,
              SUM(total_completions) as total_completions,
              SUM(total_offensive_tds) as total_offensive_tds,
              SUM(total_extra_points) as total_extra_points,
              SUM(total_two_point_conversions) as total_two_point_conversions,
              SUM(total_field_goals) as total_field_goals,
              SUM(total_interceptions) as total_interceptions,
              SUM(total_fumbles_lost) as total_fumbles_lost,
              SUM(total_first_downs) as total_first_downs,
              SUM(total_third_down_attempts) as total_third_down_attempts,
              SUM(total_third_down_conversions) as total_third_down_conversions,
              SUM(total_sacks) as total_sacks,
              SUM(total_penalty_yards) as total_penalty_yards,
              SUM(total_redzone_trips) as total_redzone_trips,
              SUM(total_redzone_tds) as total_redzone_tds
          FROM team_season_aggregates
          WHERE season_type IN ('REG', 'POST')
          GROUP BY season, posteam
          HAVING COUNT(DISTINCT season_type) > 0  -- At least one season type
      ),
      calculated_rates AS (
          SELECT *,
              -- Recalculate success rate from raw data for combined season
              (SELECT AVG(CASE WHEN success IS NOT NULL THEN success::int ELSE
  NULL END) * 100
               FROM raw_play_data
               WHERE posteam = combined_stats.posteam
                 AND season = combined_stats.season
                 AND season_type IN ('REG', 'POST')
                 AND play_type NOT IN ('no_play', 'timeout', 'extra_point')
                 AND qb_kneel = false
              ) as avg_success_rate,

              -- Recalculate other rates from combined totals
              CASE
                  WHEN total_pass_attempts > 0
                  THEN (total_completions::NUMERIC / total_pass_attempts * 100)
                  ELSE 0
              END as completion_pct,

              CASE
                  WHEN total_rush_attempts > 0
                  THEN (total_rush_yards::NUMERIC / total_rush_attempts)
                  ELSE 0
              END as rush_ypc,

              CASE
                  WHEN total_third_down_attempts > 0
                  THEN (total_third_down_conversions::NUMERIC /
  total_third_down_attempts * 100)
                  ELSE 0
              END as third_down_pct

          FROM combined_stats
      )
      SELECT * FROM calculated_rates
      ON CONFLICT (season, season_type, posteam)
      DO UPDATE SET
          games_played = EXCLUDED.games_played,
          total_plays = EXCLUDED.total_plays,
          total_yards = EXCLUDED.total_yards,
          total_drives = EXCLUDED.total_drives,
          total_rush_attempts = EXCLUDED.total_rush_attempts,
          total_rush_yards = EXCLUDED.total_rush_yards,
          total_pass_attempts = EXCLUDED.total_pass_attempts,
          total_completions = EXCLUDED.total_completions,
          total_offensive_tds = EXCLUDED.total_offensive_tds,
          total_extra_points = EXCLUDED.total_extra_points,
          total_two_point_conversions = EXCLUDED.total_two_point_conversions,
          total_field_goals = EXCLUDED.total_field_goals,
          total_interceptions = EXCLUDED.total_interceptions,
          total_fumbles_lost = EXCLUDED.total_fumbles_lost,
          total_first_downs = EXCLUDED.total_first_downs,
          total_third_down_attempts = EXCLUDED.total_third_down_attempts,
          total_third_down_conversions = EXCLUDED.total_third_down_conversions,
          total_sacks = EXCLUDED.total_sacks,
          total_penalty_yards = EXCLUDED.total_penalty_yards,
          total_redzone_trips = EXCLUDED.total_redzone_trips,
          total_redzone_tds = EXCLUDED.total_redzone_tds,
          avg_success_rate = EXCLUDED.avg_success_rate,
          completion_pct = EXCLUDED.completion_pct,
          rush_ypc = EXCLUDED.rush_ypc,
          third_down_pct = EXCLUDED.third_down_pct;

      GET DIAGNOSTICS total_rows = ROW_COUNT;

      end_time := clock_timestamp();
      duration_ms := EXTRACT(EPOCH FROM (end_time - start_time)) * 1000;

      -- Update refresh log
      INSERT INTO aggregate_refresh_log (view_name, last_refresh,
  refresh_duration_ms, rows_affected)
      VALUES ('team_season_aggregates', end_time, duration_ms, total_rows)
      ON CONFLICT (view_name)
      DO UPDATE SET
          last_refresh = EXCLUDED.last_refresh,
          refresh_duration_ms = EXCLUDED.refresh_duration_ms,
          rows_affected = EXCLUDED.rows_affected;

      RETURN QUERY SELECT
          FORMAT('Successfully refreshed team_season_aggregates with %s combined
   season records', total_rows)::TEXT as message,
          total_rows as rows_affected;
  END;
  $$;


ALTER FUNCTION "public"."refresh_team_season_aggregates_with_combined"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."update_updated_at_column"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
  BEGIN
      NEW.updated_at = NOW();
      RETURN NEW;
  END;
  $$;


ALTER FUNCTION "public"."update_updated_at_column"() OWNER TO "postgres";

SET default_tablespace = '';

SET default_table_access_method = "heap";


CREATE TABLE IF NOT EXISTS "public"."aggregate_refresh_log" (
    "view_name" character varying(100) NOT NULL,
    "last_refresh" timestamp with time zone DEFAULT "now"(),
    "rows_affected" integer,
    "refresh_duration_ms" integer
);


ALTER TABLE "public"."aggregate_refresh_log" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."raw_play_data" (
    "game_id" character varying(50) NOT NULL,
    "play_id" double precision NOT NULL,
    "season" integer NOT NULL,
    "season_type" character varying(20),
    "week" integer,
    "game_date" "date",
    "home_team" character varying(5),
    "away_team" character varying(5),
    "posteam" character varying(5),
    "defteam" character varying(5),
    "quarter" double precision,
    "down" double precision,
    "ydstogo" double precision,
    "yardline_100" double precision,
    "play_type" character varying(50),
    "yards_gained" double precision,
    "touchdown" double precision,
    "first_down" double precision,
    "rush_attempt" double precision,
    "pass_attempt" double precision,
    "sack" double precision,
    "fumble" double precision,
    "interception" double precision,
    "penalty" double precision,
    "two_point_attempt" double precision,
    "fumble_lost" double precision,
    "extra_point_result" character varying(20),
    "two_point_conv_result" character varying(20),
    "field_goal_result" character varying(20),
    "first_down_rush" double precision,
    "first_down_pass" double precision,
    "first_down_penalty" double precision,
    "penalty_team" character varying(5),
    "drive" double precision,
    "complete_pass" double precision,
    "incomplete_pass" double precision,
    "pass_touchdown" double precision,
    "rush_touchdown" double precision,
    "passing_yards" double precision,
    "rushing_yards" double precision,
    "receiving_yards" double precision,
    "td_team" character varying(5),
    "penalty_yards" double precision DEFAULT 0,
    "success" double precision,
    "epa" double precision,
    "posteam_score_post" double precision,
    "defteam_score_post" double precision,
    "qb_kneel" boolean DEFAULT false,
    "nfl_data_timestamp" timestamp with time zone
);


ALTER TABLE "public"."raw_play_data" OWNER TO "postgres";


CREATE MATERIALIZED VIEW "public"."team_game_aggregates" AS
 SELECT "season",
    "week",
    "game_id",
    "posteam",
    "home_team",
    "away_team",
    "game_date",
    "count"(*) AS "total_plays",
    "sum"("yards_gained") AS "total_yards",
    "count"(DISTINCT
        CASE
            WHEN ("drive" IS NOT NULL) THEN "drive"
            ELSE NULL::double precision
        END) AS "total_drives",
    "count"(
        CASE
            WHEN ("rush_attempt" = (1)::double precision) THEN 1
            ELSE NULL::integer
        END) AS "total_rush_attempts",
    "sum"(
        CASE
            WHEN ("rush_attempt" = (1)::double precision) THEN "yards_gained"
            ELSE (0)::double precision
        END) AS "total_rush_yards",
    "count"(
        CASE
            WHEN ("pass_attempt" = (1)::double precision) THEN 1
            ELSE NULL::integer
        END) AS "total_pass_attempts",
    "count"(
        CASE
            WHEN ("complete_pass" = (1)::double precision) THEN 1
            ELSE NULL::integer
        END) AS "total_completions",
    "count"(
        CASE
            WHEN (("touchdown" = (1)::double precision) AND (("td_team")::"text" = ("posteam")::"text")) THEN 1
            ELSE NULL::integer
        END) AS "total_offensive_tds",
    "count"(
        CASE
            WHEN (("extra_point_result")::"text" = 'good'::"text") THEN 1
            ELSE NULL::integer
        END) AS "total_extra_points",
    "count"(
        CASE
            WHEN (("two_point_conv_result")::"text" = 'success'::"text") THEN 1
            ELSE NULL::integer
        END) AS "total_two_point_conversions",
    "count"(
        CASE
            WHEN (("field_goal_result")::"text" = 'made'::"text") THEN 1
            ELSE NULL::integer
        END) AS "total_field_goals",
    "count"(
        CASE
            WHEN ("interception" = (1)::double precision) THEN 1
            ELSE NULL::integer
        END) AS "total_interceptions",
    "count"(
        CASE
            WHEN ("fumble_lost" = (1)::double precision) THEN 1
            ELSE NULL::integer
        END) AS "total_fumbles_lost",
    "count"(
        CASE
            WHEN (("first_down_rush" = (1)::double precision) OR ("first_down_pass" = (1)::double precision) OR ("first_down_penalty" = (1)::double precision)) THEN 1
            ELSE NULL::integer
        END) AS "total_first_downs",
    "count"(
        CASE
            WHEN ("down" = (3)::double precision) THEN 1
            ELSE NULL::integer
        END) AS "total_third_down_attempts",
    "count"(
        CASE
            WHEN (("down" = (3)::double precision) AND (("first_down" = (1)::double precision) OR ("touchdown" = (1)::double precision))) THEN 1
            ELSE NULL::integer
        END) AS "total_third_down_conversions",
    "count"(
        CASE
            WHEN ("sack" = (1)::double precision) THEN 1
            ELSE NULL::integer
        END) AS "total_sacks",
    "sum"(
        CASE
            WHEN ((("penalty_team")::"text" = ("posteam")::"text") AND (("posteam")::"text" = ("posteam")::"text")) THEN "penalty_yards"
            ELSE (0)::double precision
        END) AS "total_penalty_yards",
    "count"(DISTINCT
        CASE
            WHEN (("yardline_100" <= (20)::double precision) AND ("yardline_100" > (0)::double precision) AND ("drive" IS NOT NULL)) THEN "drive"
            ELSE NULL::double precision
        END) AS "total_redzone_trips",
    "count"(DISTINCT
        CASE
            WHEN (("yardline_100" <= (20)::double precision) AND ("yardline_100" > (0)::double precision) AND ("drive" IS NOT NULL) AND ("touchdown" = (1)::double precision)) THEN "drive"
            ELSE NULL::double precision
        END) AS "total_redzone_tds",
    "avg"(
        CASE
            WHEN ("success" = (1)::double precision) THEN 1.0
            ELSE 0.0
        END) AS "avg_success_rate",
    ("avg"(
        CASE
            WHEN (("pass_attempt" = (1)::double precision) AND ("complete_pass" = (1)::double precision)) THEN 1.0
            WHEN ("pass_attempt" = (1)::double precision) THEN 0.0
            ELSE NULL::numeric
        END) * (100)::numeric) AS "completion_pct",
    "avg"(
        CASE
            WHEN ("rush_attempt" = (1)::double precision) THEN "yards_gained"
            ELSE NULL::double precision
        END) AS "rush_ypc",
    ("avg"(
        CASE
            WHEN (("down" = (3)::double precision) AND (("first_down" = (1)::double precision) OR ("touchdown" = (1)::double precision))) THEN 1.0
            WHEN ("down" = (3)::double precision) THEN 0.0
            ELSE NULL::numeric
        END) * (100)::numeric) AS "third_down_pct"
   FROM "public"."raw_play_data"
  WHERE ("posteam" IS NOT NULL)
  GROUP BY "season", "week", "game_id", "posteam", "home_team", "away_team", "game_date"
  ORDER BY "season" DESC, "week" DESC, "game_id", "posteam"
  WITH NO DATA;


ALTER MATERIALIZED VIEW "public"."team_game_aggregates" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."team_game_stats" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "season" integer NOT NULL,
    "week" integer NOT NULL,
    "team_abbr" character varying(3) NOT NULL,
    "opponent_abbr" character varying(3) NOT NULL,
    "game_date" "date" NOT NULL,
    "game_id" character varying(20),
    "location" character varying(10),
    "yards_per_play" numeric(4,2),
    "total_yards" integer,
    "total_plays" integer,
    "turnovers" integer,
    "completion_pct" numeric(5,2),
    "rush_ypc" numeric(4,2),
    "sacks_allowed" integer,
    "third_down_pct" numeric(5,2),
    "success_rate" numeric(5,2),
    "first_downs" integer,
    "points_per_drive" numeric(4,2),
    "redzone_td_pct" numeric(5,2),
    "penalty_yards" integer,
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."team_game_stats" OWNER TO "postgres";


COMMENT ON TABLE "public"."team_game_stats" IS 'Game-by-game statistics for detailed 
  analysis';



CREATE MATERIALIZED VIEW "public"."team_season_aggregates" AS
 SELECT "season",
    "season_type",
    "posteam",
    "count"(DISTINCT "game_id") AS "games_played",
    "count"(*) AS "total_plays",
    "sum"("yards_gained") AS "total_yards",
    "count"(DISTINCT
        CASE
            WHEN ("drive" IS NOT NULL) THEN "concat"("game_id", '_', "drive")
            ELSE NULL::"text"
        END) AS "total_drives",
    "count"(
        CASE
            WHEN ("rush_attempt" = (1)::double precision) THEN 1
            ELSE NULL::integer
        END) AS "total_rush_attempts",
    "sum"(
        CASE
            WHEN ("rush_attempt" = (1)::double precision) THEN "yards_gained"
            ELSE (0)::double precision
        END) AS "total_rush_yards",
    "count"(
        CASE
            WHEN ("pass_attempt" = (1)::double precision) THEN 1
            ELSE NULL::integer
        END) AS "total_pass_attempts",
    "count"(
        CASE
            WHEN ("complete_pass" = (1)::double precision) THEN 1
            ELSE NULL::integer
        END) AS "total_completions",
    "count"(
        CASE
            WHEN (("touchdown" = (1)::double precision) AND (("td_team")::"text" = ("posteam")::"text")) THEN 1
            ELSE NULL::integer
        END) AS "total_offensive_tds",
    "count"(
        CASE
            WHEN (("extra_point_result")::"text" = 'good'::"text") THEN 1
            ELSE NULL::integer
        END) AS "total_extra_points",
    "count"(
        CASE
            WHEN (("two_point_conv_result")::"text" = 'success'::"text") THEN 1
            ELSE NULL::integer
        END) AS "total_two_point_conversions",
    "count"(
        CASE
            WHEN (("field_goal_result")::"text" = 'made'::"text") THEN 1
            ELSE NULL::integer
        END) AS "total_field_goals",
    "count"(
        CASE
            WHEN ("interception" = (1)::double precision) THEN 1
            ELSE NULL::integer
        END) AS "total_interceptions",
    "count"(
        CASE
            WHEN ("fumble_lost" = (1)::double precision) THEN 1
            ELSE NULL::integer
        END) AS "total_fumbles_lost",
    "count"(
        CASE
            WHEN (("first_down_rush" = (1)::double precision) OR ("first_down_pass" = (1)::double precision) OR ("first_down_penalty" = (1)::double precision)) THEN 1
            ELSE NULL::integer
        END) AS "total_first_downs",
    "count"(
        CASE
            WHEN ("down" = (3)::double precision) THEN 1
            ELSE NULL::integer
        END) AS "total_third_down_attempts",
    "count"(
        CASE
            WHEN (("down" = (3)::double precision) AND (("first_down" = (1)::double precision) OR ("touchdown" = (1)::double precision))) THEN 1
            ELSE NULL::integer
        END) AS "total_third_down_conversions",
    "count"(
        CASE
            WHEN ("sack" = (1)::double precision) THEN 1
            ELSE NULL::integer
        END) AS "total_sacks",
    "sum"(
        CASE
            WHEN ((("penalty_team")::"text" = ("posteam")::"text") AND (("posteam")::"text" = ("posteam")::"text")) THEN "penalty_yards"
            ELSE (0)::double precision
        END) AS "total_penalty_yards",
    "count"(DISTINCT
        CASE
            WHEN (("yardline_100" <= (20)::double precision) AND ("yardline_100" > (0)::double precision) AND ("drive" IS NOT NULL)) THEN "concat"("game_id", '_', "drive")
            ELSE NULL::"text"
        END) AS "total_redzone_trips",
    "count"(DISTINCT
        CASE
            WHEN (("yardline_100" <= (20)::double precision) AND ("yardline_100" > (0)::double precision) AND ("drive" IS NOT NULL) AND ("touchdown" = (1)::double precision)) THEN "concat"("game_id", '_', "drive")
            ELSE NULL::"text"
        END) AS "total_redzone_tds",
    "avg"(
        CASE
            WHEN ("success" = (1)::double precision) THEN 1.0
            ELSE 0.0
        END) AS "avg_success_rate",
    ("avg"(
        CASE
            WHEN (("pass_attempt" = (1)::double precision) AND ("complete_pass" = (1)::double precision)) THEN 1.0
            WHEN ("pass_attempt" = (1)::double precision) THEN 0.0
            ELSE NULL::numeric
        END) * (100)::numeric) AS "completion_pct",
    "avg"(
        CASE
            WHEN ("rush_attempt" = (1)::double precision) THEN "yards_gained"
            ELSE NULL::double precision
        END) AS "rush_ypc",
    ("avg"(
        CASE
            WHEN (("down" = (3)::double precision) AND (("first_down" = (1)::double precision) OR ("touchdown" = (1)::double precision))) THEN 1.0
            WHEN ("down" = (3)::double precision) THEN 0.0
            ELSE NULL::numeric
        END) * (100)::numeric) AS "third_down_pct"
   FROM "public"."raw_play_data"
  WHERE ("posteam" IS NOT NULL)
  GROUP BY "season", "season_type", "posteam"
  ORDER BY "season" DESC, "posteam"
  WITH NO DATA;


ALTER MATERIALIZED VIEW "public"."team_season_aggregates" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."team_season_combined_stats" (
    "season" integer NOT NULL,
    "season_type" character varying(10) DEFAULT 'ALL'::character varying NOT NULL,
    "posteam" character varying(3) NOT NULL,
    "games_played" integer,
    "total_plays" integer,
    "total_yards" integer,
    "total_drives" integer,
    "total_rush_attempts" integer,
    "total_rush_yards" integer,
    "total_pass_attempts" integer,
    "total_completions" integer,
    "total_offensive_tds" integer,
    "total_extra_points" integer,
    "total_two_point_conversions" integer,
    "total_field_goals" integer,
    "total_interceptions" integer,
    "total_fumbles_lost" integer,
    "total_first_downs" integer,
    "total_third_down_attempts" integer,
    "total_third_down_conversions" integer,
    "total_sacks" integer,
    "total_penalty_yards" integer,
    "total_redzone_trips" integer,
    "total_redzone_tds" integer,
    "avg_success_rate" numeric(5,2),
    "completion_pct" numeric(5,2),
    "rush_ypc" numeric(4,2),
    "third_down_pct" numeric(5,2)
);


ALTER TABLE "public"."team_season_combined_stats" OWNER TO "postgres";


CREATE OR REPLACE VIEW "public"."team_season_aggregates_with_combined" AS
 SELECT "team_season_aggregates"."season",
    "team_season_aggregates"."season_type",
    "team_season_aggregates"."posteam",
    "team_season_aggregates"."games_played",
    "team_season_aggregates"."total_plays",
    "team_season_aggregates"."total_yards",
    "team_season_aggregates"."total_drives",
    "team_season_aggregates"."total_rush_attempts",
    "team_season_aggregates"."total_rush_yards",
    "team_season_aggregates"."total_pass_attempts",
    "team_season_aggregates"."total_completions",
    "team_season_aggregates"."total_offensive_tds",
    "team_season_aggregates"."total_extra_points",
    "team_season_aggregates"."total_two_point_conversions",
    "team_season_aggregates"."total_field_goals",
    "team_season_aggregates"."total_interceptions",
    "team_season_aggregates"."total_fumbles_lost",
    "team_season_aggregates"."total_first_downs",
    "team_season_aggregates"."total_third_down_attempts",
    "team_season_aggregates"."total_third_down_conversions",
    "team_season_aggregates"."total_sacks",
    "team_season_aggregates"."total_penalty_yards",
    "team_season_aggregates"."total_redzone_trips",
    "team_season_aggregates"."total_redzone_tds",
    "team_season_aggregates"."avg_success_rate",
    "team_season_aggregates"."completion_pct",
    "team_season_aggregates"."rush_ypc",
    "team_season_aggregates"."third_down_pct"
   FROM "public"."team_season_aggregates"
UNION ALL
 SELECT "team_season_combined_stats"."season",
    "team_season_combined_stats"."season_type",
    "team_season_combined_stats"."posteam",
    "team_season_combined_stats"."games_played",
    "team_season_combined_stats"."total_plays",
    "team_season_combined_stats"."total_yards",
    "team_season_combined_stats"."total_drives",
    "team_season_combined_stats"."total_rush_attempts",
    "team_season_combined_stats"."total_rush_yards",
    "team_season_combined_stats"."total_pass_attempts",
    "team_season_combined_stats"."total_completions",
    "team_season_combined_stats"."total_offensive_tds",
    "team_season_combined_stats"."total_extra_points",
    "team_season_combined_stats"."total_two_point_conversions",
    "team_season_combined_stats"."total_field_goals",
    "team_season_combined_stats"."total_interceptions",
    "team_season_combined_stats"."total_fumbles_lost",
    "team_season_combined_stats"."total_first_downs",
    "team_season_combined_stats"."total_third_down_attempts",
    "team_season_combined_stats"."total_third_down_conversions",
    "team_season_combined_stats"."total_sacks",
    "team_season_combined_stats"."total_penalty_yards",
    "team_season_combined_stats"."total_redzone_trips",
    "team_season_combined_stats"."total_redzone_tds",
    "team_season_combined_stats"."avg_success_rate",
    "team_season_combined_stats"."completion_pct",
    "team_season_combined_stats"."rush_ypc",
    "team_season_combined_stats"."third_down_pct"
   FROM "public"."team_season_combined_stats";


ALTER VIEW "public"."team_season_aggregates_with_combined" OWNER TO "postgres";


CREATE MATERIALIZED VIEW "public"."team_season_stats_complete" AS
 SELECT "season",
    "season_type",
    "posteam",
    "count"(DISTINCT "game_id") AS "games_played",
    "count"(*) AS "total_plays",
    "sum"("yards_gained") AS "total_yards",
    "count"(DISTINCT
        CASE
            WHEN ("drive" IS NOT NULL) THEN "concat"("game_id", '_', "drive")
            ELSE NULL::"text"
        END) AS "total_drives",
    "sum"(
        CASE
            WHEN ("rush_attempt" = (1)::double precision) THEN 1
            ELSE 0
        END) AS "total_rush_attempts",
    "sum"(
        CASE
            WHEN ("rush_attempt" = (1)::double precision) THEN "yards_gained"
            ELSE (0)::double precision
        END) AS "total_rush_yards",
    "sum"(
        CASE
            WHEN ("pass_attempt" = (1)::double precision) THEN 1
            ELSE 0
        END) AS "total_pass_attempts",
    "sum"(
        CASE
            WHEN ("complete_pass" = (1)::double precision) THEN 1
            ELSE 0
        END) AS "total_completions",
    "sum"(
        CASE
            WHEN (("touchdown" = (1)::double precision) AND (("td_team")::"text" = ("posteam")::"text")) THEN 1
            ELSE 0
        END) AS "total_offensive_tds",
    "sum"(
        CASE
            WHEN (("extra_point_result")::"text" = 'good'::"text") THEN 1
            ELSE 0
        END) AS "total_extra_points",
    "sum"(
        CASE
            WHEN (("two_point_conv_result")::"text" = 'success'::"text") THEN 1
            ELSE 0
        END) AS "total_two_point_conversions",
    "sum"(
        CASE
            WHEN (("field_goal_result")::"text" = 'made'::"text") THEN 1
            ELSE 0
        END) AS "total_field_goals",
    "sum"(
        CASE
            WHEN ("interception" = (1)::double precision) THEN 1
            ELSE 0
        END) AS "total_interceptions",
    "sum"(
        CASE
            WHEN ("fumble_lost" = (1)::double precision) THEN 1
            ELSE 0
        END) AS "total_fumbles_lost",
    "sum"(
        CASE
            WHEN ("sack" = (1)::double precision) THEN 1
            ELSE 0
        END) AS "total_sacks",
    "sum"(
        CASE
            WHEN ("first_down" = (1)::double precision) THEN 1
            ELSE 0
        END) AS "total_first_downs",
    "sum"(
        CASE
            WHEN ("first_down_rush" = (1)::double precision) THEN 1
            ELSE 0
        END) AS "total_first_downs_rush",
    "sum"(
        CASE
            WHEN ("first_down_pass" = (1)::double precision) THEN 1
            ELSE 0
        END) AS "total_first_downs_pass",
    "sum"(
        CASE
            WHEN ("first_down_penalty" = (1)::double precision) THEN 1
            ELSE 0
        END) AS "total_first_downs_penalty",
    "sum"(
        CASE
            WHEN ("down" = (3)::double precision) THEN 1
            ELSE 0
        END) AS "total_third_down_attempts",
    "sum"(
        CASE
            WHEN (("down" = (3)::double precision) AND (("first_down" = (1)::double precision) OR ("touchdown" = (1)::double precision))) THEN 1
            ELSE 0
        END) AS "total_third_down_conversions",
    "sum"(
        CASE
            WHEN (("penalty" = (1)::double precision) AND (("penalty_team")::"text" = ("posteam")::"text")) THEN "penalty_yards"
            ELSE (0)::double precision
        END) AS "total_penalty_yards",
    "count"(DISTINCT
        CASE
            WHEN (("yardline_100" <= (20)::double precision) AND ("yardline_100" > (0)::double precision) AND ("drive" IS NOT NULL)) THEN "concat"("game_id", '_', "drive")
            ELSE NULL::"text"
        END) AS "total_redzone_trips",
    "count"(DISTINCT
        CASE
            WHEN (("yardline_100" <= (20)::double precision) AND ("yardline_100" > (0)::double precision) AND ("drive" IS NOT NULL) AND ("touchdown" = (1)::double precision)) THEN "concat"("game_id", '_', "drive")
            ELSE NULL::"text"
        END) AS "total_redzone_tds",
    "sum"(
        CASE
            WHEN (("down" = (1)::double precision) AND ("success" = (1)::double precision)) THEN 1
            ELSE 0
        END) AS "first_down_successful_plays",
    "sum"(
        CASE
            WHEN ("down" = (1)::double precision) THEN 1
            ELSE 0
        END) AS "first_down_total_plays",
    "sum"(
        CASE
            WHEN (("down" = (2)::double precision) AND ("success" = (1)::double precision)) THEN 1
            ELSE 0
        END) AS "second_down_successful_plays",
    "sum"(
        CASE
            WHEN ("down" = (2)::double precision) THEN 1
            ELSE 0
        END) AS "second_down_total_plays",
    "sum"(
        CASE
            WHEN (("down" >= (3)::double precision) AND ("success" = (1)::double precision)) THEN 1
            ELSE 0
        END) AS "third_down_successful_plays",
    "sum"(
        CASE
            WHEN ("down" >= (3)::double precision) THEN 1
            ELSE 0
        END) AS "third_down_total_plays",
    "sum"(
        CASE
            WHEN (("down" = (3)::double precision) AND (("first_down" = (1)::double precision) OR ("touchdown" = (1)::double precision)) AND ("rush_attempt" = (1)::double precision)) THEN 1
            ELSE 0
        END) AS "total_third_down_rush_conversions",
    "sum"(
        CASE
            WHEN (("down" = (3)::double precision) AND (("first_down" = (1)::double precision) OR ("touchdown" = (1)::double precision)) AND ("pass_attempt" = (1)::double precision)) THEN 1
            ELSE 0
        END) AS "total_third_down_pass_conversions",
    "sum"(
        CASE
            WHEN (("yardline_100" <= (20)::double precision) AND (("field_goal_result")::"text" = 'made'::"text")) THEN 1
            ELSE 0
        END) AS "total_redzone_field_goals",
    (("count"(DISTINCT
        CASE
            WHEN (("yardline_100" <= (20)::double precision) AND ("yardline_100" > (0)::double precision) AND ("drive" IS NOT NULL)) THEN "concat"("game_id", '_', "drive")
            ELSE NULL::"text"
        END) - "count"(DISTINCT
        CASE
            WHEN (("yardline_100" <= (20)::double precision) AND ("yardline_100" > (0)::double precision) AND ("drive" IS NOT NULL) AND ("touchdown" = (1)::double precision)) THEN "concat"("game_id", '_', "drive")
            ELSE NULL::"text"
        END)) - "count"(DISTINCT
        CASE
            WHEN (("yardline_100" <= (20)::double precision) AND ("yardline_100" > (0)::double precision) AND ("drive" IS NOT NULL) AND (EXISTS ( SELECT 1
               FROM "public"."raw_play_data" "rp2"
              WHERE ((("rp2"."game_id")::"text" = ("raw_play_data"."game_id")::"text") AND ("rp2"."drive" = "raw_play_data"."drive") AND (("rp2"."field_goal_result")::"text" = 'made'::"text"))))) THEN "concat"("game_id", '_', "drive")
            ELSE NULL::"text"
        END)) AS "total_redzone_failed",
    "avg"(
        CASE
            WHEN ("success" IS NOT NULL) THEN "success"
            ELSE NULL::double precision
        END) AS "avg_success_rate",
        CASE
            WHEN ("sum"(
            CASE
                WHEN ("pass_attempt" = (1)::double precision) THEN 1
                ELSE 0
            END) > 0) THEN ((("sum"(
            CASE
                WHEN ("complete_pass" = (1)::double precision) THEN 1
                ELSE 0
            END))::double precision / ("sum"(
            CASE
                WHEN ("pass_attempt" = (1)::double precision) THEN 1
                ELSE 0
            END))::double precision) * (100)::double precision)
            ELSE (0)::double precision
        END AS "completion_pct",
        CASE
            WHEN ("sum"(
            CASE
                WHEN ("rush_attempt" = (1)::double precision) THEN 1
                ELSE 0
            END) > 0) THEN ("sum"(
            CASE
                WHEN ("rush_attempt" = (1)::double precision) THEN "yards_gained"
                ELSE (0)::double precision
            END) / ("sum"(
            CASE
                WHEN ("rush_attempt" = (1)::double precision) THEN 1
                ELSE 0
            END))::double precision)
            ELSE (0)::double precision
        END AS "rush_ypc",
        CASE
            WHEN ("sum"(
            CASE
                WHEN ("down" = (3)::double precision) THEN 1
                ELSE 0
            END) > 0) THEN ((("sum"(
            CASE
                WHEN (("down" = (3)::double precision) AND (("first_down" = (1)::double precision) OR ("touchdown" = (1)::double precision))) THEN 1
                ELSE 0
            END))::double precision / ("sum"(
            CASE
                WHEN ("down" = (3)::double precision) THEN 1
                ELSE 0
            END))::double precision) * (100)::double precision)
            ELSE (0)::double precision
        END AS "third_down_pct"
   FROM "public"."raw_play_data"
  WHERE (("posteam" IS NOT NULL) AND (("play_type")::"text" <> ALL ((ARRAY['no_play'::character varying, 'timeout'::character varying, 'extra_point'::character varying])::"text"[])) AND (("qb_kneel" IS NULL) OR ("qb_kneel" = false)))
  GROUP BY "season", "season_type", "posteam"
  ORDER BY "season" DESC, "posteam"
  WITH NO DATA;


ALTER MATERIALIZED VIEW "public"."team_season_stats_complete" OWNER TO "postgres";


COMMENT ON MATERIALIZED VIEW "public"."team_season_stats_complete" IS 'Comprehensive team season statistics including detailed breakdowns for methodology display. 
Consolidates and replaces: team_season_aggregates, team_season_combined_stats, team_season_aggregates_with_combined';



ALTER TABLE ONLY "public"."aggregate_refresh_log"
    ADD CONSTRAINT "aggregate_refresh_log_pkey" PRIMARY KEY ("view_name");



ALTER TABLE ONLY "public"."raw_play_data"
    ADD CONSTRAINT "raw_play_data_pkey" PRIMARY KEY ("game_id", "play_id");



ALTER TABLE ONLY "public"."team_game_stats"
    ADD CONSTRAINT "team_game_stats_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."team_game_stats"
    ADD CONSTRAINT "team_game_stats_season_week_team_abbr_game_date_key" UNIQUE ("season", "week", "team_abbr", "game_date");



ALTER TABLE ONLY "public"."team_season_combined_stats"
    ADD CONSTRAINT "team_season_combined_stats_pkey" PRIMARY KEY ("season", "season_type", "posteam");



CREATE INDEX "idx_raw_play_data_down_distance" ON "public"."raw_play_data" USING "btree" ("down", "ydstogo", "season");



CREATE INDEX "idx_raw_play_data_game_date" ON "public"."raw_play_data" USING "btree" ("game_date");



CREATE INDEX "idx_raw_play_data_game_lookup" ON "public"."raw_play_data" USING "btree" ("game_id", "posteam");



CREATE INDEX "idx_raw_play_data_nfl_timestamp" ON "public"."raw_play_data" USING "btree" ("nfl_data_timestamp");



CREATE INDEX "idx_raw_play_data_play_order" ON "public"."raw_play_data" USING "btree" ("game_date", "game_id", "play_id");



CREATE INDEX "idx_raw_play_data_posteam" ON "public"."raw_play_data" USING "btree" ("posteam");



CREATE INDEX "idx_raw_play_data_season" ON "public"."raw_play_data" USING "btree" ("season");



CREATE INDEX "idx_raw_play_data_season_count" ON "public"."raw_play_data" USING "btree" ("season") INCLUDE ("game_id");



COMMENT ON INDEX "public"."idx_raw_play_data_season_count" IS 'Optimized for count queries';



CREATE INDEX "idx_raw_play_data_season_lookup" ON "public"."raw_play_data" USING "btree" ("season", "season_type", "posteam");



CREATE INDEX "idx_raw_play_data_season_only" ON "public"."raw_play_data" USING "btree" ("season");



CREATE INDEX "idx_raw_play_data_season_ordered" ON "public"."raw_play_data" USING "btree" ("season", "game_date", "game_id", "play_id");



COMMENT ON INDEX "public"."idx_raw_play_data_season_ordered" IS 'Primary index for full season queries with proper ordering';



CREATE INDEX "idx_raw_play_data_season_posteam" ON "public"."raw_play_data" USING "btree" ("season", "posteam");



COMMENT ON INDEX "public"."idx_raw_play_data_season_posteam" IS 'Optimized for team-specific queries';



CREATE INDEX "idx_raw_play_data_season_team_notnull" ON "public"."raw_play_data" USING "btree" ("season", "posteam") WHERE (("posteam" IS NOT NULL) AND (TRIM(BOTH FROM "posteam") <> ''::"text"));



CREATE INDEX "idx_raw_play_data_season_timestamp" ON "public"."raw_play_data" USING "btree" ("season", "nfl_data_timestamp" DESC) WHERE ("nfl_data_timestamp" IS NOT NULL);



COMMENT ON INDEX "public"."idx_raw_play_data_season_timestamp" IS 'Optimized for data freshness checks';



CREATE INDEX "idx_raw_play_data_season_type" ON "public"."raw_play_data" USING "btree" ("season", "season_type");



CREATE INDEX "idx_raw_play_data_season_type_posteam" ON "public"."raw_play_data" USING "btree" ("season", "season_type", "posteam");



COMMENT ON INDEX "public"."idx_raw_play_data_season_type_posteam" IS 'Optimized for season type filtering';



CREATE INDEX "idx_raw_play_data_stats_calc" ON "public"."raw_play_data" USING "btree" ("season", "season_type", "posteam", "play_type") WHERE ("posteam" IS NOT NULL);



CREATE INDEX "idx_raw_play_data_stats_filter" ON "public"."raw_play_data" USING "btree" ("season", "season_type", "posteam", "play_type");



CREATE INDEX "idx_raw_play_data_success" ON "public"."raw_play_data" USING "btree" ("posteam", "season", "success") WHERE ("success" IS NOT NULL);



CREATE INDEX "idx_raw_play_data_team_season" ON "public"."raw_play_data" USING "btree" ("posteam", "season");



CREATE INDEX "idx_raw_play_data_teams_distinct" ON "public"."raw_play_data" USING "btree" ("posteam") WHERE (("posteam" IS NOT NULL) AND (TRIM(BOTH FROM "posteam") <> ''::"text"));



CREATE INDEX "idx_raw_play_data_timestamp" ON "public"."raw_play_data" USING "btree" ("nfl_data_timestamp");



CREATE INDEX "idx_team_game_aggregates_lookup" ON "public"."team_game_aggregates" USING "btree" ("season", "posteam", "game_id");



CREATE UNIQUE INDEX "idx_team_game_aggregates_unique" ON "public"."team_game_aggregates" USING "btree" ("season", "game_id", "posteam");



CREATE INDEX "idx_team_game_stats_team_season" ON "public"."team_game_stats" USING "btree" ("team_abbr", "season");



CREATE INDEX "idx_team_season_aggregates_lookup" ON "public"."team_season_aggregates" USING "btree" ("season", "season_type", "posteam");



CREATE UNIQUE INDEX "idx_team_season_aggregates_unique" ON "public"."team_season_aggregates" USING "btree" ("season", "season_type", "posteam");



CREATE INDEX "idx_team_season_stats_complete_lookup" ON "public"."team_season_stats_complete" USING "btree" ("season", "season_type", "posteam");



CREATE UNIQUE INDEX "idx_team_season_stats_complete_unique" ON "public"."team_season_stats_complete" USING "btree" ("season", "season_type", "posteam");



CREATE OR REPLACE TRIGGER "auto_refresh_aggregates_after_bulk_insert" AFTER INSERT ON "public"."raw_play_data" FOR EACH STATEMENT EXECUTE FUNCTION "public"."auto_refresh_aggregates_trigger"();



CREATE OR REPLACE TRIGGER "update_team_game_stats_updated_at" BEFORE UPDATE ON "public"."team_game_stats" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();



CREATE POLICY "Allow all operations on raw_play_data" ON "public"."raw_play_data" USING (true);



ALTER TABLE "public"."raw_play_data" ENABLE ROW LEVEL SECURITY;




ALTER PUBLICATION "supabase_realtime" OWNER TO "postgres";


GRANT USAGE ON SCHEMA "public" TO "postgres";
GRANT USAGE ON SCHEMA "public" TO "anon";
GRANT USAGE ON SCHEMA "public" TO "authenticated";
GRANT USAGE ON SCHEMA "public" TO "service_role";

























































































































































GRANT ALL ON FUNCTION "public"."auto_refresh_aggregates_trigger"() TO "anon";
GRANT ALL ON FUNCTION "public"."auto_refresh_aggregates_trigger"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."auto_refresh_aggregates_trigger"() TO "service_role";



GRANT ALL ON FUNCTION "public"."refresh_all_aggregates"() TO "anon";
GRANT ALL ON FUNCTION "public"."refresh_all_aggregates"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."refresh_all_aggregates"() TO "service_role";



GRANT ALL ON FUNCTION "public"."refresh_combined_season_stats"() TO "anon";
GRANT ALL ON FUNCTION "public"."refresh_combined_season_stats"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."refresh_combined_season_stats"() TO "service_role";



GRANT ALL ON FUNCTION "public"."refresh_season_aggregates"("target_season" integer) TO "anon";
GRANT ALL ON FUNCTION "public"."refresh_season_aggregates"("target_season" integer) TO "authenticated";
GRANT ALL ON FUNCTION "public"."refresh_season_aggregates"("target_season" integer) TO "service_role";



GRANT ALL ON FUNCTION "public"."refresh_season_aggregates_simple"("target_season" integer) TO "anon";
GRANT ALL ON FUNCTION "public"."refresh_season_aggregates_simple"("target_season" integer) TO "authenticated";
GRANT ALL ON FUNCTION "public"."refresh_season_aggregates_simple"("target_season" integer) TO "service_role";



GRANT ALL ON FUNCTION "public"."refresh_team_aggregates"() TO "anon";
GRANT ALL ON FUNCTION "public"."refresh_team_aggregates"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."refresh_team_aggregates"() TO "service_role";



GRANT ALL ON FUNCTION "public"."refresh_team_season_aggregates_with_combined"() TO "anon";
GRANT ALL ON FUNCTION "public"."refresh_team_season_aggregates_with_combined"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."refresh_team_season_aggregates_with_combined"() TO "service_role";



GRANT ALL ON FUNCTION "public"."update_updated_at_column"() TO "anon";
GRANT ALL ON FUNCTION "public"."update_updated_at_column"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."update_updated_at_column"() TO "service_role";


















GRANT ALL ON TABLE "public"."aggregate_refresh_log" TO "anon";
GRANT ALL ON TABLE "public"."aggregate_refresh_log" TO "authenticated";
GRANT ALL ON TABLE "public"."aggregate_refresh_log" TO "service_role";



GRANT ALL ON TABLE "public"."raw_play_data" TO "anon";
GRANT ALL ON TABLE "public"."raw_play_data" TO "authenticated";
GRANT ALL ON TABLE "public"."raw_play_data" TO "service_role";



GRANT ALL ON TABLE "public"."team_game_aggregates" TO "anon";
GRANT ALL ON TABLE "public"."team_game_aggregates" TO "authenticated";
GRANT ALL ON TABLE "public"."team_game_aggregates" TO "service_role";



GRANT ALL ON TABLE "public"."team_game_stats" TO "anon";
GRANT ALL ON TABLE "public"."team_game_stats" TO "authenticated";
GRANT ALL ON TABLE "public"."team_game_stats" TO "service_role";



GRANT ALL ON TABLE "public"."team_season_aggregates" TO "anon";
GRANT ALL ON TABLE "public"."team_season_aggregates" TO "authenticated";
GRANT ALL ON TABLE "public"."team_season_aggregates" TO "service_role";



GRANT ALL ON TABLE "public"."team_season_combined_stats" TO "anon";
GRANT ALL ON TABLE "public"."team_season_combined_stats" TO "authenticated";
GRANT ALL ON TABLE "public"."team_season_combined_stats" TO "service_role";



GRANT ALL ON TABLE "public"."team_season_aggregates_with_combined" TO "anon";
GRANT ALL ON TABLE "public"."team_season_aggregates_with_combined" TO "authenticated";
GRANT ALL ON TABLE "public"."team_season_aggregates_with_combined" TO "service_role";



GRANT ALL ON TABLE "public"."team_season_stats_complete" TO "anon";
GRANT ALL ON TABLE "public"."team_season_stats_complete" TO "authenticated";
GRANT ALL ON TABLE "public"."team_season_stats_complete" TO "service_role";









ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "service_role";






ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "service_role";






ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "service_role";






























RESET ALL;
