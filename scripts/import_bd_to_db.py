#!/usr/bin/env python3
"""
Import .bd data-card files into the ktcards SQLite database.

Usage:
    python import_bd_to_db.py [--db <path/to/ktcards.db>] [<TeamName.bd> ...]

If no .bd files are specified, all *.bd files in the datacards/ directory
(sibling of the scripts/ directory) are processed.

The team must already exist in the Teams table OR a --season-id can be supplied
to auto-create missing teams.
"""

import argparse
import glob
import json
import os
import sqlite3
import sys


def find_db(default_relative: str) -> str:
    """Resolve DB path relative to this script's location."""
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(here, default_relative))


def import_bd(conn: sqlite3.Connection, bd_path: str, default_season_id: int) -> None:
    team_name = os.path.splitext(os.path.basename(bd_path))[0]
    print(f"Importing '{team_name}' from {bd_path} …")

    with open(bd_path, encoding="utf-8") as f:
        data = json.load(f)

    cur = conn.cursor()

    # Find or create team
    cur.execute("SELECT Id FROM Teams WHERE Name = ?", (team_name,))
    row = cur.fetchone()
    if row:
        team_id = row[0]
    else:
        cur.execute(
            "INSERT INTO Teams (Name, SeasonId) VALUES (?, ?)",
            (team_name, default_season_id),
        )
        team_id = cur.lastrowid
        print(f"  Created team '{team_name}' with id={team_id} in season {default_season_id}")

    # Delete existing cards (operatives cascade to abilities/attacks via FK)
    cur.execute("DELETE FROM Operatives WHERE TeamId = ?", (team_id,))
    cur.execute("DELETE FROM FactionRules WHERE TeamId = ?", (team_id,))
    cur.execute("DELETE FROM MarkerTokens WHERE TeamId = ?", (team_id,))
    cur.execute("DELETE FROM StrategyPloys WHERE TeamId = ?", (team_id,))
    cur.execute("DELETE FROM FirefightPloys WHERE TeamId = ?", (team_id,))
    cur.execute("DELETE FROM FactionEquipments WHERE TeamId = ?", (team_id,))

    # Insert operatives
    for op in data.get("operatives") or []:
        keywords = op.get("keywords")
        if isinstance(keywords, list):
            keywords = ", ".join(keywords)
        cur.execute(
            """INSERT INTO Operatives
               (TeamId, Name, Keywords, Movement, ActionPointLimit,
                GroupActivations, Defence, Save, Wounds, Notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                team_id,
                op.get("name") or "",
                keywords,
                op.get("movement"),
                int(op.get("actionPointLimit") or 0),
                int(op.get("groupActivations") or 0),
                int(op.get("defence") or 0),
                int(op.get("save") or 0),
                int(op.get("wounds") or 0),
                op.get("notes"),
            ),
        )
        op_id = cur.lastrowid

        for ab in op.get("abilities") or []:
            cur.execute(
                "INSERT INTO OperativeAbilities (OperativeId, Name, Description) VALUES (?, ?, ?)",
                (op_id, ab.get("name") or "", ab.get("description") or ""),
            )

        for atk in op.get("attacks") or []:
            cur.execute(
                """INSERT INTO OperativeAttacks
                   (OperativeId, Name, AttackType, Attacks, HitSkill,
                    Damage, CriticalDamage, SpecialRules)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    op_id,
                    atk.get("name") or "",
                    atk.get("type") or "",
                    int(atk.get("attacks") or 0),
                    int(atk.get("hitSkill") or 0),
                    atk.get("damage") or "",
                    atk.get("criticalDamage") or "",
                    atk.get("specialRules"),
                ),
            )

    # Insert faction rules
    for r in data.get("factionRules") or []:
        cur.execute(
            "INSERT INTO FactionRules (TeamId, Name, Description) VALUES (?, ?, ?)",
            (team_id, r.get("name") or "", r.get("description") or ""),
        )

    # Insert markers / tokens
    for m in data.get("markersTokens") or []:
        cur.execute(
            "INSERT INTO MarkerTokens (TeamId, Name, Description) VALUES (?, ?, ?)",
            (team_id, m.get("name") or "", m.get("description") or ""),
        )

    # Insert strategy ploys
    for p in data.get("strategyPloys") or []:
        cur.execute(
            "INSERT INTO StrategyPloys (TeamId, Name, CpCost, Description) VALUES (?, ?, ?, ?)",
            (team_id, p.get("name") or "", int(p.get("cpCost") or 0), p.get("description") or ""),
        )

    # Insert firefight ploys
    for p in data.get("firefightPloys") or []:
        cur.execute(
            "INSERT INTO FirefightPloys (TeamId, Name, CpCost, Description) VALUES (?, ?, ?, ?)",
            (team_id, p.get("name") or "", int(p.get("cpCost") or 0), p.get("description") or ""),
        )

    # Insert faction equipment
    for e in data.get("factionEquipment") or []:
        cur.execute(
            """INSERT INTO FactionEquipments
               (TeamId, Name, EpCost, Description, Restrictions)
               VALUES (?, ?, ?, ?, ?)""",
            (
                team_id,
                e.get("name") or "",
                int(e.get("epCost") or 0),
                e.get("description") or "",
                e.get("restrictions"),
            ),
        )

    conn.commit()
    print(f"  Done: '{team_name}'")


def ensure_season(conn: sqlite3.Connection, season_id: int) -> None:
    cur = conn.cursor()
    cur.execute("SELECT Id FROM Seasons WHERE Id = ?", (season_id,))
    if not cur.fetchone():
        cur.execute("INSERT INTO Seasons (Id, Name) VALUES (?, ?)", (season_id, f"Season {season_id}"))
        conn.commit()
        print(f"Created Season {season_id}")


def main():
    parser = argparse.ArgumentParser(description="Import .bd files into ktcards SQLite DB")
    parser.add_argument(
        "--db",
        default=None,
        help="Path to ktcards.db (default: ../ktcards.Server/ktcards.db relative to scripts/)",
    )
    parser.add_argument(
        "--season-id",
        type=int,
        default=1,
        help="Season ID to use when auto-creating teams (default: 1)",
    )
    parser.add_argument(
        "bd_files",
        nargs="*",
        help="Paths to .bd files to import. If omitted, all *.bd in datacards/ are used.",
    )
    args = parser.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))

    if args.db:
        db_path = os.path.abspath(args.db)
    else:
        db_path = find_db("../ktcards.Server/ktcards.db")

    if not os.path.isfile(db_path):
        print(f"ERROR: Database not found: {db_path}", file=sys.stderr)
        print("Tip: run 'dotnet run' in ktcards.Server once to create the DB.", file=sys.stderr)
        sys.exit(1)

    if args.bd_files:
        bd_files = [os.path.abspath(p) for p in args.bd_files]
    else:
        datacards_dir = os.path.join(here, "..", "datacards")
        bd_files = sorted(glob.glob(os.path.join(datacards_dir, "*.bd")))

    if not bd_files:
        print("No .bd files found to import.")
        sys.exit(0)

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")

    ensure_season(conn, args.season_id)

    errors = []
    for bd_path in bd_files:
        try:
            import_bd(conn, bd_path, args.season_id)
        except Exception as exc:
            print(f"ERROR importing {bd_path}: {exc}", file=sys.stderr)
            errors.append(bd_path)

    conn.close()

    if errors:
        print(f"\n{len(errors)} file(s) failed to import.", file=sys.stderr)
        sys.exit(1)

    print(f"\nAll {len(bd_files)} file(s) imported successfully.")


if __name__ == "__main__":
    main()
