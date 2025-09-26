#!/usr/bin/env python3
"""
Fight Rankings with Elimination Details
=======================================
Shows all players, their ranks, and who eliminated them.
"""

import pandas as pd
import os
from typing import Optional

def _find_latest_file(simulations_dir: str, prefix: str, suffix: str) -> Optional[str]:
    files = []
    for filename in os.listdir(simulations_dir):
        if filename.startswith(prefix) and filename.endswith(suffix):
            filepath = os.path.join(simulations_dir, filename)
            files.append((filepath, os.path.getmtime(filepath)))
    if not files:
        return None
    files.sort(key=lambda x: x[1], reverse=True)
    return files[0][0]


def _generate_detailed_from_collision(collision_csv_path: str) -> str:
    # Lê log de colisões e produz um CSV detalhado com Rank, Player, Eliminated_By
    df = pd.read_csv(collision_csv_path)

    # Normaliza coluna "Killed" para boolean
    killed_col = df["Killed"].astype(str).str.lower().isin(["true", "1", "yes"])
    df = df.assign(Killed=killed_col)

    # Conjunto de todos os jogadores vistos
    players = set(df["Particle"].astype(str)) | set(df["Opponent"].astype(str))
    total_players = len(players)

    # Para cada jogador eliminado, pegar o primeiro frame em que Killed=True
    eliminated_df = (
        df[df["Killed"] == True]  # noqa: E712 (comparação explícita com True)
        .copy()
    )
    # Se houver múltiplas linhas por jogador, manter o menor frame (eliminação mais cedo)
    eliminated_df["Player"] = eliminated_df["Particle"].astype(str)
    eliminated_df["Eliminated_By"] = eliminated_df["Opponent"].astype(str)
    first_kills = (
        eliminated_df.sort_values(["Frame"])  # ordem cronológica
        .drop_duplicates(subset=["Player"], keep="first")
    )

    # Ordena pela sequência de eliminação
    first_kills = first_kills.sort_values("Frame", ascending=True)

    # Atribui ranks: primeiro eliminado recebe rank N, depois N-1, ..., até 2
    ranks_desc = list(range(total_players, 1, -1))
    rank_rows = []
    for idx, (_, row) in enumerate(first_kills.iterrows()):
        rank_rows.append({
            "Rank": ranks_desc[idx],
            "Player": row["Player"],
            "Eliminated_By": row["Eliminated_By"],
        })

    eliminated_players = set(first_kills["Player"].astype(str))
    winners = list(players - eliminated_players)
    winner = winners[0] if winners else "UNKNOWN"

    # Adiciona o vencedor (rank 1)
    rank_rows.insert(0, {"Rank": 1, "Player": winner, "Eliminated_By": "WINNER"})

    detailed_df = pd.DataFrame(rank_rows)

    # Deriva timestamp do nome do arquivo de colisão: <simulations>/<timestamp>_collision_log.csv
    base_name = os.path.basename(collision_csv_path)
    timestamp = base_name.split("_collision_log.csv")[0]
    out_path = os.path.join(os.path.dirname(collision_csv_path), f"detailed_rankings_{timestamp}.csv")
    detailed_df.to_csv(out_path, index=False)
    return out_path


def show_rankings_with_kills():
    """
    Show all players, their rankings, and who killed them.
    """
    # Find most recent detailed rankings file
    simulations_dir = "simulations"

    # Tenta achar um detailed pronto
    latest_detailed = _find_latest_file(simulations_dir, "detailed_rankings_", ".csv")

    # Se não existir, tenta gerar a partir do último collision_log
    if latest_detailed is None:
        latest_collision = _find_latest_file(simulations_dir, "", "_collision_log.csv")
        if latest_collision is None:
            print("Error: No detailed rankings files found and no collision logs to generate from!")
            return
        latest_detailed = _generate_detailed_from_collision(latest_collision)
    
    # Read and display rankings
    df = pd.read_csv(latest_detailed)
    df = df.sort_values('Rank')
    
    print("⚔️ FIGHT RANKINGS WITH ELIMINATIONS")
    print("="*45)
    print(f"Total Players: {len(df)}")
    print("="*45)
    
    for _, row in df.iterrows():
        rank = row['Rank']
        player = row['Player']
        eliminated_by = row['Eliminated_By']
        
        # Format rank with proper suffix
        if rank == 1:
            rank_str = f"{rank}st"
            emoji = "🥇"
        elif rank == 2:
            rank_str = f"{rank}nd" 
            emoji = "🥈"
        elif rank == 3:
            rank_str = f"{rank}rd"
            emoji = "🥉"
        elif rank <= 10:
            rank_str = f"{rank}th"
            emoji = "🏅"
        elif rank <= 20:
            rank_str = f"{rank}th"
            emoji = "⭐"
        else:
            rank_str = f"{rank}th"
            emoji = "❌"
        
        # Format elimination info
        if eliminated_by == 'WINNER':
            elimination_info = "- WINNER"
        else:
            elimination_info = f"- killed by {eliminated_by}"
        
        print(f"{rank_str:<4} {player:<25} {emoji} {elimination_info}")
    
    print("="*45)
    winner = df.iloc[0]
    last_place = df.iloc[-1]
    print(f"🏆 Winner: {winner['Player']}")
    print(f"💀 First Eliminated: {last_place['Player']} (killed by {last_place['Eliminated_By']})")

if __name__ == "__main__":
    show_rankings_with_kills()
