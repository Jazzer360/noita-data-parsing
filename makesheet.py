import re
import spelldata
import gspread
from gspread.utils import rowcol_to_a1 as rc
from gspread_formatting import get_conditional_format_rules as cnd_fmt
from gspread_formatting import set_column_widths


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
            'range': get_range(col),
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
    ranges = [(get_col_a1(col), width) for col, width in col_widths.items()]
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
    create_header('Cast group modifiers', 'cast_delay', 'damage')
    create_header('Projectile attributes', 'lifetime_mod', 'dangerous')
    create_header('Damage types', 'projectile', 'explosion')
    create_header('Spawn chances', 't0', 't10')


def add_borders():
    border_cols = ['draw', 'damage', 'dangerous', 'explosion', 'radius', 't6']
    ranges = [get_range(cname, 0) for cname in border_cols]
    sheet.format(ranges, border_format)


def get_range(colname, offset=2):
    col = spelldata.keys.index(colname) + 1
    a1 = f'{rc(1 + offset, col)}:{rc(len(spell_data) + 1, col)}'
    return a1


def get_col_a1(label):
    return re.search(r'([A-Z]+)(?=)', get_range(label)).group(1)


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
    'radius':           50,        
    't0':               50,    
    't1':               50,    
    't2':               50,    
    't3':               50,    
    't4':               50,    
    't5':               50,    
    't6':               50,    
    't7':               50,    
    't10':              50,      
}

border_format = {
    'borders': {
        'right': {
            'style': 'SOLID_MEDIUM',
        }
    }
}


def main():
    setup_filter()
    format_data()
    set_widths()
    add_borders()
    create_headers()


if __name__ == '__main__':
    main()
