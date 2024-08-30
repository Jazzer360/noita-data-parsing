import csv
import re
from functools import reduce
from pprint import pprint
from bs4 import BeautifulSoup


def get_spell_texts():
    with open('common.csv', mode='r', encoding='utf-8') as f:
        return {t[0]: t[1] for t in csv.reader(f)}


def build_spellbook():
    book = []
    with open('data/scripts/gun/gun_actions.lua', 'r') as f:
        while True:
            line = f.readline()
            if '--[[' in line:
                while ']]--' not in line:
                    line = f.readline()
            elif line == '\t{\n':
                lines = []
                while True:
                    nextline = f.readline()
                    if nextline == '\t},\n' or nextline.endswith('end,\n'):
                        book.append(parse_lua(lines))
                        break
                    nextline = re.sub(r'--.*$', '', nextline)
                    lines.append(re.sub(r'\s+', '', nextline))
            elif line == '':
                break
    add_derived_stats(book)
    return book


def parse_lua(luablock):
    spell = {}
    for n in range(len(luablock)):
        line = luablock[n]
        if line.endswith(','):
            k, v = line[:-1].split("=")
            v = v.strip('"')
            if k == 'max_uses':
                k = 'charges'
            elif k == 'name':
                v = texts.get(v[1:]) or v
            elif k == 'description':
                v = texts.get(v[1:]) or v
            elif k == 'type':
                v = v[12:].title().replace("_", " ")
            elif k.startswith("--"):
                continue
            spell[k] = v
        elif line.startswith('action'):
            parse_lua_actions(luablock[n+1:], spell)
    probs = [0.0 for _ in range(9)]
    for pair in zip(spell['spawn_level'].split(','), 
                    spell['spawn_probability'].split(',')):
        probs[min(int(pair[0]), 8)] = float(pair[1])
    spell['spawn_probability'] = probs
    return spell


def parse_lua_actions(actionblock, spell):
    for line in actionblock:
        # XML data parsing
        if line.startswith('add_projectile'):
            parse_xml(re.findall(r'(?<=")([^"]+)(?=")', line), spell)
            # Timer trigger duration
            timer = re.search(
                r'(add_projectile_trigger_timer\([^,]*,)([0-9]+)', line)
            if timer:
                spell['trigger_time'] = int(timer.group(2))
            continue
        
        # Cast delay parsing
        fire_rate = re.search(
            r'(?<=c\.fire_rate_wait)([=+-]{1}[\.0-9]+)', line)
        if fire_rate:
            fire_rate = fire_rate.group(1)
            if fire_rate.startswith('='):
                spell['cast_delay'] = f'\'={float(fire_rate[1:]) / 60:.2f} s'
            else:
                spell['cast_delay'] = float(fire_rate) / 60
            continue

        # Recharge time parsing
        recharge = re.search(
            r'(?<=ACTION_DRAW_RELOAD_TIME_INCREASE)([=+-]{1}[\.0-9]+)', line)
        recharge = recharge or re.search(
            r'(?<=current_reload_time)([=+-]{1}[\.0-9]+)', line)
        if recharge:
            recharge = recharge.group(1)
            if recharge.startswith('='):
                spell['recharge'] = f'\'={float(recharge[1:]) / 60:.2f} s'
            else:
                spell['recharge'] = float(recharge) / 60
            continue
        
        # Spread parsing
        spread = re.search(
            r'(?<=c\.spread_degrees)([=+-]{1}[\.0-9]+)', line)
        if spread:
            spread = spread.group(1)
            spell['spread'] = float(spread)
            continue
        
        # Crit parsing
        crit = re.search(
            r'(?<=c\.damage_critical_chance)([=+-]{1}[\.0-9]+)', line)
        if crit:
            crit = crit.group(1)
            if crit.startswith('='):
                spell['crit'] = f'\'{crit}%'
            else:
                spell['crit'] = f'{float(crit):.2f}%'
            continue

        # Recoil parsing
        recoil = re.search(
            r'(?<=recoil_knockback)([=+-]{1}[\.0-9]+)', line)
        if recoil:
            recoil = recoil.group(1)
            if recoil.startswith('='):
                spell['recoil'] = f'\'={float(recoil[1:]):.0f}'
            else:
                spell['recoil'] = float(recoil)
            continue

        # Damage modifiers
        dmgmod = (re.search(
            r'(?<=damage_projectile_add)([+-]{1}[\.0-9]+)', line) or
            re.search(r'(?<=damage_ice_add)([+-]{1}[\.0-9]+)', line) or
            re.search(r'(?<=damage_electricity_add)([+-]{1}[\.0-9]+)', line) or
            re.search(r'(?<=damage_explosion_add)([+-]{1}[\.0-9]+)', line))
        if dmgmod:
            dmgmod = dmgmod.group(1)
            if dmgmod.startswith('='):
                spell['damage'] = f'\'={float(dmgmod[1:])*25:.0f)}'
            else:
                spell['damage'] = float(dmgmod)*25

        # Draw amount
        draw = re.search(r'(?<=draw_actions\()([0-9]+)', line)
        if draw:
            draw = draw.group(1)
            spell['draw'] = int(draw)

        # Lifetime modifier
        life = re.search(r'(?<=lifetime_add)([=+-]{1}[\.0-9]+)', line)
        if life:
            life = life.group(1)
            if life.startswith('='):
                spell['lifetime_mod'] = f'\'={float(life[1:]):.0f}'
            else:
                spell['lifetime_mod'] = f'{float(life):.0f}'

        # Speed modifier
        speed = re.search(r'(?<=c\.speed_multiplier)([*]{1}[\.0-9]+)', line)
        if speed:
            speed = speed.group(1)
            if speed.startswith('='):
                spell['speed_mod'] = f'\'{speed}'
            elif speed.startswith('*'):
                spell['speed_mod'] = f'{float(speed[1:]):.2f}'


def parse_xml(filename, spell):
    if filename:
        if filename[0].endswith('/'):
            return spell
        with open(filename[0], 'r') as f:
            soup = BeautifulSoup(f, 'lxml-xml')
            proj = soup.find('ProjectileComponent')
            expl = soup.find('config_explosion')

            if expl:
                # Explosion parsing
                if expl.has_attr('damage') and float(expl.get('damage')) > 0:
                    spell['explosion'] = float(expl['damage'])*25
                if (expl.has_attr('explosion_radius')
                        and float(expl.get('explosion_radius')) > 0):
                    spell['radius'] = int(expl['explosion_radius'])
            
            if proj:
                # Damage parsing
                if proj.has_attr('damage') and float(proj.get('damage')) > 0:
                    spell['projectile'] = float(proj['damage']) * 25

                typedmg = soup.find('damage_by_type')
                if typedmg:
                    for dtype, dmg in typedmg.attrs.items():
                        if float(dmg) > 0 or dtype == 'healing':
                            spell[dtype] = float(dmg)*25

                # Velocity parsing
                if proj.has_attr('speed_min'):
                    spell['speed_min'] = int(proj.get('speed_min'))
                if proj.has_attr('speed_max'):
                    spell['speed_max'] = int(proj.get('speed_max'))

                # Lifetime parsing
                life = proj.get('lifetime')
                if life:
                    variance = int(proj.get('lifetime_randomnees') or 0)
                    spell['lifetime_min'] = int(life) - variance
                    spell['lifetime_max'] = int(life) + variance

                # Friendly fire
                ff = False
                if proj.get('friendly_fire') == '1':
                    if (proj.has_attr('damage')
                            and float(proj.get('damage')) > 0):
                        ff = True
                    elif soup.find('damage_by_type'):
                        ff = True
                if 'explosion' in spell:
                    if proj.get('explosion_dont_damage_shooter') != '1':
                        ff = True
                if ff:
                    spell['dangerous'] = 'Yes'

                # Death velocity
                if proj.has_attr('die_on_low_velocity_limit'):
                    spell['death_speed'] = proj.get(
                        'die_on_low_velocity_limit')

                # Bounces
                if proj.has_attr('bounces_left'):
                    bounces = proj.get('bounces_left')
                    if bounces != '0':
                        spell['bounces'] = proj.get('bounces_left')
                        spell['bounce_magnitude'] = proj.get('bounce_energy')

                # Velocity scaling
                if proj.get('damage_scaled_by_speed') == '1':
                    spell['velocity_scaling'] = 'Yes'

            # Lightning bolt exception
            if spell['name'] == 'Lightning bolt':
                spell['explosion'] = 125.0


def add_derived_stats(book):
    total_weights = [0.0 for _ in range(9)]
    for spell in book:
        for n in range(9):
            total_weights[n] += spell['spawn_probability'][n]
    for spell in book:
        for n in range(9):
            out = n if n < 8 else 10
            prob = (float(spell['spawn_probability'][n])
                    / total_weights[n] * 100)
            spell[f't{out}'] = f'{prob:.2f}%' if prob > 0 else None


def make_table():
    book = build_spellbook()
    table = [[spell.get(key) for key in keys] for spell in book]
    table.insert(0, keys)
    for spell in table[1:]:
        url = '=HYPERLINK("https://noita.wiki.gg/wiki/{}", "{}")'
        if spell[1] in ['Water', 'Oil', 'Blood', 'Acid', 'Cement']:
            link_name = spell[1].title() + "_(Spell)"
        elif 'Kantele' in spell[1] or 'Ocarina' in spell[1]:
            link_name = 'Note_spells'
        elif spell[1] == '???':
            link_name = '%3F%3F%3F_(Spell)'
        else:
            link_name = spell[1].title().replace(" ", "_").replace("?", "%3F")
        spell[1] = url.format(link_name, spell[1])
    return table


def find_spells(book, attrs=None, name=None):
    for spell in book:
        if attrs and reduce(lambda a, b: a or b in spell, attrs, False):
            print(f'{spell['id']}: {spell['name']}')
            for attr in attrs:
                if attr in spell:
                    print(spell[attr])
        if name:
            if name.lower() in spell['name'].lower():
                pprint(spell)


texts = get_spell_texts()
keys = ['id',
        'name',
        'description',
        'type',
        'charges',
        'mana',
        'draw',
        'cast_delay',
        'recharge',
        'spread',
        'recoil',
        'crit',
        'damage',
        'speed_mod',
        'lifetime_mod',
        'lifetime_min',
        'lifetime_max',
        'bounces',
        'bounce_magnitude',
        'speed_min',
        'speed_max',
        'death_speed',
        'trigger_time',
        'velocity_scaling',
        'dangerous',
        'projectile',
        'slice',
        'explosion',
        'fire',
        'ice',
        'electricity',
        'holy',
        'drill',
        'melee',
        'healing',
        'radius',
        't0',
        't1',
        't2',
        't3',
        't4',
        't5',
        't6',
        't7',
        't10']
