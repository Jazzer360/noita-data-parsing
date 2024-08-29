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
            spell = spell | parse_lua_actions(luablock[n+1:])
    probs = [0.0 for _ in range(9)]
    for pair in zip(spell['spawn_level'].split(','), 
                    spell['spawn_probability'].split(',')):
        probs[min(int(pair[0]), 8)] = float(pair[1])
    spell['spawn_probability'] = probs
    return spell


def parse_lua_actions(actionblock):
    spell = {}
    for line in actionblock:
        # XML data parsing
        if line.startswith('add_projectile'):
            spell = spell | parse_xml(re.findall(r'(?<=")([^"]+)(?=")', line))
            # Timer trigger duration
            timer = re.search(
                r'(add_projectile_trigger_timer\([^,]*,)([0-9]+)', line)
            if timer:
                spell['trigger_time'] = timer.group(2)
            continue
        
        # Cast delay parsing
        fire_rate = re.search(
            r'(?<=c\.fire_rate_wait)([=+-]{1}[\.0-9]+)', line)
        if fire_rate:
            fire_rate = fire_rate.group(1)
            if fire_rate.startswith('='):
                spell['cast_delay'] = f'\'={float(fire_rate[1:]):.2f}'
            else:
                spell['cast_delay'] = f'{float(fire_rate)/60:.2f}'
            continue

        # Recharge time parsing
        recharge = re.search(
            r'(?<=ACTION_DRAW_RELOAD_TIME_INCREASE)([=+-]{1}[\.0-9]+)', line)
        recharge = recharge or re.search(
            r'(?<=current_reload_time)([=+-]{1}[\.0-9]+)', line)
        if recharge:
            recharge = recharge.group(1)
            if recharge.startswith('='):
                spell['recharge'] = f'\'={float(recharge[1:])/60:.2f}'
            else:
                spell['recharge'] = f'{float(recharge)/60:.2f}'
            continue
        
        # Spread parsing
        spread = re.search(
            r'(?<=c\.spread_degrees)([=+-]{1}[\.0-9]+)', line)
        if spread:
            spread = spread.group(1)
            spell['spread'] = f'{float(spread):.2f}'
            continue
        
        # Crit parsing
        crit = re.search(
            r'(?<=c\.damage_critical_chance)([=+-]{1}[\.0-9]+)', line)
        if crit:
            crit = crit.group(1)
            if crit.startswith('='):
                spell['crit'] = f'\'{crit}%'
            else:
                spell['crit'] = f'{float(crit):.0f}%'
            continue

        # Recoil parsing
        recoil = re.search(
            r'(?<=recoil_knockback)([=+-]{1}[\.0-9]+)', line)
        if recoil:
            recoil = recoil.group(1)
            if recoil.startswith('='):
                spell['recoil'] = f'\'={float(recoil[1:]):.0f}'
            else:
                spell['recoil'] = f'{float(recoil):.0f}'
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
                spell['damage'] = f'{float(dmgmod)*25:+.0f}'

        # Draw amount
        draw = re.search(r'(?<=draw_actions\()([0-9]+)', line)
        if draw:
            draw = draw.group(1)
            spell['draw'] = draw

        # Lifetime modifier
        life = re.search(r'(?<=lifetime_add)([=+-]{1}[\.0-9]+)', line)
        if life:
            life = life.group(1)
            if life.startswith('='):
                spell['lifetime_mod'] = f'\'={float(life[1:]):.0f}'
            else:
                spell['lifetime_mod'] = f'{float(life):.0f}'

    return spell


def parse_xml(filename):
    spell = {}
    if filename:
        if filename[0].endswith('/'):
            return spell
        with open(filename[0], 'r') as f:
            soup = BeautifulSoup(f, 'lxml-xml')
            proj = soup.find('ProjectileComponent')
            expl = soup.find('config_explosion')

            # Damage parsing
            if (proj and proj.has_attr('damage')
                    and float(proj.get('damage')) > 0):
                spell['projectile'] = float(proj['damage'])*25
            typedmg = soup.find('damage_by_type')
            if typedmg:
                for dtype, dmg in typedmg.attrs.items():
                    spell[dtype] = float(dmg)*25

            # Explosion parsing
            if (expl and expl.has_attr('damage')
                    and float(expl.get('damage')) > 0):
                spell['explosion'] = float(expl['damage'])*25
            if (expl and expl.has_attr('explosion_radius')
                    and float(expl.get('explosion_radius')) > 0):
                spell['radius'] = int(expl['explosion_radius'])

            # Velocity parsing
            if proj and proj.has_attr('speed_min'):
                spell['speed_min'] = int(proj.get('speed_min'))
            if proj and proj.has_attr('speed_max'):
                spell['speed_max'] = int(proj.get('speed_max'))

            # Lifetime parsing
            if proj:
                life = proj.get('lifetime')
                if life:
                    try:
                        variance = int(proj.get('lifetime_randomness'))
                    except TypeError:
                        variance = 0
                    spell['lifetime_min'] = int(life) - variance
                    spell['lifetime_max'] = int(life) + variance

            # Friendly fire
            if proj:
                ff = True if proj.get('friendly_fire') == '1' else False
                if 'explosion' in spell:
                    if proj.get('explosion_dont_damage_shooter') != '1':
                        ff = True
                if ff:
                    spell['dangerous'] = 'Yes'

            # Death velocity
            if proj:
                if proj.has_attr('die_on_low_velocity_limit'):
                    spell['death_speed'] = proj.get(
                        'die_on_low_velocity_limit')

            # Bounces
            if proj:
                if proj.has_attr('bounces_left'):
                    bounces = proj.get('bounces_left')
                    if bounces != '0':
                        spell['bounces'] = proj.get('bounces_left')
                        spell['bounce_magnitude'] = proj.get('bounce_energy')

    return spell


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


def print_book(book):
    for spell in book:
        print('\n')
        print(f'Id: {spell['id']}')
        print(f'Name: {spell['name']}')
        print(f'Description: {spell['description']}')
        print(f'Type: {spell['type']}')
        if 'mana' in spell:
            print(f'Mana: {spell['mana']}')
        if 'cast_delay' in spell:
            print(f'Cast delay: {spell['cast_delay']}')
        if 'projectile' in spell:
            print(f'Damage (Projectile): {spell['projectile']}')
        if 'slice' in spell:
            print(f'Damage (Slice): {spell['slice']}')
        if 'holy' in spell:
            print(f'Damage (Holy): {spell['holy']}')
        if 'fire' in spell:
            print(f'Damage (Fire): {spell['fire']}')
        if 'electricity' in spell:
            print(f'Damage (Electricity): {spell['electricity']}')
        if 'drill' in spell:
            print(f'Damage (Drill): {spell['drill']}')
        if 'melee' in spell:
            print(f'Damage (Melee): {spell['melee']}')
        if 'healing' in spell:
            print(f'Damage (Healing): {spell['healing']}')
        if 'ice' in spell:
            print(f'Damage (Ice): {spell['ice']}')
        if 'explosion' in spell:
            print(f'Damage (Explosion): {spell['explosion']}')
        if 'radius' in spell:
            print(f'Explosion Radius: {spell['radius']}')
        if 'recharge' in spell:
            print(f'Recharge time: {spell['recharge']}')
        if 'spread' in spell:
            print(f'Spread: {spell['spread']}')
        if 'crit' in spell:
            print(f'Crit: {spell['crit']}')
        if 'recoil' in spell:
            print(f'Recoil: {spell['recoil']}')
        if 'charges' in spell:
            print(f'Uses: {spell['charges']}')
        print(f'Spawn Chance: {spell['spawn_probability']}')


def make_csv(book):
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
            'lifetime_mod',
            'lifetime_min',
            'lifetime_max',
            'bounces',
            'bounce_magnitude',
            'speed_min',
            'speed_max',
            'dangerous',
            'projectile',
            'slice',
            'fire',
            'holy',
            'electricity',
            'drill',
            'melee',
            'healing',
            'ice',
            'explosion',
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
    with open('spells.csv', mode='w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(keys)
        for spell in book:
            row = [spell.get(key) for key in keys]
            writer.writerow(row)


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
book = build_spellbook()

# print_book(book)
add_derived_stats(book)
make_csv(book)
find_spells(book, attrs=['dangerous'], name='lightning')


# Do spell rarity! Add total spawn chance per tier. Figure out the logic behind
# overall spell rarity
