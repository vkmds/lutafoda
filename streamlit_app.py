import streamlit as st
import sqlite3
import pandas as pd
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "data/daily_stats.db")

# ========= DB HELPERS ========= #

def get_conn():
    return sqlite3.connect(DB_PATH)

@st.cache_data(ttl=300)
def get_available_dates():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT date FROM daily_summary ORDER BY date DESC")
    dates = [r[0] for r in cursor.fetchall()]
    conn.close()
    return ["Todos os Tempos"] + dates 

@st.cache_data(ttl=300)
def get_daily_summary(date_str):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT num_players, winner FROM daily_summary WHERE date = ?", (date_str,))
    row = cursor.fetchone()
    conn.close()
    return {"num_players": row[0], "winner": row[1]} if row else None

@st.cache_data(ttl=300)
def get_players(date_str):
    conn = get_conn()
    cursor = conn.cursor()
    if date_str == "Todos os Tempos":
        cursor.execute("SELECT DISTINCT player FROM player_stats ORDER BY player ASC")
    else:
        cursor.execute("SELECT player FROM player_stats WHERE date = ? ORDER BY player ASC", (date_str,))
    players = [r[0] for r in cursor.fetchall()]
    conn.close()
    return players


@st.cache_data(ttl=300)
def get_top_players(date_str, stat="kills", limit=10):
    conn = get_conn()
    cursor = conn.cursor()

    if date_str == "Todos os Tempos":
        cursor.execute(f"""
            SELECT player, SUM({stat}) as total_{stat}
            FROM player_stats
            GROUP BY player
            ORDER BY total_{stat} DESC
            LIMIT ?
        """, (limit,))
      
    else:
        cursor.execute(f"""
            SELECT player, {stat}
            FROM player_stats
            WHERE date = ?
            ORDER BY {stat} DESC
            LIMIT ?
        """, (date_str, limit))
    rows = cursor.fetchall()
    conn.close()
    if stat == "kills":
        col_name = "Eliminações"
    else:
        col_name = stat.capitalize()
    return pd.DataFrame(rows, columns=["Jogador", col_name])


@st.cache_data(ttl=300)
def get_player_stats(date_str, player):
    conn = get_conn()
    cursor = conn.cursor()
    if date_str == "Todos os Tempos":
        cursor.execute("""
            SELECT 
                SUM(kills), SUM(deaths),
                NULL, NULL
            FROM player_stats
            WHERE player = ?
        """, (player,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {
                "kills": row[0] or 0,
                "deaths": row[1] or 0,
                "nemesis": None,
                "victim": None,
            }
        return None
    else:
        cursor.execute("""
            SELECT kills, deaths, nemesis, victim
            FROM player_stats
            WHERE date = ? AND player = ?
        """, (date_str, player))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {
                "kills": row[0],
                "deaths": row[1],
                "nemesis": row[2],
                "victim": row[3],
            }
        return None

@st.cache_data(ttl=300)
def get_player_rank(date_str, player):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT rank FROM ranking WHERE date = ? AND player = ?
    """, (date_str, player))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

@st.cache_data(ttl=300)
def get_player_time(date_str, player):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT time FROM ranking WHERE date = ? AND player = ?
    """, (date_str, player))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

@st.cache_data(ttl=300)
def get_all_winners():
    """Return all winners per day."""
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT date, winner FROM daily_summary ORDER BY date DESC")
    rows = cursor.fetchall()
    conn.close()
    return pd.DataFrame(rows, columns=["Data", "Vencedor"])

@st.cache_data(ttl=300)
def get_wins_leaderboard(limit=10):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT winner AS player, COUNT(*) AS wins
        FROM daily_summary
        WHERE winner IS NOT NULL AND winner <> ''
        GROUP BY winner
        ORDER BY wins DESC, player ASC
        LIMIT ?
        """,
        (limit,)
    )
    rows = cursor.fetchall()
    conn.close()
    return pd.DataFrame(rows, columns=["Jogador", "Vitórias"])

@st.cache_data(ttl=300)
def get_wins(player):
    """Return how many wins a player has (all-time or specific date)."""
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM daily_summary WHERE winner = ?", (player,))
    count = cursor.fetchone()[0]
    conn.close()
    return count


# ========= APP ========= #

st.title("⚔️ fIGth club: lute ou deixe de seguir")

# Dates
available_dates = get_available_dates()
if not available_dates:
    st.error("Nenhum dado disponível no banco de dados.")
    st.stop()

selected_date = st.sidebar.selectbox("Selecionar Data", available_dates)

# Players
players = get_players(selected_date)
if not players:
    st.warning(f"Nenhum jogador encontrado para {selected_date}")
    st.stop()

if "selected_player" not in st.session_state:
    st.session_state.selected_player = players[0]

if st.session_state.selected_player not in players:
    st.sidebar.warning(f"Nenhum dado para **{st.session_state.selected_player}** em {selected_date}")

selected_player = st.sidebar.selectbox(
    "Selecionar um jogador",
    players,
    index=players.index(st.session_state.selected_player) if st.session_state.selected_player in players else 0,
    key="selected_player"
)

# Tabs
tab1, tab2 = st.tabs(["🏆 Ranking", "📊 Estatísticas do Jogador"])

with tab1:
    n_players = len(players)
    st.subheader(f"🏆 Ranking para {selected_date} — {n_players} jogadores")
    stat_choice = st.sidebar.radio("Estatística do Ranking", ["vencedores", "eliminações"])
    top_df = pd.DataFrame()
    if stat_choice == "vencedores":
        if selected_date == "Todos os Tempos":
                # Mostrar leaderboard de vitórias agregadas
                top_df = get_wins_leaderboard(limit=10)
        else: 
            winner = get_daily_summary(selected_date)['winner']
            st.markdown(f"🏅 O vencedor de {selected_date} é **[{winner}](https://instagram.com/{winner})**!")
    else:
        top_df = get_top_players(selected_date, "kills", limit=10)
    if not top_df.empty:
        st.dataframe(top_df, use_container_width=True, hide_index=True)

with tab2:
    st.header(f"📊 Estatísticas de [{selected_player}](https://instagram.com/{selected_player})")

    stats = get_player_stats(selected_date, selected_player)
    if not stats:
        st.write("Nenhuma estatística disponível para este jogador.")
    else:
        cols = st.columns(2)
        with cols[0]:
            st.metric("🔪 Eliminações", stats["kills"])
        with cols[1]:
            st.metric("☠️ Mortes", stats["deaths"])

        # Row 2
        if selected_date == "Todos os Tempos":
            with cols[0]:
                st.metric("🏅 Vitórias", get_wins(selected_player))
        else:
            rank = get_player_rank(selected_date, selected_player)
            if rank == 0:
                with cols[0]:
                    st.metric("Posição", "1!!! 👑")
            elif rank is not None:
                with cols[0]:
                    st.metric("Posição", rank)

            time = get_player_time(selected_date, selected_player)
            if time is not None:
                with cols[1]:
                    st.metric("⏱️ Tempo", f"{time:.2f} s")

        # Nemesis and Victim
        if selected_date != "Todos os Tempos":
            col_nemesis, col_victim = st.columns(2)
            with col_nemesis:
                st.markdown("### Nêmesis")
                if stats["nemesis"]:
                    st.markdown(f"[{stats['nemesis']}](https://instagram.com/{stats['nemesis']})")
                else:
                    st.write("Nenhuma nêmesis encontrada.")

            with col_victim:
                st.markdown("### Vítima")
                if stats["victim"]:
                    st.markdown(f"[{stats['victim']}](https://instagram.com/{stats['victim']})")
                else:
                    st.write("Nenhuma vítima encontrada.")