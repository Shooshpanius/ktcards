#!/usr/bin/env python3
"""
Import .bd data-card files into the ktcards MySQL database.

Usage:
    python import_bd_to_db.py [options] [<TeamName.bd> ...]

If no .bd files are specified, all *.bd files in the datacards/ directory
(sibling of the scripts/ directory) are processed.

Connection parameters can be supplied via CLI flags or environment variables:
    MYSQL_HOST      (default: 127.0.0.1)
    MYSQL_PORT      (default: 3306)
    MYSQL_USER      (default: root)
    MYSQL_PASSWORD
    MYSQL_DATABASE  (default: ktcards)

The team must already exist in the Teams table OR a --season-id can be supplied
to auto-create missing teams.
"""

import argparse
import glob
import json
import os
import sys

import pymysql
import pymysql.cursors


def get_connection(args: argparse.Namespace) -> pymysql.Connection:
    return pymysql.connect(
        host=args.host,
        port=args.port,
        user=args.user,
        password=args.password,
        database=args.database,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.Cursor,
        autocommit=False,
    )


def import_bd(conn: pymysql.Connection, bd_path: str, default_season_id: int) -> None:
    team_name = os.path.splitext(os.path.basename(bd_path))[0]
    print(f"Importing '{team_name}' from {bd_path} …")

    with open(bd_path, encoding="utf-8") as f:
        data = json.load(f)

    cur = conn.cursor()

    # Find or create team
    cur.execute("SELECT Id FROM Teams WHERE Name = %s", (team_name,))
    row = cur.fetchone()
    if row:
        team_id = row[0]
    else:
        cur.execute(
            "INSERT INTO Teams (Name, SeasonId) VALUES (%s, %s)",
            (team_name, default_season_id),
        )
        team_id = cur.lastrowid
        print(f"  Created team '{team_name}' with id={team_id} in season {default_season_id}")

    # Delete existing cards (operatives cascade to abilities/attacks via FK)
    cur.execute("DELETE FROM Operatives WHERE TeamId = %s", (team_id,))
    cur.execute("DELETE FROM FactionRules WHERE TeamId = %s", (team_id,))
    cur.execute("DELETE FROM MarkerTokens WHERE TeamId = %s", (team_id,))
    cur.execute("DELETE FROM StrategyPloys WHERE TeamId = %s", (team_id,))
    cur.execute("DELETE FROM FirefightPloys WHERE TeamId = %s", (team_id,))
    cur.execute("DELETE FROM FactionEquipments WHERE TeamId = %s", (team_id,))

    # Insert operatives
    for op in data.get("operatives") or []:
        keywords = op.get("keywords")
        if isinstance(keywords, list):
            keywords = ", ".join(keywords)
        cur.execute(
            """INSERT INTO Operatives
               (TeamId, Name, Keywords, Movement, ActionPointLimit,
                GroupActivations, Defence, Save, Wounds, Notes)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
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
                "INSERT INTO OperativeAbilities (OperativeId, Name, Description) VALUES (%s, %s, %s)",
                (op_id, ab.get("name") or "", ab.get("description") or ""),
            )

        for atk in op.get("attacks") or []:
            cur.execute(
                """INSERT INTO OperativeAttacks
                   (OperativeId, Name, AttackType, Attacks, HitSkill,
                    Damage, CriticalDamage, SpecialRules)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
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
            "INSERT INTO FactionRules (TeamId, Name, Description) VALUES (%s, %s, %s)",
            (team_id, r.get("name") or "", r.get("description") or ""),
        )

    # Insert markers / tokens
    for m in data.get("markersTokens") or []:
        cur.execute(
            "INSERT INTO MarkerTokens (TeamId, Name, Description) VALUES (%s, %s, %s)",
            (team_id, m.get("name") or "", m.get("description") or ""),
        )

    # Insert strategy ploys
    for p in data.get("strategyPloys") or []:
        cur.execute(
            "INSERT INTO StrategyPloys (TeamId, Name, CpCost, Description) VALUES (%s, %s, %s, %s)",
            (team_id, p.get("name") or "", int(p.get("cpCost") or 0), p.get("description") or ""),
        )

    # Insert firefight ploys
    for p in data.get("firefightPloys") or []:
        cur.execute(
            "INSERT INTO FirefightPloys (TeamId, Name, CpCost, Description) VALUES (%s, %s, %s, %s)",
            (team_id, p.get("name") or "", int(p.get("cpCost") or 0), p.get("description") or ""),
        )

    # Insert faction equipment
    for e in data.get("factionEquipment") or []:
        cur.execute(
            """INSERT INTO FactionEquipments
               (TeamId, Name, EpCost, Description, Restrictions)
               VALUES (%s, %s, %s, %s, %s)""",
            (
                team_id,
                e.get("name") or "",
                int(e.get("epCost") or 0),
                e.get("description") or "",
                e.get("restrictions"),
            ),
        )

    conn.commit()
    cur.close()
    print(f"  Done: '{team_name}'")


def ensure_season(conn: pymysql.Connection, season_id: int) -> None:
    cur = conn.cursor()
    cur.execute("SELECT Id FROM Seasons WHERE Id = %s", (season_id,))
    if not cur.fetchone():
        cur.execute("INSERT INTO Seasons (Id, Name) VALUES (%s, %s)", (season_id, f"Season {season_id}"))
        conn.commit()
        print(f"Created Season {season_id}")
    cur.close()


def main():
    parser = argparse.ArgumentParser(description="Import .bd files into ktcards MySQL database")
    parser.add_argument("--host", default=os.environ.get("MYSQL_HOST", "127.0.0.1"), help="MySQL host")
    parser.add_argument("--port", type=int, default=int(os.environ.get("MYSQL_PORT", "3306")), help="MySQL port")
    parser.add_argument("--user", default=os.environ.get("MYSQL_USER", "root"), help="MySQL user")
    parser.add_argument("--password", default=os.environ.get("MYSQL_PASSWORD", ""), help="MySQL password")
    parser.add_argument("--database", default=os.environ.get("MYSQL_DATABASE", "ktcards"), help="MySQL database name")
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

    if args.bd_files:
        bd_files = [os.path.abspath(p) for p in args.bd_files]
    else:
        datacards_dir = os.path.join(here, "..", "datacards")
        bd_files = sorted(glob.glob(os.path.join(datacards_dir, "*.bd")))

    if not bd_files:
        print("No .bd files found to import.")
        sys.exit(0)

    try:
        conn = get_connection(args)
    except pymysql.Error as exc:
        print(f"ERROR: Could not connect to MySQL: {exc}", file=sys.stderr)
        sys.exit(1)

    ensure_season(conn, args.season_id)

    errors = []
    for bd_path in bd_files:
        try:
            import_bd(conn, bd_path, args.season_id)
        except Exception as exc:
            conn.rollback()
            print(f"ERROR importing {bd_path}: {exc}", file=sys.stderr)
            errors.append(bd_path)

    conn.close()

    if errors:
        print(f"\n{len(errors)} file(s) failed to import.", file=sys.stderr)
        sys.exit(1)

    print(f"\nAll {len(bd_files)} file(s) imported successfully.")


if __name__ == "__main__":
    main()
