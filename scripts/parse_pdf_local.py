#!/usr/bin/env python3
"""
Parse Kill Team data-card PDFs into .bd JSON format using pdfplumber only
(no OpenAI required).

Usage:
    python parse_pdf_local.py <path/to/TeamName.pdf> [<path/to/output/TeamName.bd>]
    python parse_pdf_local.py --all   # process all PDFs in datacards/

If the output path is omitted, the .bd file is written next to the PDF.

Requires:
    pip install pdfplumber
"""

import argparse
import json
import os
import re
import sys
from typing import Optional

import pdfplumber


# ─── TEXT HELPERS ─────────────────────────────────────────────────────────────

def fix_text(text: str) -> str:
    """Fix common pdfplumber layout artifacts."""
    if not text:
        return ""
    # "R ange" -> "Range" (a common kerning artifact)
    text = re.sub(r'\bR ange\b', 'Range', text)
    # Collapse multiple spaces
    text = re.sub(r'  +', ' ', text)
    return text


def to_title(text: str) -> str:
    """Convert ALL-CAPS tokens to Title Case, preserving abbreviations."""
    KEEP = {'AP', 'CP', 'EP', 'D3', 'D6', 'APL', 'ID', 'VP', 'VPs'}
    AP_RE = re.compile(r'^\dAP$')
    parts = text.split()
    result = []
    for w in parts:
        if w in KEEP or AP_RE.match(w):
            result.append(w)
        elif w.isupper() and len(w) > 1:
            result.append(w.capitalize())
        else:
            result.append(w)
    return ' '.join(result)


# ─── WEAPON PARSING ───────────────────────────────────────────────────────────

# Weapon line: name  ATK  HIT+  DMG/CRIT  [rules]
WEAPON_RE = re.compile(
    r'^(.+?)\s+(\d)\s+(\d+)\+\s+(\d+)/(\d+)\s*(.*?)$'
)

# Words that, if present in name, indicate this is NOT a weapon line
_WEAPON_NAME_BLACKLIST = re.compile(
    r'\b(APL|MOVE|SAVE|WOUNDS|NAME|ATK|HIT|DMG|WR)\b'
)


def try_parse_weapon(line: str) -> Optional[dict]:
    """Try to parse a line as a weapon entry. Returns dict or None."""
    line = fix_text(line.strip())
    if not line:
        return None
    m = WEAPON_RE.match(line)
    if not m:
        return None
    name = m.group(1).strip()
    if _WEAPON_NAME_BLACKLIST.search(name.upper()):
        return None
    # Reject if name is unrealistically long (probably a run-on from merged columns)
    if len(name) > 60:
        return None

    atk = int(m.group(2))
    hit = int(m.group(3))
    dmg = m.group(4)
    crit = m.group(5)
    rules = m.group(6).strip() or None
    if rules == '-':
        rules = None

    attack_type = "Ranged" if rules and re.search(r'[Rr]ange', rules) else "Melee"

    return {
        "name": name,
        "type": attack_type,
        "attacks": atk,
        "hitSkill": hit,
        "damage": dmg,
        "criticalDamage": crit,
        "specialRules": rules,
    }


# ─── STATS PARSING ────────────────────────────────────────────────────────────

STATS_RE = re.compile(r'^(\d)\s+(\d+)"\s*(\d+)\+\s+(\d+)\s*$')


def parse_stats(line: str) -> Optional[dict]:
    """Parse a stats line like '2 6\" 5+ 11'."""
    m = STATS_RE.match(line.strip())
    if m:
        return {
            "apl": int(m.group(1)),
            "move": f'{m.group(2)}"',
            "save": int(m.group(3)),
            "wounds": int(m.group(4)),
        }
    return None


# ─── ABILITY PARSING ──────────────────────────────────────────────────────────

# "Name: description text" – mixed-case title, at least 3 chars before colon
ABILITY_NAMED_RE = re.compile(r'^([A-Z][A-Za-z\'\s\-\(\)]{2,60}?):\s+(.+)')
# "NAME  1AP" – action on its own line
ACTION_LINE_RE = re.compile(r'^([A-Z][A-Z\s\-\']{2,50})\s+(\dAP)\s*$')
# Keywords footer: "KEYWORD, KEYWORD, ...  32" (page number at end)
KEYWORDS_FOOTER_RE = re.compile(
    r'^([A-Z][A-Z\s\-]+(?:,\s*[A-Z][A-Z\s\-]+){1,})\s+\d{1,3}\s*$'
)
# Pure-caps line that is a faction/team banner (e.g. "FELLGOR RAVAGER")
BANNER_RE = re.compile(r"^[A-Z][A-Z\s'\u2018\u2019\-]{0,60}$")

# Pattern to find an ability name embedded mid-line after initial text.
# Matches "SomeWords: " appearing after 35+ chars of other text.
# \*? handles footnote-style names embedded mid-line ("*Headtaker:")
# Used to detect right-column abilities merged into a line.
MIDLINE_ABILITY_RE = re.compile(
    r'^(.{35,}?)\s+\*?([A-Z][A-Za-z\'\-]{1,30}(?:\s+[A-Za-z\'\-]+){0,4}):\s+(.+)'
)
# Weapon-rule footnote: "*Name: description"
FOOTNOTE_RE = re.compile(r'^\*+([A-Za-z][A-Za-z\'\s\-]{2,50}):\s+(.+)')

EMBEDDED_ACTION_RE = re.compile(
    r'^(.+?)\s+([A-Z][A-Z\s\-\']{2,40}?)\s+(\dAP)\s*$'
)


def _has_footnote_star(text_before: str) -> bool:
    """Return True if text_before ended just before a * character."""
    return bool(re.search(r'\*$', text_before.rstrip()))


def extract_keywords(text: str) -> list:
    """Find a keywords footer line and return keyword list."""
    for line in reversed(text.split('\n')):
        line = line.strip()
        m = KEYWORDS_FOOTER_RE.match(line)
        if m:
            return [k.strip() for k in m.group(1).split(',')]
    return []


def parse_abilities(text: str) -> list:
    """Parse ability/action text into [{"name": ..., "description": ...}]."""
    if not text.strip():
        return []
    text = fix_text(text)
    lines = text.split('\n')

    abilities = []
    cur_name = None
    cur_desc: list = []

    def flush():
        nonlocal cur_name, cur_desc
        if cur_name and (cur_desc or cur_name):
            desc = ' '.join(cur_desc).strip()
            if desc:
                abilities.append({"name": cur_name, "description": desc})
        cur_name = None
        cur_desc = []

    def process_lines(line_list):
        """Process a list of stripped lines for ability entries."""
        nonlocal cur_name, cur_desc

        for line in line_list:
            if not line:
                continue

            # Skip keywords footer lines
            if KEYWORDS_FOOTER_RE.match(line):
                continue
            # Skip "RULES CONTINUE ON OTHER SIDE" notices
            if 'CONTINUE' in line.upper() and 'SIDE' in line.upper():
                continue
            # Skip page headers like "FELLGOR RAVAGER  32"
            if re.match(r'^[A-Z][A-Z\s]+\s+\d{1,3}\s*$', line):
                continue

            # ── Weapon-rule footnote: "*Name: description" ──────────────
            fn = FOOTNOTE_RE.match(line)
            if fn:
                flush()
                cur_name = fn.group(1).strip() + " (weapon rule)"
                initial_desc = fn.group(2).strip()
                # Check if initial description has embedded action at end
                ea = EMBEDDED_ACTION_RE.match(initial_desc)
                if ea:
                    cur_desc = [ea.group(1).strip()]
                    flush()
                    cur_name = to_title(ea.group(2).strip()) + f" ({ea.group(3)})"
                    cur_desc = []
                else:
                    # Check for mid-line embedded ability in initial description
                    ml = MIDLINE_ABILITY_RE.match(initial_desc)
                    if ml:
                        cur_desc = [ml.group(1).strip()]
                        flush()
                        cur_name = ml.group(2).strip()
                        cur_desc = [ml.group(3).strip()]
                    else:
                        cur_desc = [initial_desc]
                continue

            # ── Exact action line: "NAME 1AP" ────────────────────────────
            m = ACTION_LINE_RE.match(line)
            if m:
                flush()
                cur_name = to_title(m.group(1).strip()) + f" ({m.group(2)})"
                cur_desc = []
                continue

            # ── Named ability "Name: description" with optional embedded action ──
            m = ABILITY_NAMED_RE.match(line)
            if m and not try_parse_weapon(line):
                # Check for embedded "CAPS 1AP" at end of line
                ea = EMBEDDED_ACTION_RE.match(line)
                if ea and ea.group(1) != line:
                    pre = ea.group(1).strip()
                    action_name = ea.group(2).strip()
                    ap_cost = ea.group(3)
                    m2 = ABILITY_NAMED_RE.match(pre)
                    if m2:
                        flush()
                        cur_name = m2.group(1).strip()
                        cur_desc = [m2.group(2).strip()]
                    elif cur_name and pre:
                        cur_desc.append(pre)
                    flush()
                    cur_name = to_title(action_name) + f" ({ap_cost})"
                    cur_desc = []
                else:
                    # Check for a mid-line embedded second named ability
                    # (handles right-column ability merged into left-column line)
                    desc_text = m.group(2).strip()
                    ml = MIDLINE_ABILITY_RE.match(line)
                    if ml:
                        # Split: first part is initial ability, second is embedded
                        flush()
                        pre_text = ml.group(1).strip()
                        embedded_name = ml.group(2).strip()
                        embedded_desc = ml.group(3).strip()
                        # Parse pre_text as the initial ability
                        m3 = ABILITY_NAMED_RE.match(pre_text)
                        if m3:
                            cur_name = m3.group(1).strip()
                            initial = m3.group(2).strip()
                        elif FOOTNOTE_RE.match(pre_text):
                            fn2 = FOOTNOTE_RE.match(pre_text)
                            cur_name = fn2.group(1).strip() + " (weapon rule)"
                            initial = fn2.group(2).strip()
                        else:
                            cur_name = m.group(1).strip()
                            initial = desc_text
                        # Check initial for embedded action
                        ea2 = EMBEDDED_ACTION_RE.match(initial)
                        if ea2:
                            cur_desc = [ea2.group(1).strip()]
                            flush()
                            cur_name = to_title(ea2.group(2).strip()) + f" ({ea2.group(3)})"
                            cur_desc = [embedded_desc]
                        else:
                            cur_desc = [initial]
                            flush()
                            cur_name = embedded_name
                            cur_desc = [embedded_desc]
                    else:
                        flush()
                        cur_name = m.group(1).strip()
                        # Check description for embedded action at end
                        ea2 = EMBEDDED_ACTION_RE.match(desc_text)
                        if ea2:
                            cur_desc = [ea2.group(1).strip()]
                            flush()
                            cur_name = to_title(ea2.group(2).strip()) + f" ({ea2.group(3)})"
                            cur_desc = []
                        else:
                            cur_desc = [desc_text]
                continue

            # ── Embedded action at end of plain description line ──────────
            ea = EMBEDDED_ACTION_RE.match(line)
            if ea and not try_parse_weapon(line):
                pre = ea.group(1).strip()
                action_name = ea.group(2).strip()
                ap_cost = ea.group(3)
                if cur_name and pre:
                    cur_desc.append(pre)
                flush()
                cur_name = to_title(action_name) + f" ({ap_cost})"
                cur_desc = []
                continue

            # ── Check for mid-line embedded ability in plain description ──
            ml = MIDLINE_ABILITY_RE.match(line)
            if ml and cur_name and not try_parse_weapon(line):
                # Append pre-text to current description, start new ability
                pre_text = ml.group(1).strip()
                embedded_name = ml.group(2).strip()
                embedded_desc = ml.group(3).strip()
                if pre_text:
                    cur_desc.append(pre_text)
                flush()
                cur_name = embedded_name
                cur_desc = [embedded_desc]
                continue

            # ── Continuation / stray description text ─────────────────────
            if cur_name is not None:
                cur_desc.append(line)

    process_lines([l.strip() for l in lines])
    flush()
    return abilities


# ─── OPERATIVE BLOCK PARSER ───────────────────────────────────────────────────

def parse_operative_block(block_text: str) -> Optional[dict]:
    """
    Parse a single operative block (text after stripping the APL MOVE SAVE WOUNDS
    header line).
    """
    block_text = fix_text(block_text)
    lines = [l for l in block_text.split('\n') if l.strip()]
    if not lines:
        return None

    # First non-empty line: operative name
    name = lines[0].strip()
    if not name or re.match(r'^\d', name):
        return None
    # Skip if looks like a page/section header with no following stats
    if BANNER_RE.match(name) and len(name.split()) <= 2 and len(lines) < 3:
        return None

    i = 1
    stats = None
    while i < len(lines):
        s = parse_stats(lines[i])
        if s:
            stats = s
            i += 1
            break
        i += 1

    if not stats:
        return None

    # Skip "NAME ATK HIT DMG WR" table header
    while i < len(lines) and 'NAME' in lines[i] and 'ATK' in lines[i]:
        i += 1

    # Parse weapons
    weapons = []
    ability_start = i
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        w = try_parse_weapon(line)
        if w:
            weapons.append(w)
            ability_start = i + 1
            i += 1
        else:
            break

    ability_text = '\n'.join(lines[ability_start:])
    keywords = extract_keywords(ability_text)
    abilities = parse_abilities(ability_text)

    return {
        "name": name,
        "keywords": keywords,
        "movement": stats["move"],
        "actionPointLimit": stats["apl"],
        "groupActivations": 1,
        "defence": 3,
        "save": stats["save"],
        "wounds": stats["wounds"],
        "notes": None,
        "abilities": abilities,
        "attacks": weapons,
    }


def merge_operative(base: dict, extra: dict) -> dict:
    """Merge a second operative block (same name) into the base entry."""
    # Add any new weapons not already present
    existing_wpn_names = {w['name'] for w in base['attacks']}
    for w in extra['attacks']:
        if w['name'] not in existing_wpn_names:
            base['attacks'].append(w)
            existing_wpn_names.add(w['name'])
    # Add any new abilities not already present
    existing_ab_names = {a['name'] for a in base['abilities']}
    for a in extra['abilities']:
        if a['name'] not in existing_ab_names:
            base['abilities'].append(a)
            existing_ab_names.add(a['name'])
    # Keep keywords from whichever entry has more
    if len(extra['keywords']) > len(base['keywords']):
        base['keywords'] = extra['keywords']
    return base


def parse_operatives_from_text(combined_text: str) -> list:
    """
    Parse all operative blocks from combined page text.
    Blocks are separated by 'APL MOVE SAVE WOUNDS'.
    Duplicate names (same operative on two pages) are merged.
    """
    # Split by the stats header that starts each operative card
    blocks = re.split(r'APL\s+MOVE\s+SAVE\s+WOUNDS\s*\n?', combined_text)

    operatives = []
    by_name: dict = {}  # name -> index in operatives list

    for block in blocks[1:]:  # skip pre-header content
        op = parse_operative_block(block)
        if not op or not op['name']:
            continue
        # Normalise name for duplicate detection
        norm = op['name'].upper().strip()
        if norm in by_name:
            operatives[by_name[norm]] = merge_operative(
                operatives[by_name[norm]], op
            )
        else:
            by_name[norm] = len(operatives)
            operatives.append(op)

    return operatives


# ─── COLUMN SPLITTING ─────────────────────────────────────────────────────────

def split_columns(page) -> tuple:
    """Return (left_text, right_text) by cropping the page at its midpoint."""
    mid = page.width / 2
    left = (
        page.crop((0, 0, mid, page.height))
        .extract_text(x_tolerance=2, y_tolerance=2) or ""
    )
    right = (
        page.crop((mid, 0, page.width, page.height))
        .extract_text(x_tolerance=2, y_tolerance=2) or ""
    )
    return fix_text(left), fix_text(right)


# ─── PLOY / EQUIPMENT PARSING ─────────────────────────────────────────────────

# A line that looks like a ploy/equipment name: ALL CAPS, 1–8 words
CARD_NAME_RE = re.compile(r"^[A-Z][A-Z\s'\u2018\u2019\u201C\u201D\-!,\.\?\(\)]{1,60}$")

def parse_card_column(col_text: str, card_type: str) -> list:
    """
    Parse ploys or equipment entries from one column of text.
    Returns list of dicts with appropriate keys.

    Each entry is preceded by:
      FACTION BANNER LINE   (all-caps, e.g. "FELLGOR RAVAGER")
      TYPE LABEL LINE       (e.g. "STRATEGY PLOY")
      ENTRY NAME LINE       (all-caps, e.g. "VIOLENT TEMPERAMENT")
      description lines…

    A page may contain mixed types (e.g. strategy + firefight ploy on the
    same page).  We extract only entries matching card_type; others are skipped.
    """
    items = []
    if not col_text.strip():
        return items

    type_upper = card_type.upper()

    # Known type-label keywords (used to identify and skip non-matching sections)
    ALL_TYPE_LABELS = (
        'STRATEGY PLOY', 'FIREFIGHT PLOY', 'FACTION EQUIPMENT', 'FACTION RULE',
    )

    def is_type_label(line: str) -> bool:
        return any(t in line.upper() for t in ALL_TYPE_LABELS)

    def is_matching_type_label(line: str) -> bool:
        return type_upper[:8] in line.upper()

    lines = [l.strip() for l in col_text.split('\n') if l.strip()]

    # Pre-process: remove banner+type_label pairs and standalone type labels.
    # Accept only entries belonging to card_type; skip entries belonging to
    # other types (they'll be picked up in a separate pass if needed).
    clean: list = []        # lines belonging to matching card_type
    skip_until_next_banner = False  # True when inside a non-matching section

    i = 0
    while i < len(lines):
        line = lines[i]
        # Check if this is a banner followed by a type label
        if (BANNER_RE.match(line) and
                i + 1 < len(lines) and
                is_type_label(lines[i + 1])):
            if is_matching_type_label(lines[i + 1]):
                skip_until_next_banner = False
                i += 2  # skip banner + matching type label
            else:
                skip_until_next_banner = True
                i += 2  # skip banner + non-matching type label
            continue
        # Standalone type label
        if is_type_label(line):
            if is_matching_type_label(line):
                skip_until_next_banner = False
            else:
                skip_until_next_banner = True
            i += 1
            continue
        # Skip lines belonging to a non-matching section
        if skip_until_next_banner:
            i += 1
            continue
        clean.append(line)
        i += 1

    cur_name = None
    cur_desc: list = []

    def flush():
        nonlocal cur_name, cur_desc
        if cur_name:
            desc = ' '.join(cur_desc).strip()
            if type_upper in ('STRATEGY PLOY', 'FIREFIGHT PLOY'):
                items.append({
                    "name": to_title(cur_name),
                    "cpCost": 1,
                    "description": desc,
                })
            else:  # FACTION EQUIPMENT
                ep_m = re.search(r'\((\d+)EP\)', cur_name)
                ep_cost = int(ep_m.group(1)) if ep_m else 1
                cname = re.sub(r'\s*\(\d+EP\)', '', cur_name).strip()
                items.append({
                    "name": to_title(cname),
                    "epCost": ep_cost,
                    "description": desc,
                    "restrictions": None,
                })
        cur_name = None
        cur_desc = []

    # Lines that look like card names but are actually weapon table headers
    # (can appear inside faction equipment descriptions)
    WEAPON_HEADER_RE = re.compile(
        r'^(?:NAME(?:\s+ATK)?(?:\s+HIT)?(?:\s+DMG)?(?:\s+WR)?|WR|ATK|HIT|DMG)\s*$'
    )

    for line in clean:
        # An all-caps line is an entry name, unless it's a weapon table header
        if CARD_NAME_RE.match(line) and not WEAPON_HEADER_RE.match(line):
            flush()
            cur_name = line
        else:
            if cur_name is not None:
                cur_desc.append(line)

    flush()
    return items


def parse_two_column_cards(page, card_type: str) -> list:
    """Parse a page containing two columns of ploys/equipment."""
    left, right = split_columns(page)
    items = []
    items.extend(parse_card_column(left, card_type))
    items.extend(parse_card_column(right, card_type))
    return items


# ─── FACTION RULE PARSING ─────────────────────────────────────────────────────

def parse_faction_rule_text(text: str) -> list:
    """
    Parse faction rule(s) from a block of text (usually the right column
    of the faction-rule page).
    Returns list of {"name": ..., "description": ...}.
    """
    if not text.strip():
        return []
    text = fix_text(text)

    lines = [l.strip() for l in text.split('\n') if l.strip()]

    # All known type labels (for section detection)
    ALL_TYPE_LABELS_FR = (
        'FACTION RULE', 'STRATEGY PLOY', 'FIREFIGHT PLOY', 'FACTION EQUIPMENT',
        'MARKER', 'TOKEN', 'GUIDE', 'COUNTER',
    )

    def _is_any_label_fr(line: str) -> bool:
        return any(kw in line.upper() for kw in ALL_TYPE_LABELS_FR)

    def _is_rule_label(line: str) -> bool:
        return 'FACTION RULE' in line.upper()

    # Pre-process: section-aware cleaning.
    # Keep only text that belongs to FACTION RULE sections.
    clean: list = []
    skip_section = False  # True inside non-rule sections

    i = 0
    while i < len(lines):
        line = lines[i]
        # Banner + type label pair
        if (BANNER_RE.match(line) and
                i + 1 < len(lines) and
                _is_any_label_fr(lines[i + 1])):
            skip_section = not _is_rule_label(lines[i + 1])
            i += 2
            continue
        # Standalone type label
        if _is_any_label_fr(line):
            skip_section = not _is_rule_label(line)
            i += 1
            continue
        if skip_section:
            i += 1
            continue
        clean.append(line)
        i += 1

    rules = []
    cur_name = None
    cur_desc: list = []

    def flush():
        nonlocal cur_name, cur_desc
        if cur_name:
            desc = ' '.join(cur_desc).strip()
            rules.append({"name": to_title(cur_name), "description": desc})
        cur_name = None
        cur_desc = []

    for line in clean:
        # Skip "CONTINUES ON OTHER SIDE" etc.
        if 'CONTINUE' in line.upper() and 'SIDE' in line.upper():
            continue
        # Stop if we've hit a marker/token section (graphical content)
        if re.search(r'token|Token', line) and len(line.split()) <= 6:
            break
        # Numbered rule: "4. STEALTHY"
        m = re.match(r'^(\d+)\.\s+([A-Z][A-Z\s]+)$', line)
        if m:
            flush()
            cur_name = m.group(2).strip()
            continue
        # ALL CAPS standalone line → new rule name
        if CARD_NAME_RE.match(line):
            flush()
            cur_name = line
            continue
        # Description text
        if cur_name is not None:
            cur_desc.append(line)

    flush()
    return rules


def parse_faction_rule_page(page) -> tuple:
    """
    Returns (faction_rules, markers_tokens) from a faction rule page.
    The right column usually has the faction rule; the left may have
    team composition or markers/tokens info.
    """
    left, right = split_columns(page)

    # The right column has the faction rule
    faction_rules = parse_faction_rule_text(right)

    # Check for markers/tokens in the page (usually mixed with faction rule)
    full_text = fix_text(
        page.extract_text(x_tolerance=2, y_tolerance=2) or ""
    )
    markers_tokens = []
    if re.search(r'MARKER|TOKEN|COUNTER', full_text.upper()):
        markers_tokens = parse_markers_tokens(full_text)

    return faction_rules, markers_tokens


def parse_markers_tokens(text: str) -> list:
    """
    Parse marker/token descriptions from text.
    Returns list of {"name": ..., "description": ...}.
    """
    # Markers are usually listed as names followed by brief descriptions
    # For now, just extract named items from the text that follow the
    # MARKER/TOKEN GUIDE heading
    text = fix_text(text)
    idx = -1
    for kw in ('MARKER/TOKEN GUIDE', 'MARKER GUIDE', 'TOKEN GUIDE', 'MARKERS', 'TOKENS'):
        idx = text.upper().find(kw)
        if idx != -1:
            break
    if idx == -1:
        return []

    marker_text = text[idx:]
    # Extract named tokens using bullet-point or bold-name patterns
    # Tokens are often just listed as names in the PDF (no detailed descriptions)
    tokens = []
    for line in marker_text.split('\n'):
        line = line.strip()
        if not line:
            continue
        # Skip the guide header itself
        if re.search(r'MARKER|TOKEN|GUIDE', line.upper()) and len(line.split()) <= 4:
            continue
        # Named token lines: capitalised name
        if re.match(r'^[A-Z][a-z]', line) and len(line) < 60:
            m = re.match(r'^([A-Z][A-Za-z\s\-]+?)(?::\s+(.+))?$', line)
            if m:
                tokens.append({
                    "name": m.group(1).strip(),
                    "description": (m.group(2) or "").strip(),
                })
    return tokens


# ─── PAGE CLASSIFICATION ──────────────────────────────────────────────────────

def classify_page(text: str) -> str:
    upper = text.upper()
    # Skip pages must be checked first - errata can mention any keyword.
    if 'UPDATE LOG' in upper or 'PREVIOUS ERRATAS' in upper:
        return 'skip'
    if 'APL MOVE SAVE WOUNDS' in upper:
        return 'operative'

    # For content pages, use first-occurrence to determine primary type.
    # This avoids misclassification when a description text mentions another type.
    MARKERS = {
        'FACTION EQUIPMENT': 'faction_equipment',
        'STRATEGY PLOY': 'strategy_ploy',
        'FIREFIGHT PLOY': 'firefight_ploy',
        'FACTION RULE': 'faction_rule',
    }
    first_pos = len(upper) + 1
    first_type = None
    for keyword, type_name in MARKERS.items():
        pos = upper.find(keyword)
        if 0 <= pos < first_pos:
            first_pos = pos
            first_type = type_name

    return first_type or 'other'


# ─── MAIN PDF PARSER ──────────────────────────────────────────────────────────

def parse_pdf(pdf_path: str) -> dict:
    team_name = os.path.splitext(os.path.basename(pdf_path))[0]

    data: dict = {
        "teamName": team_name,
        "operatives": [],
        "factionRules": [],
        "markersTokens": [],
        "strategyPloys": [],
        "firefightPloys": [],
        "factionEquipment": [],
    }

    operative_texts: list = []

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            raw = page.extract_text(x_tolerance=2, y_tolerance=2) or ""
            text = fix_text(raw)
            page_type = classify_page(text)

            if page_type == 'operative':
                operative_texts.append(text)

            elif page_type == 'strategy_ploy':
                data['strategyPloys'].extend(
                    parse_two_column_cards(page, 'STRATEGY PLOY')
                )

            elif page_type == 'firefight_ploy':
                data['firefightPloys'].extend(
                    parse_two_column_cards(page, 'FIREFIGHT PLOY')
                )

            elif page_type == 'faction_equipment':
                data['factionEquipment'].extend(
                    parse_two_column_cards(page, 'FACTION EQUIPMENT')
                )

            elif page_type == 'faction_rule':
                fr, mt = parse_faction_rule_page(page)
                data['factionRules'].extend(fr)
                data['markersTokens'].extend(mt)

            # 'other' and 'skip' are ignored

    combined = '\n\n'.join(operative_texts)
    data['operatives'] = parse_operatives_from_text(combined)

    return data


# ─── CLI ──────────────────────────────────────────────────────────────────────

def process_one(pdf_path: str, output_path: Optional[str] = None) -> bool:
    pdf_path = os.path.abspath(pdf_path)
    if not os.path.isfile(pdf_path):
        print(f"ERROR: not found: {pdf_path}", file=sys.stderr)
        return False

    if not output_path:
        stem = os.path.splitext(pdf_path)[0]
        output_path = stem + '.bd'

    print(f"Parsing: {os.path.basename(pdf_path)}")
    data = parse_pdf(pdf_path)

    counts = (
        f"  operatives={len(data['operatives'])}"
        f"  strategyPloys={len(data['strategyPloys'])}"
        f"  firefightPloys={len(data['firefightPloys'])}"
        f"  factionEquipment={len(data['factionEquipment'])}"
        f"  factionRules={len(data['factionRules'])}"
    )
    print(counts)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  → {output_path}")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Parse Kill Team PDF to .bd JSON (no OpenAI)"
    )
    parser.add_argument(
        'pdf_path',
        nargs='?',
        default=None,
        help='Path to a PDF file (omit to use --all)',
    )
    parser.add_argument(
        'output_path',
        nargs='?',
        default=None,
        help='Output .bd file path (default: same dir as PDF)',
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Process all PDFs in the datacards/ directory',
    )
    parser.add_argument(
        '--skip-existing',
        action='store_true',
        help='Skip PDFs that already have a .bd file',
    )
    args = parser.parse_args()

    if args.all:
        here = os.path.dirname(os.path.abspath(__file__))
        datacards_dir = os.path.join(here, '..', 'datacards')
        pdfs = sorted(f for f in os.listdir(datacards_dir) if f.endswith('.pdf'))
        errors = []
        for pdf_name in pdfs:
            pdf_path = os.path.join(datacards_dir, pdf_name)
            bd_path = os.path.splitext(pdf_path)[0] + '.bd'
            if args.skip_existing and os.path.isfile(bd_path):
                print(f"Skipping (exists): {pdf_name}")
                continue
            if not process_one(pdf_path, bd_path):
                errors.append(pdf_name)
        if errors:
            print(f"\n{len(errors)} file(s) failed.", file=sys.stderr)
            sys.exit(1)
        print(f"\nDone: {len(pdfs)} files processed.")
    elif args.pdf_path:
        ok = process_one(args.pdf_path, args.output_path)
        sys.exit(0 if ok else 1)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
