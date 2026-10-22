"""Builds the TCG Arena files for Citadel Rush.

Inputs: tools/kitdata.json (card data from the print-and-play kit), tools/rarity.json,
rendered card images in repo/images/cards. Output: repo/*.json and token images.
Run: python3 tools/build.py
"""
import json, os, re, shutil
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(HERE, '..', 'repo')
BASE = 'https://raw.githubusercontent.com/bwellsean/citadel-rush-arena/main/'
VERSION = '2'

kit = json.load(open(os.path.join(HERE, 'kitdata.json')))
rarity = json.load(open(os.path.join(HERE, 'rarity.json')))
rarity['Hardened Frame'] = rarity.get('Reinforced Plating', 'Uncommon')


def slug(name):
    return re.sub(r'[^a-z0-9]+', '-', name.lower().replace("'", '')).strip('-')


def url(path):
    return BASE + path + '?v=' + VERSION


# Image files were rendered with apostrophes turned into dashes; normalise to the id slug.
card_dir = os.path.join(REPO, 'images', 'cards')
for f in os.listdir(card_dir):
    want = slug(f[:-5].replace('-s-', 's-')) + '.webp' if '-s-' in f else f
    if f == 'hero-s-sacrifice.webp':
        want = 'heros-sacrifice.webp'
    if want != f:
        os.replace(os.path.join(card_dir, f), os.path.join(card_dir, want))

cards = {}


def add(name, ctype, cost, **extra):
    cid = slug(name)
    img = f'images/cards/{cid}.webp'
    assert os.path.exists(os.path.join(REPO, img)), img
    cards[cid] = {
        'id': cid,
        'face': {'front': {'name': name, 'type': ctype, 'cost': cost, 'image': url(img)}},
        'name': name,
        'type': ctype,
        'cost': cost,
        **extra,
    }
    return cid


for r in kit['runners']:
    meta = [m.strip() for m in r['meta'].split('·')]
    rar = rarity.get(r['name'], 'Common')
    if 'Champion' in meta:
        rar = 'Champion'
    elif 'Legendary' in meta:
        rar = 'Legendary'
    add(r['name'], 'Runner', r['cost'],
        faction=r['faction'], rarity=rar, source=meta[1] if len(meta) > 1 else '',
        role=meta[2] if len(meta) > 2 else '', atk=r['atk'], mov=r['mov'],
        health=len(r['steps']) + 1)

for s in kit['supports']:
    add(s['name'], s['title'], s['cost'],
        faction=s.get('trapFaction') or s.get('faction') or 'Neutral',
        rarity=rarity.get(s['name'], 'Common'))

# Halcyte is a resource token: 6 per player, created at setup, never in the deck.
cards['halcyte'] = {
    'id': 'halcyte', 'isToken': True,
    'face': {'front': {'name': 'Halcyte', 'type': 'Halcyte', 'cost': 0, 'image': url('images/cards/halcyte.webp')}},
    'name': 'Halcyte', 'type': 'Halcyte', 'cost': 0, 'faction': 'Neutral', 'rarity': 'Common',
}

json.dump(cards, open(os.path.join(REPO, 'cards.json'), 'w'), indent=1, ensure_ascii=False)

# ---------- Tokens ----------
tok_dir = os.path.join(REPO, 'images', 'tokens')
os.makedirs(tok_dir, exist_ok=True)
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'


def token(fname, label, fill, ink='#ffffff', ring='#15121c', size=160):
    im = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((4, 4, size - 4, size - 4), fill=fill, outline=ring, width=10)
    lines = label.split('\n')
    fs = 64 if max(len(l) for l in lines) <= 2 else 34 if max(len(l) for l in lines) <= 5 else 26
    font = ImageFont.truetype(FONT, fs)
    total = sum(font.getbbox(l)[3] - font.getbbox(l)[1] for l in lines) + 8 * (len(lines) - 1)
    y = (size - total) / 2
    for l in lines:
        bb = font.getbbox(l)
        d.text(((size - (bb[2] - bb[0])) / 2 - bb[0], y - bb[1]), l, font=font, fill=ink)
        y += bb[3] - bb[1] + 8
    im.save(os.path.join(tok_dir, fname))
    return url('images/tokens/' + fname)


draggable = [
    ('wounded', 'Wounded', token('wounded.png', 'WOUND\nED', '#f2c12e', '#2a1f00')),
    ('critical', 'Critical', token('critical.png', 'CRIT', '#d9442b')),
    ('last-stand', 'Last Stand', token('last-stand.png', 'LAST\nSTAND', '#15121c', '#ffffff', '#f2c12e')),
    ('stunned', 'Stunned', token('stunned.png', 'STUN', '#3b82c4')),
    ('double-damage', 'Double Damage', token('double-damage.png', 'x2', '#f07a1a')),
    ('infused', 'Infused +1 ATK', token('infused.png', '+1', '#e8a93a', '#2a1d08')),
    ('snared', 'Snared (no move)', token('snared.png', 'SNARE', '#6b7280')),
    ('used', 'Once per game: used', token('used.png', 'USED', '#4b3a63')),
    ('marked', 'Marked', token('marked.png', 'MARK', '#9b1c1c')),
]
player_tokens = [
    {'name': 'First player', 'image': token('first-player.png', '1st', '#4fae5c'), 'isUnique': True},
    {'name': 'Citadel Strike used', 'image': token('citadel-strike.png', 'STRIKE', '#d9442b'), 'leavesAtEndOfTurn': True},
]

# ---------- Menu background and playmat ----------
art = Image.open(os.path.join(HERE, 'card-back-art.png')).convert('RGB')
w, h = art.size
banner = art.crop((0, int(h * 0.18), w, int(h * 0.18) + int(w * 9 / 16))).resize((1600, 900))
banner.save(os.path.join(REPO, 'images', 'banner.webp'), quality=85)
mat = art.resize((1600, int(1600 * h / w))).crop((0, 300, 1600, 1200)).filter(ImageFilter.GaussianBlur(18))
mat = Image.blend(mat, Image.new('RGB', mat.size, '#120e1c'), 0.62)
mat.save(os.path.join(REPO, 'images', 'playmat.webp'), quality=85)

# ---------- Game file ----------
LANES = 'ABCDE'
ROWS = 6
cell_h = 9.5


def cell(lane, row):
    return f'{lane}{row}'


rows = []
for row in range(ROWS, 0, -1):  # row 6 (far side) at the top, row 1 (your back row) at the bottom
    rows.append({
        'direction': 'row',
        'reverseForOppositeSide': True,
        'content': [{'section': cell(l, row), 'style': {'width': '20%'}} for l in LANES],
    })
board = {'direction': 'column', 'reverseForOppositeSide': True, 'content': rows}

sections = {}
for row in range(1, ROWS + 1):
    for l in LANES:
        sections[cell(l, row)] = {
            'isHidden': 'no', 'height': cell_h, 'alignment': 'CENTER',
            'displayedTitle': f'{l}{row}' + (' · P1 back row' if row == 1 and l == 'C' else ' · P2 back row' if row == ROWS and l == 'C' else ''),
            'noQuickActions': True,
        }
sections['Halcyte'] = {
    'isHidden': 'no', 'height': 9, 'alignment': 'START', 'displayedTitle': 'Halcyte (available)',
    'noQuickActions': False, 'isGroupForbidden': True,
}
sections['Mana'] = {
    'isHidden': 'no', 'height': 9, 'alignment': 'START', 'displayedTitle': 'Halcyte supply',
    'isGroupForbidden': True,
}

help_text = (
    "CITADEL RUSH quick reference\n"
    "Board: 5 lanes (A-E) x 6 rows, shown the same way on both screens. Player 1 (the host, first seat) owns rows 1 to 3 at the bottom "
    "and moves up. Player 2 owns rows 4 to 6 at the top and moves down. Each Citadel sits beyond its owner's back row "
    "(row 1 for Player 1, row 6 for Player 2). Bring the enemy Citadel from 15 to 0 to win; track your own Citadel Health on your counter.\n"
    "Halcyte: you start with 6 in your supply. Turn 1 you have 1 (second player: 2), then 1 more each turn, max 6. "
    "At the start of your turn drag 1 from the supply to Available. Tap a Halcyte to spend it; they untap each turn.\n"
    "Turn: Draw 1. Main phase: deploy up to 1 Runner on an empty square of your back row, play any Traps, Upgrades and Protocols you can pay for, "
    "Infuse (1 Halcyte: +1 ATK this turn, max 2 per Runner), Citadel Strike (2 Halcyte: 3 damage to an enemy Runner in your back row, once per turn), "
    "and make up to 2 moves with different Runners (first move is required if possible). Free sidestep if a Runner is directly ahead. "
    "Attack phase: each Runner may attack once.\n"
    "Traps: play face down on an empty square in your half. Upgrades: drop onto your Runner (max 1).\n"
    "Runner Health: a hit of 2+ below the current Lethal drops 1 step; a hit at or above Lethal defeats it; 0 or 1 glances. "
    "Mark steps with the Wounded, Critical and Last Stand tokens (drag from the token bar onto the card). Only survivors hit back.\n"
    "Deck: 40 cards, 1 faction, at least 12 Runners, up to 3 copies, 1 Champion, at most 2 Legendary cards. "
    "The deck builder checks size and copies; check Champions, Legendaries and the 12-Runner minimum yourself.\n"
    "Full rules: https://claude.ai/artifact/SdixphB2RvUK1PvQtYAVz9"
)

gameplay = {
    'mulligan': {
        'startingHandSize': 5,
        'mulliganCount': {'min': 0, 'max': 10},
        'mulliganCycle': {
            'info': 'Redraw rule: only if your hand has no Runner. Select your whole hand to shuffle it back and draw 5 new cards.',
            'steps': ['toBottom', 'shuffle', 'draw'],
            'selectionRange': {'min': 5, 'max': 5},
        },
    },
    'newTurn': {'drawOnStart': True, 'drawPerTurn': 1, 'sharedTurn': False, 'firstPlayerTokenName': 'First player'},
    'countersStartingValues': [15],
    'defaultNotes': 'Citadel Health starts at 15 (counter).\nHalcyte this turn: \nOnce-per-game abilities used: ',
    'cardRotation': 90,
    'tokens': player_tokens,
    'draggableTokens': [{'id': i, 'name': n, 'image': img} for i, n, img in draggable],
    'beforeGameStart': {
        'initialBoardSetup': [
            {'createCardId': 'halcyte', 'count': 6, 'destination': 'Mana'},
        ],
    },
    'sections': {
        'layout': {
            'direction': 'row',
            'content': [
                {'section': 'Halcyte', 'style': {'width': '60%'}},
                {'section': 'Mana', 'style': {'width': '40%'}},
            ],
        },
        'sharedZone': {'height': round(cell_h * ROWS + 6), 'layout': board},
        'sectionsDict': sections,
    },
}

game = {
    'name': 'Citadel Rush',
    'menuBackgroundImage': url('images/banner.webp'),
    'cardRotation': 90,
    'customHelp': help_text,
    'defaultRessources': {
        'backgrounds': [url('images/playmat.webp')],
        'decksUrl': url('decks.json'),
    },
    'deckBuilding': {
        'mainFilters': ['type', 'faction', 'cost', 'rarity'],
        'costCurveIgnoredTypes': [],
        'formats': [{'title': 'Standard', 'gameplay': 'Standard', 'deckRuleset': 'Standard'}],
        'deckRulesets': {
            'Standard': {'general': {'min': 40, 'max': 40, 'maxPerCard': 3}},
        },
    },
    'deckRulesets': {
        'Standard': {'general': {'min': 40, 'max': 40, 'maxPerCard': 3}},
    },
    'gameplay': {'Standard': gameplay},
    'cards': {
        'dataUrl': url('cards.json'),
        'cardBack': url('images/card-back.webp'),
        'cardBackColor': '#2a2440',
    },
}
json.dump(game, open(os.path.join(REPO, 'game.json'), 'w'), indent=1, ensure_ascii=False)

# ---------- Starter decks ----------
DECKS = {
    'Sentinels: Radiant Battery': {
        'Conduit': 2, 'Ember': 3, 'Flashpoint': 3, 'Tinder': 3, 'Arc': 3, 'Spire': 3, 'Zenith': 3, 'Aria': 1, 'Faedra': 1,
        'Ambush Alarm': 2, 'Suppression Mine': 3, 'Mirror Ward': 2,
        'Halcyte Capacitor': 1, 'Overcharged Rounds': 2, 'Prism Focus': 3,
        'Field Intel': 1, 'Arc Flash': 3, 'Blinding Flare': 1,
    },
    'Sentinels: Pathfinders': {
        'Waypoint': 3, 'Flashpoint': 2, 'Herald': 1, 'Geode': 3, 'Raider': 3, 'Tailwind': 3, 'Vault': 3, 'Avenger': 3,
        'Spire': 2, 'Trailblazer': 1, 'Faedra': 1,
        'Sanctuary Glyph': 2, 'Stasis Cage': 3, 'Courier Pack': 3, 'Rift Striders': 2, 'Field Intel': 2, 'Breakaway': 3,
    },
    'Syndicate: Drone Swarm': {
        'Drone Pilot': 3, 'Relay Drone': 1, 'Swarm Drone': 3, 'Blink': 3, 'Hornet': 3, 'Anvil': 3, 'Scrapper': 3,
        'Swarmcaller': 3, 'Hangar': 1, 'Leviathan': 1,
        'Overload Coil': 3, 'Suppression Mine': 2, 'Blast Barricade': 3, 'Claymore': 2,
        'Uplink Module': 3, 'Overcharged Rounds': 2, 'Relay Beacon': 1,
    },
    'Syndicate: Iron Line': {
        'Blink': 2, 'Welder': 3, 'Anvil': 3, 'Ballast': 3, 'Lockstep': 3, 'Hammerhead': 3, 'Mortar': 3, 'Rampart': 3,
        'Breaker': 1, 'Leviathan': 1,
        'Overload Coil': 2, 'Claymore': 3, 'Emergency Stabilizer': 2, 'Heavy Plating': 3, 'Hardened Frame': 2, 'Fortify': 3,
    },
    'Syndicate: Rift Ambush': {
        'Gremlin': 3, 'Hook': 3, 'Hornet': 3, 'Blink': 2, 'Anvil': 3, 'Lockstep': 2, 'Ballast': 1, 'Payload': 2,
        'Bounty Hunter': 1, 'The Wanderer': 2, 'Leviathan': 1,
        'Suppression Mine': 3, 'Snare': 2, 'Claymore': 1, 'Overload Coil': 1,
        'Overcharged Rounds': 2, 'Emergency Stabilizer': 2, 'Halcyte Capacitor': 1,
        'Field Intel': 2, 'Fortify': 2, 'Remote Detonation': 1,
    },
}
order = ['Runner', 'Trap', 'Upgrade', 'Protocol']
decks = []
for i, (title, lst) in enumerate(DECKS.items()):
    total = sum(lst.values())
    assert total == 40, (title, total)
    runners = sum(n for c, n in lst.items() if cards[slug(c)]['type'] == 'Runner')
    assert runners >= 12, (title, runners)
    dl = {'categoriesOrder': order}
    for t in order:
        dl[t] = [{'count': n, 'id': slug(c)} for c, n in lst.items() if cards[slug(c)]['type'] == t]
    decks.append({
        'title': title, 'id': 'citadel-rush-' + slug(title), 'cardCount': 40,
        'createdAt': '2026-10-22T00:00:00.000Z', 'lastModifiedAt': '2026-10-22T00:00:00.000Z',
        'game': 'Citadel Rush', 'format': ['Standard'], 'deckList': dl,
    })
json.dump(decks, open(os.path.join(REPO, 'decks.json'), 'w'), indent=1, ensure_ascii=False)
print(len(cards), 'cards;', len(decks), 'decks')
