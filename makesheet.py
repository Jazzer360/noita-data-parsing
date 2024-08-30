import re
import spelldata
import gspread
from gspread.utils import rowcol_to_a1 as rc
from gspread_formatting import (get_conditional_format_rules,
                                set_column_widths, ConditionalFormatRule,
                                BooleanRule, GradientRule, BooleanCondition,
                                CellFormat, GridRange, InterpolationPoint,
                                Color)


def num_format(pattern):
    return {
        'numberFormat': {
            'type': 'NUMBER',
            'pattern': pattern
        }
    }


def build_formats():
    formats = []
    for col, fmt in col_formats.items():
        formats.append({
            'range': get_col_range(col),
            'format': fmt
        })
    return formats


def format_data():
    formats = [
        {
            'range': f'{rc(3, 5)}:{rc(rows, cols)}',
            'format': {
                'horizontalAlignment': 'RIGHT'
            },
        },
        {
            'range': '1:1',
            'format': {
                'horizontalAlignment': 'CENTER',
                'textFormat': {
                    'bold': True
                }
            }
        }
    ]
    formats += build_formats()
    sheet.batch_format(formats)


def set_widths():
    ranges = [(get_col_alpha(col), width) for col, width in col_widths.items()]
    set_column_widths(sheet, ranges)


def setup_filter():
    sheet.set_basic_filter(2, 1, len(spell_data) + 1, len(spell_data[0]))
    sheet.freeze(2, 2)
    sheet.hide_columns(0, 1)
    sheet.hide_columns(spelldata.keys.index('t7'), spelldata.keys.index('t10'))


def create_header(title, beg, end):
    c1 = spelldata.keys.index(beg) + 1
    c2 = spelldata.keys.index(end) + 1
    rng = f'{rc(1, c1)}:{rc(1, c2)}'
    sheet.update_cell(1, c1, title)
    sheet.merge_cells(rng)


def create_headers():
    create_header('Cast group modifiers', 'cast_delay', 'lifetime_mod')
    create_header('Projectile attributes', 'lifetime_min', 'dangerous')
    create_header('Damage types', 'projectile', 'healing')
    create_header('Spawn chances', 't0', 't10')


def add_borders():
    border_cols = ['draw', 'lifetime_mod', 'dangerous', 'healing', 'radius',
                   't6']
    ranges = [get_col_range(cname, 0) for cname in border_cols]
    sheet.format(ranges, border_format)


def add_conditional_format():
    rules = get_conditional_format_rules(sheet)
    for rule in conditionals:
        rules.append(rule)
    rules.save()


def make_boolean_rule(ranges, condition, color, criteria=[]):
    return ConditionalFormatRule(
        ranges=[GridRange(sheet.id, *ranges)],
        booleanRule=BooleanRule(
            condition=BooleanCondition(condition, criteria),
            format=CellFormat(backgroundColor=Color.fromHex(color))
            )
        )


def make_gradient_rule(ranges, min, mid, max):
    minpt = InterpolationPoint(
        Color.fromHex(min[2]), type=min[0], value=min[1])
    midpt = None
    if mid:
        midpt = InterpolationPoint(
            Color.fromHex(mid[2]), type=mid[0], value=mid[1])
    maxpt = InterpolationPoint(
        Color.fromHex(max[2]), type=max[0], value=max[1])
    return ConditionalFormatRule(
        ranges=[GridRange(sheet.id, *ranges)],
        gradientRule=GradientRule(minpt, maxpt, midpt))


def get_col_range(colname, offset=2):
    col = spelldata.keys.index(colname) + 1
    a1 = f'{rc(1 + offset, col)}:{rc(len(spell_data) + 1, col)}'
    return a1


def get_col_alpha(label):
    return re.search(r'([A-Z]+)(?=)', get_col_range(label)).group(1)


def get_range(colfrom, colto=None, offset=2):
    colto = colto or colfrom
    fromi = spelldata.keys.index(colfrom)
    toi = spelldata.keys.index(colto) + 1
    return [offset, rows, fromi, toi]


def sort():
    sheet.sort((spelldata.keys.index('name') + 1, 'asc'))
    sheet.sort((spelldata.keys.index('type') + 1, 'asc'))


spell_data = spelldata.make_table()

gc = gspread.oauth()

workbook = gc.open('Noita Spells v1')
sheet = workbook.add_worksheet(
    title='newsheet', rows=len(spell_data) + 1, cols=len(spell_data[0]))
workbook.del_worksheet(workbook.sheet1)
sheet.update_title('spells')
sheet.update(spell_data, 'A2', raw=False)
rows = len(spell_data) + 1
cols = len(spelldata.keys)

seconds_fmt = num_format('+#,##0.00_)"s";-#,##0.00_)"s"')
num_1_fmt = num_format('0.0;-0.0')
num_2_fmt = num_format('0.00;-0.00')
num_1_pos_fmt = num_format('+0.0;-0.0')
num_pos_fmt = num_format('+0;-0')
pct_fmt = num_format('0%;-0%')
pct_2_fmt = num_format('0.00%;-0.00%')
deg_1_fmt = num_format('+0.0"°";-0.0"°"')

col_formats = {
    'cast_delay': seconds_fmt,
    'recharge': seconds_fmt,
    'spread': deg_1_fmt,
    'recoil': num_pos_fmt,
    'crit': pct_fmt,
    'damage': num_1_pos_fmt,
    'speed_mod': pct_fmt,
    'lifetime_mod': num_pos_fmt,
    'bounce_magnitude': pct_fmt,
    'projectile': num_1_fmt,
    'slice': num_1_fmt,
    'fire': num_1_fmt,
    'holy': num_1_fmt,
    'electricity': num_1_fmt,
    'drill': num_1_fmt,
    'melee': num_1_fmt,
    'healing': num_1_fmt,
    'ice': num_1_fmt,
    'explosion': num_1_fmt,
}

col_widths = {
    'name':             150,
    'description':      300,
    'type':             100,
    'charges':          50,
    'mana':             50,
    'draw':             50,
    'cast_delay':       60,
    'recharge':         60,
    'spread':           60,
    'recoil':           50,
    'crit':             50,
    'damage':           50,
    'speed_mod':        50,
    'lifetime_mod':     50,
    'lifetime_min':     50,
    'lifetime_max':     50,
    'bounces':          50,
    'bounce_magnitude': 50,
    'speed_min':        50,
    'speed_max':        50,
    'death_speed':      50,
    'trigger_time':     50,
    'dangerous':        50,
    'projectile':       50,
    'slice':            50,
    'fire':             50,
    'holy':             50,
    'electricity':      50,
    'drill':            50,
    'melee':            50,
    'healing':          50,
    'ice':              50,
    'explosion':        50,
    'radius':           45,
    't0':               45,
    't1':               45,
    't2':               45,
    't3':               45,
    't4':               45,
    't5':               45,
    't6':               45,
    't7':               45,
    't10':              45,
}

border_format = {
    'borders': {
        'right': {
            'style': 'SOLID_MEDIUM',
        }
    }
}

# Colors
red = '#E67C73'
lt_red = '#EA9999'
orange = '#FFD666'
lt_orange = '#F9CB9C'
yellow = '#FFFF00'
lt_yellow = '#FFE599'
green = '#57BB8A'
lt_green = '#B6D7A8'
lt_cyan = '#A2C4C9'
blue = '#C9DAF8'
lt_blue = '#9FC5E8'
lt_purple = '#B4A7D6'
lt_magenta = '#D5A6BD'
white = '#FFFFFF'
lt_gray = '#EFEFEF'
gray = '#CCCCCC'

conditionals = [
    make_gradient_rule(
        get_range('cast_delay'),
        ('MIN', None, green),
        ('NUMBER', '0', white),
        ('NUMBER', '2', red)),
    make_boolean_rule(
        get_range('cast_delay'), 'TEXT_STARTS_WITH', blue, ['=']),
    make_gradient_rule(
        get_range('recharge'),
        ('MIN', None, green),
        ('NUMBER', '0', white),
        ('NUMBER', '2', red)),
    make_boolean_rule(
        get_range('recharge'), 'TEXT_STARTS_WITH', blue, ['=']),
    make_gradient_rule(
        get_range('spread'),
        ('PERCENTILE', '5', green),
        ('NUMBER', '0', white),
        ('PERCENTILE', '90', red)),
    make_gradient_rule(
        get_range('recoil'),
        ('NUMBER', '-100', green),
        ('NUMBER', '0', white),
        ('NUMBER', '100', red)),
    make_boolean_rule(
        get_range('recoil'), 'TEXT_STARTS_WITH', blue, ['=']),
    make_gradient_rule(
        get_range('crit'),
        ('MIN', None, white),
        None,
        ('MAX', '100', green)),
    make_gradient_rule(
        get_range('damage'),
        ('MIN', None, red),
        ('NUMBER', '0', white),
        ('MAX', None, green)),
    make_gradient_rule(
        get_range('speed_mod'),
        ('MIN', None, red),
        ('NUMBER', '1', white),
        ('MAX', None, green)),
    make_boolean_rule(
        get_range('dangerous'), 'NOT_BLANK', yellow),
    make_boolean_rule(
        get_range('projectile', offset=1), 'NOT_BLANK', lt_gray),
    make_boolean_rule(
        get_range('slice', offset=1), 'NOT_BLANK', gray),
    make_boolean_rule(
        get_range('explosion', offset=1), 'NOT_BLANK', lt_red),
    make_boolean_rule(
        get_range('fire', offset=1), 'NOT_BLANK', lt_orange),
    make_boolean_rule(
        get_range('ice', offset=1), 'NOT_BLANK', lt_blue),
    make_boolean_rule(
        get_range('electricity', offset=1), 'NOT_BLANK', lt_cyan),
    make_boolean_rule(
        get_range('holy', offset=1), 'NOT_BLANK', lt_yellow),
    make_boolean_rule(
        get_range('drill', offset=1), 'NOT_BLANK', lt_magenta),
    make_boolean_rule(
        get_range('melee', offset=1), 'NOT_BLANK', lt_purple),
    make_boolean_rule(
        get_range('healing', offset=1), 'NOT_BLANK', lt_green),
    make_gradient_rule(
        get_range('t0', 't6'),
        ('PERCENTILE', '2', red),
        ('PERCENTILE', '50', orange),
        ('PERCENTILE', '98', green)),
    make_gradient_rule(
        get_range('t0', 't10'),
        ('MIN', None, red),
        ('PERCENTILE', '50', orange),
        ('MAX', None, green))
]


def main():
    setup_filter()
    format_data()
    set_widths()
    add_borders()
    create_headers()
    add_conditional_format()
    sort()


if __name__ == '__main__':
    main()
