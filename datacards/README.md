# datacards

This directory stores:

1. **PDF files** — source data-card files for Kill Team rosters (one PDF per team, named `TeamName.pdf`).
2. **`.bd` files** — structured JSON data extracted from the PDFs (one per team, named `TeamName.bd`).

---

## `.bd` File Format

The `.bd` file is a JSON document with the following structure:

```json
{
  "teamName": "Team Name",
  "operatives": [
    {
      "name": "Operative Name",
      "keywords": ["Keyword1", "Keyword2"],
      "movement": "3\"",
      "actionPointLimit": 2,
      "groupActivations": 1,
      "defence": 3,
      "save": 4,
      "wounds": 8,
      "notes": "Optional notes",
      "abilities": [
        { "name": "Ability Name", "description": "Ability description." }
      ],
      "attacks": [
        {
          "name": "Attack Name",
          "type": "Melee",
          "attacks": 4,
          "hitSkill": 3,
          "damage": "4",
          "criticalDamage": "5",
          "specialRules": "Optional special rules"
        }
      ]
    }
  ],
  "factionRules": [
    { "name": "Rule Name", "description": "Rule description." }
  ],
  "markersTokens": [
    { "name": "Token Name", "description": "Token description." }
  ],
  "strategyPloys": [
    { "name": "Ploy Name", "cpCost": 1, "description": "Ploy description." }
  ],
  "firefightPloys": [
    { "name": "Ploy Name", "cpCost": 1, "description": "Ploy description." }
  ],
  "factionEquipment": [
    {
      "name": "Equipment Name",
      "epCost": 1,
      "description": "Equipment description.",
      "restrictions": "Optional restrictions"
    }
  ]
}
```

### Fields reference

| Section | Field | Type | Description |
|---|---|---|---|
| operative | `name` | string | Operative name |
| operative | `keywords` | string[] | List of keywords |
| operative | `movement` | string | Movement value (e.g. `"3\""`) |
| operative | `actionPointLimit` | int | APL value |
| operative | `groupActivations` | int | Group activations count |
| operative | `defence` | int | Defence dice value |
| operative | `save` | int | Save value (e.g. `4` for 4+) |
| operative | `wounds` | int | Wounds value |
| operative | `notes` | string? | Optional description |
| attack | `type` | string | `"Melee"` or `"Ranged"` |
| attack | `attacks` | int | Number of attack dice |
| attack | `hitSkill` | int | Hit skill (e.g. `3` for 3+) |
| attack | `damage` | string | Normal damage |
| attack | `criticalDamage` | string | Critical damage |
| ploy | `cpCost` | int | Command point cost |
| equipment | `epCost` | int | Equipment point cost |
| equipment | `restrictions` | string? | Optional restrictions |

---

## Workflow

1. Place the team's PDF in this directory as `TeamName.pdf`.
2. Parse the PDF and create `TeamName.bd` in this directory.
3. In the Admin Panel, find the team and click **"Загрузить данные из файла"** to import cards into the database.
