import streamlit as st
import pandas as pd
from pathlib import Path
import datetime
import os
import hashlib

st.set_page_config(page_title="Daily Occupancy Dashboard", layout="wide")

# --- Force Reset Button (ALWAYS shows) ---
if st.button("Force Clear Date Reset (for testing)"):
    st.session_state.clear_dates = {}
    st.session_state.clear_dates_completed = False
    st.session_state.clear_date_force_reset = True
    st.experimental_rerun()  # If you get AttributeError, update Streamlit!

# --- Always initialize session state ---
if 'clear_dates' not in st.session_state:
    st.session_state.clear_dates = {}
if 'clear_dates_completed' not in st.session_state:
    st.session_state.clear_dates_completed = False

# --- Load Data ---
layout_path = Path('shelter_layout_template.csv')
animal_path = Path('AnimalInventory.csv')
clear_path = Path('clear.csv')

layout_df = pd.read_csv(layout_path)
try:
    animal_df = pd.read_csv(animal_path, skiprows=3)
except Exception:
    animal_df = pd.read_csv(animal_path)

for col in ["AnimalName", "Stage", "Location_1", "SubLocation"]:
    if col in animal_df.columns:
        animal_df[col] = animal_df[col].astype(str).str.strip()

# --- Load clear dates from clear.csv ---
if clear_path.exists():
    try:
        clear_df = pd.read_csv(clear_path, dtype=str, encoding='utf-8', on_bad_lines='skip')
    except UnicodeDecodeError:
        clear_df = pd.read_csv(clear_path, dtype=str, encoding='latin1', on_bad_lines='skip')
    clear_df.columns = [c.strip() for c in clear_df.columns]
    clear_df['AnimalNumber'] = clear_df['AnimalNumber'].astype(str)
    # Fix Excel serial numbers in ClearDate
    def excel_serial_to_date(val):
        try:
            val = float(val)
            return (datetime.datetime(1899, 12, 30) + datetime.timedelta(days=val)).strftime("%m/%d/%y")
        except Exception:
            return val
    if 'ClearDate' in clear_df.columns:
        clear_df['ClearDate'] = clear_df['ClearDate'].apply(excel_serial_to_date)
    clear_dates_dict = dict(zip(clear_df['AnimalNumber'], clear_df['ClearDate']))
else:
    clear_dates_dict = {}

# --- Warn if any animals needing clear dates are missing from clear.csv ---
clear_date_needed = animal_df[
    animal_df['Stage'].str.contains('Bite/Scratch|Stray|Legal', case=False, na=False)
].copy()
missing_clear = []
for idx, row in clear_date_needed.iterrows():
    if str(row['AnimalNumber']) not in clear_dates_dict:
        missing_clear.append(f"{row['AnimalNumber']} ({row['AnimalName']})")
if missing_clear:
    st.warning("Missing clear dates for: " + ", ".join(missing_clear))

# --- Status to Abbreviation Mapping (copy from RoundsMapp.py) ---
STATUS_MAP = {
    'Evaluate': 'EVAL',
    'Hold - Adopted!': 'ADPT',
    'Hold - Behavior': 'BEHA',
    'Hold - Behavior Foster': 'BFOS',
    'Hold - Behavior Mod.': 'BMOD',
    'Hold - Bite/Scratch': 'B/S',
    'Hold - Canisus Program': 'CANISUS',
    'Hold - Complaint': 'COMP',
    'Hold - Cruelty Foster': 'CF',
    'Hold - Dental': 'DENT',
    'Hold - Doc': 'DOC',
    'Hold - Evidence!': 'EVID',
    'Hold - For RTO': 'RTO',
    'Hold - Foster': 'FOST',
    'Hold - Legal Notice': 'LEGAL',
    'Hold - Media!': 'MEDIA',
    'Hold - Meet and Greet': 'M+G',
    'Hold - Offsite': 'OFFSITE',
    'Hold - Possible Adoption': 'PADPT',
    'Hold - Pups at the Pen!': 'PEN',
    'Hold - Rescue': 'RESC',
    'Hold - SAFE Foster': 'SAFE',
    'Hold - Special Event': 'SPEC',
    'Hold - Stray': 'STRAY',
    'Hold - Surgery': 'SX',
}

def map_status(stage):
    for key in sorted(STATUS_MAP.keys(), key=len, reverse=True):
        abbr = STATUS_MAP[key]
        if stage.lower().startswith(key.lower()):
            return abbr
    if 'evaluate' in stage.lower():
        return STATUS_MAP['Evaluate']
    return ""

def format_clear_date(date_str):
    # If it's already 'UNK' or empty, return as is
    if not date_str or date_str.upper() == 'UNK':
        return date_str
    # Try to parse and reformat
    for fmt in ("%m/%d/%y", "%m/%d/%Y", "%-m/%-d/%y", "%-m/%-d/%Y"):
        try:
            dt = datetime.datetime.strptime(date_str, fmt)
            return dt.strftime("%m/%d/%y")
        except Exception:
            continue
    return date_str  # fallback: return as is if parsing fails

def format_display_line(row):
    name = row["AnimalName"]
    if name.lower() == 'nan' or name.strip() == '' or pd.isna(name):
        animal_number = str(row.get("AnimalNumber", ""))
        name = animal_number[-8:] if len(animal_number) >= 8 else animal_number
    name = name.title()
    stage = row["Stage"]
    abbr = map_status(stage)
    animal_id = str(row.get("AnimalNumber", ""))
    clear_date = clear_dates_dict.get(animal_id, "")
    clear_date = format_clear_date(clear_date)
    if abbr:
        if clear_date:
            return f'{name} <span class="stage-abbr">{abbr}</span> <span class="clear-date">{clear_date}</span>'
        return f'{name} <span class="stage-abbr">{abbr}</span>'
    return name

def format_kennel_label(row):
    letter = row["Location_1"][-1]
    try:
        number = str(int(row["SubLocation"].strip()))
    except Exception:
        number = row["SubLocation"].strip()
    return f"{letter}{number}"

# --- Area selection ---
area_options = {
    "Canine Adoptions & Holding": [
        "Dog Adoptions A", "Dog Adoptions B", "Dog Adoptions C", "Dog Adoptions D",
        "Dog Holding E", "Dog Holding F"
    ],
    "Adoptions Lobby": [
        "Feature Room 1", "Feature Room 2", "Adoptions Lobby"
    ],
    "Cat Condo Room": [
        "Condo A", "Condo B", "Condo C", "Condo D", "Condo E", "Condo F", "Rabbitat 1", "Rabbitat 2", "Room 109-B", "Meet & Greet 109B"
    ],
    "G Available Cats": [
        "01", "02", "03", "04", "05", "06", "07", "08"
    ],
    "H Available Cats": [
        "01", "02", "03", "04", "05", "06", "07", "08"
    ],
    "I Behavior/Bite Case": [
        "01", "02", "03", "04", "05", "06", "07", "08"
    ],
    "Foster Care": [
        "01", "02", "03", "04", "05", "06", "07", "08"
    ],
    "Cat Isolation 235": [
        "Cage 1", "Cage 2", "Cage 3", "Cage 4", "Cage 5", "Cage 6", "Cage 7", "Cage 8", "Cage 9"
    ],
    "Cat Isolation 234 Overflow": [
        "Cage 1", "Cage 2", "Cage 3", "Cage 4", "Cage 5", "Cage 6"
    ],
    "Cat Isolation 233 Ringworm": [
        "Cage 1", "Cage 2", "Cage 3", "Cage 4", "Cage 5", "Cage 6"
    ],
    "Cat Isolation 232 Panleuk": [
        "Cage 1", "Cage 2", "Cage 3", "Cage 4", "Cage 5", "Cage 6"
    ],
    "Cat Isolation 231 Holds": [
        "Cage 1", "Cage 2", "Cage 3", "Cage 4", "Cage 5", "Cage 6", "Cage 7", "Cage 8", "Cage 9"
    ],
    "Cat Treatment": [
        "01", "02", "03", "04", "05", "06", "Incubator 1", "Incubator 2", "Incubator 3", "Incubator 4", "Incubator 5", "Incubator 6", "Incubator 210A", "Incubator 210B", "Incubator 210C", "Incubator 210D"
    ],
    "ICU": [
        "DENT1", "ICU2", "ICU3", "ICU4", "ICU5", "ICU6", "ICU7", "ICU8"
    ],
    "Administration": [
        "Barb H's Office", "Gina's Office", "Sue's Office"
    ],
    "Multi-Species Holding": [
        "229 Boaphile 1", "229 Boaphile 2", "229 Cat 1", "229 Cat 2", "229 Cat 3", "229 Cat 4", "229 Cat 5", "229 Cat 6", "229 Multi Animal Holding", "229 Rabbitat 1", "229 Rabbitat 2", "229 Room 1", "229 Room 2", "229 Turtle Tank 1", "229 Turtle Tank 2", "229 Turtle Tank 3", "229 Turtle Tank 4",
        "227 Bird Cage", "227 Boaphile 1", "227 Boaphile 2", "227 Mammal 1", "227 Mammal 2"
    ],
    "Small Animals & Exotics": [
        "Bird Cage 1", "Bird Cage 2", "Bird Cage 3", "Bird Cage 4", "Bird Cage EXTRA",
        "Small Animal 1", "Small Animal 2", "Small Animal 3", "Small Animal 4", "Small Animal 5", "Small Animal 6", "Small Animal 7", "Small Animal 8",
        "Mammal 1", "Mammal 2", "Mammal 3", "Mammal 4",
        "Reptile 1", "Reptile 2", "Reptile 3", "Reptile 4", "Reptile 5",
        "Countertop Cage 1", "Countertop Cage 2"
    ],
    "Cat Recovery": [str(i).zfill(2) for i in range(1, 19)],
    "Dog Recovery": [f"Large {str(i).zfill(2)}" for i in range(1, 5)] + [f"Small {str(i).zfill(2)}" for i in range(1, 7)]
}

st.title("Daily Occupancy Dashboard")
today = datetime.date.today()
st.caption(f"{today.strftime('%B %d, %Y')}")
area = st.selectbox("Select Area", list(area_options.keys()))
selected_locations = area_options[area]

if area == "Canine Adoptions & Holding":
    dog_df = animal_df[animal_df["Location_1"].isin(selected_locations)].copy()
    dog_df["KennelLabel"] = dog_df.apply(format_kennel_label, axis=1)
    dog_df["DisplayLine"] = dog_df.apply(format_display_line, axis=1)
    kennel_animals = dog_df.groupby("KennelLabel")["DisplayLine"].apply(list).to_dict()

    # Layout bounds (Dog Adoptions: A-D, Dog Holding: E-F)
    row_letters = ["A", "B", "C", "D", "E", "F"]
    kennel_positions = {
        row["Label"]: (int(row["X"]), int(abs(row["Y"])), int(row["Width"]), int(row["Height"]), row["Label"][0])
        for _, row in layout_df.iterrows() if row["Label"][0] in row_letters
    }

    # Map row letters to grid row indices
    row_to_gridrow = {"A": 2, "B": 3, "C": 4, "D": 5, "E": 7, "F": 8}

    # Build kennel blocks, inserting area headings in their own grid rows
    kennel_blocks = []
    # Add Canine Adoptions heading
    kennel_blocks.append(
        '<div class="area-heading adoptions-heading" style="grid-column: 1 / span 12; grid-row: 1; text-align: left; font-size: 1em; font-weight: 500; color: #333; background: #fff; padding: 2px 0 2px 8px; letter-spacing: 0.5px;">Canine Adoptions</div>'
    )
    # Add Canine Holding heading
    kennel_blocks.append(
        '<div class="area-heading holding-heading" style="grid-column: 1 / span 12; grid-row: 6; text-align: left; font-size: 1em; font-weight: 500; color: #333; background: #fff; padding: 2px 0 2px 8px; letter-spacing: 0.5px;">Canine Holding</div>'
    )

    for label, (x, y, w, h, row_letter) in sorted(kennel_positions.items(), key=lambda item: ("ABCDEF".index(item[1][4]), item[1][1], item[1][0])):
        grid_row = row_to_gridrow[row_letter]
        animal_lines = kennel_animals.get(label, [])
        animal_html = (
            f'<div class="kennel-animal-list">' +
            (''.join(f'<div class="kennel-animal">{line}</div>' for line in animal_lines) or '<div class="kennel-animal">-</div>') +
            '</div>'
        )
        block_html = f'''
        <div class="kennel-block" style="grid-column: {x+1} / span {w}; grid-row: {grid_row} / span {h}; position: relative;">
            <div class="kennel-label-small">{label}</div>
            {animal_html}
        </div>
        '''
        kennel_blocks.append(block_html)

    grid_html = f'''<div id="kennel-grid" class="kennel-grid-container canine-grid">{''.join(kennel_blocks)}</div>'''

    st.components.v1.html(
        f"""
        <style>
        .kennel-grid-container.canine-grid {{
            width: 98vw;
            max-width: 1400px;
            aspect-ratio: 4 / 3;
            margin: 0 auto 32px auto;
            display: grid;
            grid-template-columns: repeat(12, 1fr);
            grid-template-rows: 0.4fr repeat(4, 1fr) 0.4fr repeat(2, 1fr);
            gap: 6px;
            border: 2px solid #333;
            background: #eee;
            box-sizing: border-box;
            align-items: stretch;
            justify-items: stretch;
        }}
        .kennel-block {{
            background: #f9f9f9;
            border: 1.5px solid #333;
            border-radius: 6px;
            display: flex;
            flex-direction: column;
            align-items: flex-start;
            justify-content: flex-start;
            min-width: 0;
            min-height: 0;
            width: 100%;
            height: 100%;
            padding: 8px 8px 8px 8px;
            box-sizing: border-box;
            overflow: hidden;
            position: relative;
        }}
        .kennel-label-small {{
            position: absolute;
            top: 6px;
            left: 10px;
            font-size: 0.95em;
            color: #333;
            font-weight: 600;
            opacity: 0.95;
            z-index: 2;
            pointer-events: none;
        }}
        .kennel-animal-list {{
            margin-top: 2.2em;
            width: 100%;
            max-height: 100%;
            overflow-y: auto;
            container-type: inline-size;
        }}
        .kennel-animal {{
            color: #222;
            font-size: 1em; /* Base size */
            margin: 0;
            padding: 0;
            line-height: 1.1em;
            word-break: break-word;
            font-stretch: ultra-condensed;
            white-space: normal;
        }}
        .stage-abbr {{
            color: #c00;
            font-weight: bold;
            text-transform: uppercase;
            margin-left: 0.25em;
        }}
        .area-heading {{
            grid-column: 1 / span 12;
            text-align: left;
            font-size: 1em;
            font-weight: 500;
            color: #333;
            background: #fff;
            padding: 2px 0 2px 8px;
            letter-spacing: 0.5px;
            z-index: 2;
            height: 100%;
            display: flex;
            align-items: center;
        }}
        @container (max-width: 200px) {{
            .kennel-animal {{
                font-size: 0.8em;
            }}
        }}
        @container (max-width: 150px) {{
            .kennel-animal {{
                font-size: 0.7em;
            }}
        }}
        @container (max-width: 100px) {{
            .kennel-animal {{
                font-size: 0.6em;
            }}
        }}
        </style>
        <script>
        function scaleText() {{
            document.querySelectorAll('.kennel-animal-list').forEach(container => {{
                const animals = container.querySelectorAll('.kennel-animal');
                if (animals.length === 0) return;
                
                // Start with base size
                let fontSize = 1;
                const containerHeight = container.clientHeight;
                const containerWidth = container.clientWidth;
                
                // Scale down until all content fits
                while (true) {{
                    let totalHeight = 0;
                    animals.forEach(animal => {{
                        animal.style.fontSize = fontSize + 'em';
                        totalHeight += animal.offsetHeight;
                    }});
                    
                    if (totalHeight <= containerHeight && 
                        Math.max(...Array.from(animals).map(a => a.offsetWidth)) <= containerWidth) {{
                        break;
                    }}
                    
                    fontSize -= 0.1;
                    if (fontSize <= 0.5) break; // Don't go smaller than 0.5em
                }}
            }});
        }}
        
        // Run on load and resize
        window.addEventListener('load', scaleText);
        window.addEventListener('resize', scaleText);
        </script>
        {grid_html}
        """,
        height=2000,
        scrolling=False
    )

elif area == "Cat Condo Room":
    cat_df = animal_df[animal_df["Location_1"] == "Cat Adoption Condo Rooms"].copy()
    # Define grid cells: top row (F to A), bottom row (Room 109-B, Rabbitat 1, Rabbitat 2)
    cells = [
        {"label": "Condo F", "sublocation": "Condo F"},
        {"label": "Condo E", "sublocation": "Condo E"},
        {"label": "Condo D", "sublocation": "Condo D"},
        {"label": "Condo C", "sublocation": "Condo C"},
        {"label": "Condo B", "sublocation": "Condo B"},
        {"label": "Condo A", "sublocation": "Condo A"},
        {"label": "Room 109-B", "sublocation": ["Room 109-B", "Meet & Greet 109B"]},
        {"label": "Rabbitat 1", "sublocation": "Rabbitat 1"},
        {"label": "Rabbitat 2", "sublocation": "Rabbitat 2"},
    ]
    # Build grid HTML with grid-area for placement
    cell_html = [None]*9
    for i, cell in enumerate(cells):
        if isinstance(cell["sublocation"], list):
            mask = cat_df["SubLocation"].isin(cell["sublocation"])
        else:
            mask = cat_df["SubLocation"] == cell["sublocation"]
        cell_animals = cat_df[mask].copy()
        animal_html = ""
        if not cell_animals.empty:
            for _, row in cell_animals.iterrows():
                animal_html += f'<div class="kennel-animal">{format_display_line(row)}</div>'
        else:
            animal_html = '<div class="kennel-animal">-</div>'
        cell_html[i] = f'''
            <div class="kennel-block cat-condo-block cat-condo-{i+1}">
                <div class="kennel-label-small">{cell['label']}</div>
                <div class="kennel-animal-list">{animal_html}</div>
            </div>
        '''
    # CSS grid: 6 columns top, 3 columns bottom, 2 rows
    grid_html = f'''
    <div class="kennel-grid-container cat-condo-grid" style="grid-template-columns: repeat(6, 1fr); grid-template-rows: 1fr 1fr; grid-gap: 12px;">
        {cell_html[0]}
        {cell_html[1]}
        {cell_html[2]}
        {cell_html[3]}
        {cell_html[4]}
        {cell_html[5]}
        <div></div><div></div><div></div>
        {cell_html[6]}
        {cell_html[7]}
        {cell_html[8]}
    </div>
    '''
    st.components.v1.html(
        f"""
        <style>
        .kennel-grid-container.cat-condo-grid {{
            width: 98vw;
            max-width: 1400px;
            aspect-ratio: 4 / 3;
            margin: 0 auto 32px auto;
            display: grid;
            grid-template-columns: repeat(6, 1fr);
            grid-template-rows: 1fr 1fr;
            gap: 12px;
            border: 2px solid #333;
            background: #eee;
            box-sizing: border-box;
            align-items: stretch;
            justify-items: stretch;
        }}
        .cat-condo-block {{
            background: #f9f9f9;
            border: 1.5px solid #333;
            border-radius: 6px;
            display: flex;
            flex-direction: column;
            align-items: flex-start;
            justify-content: flex-start;
            min-width: 0;
            min-height: 0;
            width: 100%;
            height: 100%;
            padding: 8px 8px 8px 8px;
            box-sizing: border-box;
            overflow: hidden;
            position: relative;
        }}
        .kennel-label-small {{
            position: absolute;
            top: 6px;
            left: 10px;
            font-size: 0.95em;
            color: #333;
            font-weight: 600;
            opacity: 0.95;
            z-index: 2;
            pointer-events: none;
        }}
        .kennel-animal-list {{
            margin-top: 2.2em;
            width: 100%;
            max-height: 100%;
            overflow-y: auto;
            container-type: inline-size;
        }}
        .kennel-animal {{
            color: #222;
            font-size: 1em; /* Base size */
            margin: 0;
            padding: 0;
            line-height: 1.1em;
            word-break: break-word;
            font-stretch: ultra-condensed;
            white-space: normal;
        }}
        .stage-abbr {{
            color: #c00;
            font-weight: bold;
            text-transform: uppercase;
            margin-left: 0.25em;
        }}
        @container (max-width: 200px) {{
            .kennel-animal {{
                font-size: 0.8em;
            }}
        }}
        @container (max-width: 150px) {{
            .kennel-animal {{
                font-size: 0.7em;
            }}
        }}
        @container (max-width: 100px) {{
            .kennel-animal {{
                font-size: 0.6em;
            }}
        }}
        </style>
        <script>
        function scaleText() {{
            document.querySelectorAll('.kennel-animal-list').forEach(container => {{
                const animals = container.querySelectorAll('.kennel-animal');
                if (animals.length === 0) return;
                
                // Start with base size
                let fontSize = 1;
                const containerHeight = container.clientHeight;
                const containerWidth = container.clientWidth;
                
                // Scale down until all content fits
                while (true) {{
                    let totalHeight = 0;
                    animals.forEach(animal => {{
                        animal.style.fontSize = fontSize + 'em';
                        totalHeight += animal.offsetHeight;
                    }});
                    
                    if (totalHeight <= containerHeight && 
                        Math.max(...Array.from(animals).map(a => a.offsetWidth)) <= containerWidth) {{
                        break;
                    }}
                    
                    fontSize -= 0.1;
                    if (fontSize <= 0.5) break; // Don't go smaller than 0.5em
                }}
            }});
        }}
        
        // Run on load and resize
        window.addEventListener('load', scaleText);
        window.addEventListener('resize', scaleText);
        </script>
        {grid_html}
        """,
        height=2000,
        scrolling=False
    )

elif area == "G Available Cats":
    g_df = animal_df[animal_df["Location_1"] == "Cat Adoption Room G"].copy()
    # Ensure SubLocation is zero-padded string
    g_df["SubLocation"] = g_df["SubLocation"].astype(str).str.zfill(2)
    # Map grid positions to SubLocations (matching your image)
    grid_map = [
        [None, "03", "06"],
        ["01", "04", "07"],
        ["02", "05", "08"]
    ]
    cell_html = []
    for row in grid_map:
        for subloc in row:
            if subloc is None:
                cell_html.append('<div class="kennel-block" style="background:transparent;border:none;"></div>')
            else:
                cell_animals = g_df[g_df["SubLocation"] == subloc].copy()
                animal_html = ""
                if not cell_animals.empty:
                    for _, row in cell_animals.iterrows():
                        animal_html += f'<div class="kennel-animal">{format_display_line(row)}</div>'
                else:
                    animal_html = '<div class="kennel-animal">-</div>'
                cell_html.append(
                    f'''
                    <div class="kennel-block">
                        <div class="kennel-label-small">{int(subloc)}</div>
                        <div class="kennel-animal-list">{animal_html}</div>
                    </div>
                    '''
                )
    grid_html = f'''
    <div class="kennel-grid-container g-cats-grid" style="grid-template-columns: repeat(3, 1fr); grid-template-rows: repeat(3, 1fr); gap: 12px;">
        {''.join(cell_html)}
    </div>
    '''
    st.components.v1.html(
        f"""
        <style>
        .kennel-grid-container.g-cats-grid {{
            width: 98vw;
            max-width: 1400px;
            aspect-ratio: 4 / 3;
            margin: 0 auto 32px auto;
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            grid-template-rows: repeat(3, 1fr);
            gap: 12px;
            border: 2px solid #333;
            background: #eee;
            box-sizing: border-box;
            align-items: stretch;
            justify-items: stretch;
        }}
        .kennel-block {{
            background: #f9f9f9;
            border: 1.5px solid #333;
            border-radius: 6px;
            display: flex;
            flex-direction: column;
            align-items: flex-start;
            justify-content: flex-start;
            min-width: 0;
            min-height: 0;
            width: 100%;
            height: 100%;
            padding: 8px 8px 8px 8px;
            box-sizing: border-box;
            overflow: hidden;
            position: relative;
        }}
        .kennel-label-small {{
            position: absolute;
            top: 6px;
            left: 10px;
            font-size: 0.95em;
            color: #333;
            font-weight: 600;
            opacity: 0.95;
            z-index: 2;
            pointer-events: none;
        }}
        .kennel-animal-list {{
            margin-top: 2.2em;
            width: 100%;
            max-height: 100%;
            overflow-y: auto;
            container-type: inline-size;
        }}
        .kennel-animal {{
            color: #222;
            font-size: 1em; /* Base size */
            margin: 0;
            padding: 0;
            line-height: 1.1em;
            word-break: break-word;
            font-stretch: ultra-condensed;
            white-space: normal;
        }}
        .stage-abbr {{
            color: #c00;
            font-weight: bold;
            text-transform: uppercase;
            margin-left: 0.25em;
        }}
        @container (max-width: 200px) {{
            .kennel-animal {{
                font-size: 0.8em;
            }}
        }}
        @container (max-width: 150px) {{
            .kennel-animal {{
                font-size: 0.7em;
            }}
        }}
        @container (max-width: 100px) {{
            .kennel-animal {{
                font-size: 0.6em;
            }}
        }}
        </style>
        <script>
        function scaleText() {{
            document.querySelectorAll('.kennel-animal-list').forEach(container => {{
                const animals = container.querySelectorAll('.kennel-animal');
                if (animals.length === 0) return;
                
                // Start with base size
                let fontSize = 1;
                const containerHeight = container.clientHeight;
                const containerWidth = container.clientWidth;
                
                // Scale down until all content fits
                while (true) {{
                    let totalHeight = 0;
                    animals.forEach(animal => {{
                        animal.style.fontSize = fontSize + 'em';
                        totalHeight += animal.offsetHeight;
                    }});
                    
                    if (totalHeight <= containerHeight && 
                        Math.max(...Array.from(animals).map(a => a.offsetWidth)) <= containerWidth) {{
                        break;
                    }}
                    
                    fontSize -= 0.1;
                    if (fontSize <= 0.5) break; // Don't go smaller than 0.5em
                }}
            }});
        }}
        
        // Run on load and resize
        window.addEventListener('load', scaleText);
        window.addEventListener('resize', scaleText);
        </script>
        {grid_html}
        """,
        height=2000,
        scrolling=False
    )

elif area == "H Available Cats":
    h_df = animal_df[animal_df["Location_1"] == "Cat Adoption Room H"].copy()
    # Ensure SubLocation is zero-padded string
    h_df["SubLocation"] = h_df["SubLocation"].astype(str).str.zfill(2)
    # Map grid positions to SubLocations (matching your image)
    grid_map = [
        ["01", "04", None],
        ["02", "05", "07"],
        ["03", "06", "08"]
    ]
    cell_html = []
    for row in grid_map:
        for subloc in row:
            if subloc is None:
                cell_html.append('<div class="kennel-block" style="background:transparent;border:none;"></div>')
            else:
                cell_animals = h_df[h_df["SubLocation"] == subloc].copy()
                animal_html = ""
                if not cell_animals.empty:
                    for _, row in cell_animals.iterrows():
                        animal_html += f'<div class="kennel-animal">{format_display_line(row)}</div>'
                else:
                    animal_html = '<div class="kennel-animal">-</div>'
                cell_html.append(
                    f'''
                    <div class="kennel-block">
                        <div class="kennel-label-small">{int(subloc)}</div>
                        <div class="kennel-animal-list">{animal_html}</div>
                    </div>
                    '''
                )
    grid_html = f'''
    <div class="kennel-grid-container h-cats-grid" style="grid-template-columns: repeat(3, 1fr); grid-template-rows: repeat(3, 1fr); gap: 12px;">
        {''.join(cell_html)}
    </div>
    '''
    st.components.v1.html(
        f"""
        <style>
        .kennel-grid-container.h-cats-grid {{
            width: 98vw;
            max-width: 1400px;
            aspect-ratio: 4 / 3;
            margin: 0 auto 32px auto;
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            grid-template-rows: repeat(3, 1fr);
            gap: 12px;
            border: 2px solid #333;
            background: #eee;
            box-sizing: border-box;
            align-items: stretch;
            justify-items: stretch;
        }}
        .kennel-block {{
            background: #f9f9f9;
            border: 1.5px solid #333;
            border-radius: 6px;
            display: flex;ç
            flex-direction: column;
            align-items: flex-start;
            justify-content: flex-start;
            min-width: 0;
            min-height: 0;
            width: 100%;
            height: 100%;
            padding: 8px 8px 8px 8px;
            box-sizing: border-box;
            overflow: hidden;
            position: relative;
        }}
        .kennel-label-small {{
            position: absolute;
            top: 6px;
            left: 10px;
            font-size: 0.95em;
            color: #333;
            font-weight: 600;
            opacity: 0.95;
            z-index: 2;
            pointer-events: none;
        }}
        .kennel-animal-list {{
            margin-top: 2.2em;
            width: 100%;
            max-height: 100%;
            overflow-y: auto;
            container-type: inline-size;
        }}
        .kennel-animal {{
            color: #222;
            font-size: 1em; /* Base size */
            margin: 0;
            padding: 0;
            line-height: 1.1em;
            word-break: break-word;
            font-stretch: ultra-condensed;
            white-space: normal;
        }}
        .stage-abbr {{
            color: #c00;
            font-weight: bold;
            text-transform: uppercase;
            margin-left: 0.25em;
        }}
        @container (max-width: 200px) {{
            .kennel-animal {{
                font-size: 0.8em;
            }}
        }}
        @container (max-width: 150px) {{
            .kennel-animal {{
                font-size: 0.7em;
            }}
        }}
        @container (max-width: 100px) {{
            .kennel-animal {{
                font-size: 0.6em;
            }}
        }}
        </style>
        <script>
        function scaleText() {{
            document.querySelectorAll('.kennel-animal-list').forEach(container => {{
                const animals = container.querySelectorAll('.kennel-animal');
                if (animals.length === 0) return;
                
                // Start with base size
                let fontSize = 1;
                const containerHeight = container.clientHeight;
                const containerWidth = container.clientWidth;
                
                // Scale down until all content fits
                while (true) {{
                    let totalHeight = 0;
                    animals.forEach(animal => {{
                        animal.style.fontSize = fontSize + 'em';
                        totalHeight += animal.offsetHeight;
                    }});
                    
                    if (totalHeight <= containerHeight && 
                        Math.max(...Array.from(animals).map(a => a.offsetWidth)) <= containerWidth) {{
                        break;
                    }}
                    
                    fontSize -= 0.1;
                    if (fontSize <= 0.5) break; // Don't go smaller than 0.5em
                }}
            }});
        }}
        
        // Run on load and resize
        window.addEventListener('load', scaleText);
        window.addEventListener('resize', scaleText);
        </script>
        {grid_html}
        """,
        height=2000,
        scrolling=False
    )

elif area == "I Behavior/Bite Case":
    i_df = animal_df[animal_df["Location_1"] == "Cat Behavior Room I"].copy()
    # Ensure SubLocation is zero-padded string
    i_df["SubLocation"] = i_df["SubLocation"].astype(str).str.zfill(2)
    # Map grid positions to SubLocations (same as G Available Cats)
    grid_map = [
        [None, "03", "06"],
        ["01", "04", "07"],
        ["02", "05", "08"]
    ]
    cell_html = []
    for row in grid_map:
        for subloc in row:
            if subloc is None:
                cell_html.append('<div class="kennel-block" style="background:transparent;border:none;"></div>')
            else:
                cell_animals = i_df[i_df["SubLocation"] == subloc].copy()
                animal_html = ""
                if not cell_animals.empty:
                    for _, row in cell_animals.iterrows():
                        animal_html += f'<div class="kennel-animal">{format_display_line(row)}</div>'
                else:
                    animal_html = '<div class="kennel-animal">-</div>'
                cell_html.append(
                    f'''
                    <div class="kennel-block">
                        <div class="kennel-label-small">{int(subloc)}</div>
                        <div class="kennel-animal-list">{animal_html}</div>
                    </div>
                    '''
                )
    grid_html = f'''
    <div class="kennel-grid-container i-cats-grid" style="grid-template-columns: repeat(3, 1fr); grid-template-rows: repeat(3, 1fr); gap: 12px;">
        {''.join(cell_html)}
    </div>
    '''
    st.components.v1.html(
        f"""
        <style>
        .kennel-grid-container.i-cats-grid {{
            width: 98vw;
            max-width: 1400px;
            aspect-ratio: 4 / 3;
            margin: 0 auto 32px auto;
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            grid-template-rows: repeat(3, 1fr);
            gap: 12px;
            border: 2px solid #333;
            background: #eee;
            box-sizing: border-box;
            align-items: stretch;
            justify-items: stretch;
        }}
        .kennel-block {{
            background: #f9f9f9;
            border: 1.5px solid #333;
            border-radius: 6px;
            display: flex;
            flex-direction: column;
            align-items: flex-start;
            justify-content: flex-start;
            min-width: 0;
            min-height: 0;
            width: 100%;
            height: 100%;
            padding: 8px 8px 8px 8px;
            box-sizing: border-box;
            overflow: hidden;
            position: relative;
        }}
        .kennel-label-small {{
            position: absolute;
            top: 6px;
            left: 10px;
            font-size: 0.95em;
            color: #333;
            font-weight: 600;
            opacity: 0.95;
            z-index: 2;
            pointer-events: none;
        }}
        .kennel-animal-list {{
            margin-top: 2.2em;
            width: 100%;
            max-height: 100%;
            overflow-y: auto;
            container-type: inline-size;
        }}
        .kennel-animal {{
            color: #222;
            font-size: 1em; /* Base size */
            margin: 0;
            padding: 0;
            line-height: 1.1em;
            word-break: break-word;
            font-stretch: ultra-condensed;
            white-space: normal;
        }}
        .stage-abbr {{
            color: #c00;
            font-weight: bold;
            text-transform: uppercase;
            margin-left: 0.25em;
        }}
        @container (max-width: 200px) {{
            .kennel-animal {{
                font-size: 0.8em;
            }}
        }}
        @container (max-width: 150px) {{
            .kennel-animal {{
                font-size: 0.7em;
            }}
        }}
        @container (max-width: 100px) {{
            .kennel-animal {{
                font-size: 0.6em;
            }}
        }}
        </style>
        <script>
        function scaleText() {{
            document.querySelectorAll('.kennel-animal-list').forEach(container => {{
                const animals = container.querySelectorAll('.kennel-animal');
                if (animals.length === 0) return;
                
                // Start with base size
                let fontSize = 1;
                const containerHeight = container.clientHeight;
                const containerWidth = container.clientWidth;
                
                // Scale down until all content fits
                while (true) {{
                    let totalHeight = 0;
                    animals.forEach(animal => {{
                        animal.style.fontSize = fontSize + 'em';
                        totalHeight += animal.offsetHeight;
                    }});
                    
                    if (totalHeight <= containerHeight && 
                        Math.max(...Array.from(animals).map(a => a.offsetWidth)) <= containerWidth) {{
                        break;
                    }}
                    
                    fontSize -= 0.1;
                    if (fontSize <= 0.5) break; // Don't go smaller than 0.5em
                }}
            }});
        }}
        
        // Run on load and resize
        window.addEventListener('load', scaleText);
        window.addEventListener('resize', scaleText);
        </script>
        {grid_html}
        """,
        height=2000,
        scrolling=False
    )

elif area == "Foster Care":
    foster_df = animal_df[animal_df["Location_1"] == "Foster Care Room"].copy()
    # Ensure SubLocation is zero-padded string
    foster_df["SubLocation"] = foster_df["SubLocation"].astype(str).str.zfill(2)
    # Map grid positions to SubLocations (same as H Available Cats)
    grid_map = [
        ["01", "04", None],
        ["02", "05", "07"],
        ["03", "06", "08"]
    ]
    cell_html = []
    for row in grid_map:
        for subloc in row:
            if subloc is None:
                cell_html.append('<div class="kennel-block" style="background:transparent;border:none;"></div>')
            else:
                cell_animals = foster_df[foster_df["SubLocation"] == subloc].copy()
                animal_html = ""
                if not cell_animals.empty:
                    for _, row in cell_animals.iterrows():
                        animal_html += f'<div class="kennel-animal">{format_display_line(row)}</div>'
                else:
                    animal_html = '<div class="kennel-animal">-</div>'
                cell_html.append(
                    f'''
                    <div class="kennel-block">
                        <div class="kennel-label-small">{int(subloc)}</div>
                        <div class="kennel-animal-list">{animal_html}</div>
                    </div>
                    '''
                )
    grid_html = f'''
    <div class="kennel-grid-container foster-grid" style="grid-template-columns: repeat(3, 1fr); grid-template-rows: repeat(3, 1fr); gap: 12px;">
        {''.join(cell_html)}
    </div>
    '''
    st.components.v1.html(
        f"""
        <style>
        .kennel-grid-container.foster-grid {{
            width: 98vw;
            max-width: 1400px;
            aspect-ratio: 4 / 3;
            margin: 0 auto 32px auto;
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            grid-template-rows: repeat(3, 1fr);
            gap: 12px;
            border: 2px solid #333;
            background: #eee;
            box-sizing: border-box;
            align-items: stretch;
            justify-items: stretch;
        }}
        .kennel-block {{
            background: #f9f9f9;
            border: 1.5px solid #333;
            border-radius: 6px;
            display: flex;
            flex-direction: column;
            align-items: flex-start;
            justify-content: flex-start;
            min-width: 0;
            min-height: 0;
            width: 100%;
            height: 100%;
            padding: 8px 8px 8px 8px;
            box-sizing: border-box;
            overflow: hidden;
            position: relative;
        }}
        .kennel-label-small {{
            position: absolute;
            top: 6px;
            left: 10px;
            font-size: 0.95em;
            color: #333;
            font-weight: 600;
            opacity: 0.95;
            z-index: 2;
            pointer-events: none;
        }}
        .kennel-animal-list {{
            margin-top: 2.2em;
            width: 100%;
            max-height: 100%;
            overflow-y: auto;
            container-type: inline-size;
        }}
        .kennel-animal {{
            color: #222;
            font-size: 1em; /* Base size */
            margin: 0;
            padding: 0;
            line-height: 1.1em;
            word-break: break-word;
            font-stretch: ultra-condensed;
            white-space: normal;
        }}
        .stage-abbr {{
            color: #c00;
            font-weight: bold;
            text-transform: uppercase;
            margin-left: 0.25em;
        }}
        @container (max-width: 200px) {{
            .kennel-animal {{
                font-size: 0.8em;
            }}
        }}
        @container (max-width: 150px) {{
            .kennel-animal {{
                font-size: 0.7em;
            }}
        }}
        @container (max-width: 100px) {{
            .kennel-animal {{
                font-size: 0.6em;
            }}
        }}
        </style>
        <script>
        function scaleText() {{
            document.querySelectorAll('.kennel-animal-list').forEach(container => {{
                const animals = container.querySelectorAll('.kennel-animal');
                if (animals.length === 0) return;
                
                // Start with base size
                let fontSize = 1;
                const containerHeight = container.clientHeight;
                const containerWidth = container.clientWidth;
                
                // Scale down until all content fits
                while (true) {{
                    let totalHeight = 0;
                    animals.forEach(animal => {{
                        animal.style.fontSize = fontSize + 'em';
                        totalHeight += animal.offsetHeight;
                    }});
                    
                    if (totalHeight <= containerHeight && 
                        Math.max(...Array.from(animals).map(a => a.offsetWidth)) <= containerWidth) {{
                        break;
                    }}
                    
                    fontSize -= 0.1;
                    if (fontSize <= 0.5) break; // Don't go smaller than 0.5em
                }}
            }});
        }}
        
        // Run on load and resize
        window.addEventListener('load', scaleText);
        window.addEventListener('resize', scaleText);
        </script>
        {grid_html}
        """,
        height=2000,
        scrolling=False
    )

elif area == "Cat Isolation 235":
    iso_df = animal_df[animal_df["Location_1"] == "Cat Isolation 235"].copy()
    # Extract cage number from SubLocation (e.g., 'Cage 1' -> '1')
    iso_df["CageNum"] = iso_df["SubLocation"].astype(str).str.extract(r'(\d+)')
    # Map grid positions to cage numbers
    grid_map = [
        ["1", "4", "7"],
        ["2", "5", "8"],
        ["3", "6", "9"]
    ]
    cell_html = []
    for row in grid_map:
        for cage_num in row:
            cell_animals = iso_df[iso_df["CageNum"] == cage_num].copy()
            animal_html = ""
            if not cell_animals.empty:
                for _, row in cell_animals.iterrows():
                    animal_html += f'<div class="kennel-animal">{format_display_line(row)}</div>'
            else:
                animal_html = '<div class="kennel-animal">-</div>'
            cell_html.append(
                f'''
                <div class="kennel-block">
                    <div class="kennel-label-small">{cage_num}</div>
                    <div class="kennel-animal-list">{animal_html}</div>
                </div>
                '''
            )
    grid_html = f'''
    <div class="kennel-grid-container iso-grid" style="grid-template-columns: repeat(3, 1fr); grid-template-rows: repeat(3, 1fr); gap: 12px;">
        {''.join(cell_html)}
    </div>
    '''
    st.components.v1.html(
        f"""
        <style>
        .kennel-grid-container.iso-grid {{
            width: 98vw;
            max-width: 1400px;
            aspect-ratio: 4 / 3;
            margin: 0 auto 32px auto;
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            grid-template-rows: repeat(3, 1fr);
            gap: 12px;
            border: 2px solid #333;
            background: #eee;
            box-sizing: border-box;
            align-items: stretch;
            justify-items: stretch;
        }}
        .kennel-block {{
            background: #f9f9f9;
            border: 1.5px solid #333;
            border-radius: 6px;
            display: flex;
            flex-direction: column;
            align-items: flex-start;
            justify-content: flex-start;
            min-width: 0;
            min-height: 0;
            width: 100%;
            height: 100%;
            padding: 8px 8px 8px 8px;
            box-sizing: border-box;
            overflow: hidden;
            position: relative;
        }}
        .kennel-label-small {{
            position: absolute;
            top: 6px;
            left: 10px;
            font-size: 0.95em;
            color: #333;
            font-weight: 600;
            opacity: 0.95;
            z-index: 2;
            pointer-events: none;
        }}
        .kennel-animal-list {{
            margin-top: 2.2em;
            width: 100%;
            max-height: 100%;
            overflow-y: auto;
            container-type: inline-size;
        }}
        .kennel-animal {{
            color: #222;
            font-size: 1em; /* Base size */
            margin: 0;
            padding: 0;
            line-height: 1.1em;
            word-break: break-word;
            font-stretch: ultra-condensed;
            white-space: normal;
        }}
        .stage-abbr {{
            color: #c00;
            font-weight: bold;
            text-transform: uppercase;
            margin-left: 0.25em;
        }}
        @container (max-width: 200px) {{
            .kennel-animal {{
                font-size: 0.8em;
            }}
        }}
        @container (max-width: 150px) {{
            .kennel-animal {{
                font-size: 0.7em;
            }}
        }}
        @container (max-width: 100px) {{
            .kennel-animal {{
                font-size: 0.6em;
            }}
        }}
        </style>
        <script>
        function scaleText() {{
            document.querySelectorAll('.kennel-animal-list').forEach(container => {{
                const animals = container.querySelectorAll('.kennel-animal');
                if (animals.length === 0) return;
                
                // Start with base size
                let fontSize = 1;
                const containerHeight = container.clientHeight;
                const containerWidth = container.clientWidth;
                
                // Scale down until all content fits
                while (true) {{
                    let totalHeight = 0;
                    animals.forEach(animal => {{
                        animal.style.fontSize = fontSize + 'em';
                        totalHeight += animal.offsetHeight;
                    }});
                    
                    if (totalHeight <= containerHeight && 
                        Math.max(...Array.from(animals).map(a => a.offsetWidth)) <= containerWidth) {{
                        break;
                    }}
                    
                    fontSize -= 0.1;
                    if (fontSize <= 0.5) break; // Don't go smaller than 0.5em
                }}
            }});
        }}
        
        // Run on load and resize
        window.addEventListener('load', scaleText);
        window.addEventListener('resize', scaleText);
        </script>
        {grid_html}
        """,
        height=2000,
        scrolling=False
    )

elif area == "Cat Isolation 234 Overflow":
    iso234_df = animal_df[animal_df["Location_1"] == "Cat Isolation 234"].copy()
    # Extract cage number from SubLocation (e.g., 'Cage 1' -> '1')
    iso234_df["CageNum"] = iso234_df["SubLocation"].astype(str).str.extract(r'(\d+)')
    # Map grid positions to cage numbers
    grid_map = [
        ["1", None, None],
        ["2", "4", None],
        ["3", "5", "6"]
    ]
    cell_html = []
    for row in grid_map:
        for cage_num in row:
            if cage_num is None:
                cell_html.append('<div class="kennel-block" style="background:transparent;border:none;"></div>')
            else:
                cell_animals = iso234_df[iso234_df["CageNum"] == cage_num].copy()
                animal_html = ""
                if not cell_animals.empty:
                    for _, row in cell_animals.iterrows():
                        animal_html += f'<div class="kennel-animal">{format_display_line(row)}</div>'
                else:
                    animal_html = '<div class="kennel-animal">-</div>'
                cell_html.append(
                    f'''
                    <div class="kennel-block">
                        <div class="kennel-label-small">{cage_num}</div>
                        <div class="kennel-animal-list">{animal_html}</div>
                    </div>
                    '''
                )
    grid_html = f'''
    <div class="kennel-grid-container iso234-grid" style="grid-template-columns: repeat(3, 1fr); grid-template-rows: repeat(3, 1fr); gap: 12px;">
        {''.join(cell_html)}
    </div>
    '''
    st.components.v1.html(
        f"""
        <style>
        .kennel-grid-container.iso234-grid {{
            width: 98vw;
            max-width: 1400px;
            aspect-ratio: 4 / 3;
            margin: 0 auto 32px auto;
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            grid-template-rows: repeat(3, 1fr);
            gap: 12px;
            border: 2px solid #333;
            background: #eee;
            box-sizing: border-box;
            align-items: stretch;
            justify-items: stretch;
        }}
        .kennel-block {{
            background: #f9f9f9;
            border: 1.5px solid #333;
            border-radius: 6px;
            display: flex;
            flex-direction: column;
            align-items: flex-start;
            justify-content: flex-start;
            min-width: 0;
            min-height: 0;
            width: 100%;
            height: 100%;
            padding: 8px 8px 8px 8px;
            box-sizing: border-box;
            overflow: hidden;
            position: relative;
        }}
        .kennel-label-small {{
            position: absolute;
            top: 6px;
            left: 10px;
            font-size: 0.95em;
            color: #333;
            font-weight: 600;
            opacity: 0.95;
            z-index: 2;
            pointer-events: none;
        }}
        .kennel-animal-list {{
            margin-top: 2.2em;
            width: 100%;
            max-height: 100%;
            overflow-y: auto;
            container-type: inline-size;
        }}
        .kennel-animal {{
            color: #222;
            font-size: 1em; /* Base size */
            margin: 0;
            padding: 0;
            line-height: 1.1em;
            word-break: break-word;
            font-stretch: ultra-condensed;
            white-space: normal;
        }}
        .stage-abbr {{
            color: #c00;
            font-weight: bold;
            text-transform: uppercase;
            margin-left: 0.25em;
        }}
        @container (max-width: 200px) {{
            .kennel-animal {{
                font-size: 0.8em;
            }}
        }}
        @container (max-width: 150px) {{
            .kennel-animal {{
                font-size: 0.7em;
            }}
        }}
        @container (max-width: 100px) {{
            .kennel-animal {{
                font-size: 0.6em;
            }}
        }}
        </style>
        <script>
        function scaleText() {{
            document.querySelectorAll('.kennel-animal-list').forEach(container => {{
                const animals = container.querySelectorAll('.kennel-animal');
                if (animals.length === 0) return;
                
                // Start with base size
                let fontSize = 1;
                const containerHeight = container.clientHeight;
                const containerWidth = container.clientWidth;
                
                // Scale down until all content fits
                while (true) {{
                    let totalHeight = 0;
                    animals.forEach(animal => {{
                        animal.style.fontSize = fontSize + 'em';
                        totalHeight += animal.offsetHeight;
                    }});
                    
                    if (totalHeight <= containerHeight && 
                        Math.max(...Array.from(animals).map(a => a.offsetWidth)) <= containerWidth) {{
                        break;
                    }}
                    
                    fontSize -= 0.1;
                    if (fontSize <= 0.5) break; // Don't go smaller than 0.5em
                }}
            }});
        }}
        
        // Run on load and resize
        window.addEventListener('load', scaleText);
        window.addEventListener('resize', scaleText);
        </script>
        {grid_html}
        """,
        height=2000,
        scrolling=False
    )

elif area == "Cat Isolation 233 Ringworm":
    iso233_df = animal_df[animal_df["Location_1"] == "Cat Isolation 233"].copy()
    # Extract cage number from SubLocation (e.g., 'Cage 1' -> '1')
    iso233_df["CageNum"] = iso233_df["SubLocation"].astype(str).str.extract(r'(\d+)')
    # Map grid positions to cage numbers
    # Top row: 1, 2, 4, 5; Bottom row: 3 (span 2), 6 (span 2)
    cell_html = []
    # Top row
    for cage_num in ["1", "2", "4", "5"]:
        cell_animals = iso233_df[iso233_df["CageNum"] == cage_num].copy()
        animal_html = ""
        if not cell_animals.empty:
            for _, row in cell_animals.iterrows():
                animal_html += f'<div class="kennel-animal">{format_display_line(row)}</div>'
        else:
            animal_html = '<div class="kennel-animal">-</div>'
        cell_html.append(
            f'''
            <div class="kennel-block">
                <div class="kennel-label-small">{cage_num}</div>
                <div class="kennel-animal-list">{animal_html}</div>
            </div>
            '''
        )
    # Bottom row: 3 (span 2), 6 (span 2)
    for cage_num in ["3", "6"]:
        cell_animals = iso233_df[iso233_df["CageNum"] == cage_num].copy()
        animal_html = ""
        if not cell_animals.empty:
            for _, row in cell_animals.iterrows():
                animal_html += f'<div class="kennel-animal">{format_display_line(row)}</div>'
        else:
            animal_html = '<div class="kennel-animal">-</div>'
        cell_html.append(
            f'''
            <div class="kennel-block" style="grid-column: span 2;">
                <div class="kennel-label-small">{cage_num}</div>
                <div class="kennel-animal-list">{animal_html}</div>
            </div>
            '''
        )
    grid_html = f'''
    <div class="kennel-grid-container iso233-grid" style="grid-template-columns: repeat(4, 1fr); grid-template-rows: repeat(2, 1fr); gap: 12px;">
        {''.join(cell_html)}
    </div>
    '''
    st.components.v1.html(
        f"""
        <style>
        .kennel-grid-container.iso233-grid {{
            width: 98vw;
            max-width: 1400px;
            aspect-ratio: 4 / 3;
            margin: 0 auto 32px auto;
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            grid-template-rows: repeat(2, 1fr);
            gap: 12px;
            border: 2px solid #333;
            background: #eee;
            box-sizing: border-box;
            align-items: stretch;
            justify-items: stretch;
        }}
        .kennel-block {{
            background: #f9f9f9;
            border: 1.5px solid #333;
            border-radius: 6px;
            display: flex;
            flex-direction: column;
            align-items: flex-start;
            justify-content: flex-start;
            min-width: 0;
            min-height: 0;
            width: 100%;
            height: 100%;
            padding: 8px 8px 8px 8px;
            box-sizing: border-box;
            overflow: hidden;
            position: relative;
        }}
        .kennel-label-small {{
            position: absolute;
            top: 6px;
            left: 10px;
            font-size: 0.95em;
            color: #333;
            font-weight: 600;
            opacity: 0.95;
            z-index: 2;
            pointer-events: none;
        }}
        .kennel-animal-list {{
            margin-top: 2.2em;
            width: 100%;
            max-height: 100%;
            overflow-y: auto;
            container-type: inline-size;
        }}
        .kennel-animal {{
            color: #222;
            font-size: 1em; /* Base size */
            margin: 0;
            padding: 0;
            line-height: 1.1em;
            word-break: break-word;
            font-stretch: ultra-condensed;
            white-space: normal;
        }}
        .stage-abbr {{
            color: #c00;
            font-weight: bold;
            text-transform: uppercase;
            margin-left: 0.25em;
        }}
        @container (max-width: 200px) {{
            .kennel-animal {{
                font-size: 0.8em;
            }}
        }}
        @container (max-width: 150px) {{
            .kennel-animal {{
                font-size: 0.7em;
            }}
        }}
        @container (max-width: 100px) {{
            .kennel-animal {{
                font-size: 0.6em;
            }}
        }}
        </style>
        <script>
        function scaleText() {{
            document.querySelectorAll('.kennel-animal-list').forEach(container => {{
                const animals = container.querySelectorAll('.kennel-animal');
                if (animals.length === 0) return;
                
                // Start with base size
                let fontSize = 1;
                const containerHeight = container.clientHeight;
                const containerWidth = container.clientWidth;
                
                // Scale down until all content fits
                while (true) {{
                    let totalHeight = 0;
                    animals.forEach(animal => {{
                        animal.style.fontSize = fontSize + 'em';
                        totalHeight += animal.offsetHeight;
                    }});
                    
                    if (totalHeight <= containerHeight && 
                        Math.max(...Array.from(animals).map(a => a.offsetWidth)) <= containerWidth) {{
                        break;
                    }}
                    
                    fontSize -= 0.1;
                    if (fontSize <= 0.5) break; // Don't go smaller than 0.5em
                }}
            }});
        }}
        
        // Run on load and resize
        window.addEventListener('load', scaleText);
        window.addEventListener('resize', scaleText);
        </script>
        {grid_html}
        """,
        height=2000,
        scrolling=False
    )

elif area == "Cat Isolation 232 Panleuk":
    iso232_df = animal_df[animal_df["Location_1"] == "Cat Isolation 232"].copy()
    # Extract cage number from SubLocation (e.g., 'Cage 1' -> '1')
    iso232_df["CageNum"] = iso232_df["SubLocation"].astype(str).str.extract(r'(\d+)')
    # Map grid positions to cage numbers
    grid_map = [
        ["1", "4"],
        ["2", "5"],
        ["3", "6"]
    ]
    cell_html = []
    for row in grid_map:
        for cage_num in row:
            cell_animals = iso232_df[iso232_df["CageNum"] == cage_num].copy()
            animal_html = ""
            if not cell_animals.empty:
                for _, row in cell_animals.iterrows():
                    animal_html += f'<div class="kennel-animal">{format_display_line(row)}</div>'
            else:
                animal_html = '<div class="kennel-animal">-</div>'
            cell_html.append(
                f'''
                <div class="kennel-block">
                    <div class="kennel-label-small">{cage_num}</div>
                    <div class="kennel-animal-list">{animal_html}</div>
                </div>
                '''
            )
    grid_html = f'''
    <div class="kennel-grid-container iso232-grid" style="grid-template-columns: repeat(2, 1fr); grid-template-rows: repeat(3, 1fr); gap: 12px;">
        {''.join(cell_html)}
    </div>
    '''
    st.components.v1.html(
        f"""
        <style>
        .kennel-grid-container.iso232-grid {{
            width: 98vw;
            max-width: 1400px;
            aspect-ratio: 4 / 3;
            margin: 0 auto 32px auto;
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            grid-template-rows: repeat(3, 1fr);
            gap: 12px;
            border: 2px solid #333;
            background: #eee;
            box-sizing: border-box;
            align-items: stretch;
            justify-items: stretch;
        }}
        .kennel-block {{
            background: #f9f9f9;
            border: 1.5px solid #333;
            border-radius: 6px;
            display: flex;
            flex-direction: column;
            align-items: flex-start;
            justify-content: flex-start;
            min-width: 0;
            min-height: 0;
            width: 100%;
            height: 100%;
            padding: 8px 8px 8px 8px;
            box-sizing: border-box;
            overflow: hidden;
            position: relative;
        }}
        .kennel-label-small {{
            position: absolute;
            top: 6px;
            left: 10px;
            font-size: 0.95em;
            color: #333;
            font-weight: 600;
            opacity: 0.95;
            z-index: 2;
            pointer-events: none;
        }}
        .kennel-animal-list {{
            margin-top: 2.2em;
            width: 100%;
            max-height: 100%;
            overflow-y: auto;
            container-type: inline-size;
        }}
        .kennel-animal {{
            color: #222;
            font-size: 1em; /* Base size */
            margin: 0;
            padding: 0;
            line-height: 1.1em;
            word-break: break-word;
            font-stretch: ultra-condensed;
            white-space: normal;
        }}
        .stage-abbr {{
            color: #c00;
            font-weight: bold;
            text-transform: uppercase;
            margin-left: 0.25em;
        }}
        @container (max-width: 200px) {{
            .kennel-animal {{
                font-size: 0.8em;
            }}
        }}
        @container (max-width: 150px) {{
            .kennel-animal {{
                font-size: 0.7em;
            }}
        }}
        @container (max-width: 100px) {{
            .kennel-animal {{
                font-size: 0.6em;
            }}
        }}
        </style>
        <script>
        function scaleText() {{
            document.querySelectorAll('.kennel-animal-list').forEach(container => {{
                const animals = container.querySelectorAll('.kennel-animal');
                if (animals.length === 0) return;
                
                // Start with base size
                let fontSize = 1;
                const containerHeight = container.clientHeight;
                const containerWidth = container.clientWidth;
                
                // Scale down until all content fits
                while (true) {{
                    let totalHeight = 0;
                    animals.forEach(animal => {{
                        animal.style.fontSize = fontSize + 'em';
                        totalHeight += animal.offsetHeight;
                    }});
                    
                    if (totalHeight <= containerHeight && 
                        Math.max(...Array.from(animals).map(a => a.offsetWidth)) <= containerWidth) {{
                        break;
                    }}
                    
                    fontSize -= 0.1;
                    if (fontSize <= 0.5) break; // Don't go smaller than 0.5em
                }}
            }});
        }}
        
        // Run on load and resize
        window.addEventListener('load', scaleText);
        window.addEventListener('resize', scaleText);
        </script>
        {grid_html}
        """,
        height=2000,
        scrolling=False
    )

elif area == "Cat Isolation 231 Holds":
    iso231_df = animal_df[animal_df["Location_1"] == "Cat Isolation 231"].copy()
    # Extract cage number from SubLocation (e.g., 'Cage 1' -> '1')
    iso231_df["CageNum"] = iso231_df["SubLocation"].astype(str).str.extract(r'(\d+)')
    # Map grid positions to cage numbers
    grid_map = [
        ["1", "4", "7"],
        ["2", "5", "8"],
        ["3", "6", "9"]
    ]
    cell_html = []
    for row in grid_map:
        for cage_num in row:
            cell_animals = iso231_df[iso231_df["CageNum"] == cage_num].copy()
            animal_html = ""
            if not cell_animals.empty:
                for _, row in cell_animals.iterrows():
                    animal_html += f'<div class="kennel-animal">{format_display_line(row)}</div>'
            else:
                animal_html = '<div class="kennel-animal">-</div>'
            cell_html.append(
                f'''
                <div class="kennel-block">
                    <div class="kennel-label-small">{cage_num}</div>
                    <div class="kennel-animal-list">{animal_html}</div>
                </div>
                '''
            )
    grid_html = f'''
    <div class="kennel-grid-container iso231-grid" style="grid-template-columns: repeat(3, 1fr); grid-template-rows: repeat(3, 1fr); gap: 12px;">
        {''.join(cell_html)}
    </div>
    '''
    st.components.v1.html(
        f"""
        <style>
        .kennel-grid-container.iso231-grid {{
            width: 98vw;
            max-width: 1400px;
            aspect-ratio: 4 / 3;
            margin: 0 auto 32px auto;
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            grid-template-rows: repeat(3, 1fr);
            gap: 12px;
            border: 2px solid #333;
            background: #eee;
            box-sizing: border-box;
            align-items: stretch;
            justify-items: stretch;
        }}
        .kennel-block {{
            background: #f9f9f9;
            border: 1.5px solid #333;
            border-radius: 6px;
            display: flex;
            flex-direction: column;
            align-items: flex-start;
            justify-content: flex-start;
            min-width: 0;
            min-height: 0;
            width: 100%;
            height: 100%;
            padding: 8px 8px 8px 8px;
            box-sizing: border-box;
            overflow: hidden;
            position: relative;
        }}
        .kennel-label-small {{
            position: absolute;
            top: 6px;
            left: 10px;
            font-size: 0.95em;
            color: #333;
            font-weight: 600;
            opacity: 0.95;
            z-index: 2;
            pointer-events: none;
        }}
        .kennel-animal-list {{
            margin-top: 2.2em;
            width: 100%;
            max-height: 100%;
            overflow-y: auto;
            container-type: inline-size;
        }}
        .kennel-animal {{
            color: #222;
            font-size: 1em; /* Base size */
            margin: 0;
            padding: 0;
            line-height: 1.1em;
            word-break: break-word;
            font-stretch: ultra-condensed;
            white-space: normal;
        }}
        .stage-abbr {{
            color: #c00;
            font-weight: bold;
            text-transform: uppercase;
            margin-left: 0.25em;
        }}
        @container (max-width: 200px) {{
            .kennel-animal {{
                font-size: 0.8em;
            }}
        }}
        @container (max-width: 150px) {{
            .kennel-animal {{
                font-size: 0.7em;
            }}
        }}
        @container (max-width: 100px) {{
            .kennel-animal {{
                font-size: 0.6em;
            }}
        }}
        </style>
        <script>
        function scaleText() {{
            document.querySelectorAll('.kennel-animal-list').forEach(container => {{
                const animals = container.querySelectorAll('.kennel-animal');
                if (animals.length === 0) return;
                
                // Start with base size
                let fontSize = 1;
                const containerHeight = container.clientHeight;
                const containerWidth = container.clientWidth;
                
                // Scale down until all content fits
                while (true) {{
                    let totalHeight = 0;
                    animals.forEach(animal => {{
                        animal.style.fontSize = fontSize + 'em';
                        totalHeight += animal.offsetHeight;
                    }});
                    
                    if (totalHeight <= containerHeight && 
                        Math.max(...Array.from(animals).map(a => a.offsetWidth)) <= containerWidth) {{
                        break;
                    }}
                    
                    fontSize -= 0.1;
                    if (fontSize <= 0.5) break; // Don't go smaller than 0.5em
                }}
            }});
        }}
        
        // Run on load and resize
        window.addEventListener('load', scaleText);
        window.addEventListener('resize', scaleText);
        </script>
        {grid_html}
        """,
        height=2000,
        scrolling=False
    )

elif area == "Cat Treatment":
    treat_df = animal_df[animal_df["Location_1"] == "Cat Treatment"].copy()
    treat_df["SubLocation"] = treat_df["SubLocation"].astype(str).str.strip()
    # --- Incubator 1-6 block (3x2) ---
    inc1_6_html = []
    for row in range(3):
        for col in range(2):
            idx = row + col*3
            label = f"Incubator {col*3+row+1}"
            subloc = f"Incubator {col*3+row+1}"
            cell_animals = treat_df[treat_df["SubLocation"] == subloc].copy()
            animal_html = ""
            if not cell_animals.empty:
                for _, row_ in cell_animals.iterrows():
                    animal_html += f'<div class="kennel-animal">{format_display_line(row_)}</div>'
            else:
                animal_html = '<div class="kennel-animal">-</div>'
            inc1_6_html.append(
                f'''
                <div class="kennel-block">
                    <div class="kennel-label-small">{label}</div>
                    <div class="kennel-animal-list">{animal_html}</div>
                </div>
                '''
            )
    inc1_6_grid = f'''<div class="cat-treat-inc1-6" style="display:grid;grid-template-columns:1fr 1fr;grid-template-rows:repeat(3,1fr);gap:4px;">{''.join(inc1_6_html)}</div>'''
    # --- Incubator 210A-D block (4x1) ---
    inc210_html = []
    for subloc in ["Incubator 210A", "Incubator 210B", "Incubator 210C", "Incubator 210D"]:
        label = subloc
        cell_animals = treat_df[treat_df["SubLocation"] == subloc].copy()
        animal_html = ""
        if not cell_animals.empty:
            for _, row_ in cell_animals.iterrows():
                animal_html += f'<div class="kennel-animal">{format_display_line(row_)}</div>'
        else:
            animal_html = '<div class="kennel-animal">-</div>'
        inc210_html.append(
            f'''
            <div class="kennel-block">
                <div class="kennel-label-small">{label}</div>
                <div class="kennel-animal-list">{animal_html}</div>
            </div>
            '''
        )
    inc210_grid = f'''<div class="cat-treat-inc210" style="display:grid;grid-template-columns:1fr;grid-template-rows:repeat(4,1fr);gap:4px;">{''.join(inc210_html)}</div>'''
    # --- Cages block (2x4, with 3 and 6 spanning 2 columns) ---
    cage_html = []
    # Top row: 1,2,4,5
    for idx, cage in enumerate(["01", "02", "04", "05"]):
        label = str(int(cage))
        cell_animals = treat_df[treat_df["SubLocation"] == cage].copy()
        animal_html = ""
        if not cell_animals.empty:
            for _, row_ in cell_animals.iterrows():
                animal_html += f'<div class="kennel-animal">{format_display_line(row_)}</div>'
        else:
            animal_html = '<div class="kennel-animal">-</div>'
        cage_html.append(
            f'''
            <div class="kennel-block" style="grid-column: {idx+1}; grid-row: 1;">
                <div class="kennel-label-small">{label}</div>
                <div class="kennel-animal-list">{animal_html}</div>
            </div>
            '''
        )
    # Bottom row: 3 (span 2), 6 (span 2)
    for idx, cage in enumerate(["03", "06"]):
        label = str(int(cage))
        cell_animals = treat_df[treat_df["SubLocation"] == cage].copy()
        animal_html = ""
        if not cell_animals.empty:
            for _, row_ in cell_animals.iterrows():
                animal_html += f'<div class="kennel-animal">{format_display_line(row_)}</div>'
        else:
            animal_html = '<div class="kennel-animal">-</div>'
        col_start = 1 if idx == 0 else 3
        cage_html.append(
            f'''
            <div class="kennel-block" style="grid-column: {col_start} / span 2; grid-row: 2;">
                <div class="kennel-label-small">{label}</div>
                <div class="kennel-animal-list">{animal_html}</div>
            </div>
            '''
        )
    cage_grid = f'''<div class="cat-treat-cages" style="display:grid;grid-template-columns:repeat(4,1fr);grid-template-rows:repeat(2,1fr);gap:4px;width:100%;height:100%;">{''.join(cage_html)}</div>'''
    # --- Layout all blocks in a flex row ---
    grid_html = f'''
    <div class="cat-treat-flex" style="display:flex;flex-direction:row;justify-content:space-between;align-items:stretch;width:98vw;max-width:1400px;aspect-ratio:4/3;margin:0 auto 32px auto;gap:8px;">
        <div class="cat-treat-inc1-6" style="display:grid;grid-template-columns:1fr 1fr;grid-template-rows:repeat(3,1fr);gap:4px;">{''.join(inc1_6_html)}</div>
        <div class="cat-treat-inc210" style="display:grid;grid-template-columns:1fr;grid-template-rows:repeat(4,1fr);gap:4px;">{''.join(inc210_html)}</div>
        <div class="cat-treat-cages" style="display:grid;grid-template-columns:repeat(4,1fr);grid-template-rows:repeat(2,1fr);gap:4px;width:100%;height:100%;">{''.join(cage_html)}</div>
    </div>
    '''
    st.components.v1.html(
        f"""
        <style>
        .kennel-block {{
            background: #f9f9f9;
            border: 1.5px solid #333;
            border-radius: 6px;
            display: flex;
            flex-direction: column;
            align-items: flex-start;
            justify-content: flex-start;
            min-width: 0;
            min-height: 0;
            width: 100%;
            height: 100%;
            padding: 8px 8px 8px 8px;
            box-sizing: border-box;
            overflow: hidden;
            position: relative;
        }}
        .kennel-label-small {{
            position: absolute;
            top: 6px;
            left: 10px;
            font-size: 0.95em;
            color: #333;
            font-weight: 600;
            opacity: 0.95;
            z-index: 2;
            pointer-events: none;
        }}
        .kennel-animal-list {{
            margin-top: 2.2em;
            width: 100%;
            max-height: 100%;
            overflow-y: auto;
            container-type: inline-size;
        }}
        .kennel-animal {{
            color: #222;
            font-size: 1em; /* Base size */
            margin: 0;
            padding: 0;
            line-height: 1.1em;
            word-break: break-word;
            font-stretch: ultra-condensed;
            white-space: normal;
        }}
        .stage-abbr {{
            color: #c00;
            font-weight: bold;
            text-transform: uppercase;
            margin-left: 0.25em;
        }}
        .cat-treat-inc1-6 {{ 
            flex: 0 1 25%; 
            min-width: 220px;
            height: 100%;
        }}
        .cat-treat-inc210 {{ 
            flex: 0 1 15%; 
            min-width: 120px;
            height: 100%;
        }}
        .cat-treat-cages {{ 
            flex: 1 1 60%; 
            min-width: 320px;
            height: 100%;
        }}
        </style>
        <script>
        function scaleText() {{
            document.querySelectorAll('.kennel-animal-list').forEach(container => {{
                const animals = container.querySelectorAll('.kennel-animal');
                if (animals.length === 0) return;
                
                // Start with base size
                let fontSize = 1;
                const containerHeight = container.clientHeight;
                const containerWidth = container.clientWidth;
                
                // Scale down until all content fits
                while (true) {{
                    let totalHeight = 0;
                    animals.forEach(animal => {{
                        animal.style.fontSize = fontSize + 'em';
                        totalHeight += animal.offsetHeight;
                    }});
                    
                    if (totalHeight <= containerHeight && 
                        Math.max(...Array.from(animals).map(a => a.offsetWidth)) <= containerWidth) {{
                        break;
                    }}
                    
                    fontSize -= 0.1;
                    if (fontSize <= 0.5) break; // Don't go smaller than 0.5em
                }}
            }});
        }}
        
        // Run on load and resize
        window.addEventListener('load', scaleText);
        window.addEventListener('resize', scaleText);
        </script>
        {grid_html}
        """,
        height=2000,
        scrolling=False
    )

elif area == "ICU":
    # DENT1: Dental Area, Cage 1
    dent_df = animal_df[(animal_df["Location_1"] == "Dental Area") & (animal_df["SubLocation"].str.strip() == "Cage 1")].copy()
    # ICU2-ICU8: ICU, SubLocation 02-08
    icu_df = animal_df[(animal_df["Location_1"] == "ICU") & (animal_df["SubLocation"].str.zfill(2).isin(["02","03","04","05","06","07","08"]))].copy()
    icu_df["SubLocation"] = icu_df["SubLocation"].astype(str).str.zfill(2)

    # Block 1: DENT1 (big square)
    dent_html = f'''
        <div class="kennel-block" style="width:100%;height:100%;display:flex;align-items:stretch;justify-content:stretch;">
            <div class="kennel-label-small">DENT 1</div>
            <div class="kennel-animal-list">{''.join(f'<div class="kennel-animal">{format_display_line(row)}</div>' for _, row in dent_df.iterrows()) or '<div class="kennel-animal">-</div>'}</div>
        </div>
    '''
    dent_grid = f'''<div class="icu-dent-grid" style="display:grid;grid-template-columns:1fr;grid-template-rows:1fr 1fr;min-width:160px;min-height:220px;flex:0 0 20%;">{dent_html}</div>'''

    # Block 2: ICU2, ICU3, ICU4 (ICU4 spans both columns in row 2)
    icu2 = icu_df[icu_df["SubLocation"] == "02"]
    icu3 = icu_df[icu_df["SubLocation"] == "03"]
    icu4 = icu_df[icu_df["SubLocation"] == "04"]
    icu2_html = f'''<div class="kennel-block" style="grid-row:1;grid-column:1;"><div class="kennel-label-small">ICU 2</div><div class="kennel-animal-list">{''.join(f'<div class="kennel-animal">{format_display_line(row)}</div>' for _, row in icu2.iterrows()) or '<div class="kennel-animal">-</div>'}</div></div>'''
    icu3_html = f'''<div class="kennel-block" style="grid-row:1;grid-column:2;"><div class="kennel-label-small">ICU 3</div><div class="kennel-animal-list">{''.join(f'<div class="kennel-animal">{format_display_line(row)}</div>' for _, row in icu3.iterrows()) or '<div class="kennel-animal">-</div>'}</div></div>'''
    icu4_html = f'''<div class="kennel-block" style="grid-row:2;grid-column:1/span 2;"><div class="kennel-label-small">ICU 4</div><div class="kennel-animal-list">{''.join(f'<div class="kennel-animal">{format_display_line(row)}</div>' for _, row in icu4.iterrows()) or '<div class="kennel-animal">-</div>'}</div></div>'''
    icu2_4_grid = f'''<div class="icu-2-4-grid" style="display:grid;grid-template-columns:1fr 1fr;grid-template-rows:1fr 1fr;min-width:180px;min-height:220px;flex:0 0 25%;gap:8px;">{icu2_html}{icu3_html}{icu4_html}</div>'''

    # Block 3: ICU5, ICU6, ICU7, ICU8 (2x2 grid)
    icu5 = icu_df[icu_df["SubLocation"] == "05"]
    icu6 = icu_df[icu_df["SubLocation"] == "06"]
    icu7 = icu_df[icu_df["SubLocation"] == "07"]
    icu8 = icu_df[icu_df["SubLocation"] == "08"]
    icu5_html = f'''<div class="kennel-block" style="grid-row:1;grid-column:1;"><div class="kennel-label-small">ICU 5</div><div class="kennel-animal-list">{''.join(f'<div class="kennel-animal">{format_display_line(row)}</div>' for _, row in icu5.iterrows()) or '<div class="kennel-animal">-</div>'}</div></div>'''
    icu6_html = f'''<div class="kennel-block" style="grid-row:1;grid-column:2;"><div class="kennel-label-small">ICU 6</div><div class="kennel-animal-list">{''.join(f'<div class="kennel-animal">{format_display_line(row)}</div>' for _, row in icu6.iterrows()) or '<div class="kennel-animal">-</div>'}</div></div>'''
    icu7_html = f'''<div class="kennel-block" style="grid-row:2;grid-column:1;"><div class="kennel-label-small">ICU 7</div><div class="kennel-animal-list">{''.join(f'<div class="kennel-animal">{format_display_line(row)}</div>' for _, row in icu7.iterrows()) or '<div class="kennel-animal">-</div>'}</div></div>'''
    icu8_html = f'''<div class="kennel-block" style="grid-row:2;grid-column:2;"><div class="kennel-label-small">ICU 8</div><div class="kennel-animal-list">{''.join(f'<div class="kennel-animal">{format_display_line(row)}</div>' for _, row in icu8.iterrows()) or '<div class="kennel-animal">-</div>'}</div></div>'''
    icu5_8_grid = f'''<div class="icu-5-8-grid" style="display:grid;grid-template-columns:1fr 1fr;grid-template-rows:1fr 1fr;min-width:180px;min-height:220px;flex:0 0 25%;gap:8px;">{icu5_html}{icu6_html}{icu7_html}{icu8_html}</div>'''

    # Layout all blocks in a flex row
    grid_html = f'''
    <div class="icu-flex" style="display:flex;flex-direction:row;justify-content:center;align-items:stretch;width:98vw;max-width:1400px;aspect-ratio:4/3;margin:0 auto 32px auto;gap:16px;">
        {dent_grid}
        {icu2_4_grid}
        {icu5_8_grid}
    </div>
    '''
    st.components.v1.html(
        f"""
        <style>
        .kennel-block {{
            background: #f9f9f9;
            border: 1.5px solid #333;
            border-radius: 6px;
            display: flex;
            flex-direction: column;
            align-items: flex-start;
            justify-content: flex-start;
            min-width: 0;
            min-height: 0;
            width: 100%;
            height: 100%;
            padding: 8px 8px 8px 8px;
            box-sizing: border-box;
            overflow: hidden;
            position: relative;
        }}
        .kennel-label-small {{
            position: absolute;
            top: 6px;
            left: 10px;
            font-size: 0.95em;
            color: #333;
            font-weight: 600;
            opacity: 0.95;
            z-index: 2;
            pointer-events: none;
        }}
        .kennel-animal-list {{
            margin-top: 2.2em;
            width: 100%;
            max-height: 100%;
            overflow-y: auto;
            container-type: inline-size;
        }}
        .kennel-animal {{
            color: #222;
            font-size: 1em; /* Base size */
            margin: 0;
            padding: 0;
            line-height: 1.1em;
            word-break: break-word;
            font-stretch: ultra-condensed;
            white-space: normal;
        }}
        .stage-abbr {{
            color: #c00;
            font-weight: bold;
            text-transform: uppercase;
            margin-left: 0.25em;
        }}
        @container (max-width: 200px) {{
            .kennel-animal {{
                font-size: 0.8em;
            }}
        }}
        @container (max-width: 150px) {{
            .kennel-animal {{
                font-size: 0.7em;
            }}
        }}
        @container (max-width: 100px) {{
            .kennel-animal {{
                font-size: 0.6em;
            }}
        }}
        </style>
        <script>
        function scaleText() {{
            document.querySelectorAll('.kennel-animal-list').forEach(container => {{
                const animals = container.querySelectorAll('.kennel-animal');
                if (animals.length === 0) return;
                
                // Start with base size
                let fontSize = 1;
                const containerHeight = container.clientHeight;
                const containerWidth = container.clientWidth;
                
                // Scale down until all content fits
                while (true) {{
                    let totalHeight = 0;
                    animals.forEach(animal => {{
                        animal.style.fontSize = fontSize + 'em';
                        totalHeight += animal.offsetHeight;
                    }});
                    
                    if (totalHeight <= containerHeight && 
                        Math.max(...Array.from(animals).map(a => a.offsetWidth)) <= containerWidth) {{
                        break;
                    }}
                    
                    fontSize -= 0.1;
                    if (fontSize <= 0.5) break; // Don't go smaller than 0.5em
                }}
            }});
        }}
        
        // Run on load and resize
        window.addEventListener('load', scaleText);
        window.addEventListener('resize', scaleText);
        </script>
        {grid_html}
        """,
        height=1000,
        scrolling=False
    )

elif area == "Administration":
    admin_df = animal_df[animal_df["Location_1"] == "Main Offices"].copy()
    offices = admin_df["SubLocation"].dropna().unique().tolist()
    # Only show offices that have animals
    offices = [office for office in offices if not admin_df[admin_df["SubLocation"] == office].empty]
    n = len(offices)
    ncols = 2
    nrows = (n + 1) // 2
    cell_html = []
    for office in offices:
        cell_animals = admin_df[admin_df["SubLocation"] == office].copy()
        animal_html = ""
        if not cell_animals.empty:
            for _, row in cell_animals.iterrows():
                animal_html += f'<div class="kennel-animal">{format_display_line(row)}</div>'
        else:
            animal_html = '<div class="kennel-animal">-</div>'
        cell_html.append(
            f'''
            <div class="kennel-block">
                <div class="kennel-label-small">{office}</div>
                <div class="kennel-animal-list">{animal_html}</div>
            </div>
            '''
        )
    # Fill out grid to keep it rectangular if odd number
    if n % 2 == 1:
        cell_html.append('<div class="kennel-block" style="background:transparent;border:none;"></div>')
    grid_html = f'''
    <div class="kennel-grid-container admin-grid" style="display:grid;grid-template-columns:repeat(2,1fr);grid-template-rows:repeat({nrows},1fr);gap:12px;width:98vw;max-width:800px;aspect-ratio:4/3;margin:0 auto 32px auto;">
        {''.join(cell_html)}
    </div>
    '''
    st.components.v1.html(
        f"""
        <style>
        .kennel-grid-container.admin-grid {{
            width: 98vw;
            max-width: 800px;
            aspect-ratio: 4 / 3;
            margin: 0 auto 32px auto;
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            grid-template-rows: repeat({nrows}, 1fr);
            gap: 12px;
            border: 2px solid #333;
            background: #eee;
            box-sizing: border-box;
            align-items: stretch;
            justify-items: stretch;
        }}
        .kennel-block {{
            background: #f9f9f9;
            border: 1.5px solid #333;
            border-radius: 6px;
            display: flex;
            flex-direction: column;
            align-items: flex-start;
            justify-content: flex-start;
            min-width: 0;
            min-height: 0;
            width: 100%;
            height: 100%;
            padding: 8px 8px 8px 8px;
            box-sizing: border-box;
            overflow: hidden;
            position: relative;
        }}
        .kennel-label-small {{
            position: absolute;
            top: 6px;
            left: 10px;
            font-size: 0.95em;
            color: #333;
            font-weight: 600;
            opacity: 0.95;
            z-index: 2;
            pointer-events: none;
        }}
        .kennel-animal-list {{
            margin-top: 2.2em;
            width: 100%;
            max-height: 100%;
            overflow-y: auto;
            container-type: inline-size;
        }}
        .kennel-animal {{
            color: #222;
            font-size: 1em; /* Base size */
            margin: 0;
            padding: 0;
            line-height: 1.1em;
            word-break: break-word;
            font-stretch: ultra-condensed;
            white-space: normal;
        }}
        .stage-abbr {{
            color: #c00;
            font-weight: bold;
            text-transform: uppercase;
            margin-left: 0.25em;
        }}
        @container (max-width: 200px) {{
            .kennel-animal {{
                font-size: 0.8em;
            }}
        }}
        @container (max-width: 150px) {{
            .kennel-animal {{
                font-size: 0.7em;
            }}
        }}
        @container (max-width: 100px) {{
            .kennel-animal {{
                font-size: 0.6em;
            }}
        }}
        </style>
        <script>
        function scaleText() {{
            document.querySelectorAll('.kennel-animal-list').forEach(container => {{
                const animals = container.querySelectorAll('.kennel-animal');
                if (animals.length === 0) return;
                
                // Start with base size
                let fontSize = 1;
                const containerHeight = container.clientHeight;
                const containerWidth = container.clientWidth;
                
                // Scale down until all content fits
                while (true) {{
                    let totalHeight = 0;
                    animals.forEach(animal => {{
                        animal.style.fontSize = fontSize + 'em';
                        totalHeight += animal.offsetHeight;
                    }});
                    
                    if (totalHeight <= containerHeight && 
                        Math.max(...Array.from(animals).map(a => a.offsetWidth)) <= containerWidth) {{
                        break;
                    }}
                    
                    fontSize -= 0.1;
                    if (fontSize <= 0.5) break; // Don't go smaller than 0.5em
                }}
            }});
        }}
        
        // Run on load and resize
        window.addEventListener('load', scaleText);
        window.addEventListener('resize', scaleText);
        </script>
        {grid_html}
        """,
        height=800,
        scrolling=False
    )

elif area == "Multi-Species Holding":
    # Define locations and allowed sublocations
    loc_229 = "Multi-Animal Holding, Room 229"
    loc_227 = "Multi-Animal Holding, Room 227"
    sublocs_229 = [
        "Boaphile 1", "Boaphile 2", "Cat 1", "Cat 2", "Cat 3", "Cat 4", "Cat 5", "Cat 6",
        "Multi Animal Holding", "Rabbitat 1", "Rabbitat 2", "Room 1", "Room 2",
        "Turtle Tank 1", "Turtle Tank 2", "Turtle Tank 3", "Turtle Tank 4"
    ]
    sublocs_227 = [
        "Bird Cage", "Boaphile 1", "Boaphile 2", "Mammal 1", "Mammal 2"
    ]
    ms_df = animal_df[animal_df["Location_1"].isin([loc_229, loc_227])].copy()
    # Build list of (label, df) for each present sublocation
    cells = []
    for subloc in sublocs_229:
        df = ms_df[(ms_df["Location_1"] == loc_229) & (ms_df["SubLocation"].str.strip() == subloc)]
        if not df.empty:
            label = f"229 {subloc}"
            cells.append((label, df))
    for subloc in sublocs_227:
        df = ms_df[(ms_df["Location_1"] == loc_227) & (ms_df["SubLocation"].str.strip() == subloc)]
        if not df.empty:
            label = f"227 {subloc}"
            cells.append((label, df))
    n = len(cells)
    ncols = 2
    nrows = (n + 1) // 2
    cell_html = []
    for label, df in cells:
        animal_html = ""
        for _, row in df.iterrows():
            animal_html += f'<div class="kennel-animal">{format_display_line(row)}</div>'
        cell_html.append(
            f'''
            <div class="kennel-block">
                <div class="kennel-label-small">{label}</div>
                <div class="kennel-animal-list">{animal_html}</div>
            </div>
            '''
        )
    # Fill out grid to keep it rectangular if odd number
    if n % 2 == 1:
        cell_html.append('<div class="kennel-block" style="background:transparent;border:none;"></div>')
    grid_html = f'''
    <div class="kennel-grid-container ms-hold-grid" style="display:grid;grid-template-columns:repeat(2,1fr);grid-template-rows:repeat({nrows},1fr);gap:12px;width:98vw;max-width:1000px;aspect-ratio:4/3;margin:0 auto 32px auto;">
        {''.join(cell_html)}
    </div>
    '''
    st.components.v1.html(
        f"""
        <style>
        .kennel-grid-container.ms-hold-grid {{
            width: 98vw;
            max-width: 1000px;
            aspect-ratio: 4 / 3;
            margin: 0 auto 32px auto;
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            grid-template-rows: repeat({nrows}, 1fr);
            gap: 12px;
            border: 2px solid #333;
            background: #eee;
            box-sizing: border-box;
            align-items: stretch;
            justify-items: stretch;
        }}
        .kennel-block {{
            background: #f9f9f9;
            border: 1.5px solid #333;
            border-radius: 6px;
            display: flex;
            flex-direction: column;
            align-items: flex-start;
            justify-content: flex-start;
            min-width: 0;
            min-height: 0;
            width: 100%;
            height: 100%;
            padding: 8px 8px 8px 8px;
            box-sizing: border-box;
            overflow: hidden;
            position: relative;
        }}
        .kennel-label-small {{
            position: absolute;
            top: 6px;
            left: 10px;
            font-size: 0.95em;
            color: #333;
            font-weight: 600;
            opacity: 0.95;
            z-index: 2;
            pointer-events: none;
        }}
        .kennel-animal-list {{
            margin-top: 2.2em;
            width: 100%;
            max-height: 100%;
            overflow-y: auto;
            container-type: inline-size;
        }}
        .kennel-animal {{
            color: #222;
            font-size: 1em; /* Base size */
            margin: 0;
            padding: 0;
            line-height: 1.1em;
            word-break: break-word;
            font-stretch: ultra-condensed;
            white-space: normal;
        }}
        .stage-abbr {{
            color: #c00;
            font-weight: bold;
            text-transform: uppercase;
            margin-left: 0.25em;
        }}
        @container (max-width: 200px) {{
            .kennel-animal {{
                font-size: 0.8em;
            }}
        }}
        @container (max-width: 150px) {{
            .kennel-animal {{
                font-size: 0.7em;
            }}
        }}
        @container (max-width: 100px) {{
            .kennel-animal {{
                font-size: 0.6em;
            }}
        }}
        </style>
        <script>
        function scaleText() {{
            document.querySelectorAll('.kennel-animal-list').forEach(container => {{
                const animals = container.querySelectorAll('.kennel-animal');
                if (animals.length === 0) return;
                
                // Start with base size
                let fontSize = 1;
                const containerHeight = container.clientHeight;
                const containerWidth = container.clientWidth;
                
                // Scale down until all content fits
                while (true) {{
                    let totalHeight = 0;
                    animals.forEach(animal => {{
                        animal.style.fontSize = fontSize + 'em';
                        totalHeight += animal.offsetHeight;
                    }});
                    
                    if (totalHeight <= containerHeight && 
                        Math.max(...Array.from(animals).map(a => a.offsetWidth)) <= containerWidth) {{
                        break;
                    }}
                    
                    fontSize -= 0.1;
                    if (fontSize <= 0.5) break; // Don't go smaller than 0.5em
                }}
            }});
        }}
        
        // Run on load and resize
        window.addEventListener('load', scaleText);
        window.addEventListener('resize', scaleText);
        </script>
        {grid_html}
        """,
        height=1000,
        scrolling=False
    )

elif area == "Small Animals & Exotics":
    sa_df = animal_df[animal_df["Location_1"] == "Small Animals & Exotics"].copy()
    # --- Birds ---
    bird_cages = ["Bird Cage 1", "Bird Cage 2", "Bird Cage 3", "Bird Cage 4"]
    bird_extra = "Bird Cage EXTRA"
    bird_cells = []
    for i, cage in enumerate(bird_cages):
        cell_animals = sa_df[sa_df["SubLocation"] == cage]
        label = str(i+1)
        animal_html = ""
        if not cell_animals.empty:
            for _, row in cell_animals.iterrows():
                animal_html += f'<div class="kennel-animal">{format_display_line(row)}</div>'
        else:
            animal_html = '<div class="kennel-animal">-</div>'
        bird_cells.append(f'<div class="kennel-block"><div class="kennel-label-small">{label}</div><div class="kennel-animal-list">{animal_html}</div></div>')
    # Bird Extra (spans 2 columns)
    cell_animals = sa_df[sa_df["SubLocation"] == bird_extra]
    animal_html = ""
    if not cell_animals.empty:
        for _, row in cell_animals.iterrows():
            animal_html += f'<div class="kennel-animal">{format_display_line(row)}</div>'
    else:
        animal_html = '<div class="kennel-animal">-</div>'
    bird_cells.append(f'<div class="kennel-block" style="grid-column: 1 / span 2;"><div class="kennel-label-small">EXTRA</div><div class="kennel-animal-list">{animal_html}</div></div>')
    bird_grid = f'''<div class="sa-block"><div class="sa-heading">Birds</div><div class="sa-bird-grid" style="display:grid;grid-template-columns:1fr 1fr;grid-template-rows:1fr 1fr 1fr;gap:8px;">{bird_cells[0]}{bird_cells[1]}{bird_cells[2]}{bird_cells[3]}{bird_cells[4]}</div></div>'''
    # --- Small Animals ---
    sa_cages = [f"Small Animal {i}" for i in range(1,9)]
    sa_cells = []
    for i, cage in enumerate(sa_cages):
        cell_animals = sa_df[sa_df["SubLocation"] == cage]
        label = str(i+1)
        animal_html = ""
        if not cell_animals.empty:
            for _, row in cell_animals.iterrows():
                animal_html += f'<div class="kennel-animal">{format_display_line(row)}</div>'
        else:
            animal_html = '<div class="kennel-animal">-</div>'
        sa_cells.append(f'<div class="kennel-block"><div class="kennel-label-small">{label}</div><div class="kennel-animal-list">{animal_html}</div></div>')
    # 3x3 grid, last cell empty
    sa_cells.append('<div class="kennel-block" style="background:transparent;border:none;"></div>')
    sa_grid = f'''<div class="sa-block"><div class="sa-heading">Small Animals</div><div class="sa-sa-grid" style="display:grid;grid-template-columns:1fr 1fr 1fr;grid-template-rows:1fr 1fr 1fr;gap:8px;">{''.join(sa_cells)}</div></div>'''
    # --- Mammals 1-2 ---
    mammal1_cells = []
    for i in range(1,3):
        cage = f"Mammal {i}"
        cell_animals = sa_df[sa_df["SubLocation"] == cage]
        label = str(i)
        animal_html = ""
        if not cell_animals.empty:
            for _, row in cell_animals.iterrows():
                animal_html += f'<div class="kennel-animal">{format_display_line(row)}</div>'
        else:
            animal_html = '<div class="kennel-animal">-</div>'
        mammal1_cells.append(f'<div class="kennel-block"><div class="kennel-label-small">{label}</div><div class="kennel-animal-list">{animal_html}</div></div>')
    mammal1_grid = f'''<div class="sa-block"><div class="sa-heading">Mammals</div><div class="sa-mammal1-grid" style="display:grid;grid-template-columns:1fr;grid-template-rows:1fr 1fr;gap:8px;">{''.join(mammal1_cells)}</div></div>'''
    # --- Mammals 3-4 ---
    mammal2_cells = []
    for i in range(3,5):
        cage = f"Mammal {i}"
        cell_animals = sa_df[sa_df["SubLocation"] == cage]
        label = str(i)
        animal_html = ""
        if not cell_animals.empty:
            for _, row in cell_animals.iterrows():
                animal_html += f'<div class="kennel-animal">{format_display_line(row)}</div>'
        else:
            animal_html = '<div class="kennel-animal">-</div>'
        mammal2_cells.append(f'<div class="kennel-block"><div class="kennel-label-small">{label}</div><div class="kennel-animal-list">{animal_html}</div></div>')
    mammal2_grid = f'''<div class="sa-block"><div class="sa-heading">Mammals</div><div class="sa-mammal2-grid" style="display:grid;grid-template-columns:1fr;grid-template-rows:1fr 1fr;gap:8px;">{''.join(mammal2_cells)}</div></div>'''
    # --- Reptiles ---
    reptile_cages = [f"Reptile {i}" for i in range(1,6)]
    reptile_cells = []
    for i, cage in enumerate(reptile_cages):
        cell_animals = sa_df[sa_df["SubLocation"] == cage]
        label = str(i+1)
        animal_html = ""
        if not cell_animals.empty:
            for _, row in cell_animals.iterrows():
                animal_html += f'<div class="kennel-animal">{format_display_line(row)}</div>'
        else:
            animal_html = '<div class="kennel-animal">-</div>'
        if i < 4:
            reptile_cells.append(f'<div class="kennel-block"><div class="kennel-label-small">{label}</div><div class="kennel-animal-list">{animal_html}</div></div>')
        else:
            reptile_cells.append(f'<div class="kennel-block" style="grid-column: 1 / span 2;"><div class="kennel-label-small">{label}</div><div class="kennel-animal-list">{animal_html}</div></div>')
    reptile_grid = f'''<div class="sa-block"><div class="sa-heading">Reptiles</div><div class="sa-reptile-grid" style="display:grid;grid-template-columns:1fr 1fr;grid-template-rows:1fr 1fr 1fr;gap:8px;">{reptile_cells[0]}{reptile_cells[1]}{reptile_cells[2]}{reptile_cells[3]}{reptile_cells[4]}</div></div>'''
    # --- Countertop Cages ---
    counter_cells = []
    for i in range(1,3):
        cage = f"Countertop Cage {i}"
        cell_animals = sa_df[sa_df["SubLocation"] == cage]
        label = str(i)
        animal_html = ""
        if not cell_animals.empty:
            for _, row in cell_animals.iterrows():
                animal_html += f'<div class="kennel-animal">{format_display_line(row)}</div>'
        else:
            animal_html = '<div class="kennel-animal">-</div>'
        counter_cells.append(f'<div class="kennel-block"><div class="kennel-label-small">{label}</div><div class="kennel-animal-list">{animal_html}</div></div>')
    # Countertop cages grid: 2 columns, 1 row, centered and wide
    counter_grid = f'''<div class="sa-block sa-counter-wide"><div class="sa-heading">Countertop Cages</div><div class="sa-counter-grid" style="display:grid;grid-template-columns:1fr 1fr;grid-template-rows:1fr;gap:8px;">{''.join(counter_cells)}</div></div>'''
    # --- Layout: top row flex, bottom row centered ---
    grid_html = f'''
    <div class="sa-main-bg">
        <div class="sa-horizontal-row" style="display:flex;flex-direction:row;align-items:flex-start;gap:24px;width:100%;justify-content:center;">
            {bird_grid}
            {sa_grid}
            {mammal1_grid}
            {reptile_grid}
            {mammal2_grid}
        </div>
        <div class="sa-counter-center" style="display:flex;flex-direction:row;justify-content:center;width:60%;min-width:340px;max-width:700px;">
            {counter_grid}
        </div>
    </div>
    '''
    st.components.v1.html(
        f"""
        <style>
        .sa-main-bg {{
            background: #eee;
            border: 2px solid #333;
            border-radius: 10px;
            box-sizing: border-box;
            width: 98vw;
            max-width: 1400px;
            margin: 0 auto 32px auto;
            padding: 24px 12px;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 32px;
        }}
        .sa-block {{
            background: #f9f9f9;
            border: 1.5px solid #333;
            border-radius: 6px;
            box-sizing: border-box;
            min-width: 120px;
            flex: 1 1 0;
            margin: 0;
            padding: 0;
            display: flex;
            flex-direction: column;
        }}
        .sa-heading {{
            font-size: 1.1em;
            font-weight: 600;
            color: #222;
            margin-bottom: 6px;
            margin-left: 2px;
            padding-top: 4px;
        }}
        .kennel-block {{
            background: #f9f9f9;
            border: 1.5px solid #333;
            border-radius: 6px;
            display: flex;
            flex-direction: column;
            align-items: flex-start;
            justify-content: flex-start;
            min-width: 0;
            min-height: 80px;  /* Ensures empty cages are not tiny */
            width: 100%;
            height: 100%;
            padding: 8px 8px 8px 8px;
            box-sizing: border-box;
            overflow: hidden;
            position: relative;
        }}
        .kennel-label-small {{
            position: absolute;
            top: 6px;
            left: 10px;
            font-size: 0.95em;
            color: #333;
            font-weight: 600;
            opacity: 0.95;
            z-index: 2;
            pointer-events: none;
        }}
        .kennel-animal-list {{
            margin-top: 2.2em;
            width: 100%;
            max-height: 100%;
            overflow-y: auto;
            container-type: inline-size;
        }}
        .kennel-animal {{
            color: #222;
            font-size: 1em; /* Base size */
            margin: 0;
            padding: 0;
            line-height: 1.1em;
            word-break: break-word;
            font-stretch: ultra-condensed;
            white-space: normal;
        }}
        .stage-abbr {{
            color: #c00;
            font-weight: bold;
            text-transform: uppercase;
            margin-left: 0.25em;
        }}
        .sa-counter-wide {{
            width: 100%;
            max-width: 700px;
        }}
        </style>
        <div class="sa-main-bg">
          <div class="sa-horizontal-row" style="display:flex;flex-direction:row;align-items:flex-start;gap:24px;width:100%;justify-content:center;">
            {bird_grid}
            {sa_grid}
            {mammal1_grid}
            {reptile_grid}
            {mammal2_grid}
          </div>
          <div class="sa-counter-center" style="display:flex;flex-direction:row;justify-content:center;width:60%;min-width:340px;max-width:700px;">
            {counter_grid}
          </div>
        </div>
        """,
        height=1000,
        scrolling=False
    )

elif area == "Cat Recovery":
    rec_df = animal_df[animal_df["Location_1"] == "Cat Recovery"].copy()
    rec_df["SubLocation"] = rec_df["SubLocation"].astype(str).str.zfill(2)
    # Build grid: 8 columns, 3 rows
    grid_cells = []
    # Top row: 1-8
    for i in range(1, 9):
        num = str(i).zfill(2)
        cell_animals = rec_df[rec_df["SubLocation"] == num]
        animal_html = ""
        if not cell_animals.empty:
            for _, row in cell_animals.iterrows():
                animal_html += f'<div class="kennel-animal">{format_display_line(row)}</div>'
        else:
            animal_html = '<div class="kennel-animal">-</div>'
        grid_cells.append(f'<div class="kennel-block" style="grid-row:1;grid-column:{i};"><div class="kennel-label-small">{i}</div><div class="kennel-animal-list">{animal_html}</div></div>')
    # Middle row: 9-14 (cols 2-7)
    for i in range(9, 15):
        col = i - 7  # 9->2, 10->3, ..., 14->7
        num = str(i).zfill(2)
        cell_animals = rec_df[rec_df["SubLocation"] == num]
        animal_html = ""
        if not cell_animals.empty:
            for _, row in cell_animals.iterrows():
                animal_html += f'<div class="kennel-animal">{format_display_line(row)}</div>'
        else:
            animal_html = '<div class="kennel-animal">-</div>'
        grid_cells.append(f'<div class="kennel-block" style="grid-row:2;grid-column:{col};"><div class="kennel-label-small">{i}</div><div class="kennel-animal-list">{animal_html}</div></div>')
    # Bottom row: 15-18 (each spans 2 columns)
    for i in range(15, 19):
        col = 1 + (i - 15) * 2
        num = str(i).zfill(2)
        cell_animals = rec_df[rec_df["SubLocation"] == num]
        animal_html = ""
        if not cell_animals.empty:
            for _, row in cell_animals.iterrows():
                animal_html += f'<div class="kennel-animal">{format_display_line(row)}</div>'
        else:
            animal_html = '<div class="kennel-animal">-</div>'
        grid_cells.append(f'<div class="kennel-block" style="grid-row:3;grid-column:{col}/span 2;"><div class="kennel-label-small">{i}</div><div class="kennel-animal-list">{animal_html}</div></div>')
    grid_html = f'''
    <div class="cat-recovery-bg">
        <div class="cat-recovery-grid" style="display:grid;grid-template-columns:repeat(8,1fr);grid-template-rows:repeat(3,1fr);gap:12px;width:98vw;max-width:1400px;aspect-ratio:16/5;margin:0 auto 32px auto;">
            {''.join(grid_cells)}
        </div>
    </div>
    '''
    st.components.v1.html(
        f"""
        <style>
        .cat-recovery-bg {{
            background: #eee;
            border: 2px solid #333;
            border-radius: 10px;
            box-sizing: border-box;
            width: 98vw;
            max-width: 1400px;
            margin: 0 auto 32px auto;
            padding: 24px 12px;
        }}
        .cat-recovery-grid {{
            width: 100%;
            aspect-ratio: 16/5;
            display: grid;
            grid-template-columns: repeat(8, 1fr);
            grid-template-rows: repeat(3, 1fr);
            gap: 12px;
            align-items: stretch;
            justify-items: stretch;
        }}
        .kennel-block {{
            background: #f9f9f9;
            border: 1.5px solid #333;
            border-radius: 6px;
            display: flex;
            flex-direction: column;
            align-items: flex-start;
            justify-content: flex-start;
            min-width: 0;
            min-height: 80px;  /* Ensures empty cages are not tiny */
            width: 100%;
            height: 100%;
            padding: 8px 8px 8px 8px;
            box-sizing: border-box;
            overflow: hidden;
            position: relative;
        }}
        .kennel-label-small {{
            position: absolute;
            top: 6px;
            left: 10px;
            font-size: 0.95em;
            color: #333;
            font-weight: 600;
            opacity: 0.95;
            z-index: 2;
            pointer-events: none;
        }}
        .kennel-animal-list {{
            margin-top: 2.2em;
            width: 100%;
            max-height: 100%;
            overflow-y: auto;
            container-type: inline-size;
        }}
        .kennel-animal {{
            color: #222;
            font-size: 1em; /* Base size */
            margin: 0;
            padding: 0;
            line-height: 1.1em;
            word-break: break-word;
            font-stretch: ultra-condensed;
            white-space: normal;
        }}
        .stage-abbr {{
            color: #c00;
            font-weight: bold;
            text-transform: uppercase;
            margin-left: 0.25em;
        }}
        @container (max-width: 200px) {{
            .kennel-animal {{
                font-size: 0.8em;
            }}
        }}
        @container (max-width: 150px) {{
            .kennel-animal {{
                font-size: 0.7em;
            }}
        }}
        @container (max-width: 100px) {{
            .kennel-animal {{
                font-size: 0.6em;
            }}
        }}
        </style>
        <script>
        function scaleText() {{
            document.querySelectorAll('.kennel-animal-list').forEach(container => {{
                const animals = container.querySelectorAll('.kennel-animal');
                if (animals.length === 0) return;
                
                // Start with base size
                let fontSize = 1;
                const containerHeight = container.clientHeight;
                const containerWidth = container.clientWidth;
                
                // Scale down until all content fits
                while (true) {{
                    let totalHeight = 0;
                    animals.forEach(animal => {{
                        animal.style.fontSize = fontSize + 'em';
                        totalHeight += animal.offsetHeight;
                    }});
                    
                    if (totalHeight <= containerHeight && 
                        Math.max(...Array.from(animals).map(a => a.offsetWidth)) <= containerWidth) {{
                        break;
                    }}
                    
                    fontSize -= 0.1;
                    if (fontSize <= 0.5) break; // Don't go smaller than 0.5em
                }}
            }});
        }}
        
        // Run on load and resize
        window.addEventListener('load', scaleText);
        window.addEventListener('resize', scaleText);
        </script>
        {grid_html}
        """,
        height=600,
        scrolling=False
    )

elif area == "Dog Recovery":
    # Large Dog Recovery
    large_df = animal_df[animal_df["Location_1"] == "Large Dog Recovery"].copy()
    large_df["SubLocation"] = large_df["SubLocation"].astype(str).str.zfill(2)
    large_cells = []
    for i in range(1, 5):
        num = str(i).zfill(2)
        cell_animals = large_df[large_df["SubLocation"] == num]
        label = f"Large Dog {i}"
        animal_html = ""
        if not cell_animals.empty:
            for _, row in cell_animals.iterrows():
                animal_html += f'<div class="kennel-animal">{format_display_line(row)}</div>'
        else:
            animal_html = '<div class="kennel-animal">-</div>'
        large_cells.append(f'<div class="kennel-block"><div class="kennel-label-small">{label}</div><div class="kennel-animal-list">{animal_html}</div></div>')
    large_grid = f'''<div class="dogrec-block"><div class="dogrec-heading">Large Dog Recovery</div><div class="dogrec-large-grid" style="display:grid;grid-template-columns:repeat(4,1fr);grid-template-rows:1fr;gap:12px;">{''.join(large_cells)}</div></div>'''
    # Small Dog Recovery
    small_df = animal_df[animal_df["Location_1"] == "Small Dog Recovery"].copy()
    small_df["SubLocation"] = small_df["SubLocation"].astype(str).str.zfill(2)
    small_cells = []
    for i in range(1, 7):
        num = str(i).zfill(2)
        cell_animals = small_df[small_df["SubLocation"] == num]
        label = f"Small Dog {i}"
        animal_html = ""
        if not cell_animals.empty:
            for _, row in cell_animals.iterrows():
                animal_html += f'<div class="kennel-animal">{format_display_line(row)}</div>'
        else:
            animal_html = '<div class="kennel-animal">-</div>'
        small_cells.append(f'<div class="kennel-block"><div class="kennel-label-small">{label}</div><div class="kennel-animal-list">{animal_html}</div></div>')
    small_grid = f'''<div class="dogrec-block"><div class="dogrec-heading">Small Dog Recovery</div><div class="dogrec-small-grid" style="display:grid;grid-template-columns:repeat(3,1fr);grid-template-rows:repeat(2,1fr);gap:12px;">{''.join(small_cells)}</div></div>'''
    # Stack both grids vertically in a container
    grid_html = f'''
    <div class="dogrec-bg">
        {large_grid}
        {small_grid}
    </div>
    '''
    st.components.v1.html(
        f"""
        <style>
        .dogrec-bg {{
            background: #eee;
            border: 2px solid #333;
            border-radius: 10px;
            box-sizing: border-box;
            width: 98vw;
            max-width: 900px;
            margin: 0 auto 32px auto;
            padding: 24px 12px;
            display: flex;
            flex-direction: column;
            align-items: stretch;
            gap: 32px;
        }}
        .dogrec-block {{
            width: 100%;
        }}
        .dogrec-heading {{
            font-size: 1.1em;
            font-weight: 600;
            color: #222;
            margin-bottom: 6px;
            margin-left: 2px;
            padding-top: 4px;
        }}
        .kennel-block {{
            background: #f9f9f9;
            border: 1.5px solid #333;
            border-radius: 6px;
            display: flex;
            flex-direction: column;
            align-items: flex-start;
            justify-content: flex-start;
            min-width: 0;
            min-height: 80px;  /* Ensures empty cages are not tiny */
            width: 100%;
            height: 100%;
            padding: 8px 8px 8px 8px;
            box-sizing: border-box;
            overflow: hidden;
            position: relative;
        }}
        .kennel-label-small {{
            position: absolute;
            top: 6px;
            left: 10px;
            font-size: 0.95em;
            color: #333;
            font-weight: 600;
            opacity: 0.95;
            z-index: 2;
            pointer-events: none;
        }}
        .kennel-animal-list {{
            margin-top: 2.2em;
            width: 100%;
            max-height: 100%;
            overflow-y: auto;
            container-type: inline-size;
        }}
        .kennel-animal {{
            color: #222;
            font-size: 1em; /* Base size */
            margin: 0;
            padding: 0;
            line-height: 1.1em;
            word-break: break-word;
            font-stretch: ultra-condensed;
            white-space: normal;
        }}
        .stage-abbr {{
            color: #c00;
            font-weight: bold;
            text-transform: uppercase;
            margin-left: 0.25em;
        }}
        @container (max-width: 200px) {{
            .kennel-animal {{
                font-size: 0.8em;
            }}
        }}
        @container (max-width: 150px) {{
            .kennel-animal {{
                font-size: 0.7em;
            }}
        }}
        @container (max-width: 100px) {{
            .kennel-animal {{
                font-size: 0.6em;
            }}
        }}
        </style>
        <script>
        function scaleText() {{
            document.querySelectorAll('.kennel-animal-list').forEach(container => {{
                const animals = container.querySelectorAll('.kennel-animal');
                if (animals.length === 0) return;
                
                // Start with base size
                let fontSize = 1;
                const containerHeight = container.clientHeight;
                const containerWidth = container.clientWidth;
                
                // Scale down until all content fits
                while (true) {{
                    let totalHeight = 0;
                    animals.forEach(animal => {{
                        animal.style.fontSize = fontSize + 'em';
                        totalHeight += animal.offsetHeight;
                    }});
                    
                    if (totalHeight <= containerHeight && 
                        Math.max(...Array.from(animals).map(a => a.offsetWidth)) <= containerWidth) {{
                        break;
                    }}
                    
                    fontSize -= 0.1;
                    if (fontSize <= 0.5) break; // Don't go smaller than 0.5em
                }}
            }});
        }}
        
        // Run on load and resize
        window.addEventListener('load', scaleText);
        window.addEventListener('resize', scaleText);
        </script>
        {grid_html}
        """,
        height=700,
        scrolling=False
    )

else:  # Adoptions Lobby
    # Define grid cells and their filters
    cells = [
        {
            "label": "Feature Room 1",
            "filter": (animal_df["Location_1"] == "Feature Room 1")
        },
        {
            "label": "Lobby Rabbitat 1",
            "filter": (animal_df["Location_1"] == "Adoptions Lobby") & (animal_df["SubLocation"] == "Rabbitat 1")
        },
        {
            "label": "Feature Room 2",
            "filter": (animal_df["Location_1"] == "Feature Room 2")
        },
        {
            "label": "Lobby Rabbitat 2",
            "filter": (animal_df["Location_1"] == "Adoptions Lobby") & (animal_df["SubLocation"] == "Rabbitat 2")
        },
    ]

    # Build grid as HTML for consistent styling
    cell_html = []
    for cell in cells:
        cell_animals = animal_df[cell["filter"]].copy()
        animal_html = ""
        if not cell_animals.empty:
            for _, row in cell_animals.iterrows():
                animal_html += f'<div class="kennel-animal">{format_display_line(row)}</div>'
        else:
            animal_html = '<div class="kennel-animal">-</div>'
        cell_html.append(
            f'''
            <div class="kennel-block">
                <div class="kennel-label-small">{cell['label']}</div>
                <div class="kennel-animal-list">{animal_html}</div>
            </div>
            '''
        )

    grid_html = f'''
    <div class="kennel-grid-container lobby-grid" style="grid-template-columns: 1fr 1fr; grid-template-rows: 1fr 1fr; gap: 12px;">
        {cell_html[0]}
        {cell_html[1]}
        {cell_html[2]}
        {cell_html[3]}
    </div>
    '''

    st.components.v1.html(
        f"""
        <style>
        .kennel-grid-container.lobby-grid {{
            width: 98vw;
            max-width: 1400px;
            aspect-ratio: 4 / 3;
            margin: 0 auto 32px auto;
            display: grid;
            grid-template-columns: 1fr 1fr;
            grid-template-rows: 1fr 1fr;
            gap: 12px;
            border: 2px solid #333;
            background: #eee;
            box-sizing: border-box;
            align-items: stretch;
            justify-items: stretch;
        }}
        .kennel-block {{
            background: #f9f9f9;
            border: 1.5px solid #333;
            border-radius: 6px;
            display: flex;
            flex-direction: column;
            align-items: flex-start;
            justify-content: flex-start;
            min-width: 0;
            min-height: 0;
            width: 100%;
            height: 100%;
            padding: 8px 8px 8px 8px;
            box-sizing: border-box;
            overflow: hidden;
            position: relative;
        }}
        .kennel-label-small {{
            position: absolute;
            top: 6px;
            left: 10px;
            font-size: 0.95em;
            color: #333;
            font-weight: 600;
            opacity: 0.95;
            z-index: 2;
            pointer-events: none;
        }}
        .kennel-animal-list {{
            margin-top: 2.2em;
            width: 100%;
            max-height: 100%;
            overflow-y: auto;
            container-type: inline-size;
        }}
        .kennel-animal {{
            color: #222;
            font-size: 1em; /* Base size */
            margin: 0;
            padding: 0;
            line-height: 1.1em;
            word-break: break-word;
            font-stretch: ultra-condensed;
            white-space: normal;
        }}
        .stage-abbr {{
            color: #c00;
            font-weight: bold;
            text-transform: uppercase;
            margin-left: 0.25em;
        }}
        @container (max-width: 200px) {{
            .kennel-animal {{
                font-size: 0.8em;
            }}
        }}
        @container (max-width: 150px) {{
            .kennel-animal {{
                font-size: 0.7em;
            }}
        }}
        @container (max-width: 100px) {{
            .kennel-animal {{
                font-size: 0.6em;
            }}
        }}
        </style>
        <script>
        function scaleText() {{
            document.querySelectorAll('.kennel-animal-list').forEach(container => {{
                const animals = container.querySelectorAll('.kennel-animal');
                if (animals.length === 0) return;
                
                // Start with base size
                let fontSize = 1;
                const containerHeight = container.clientHeight;
                const containerWidth = container.clientWidth;
                
                // Scale down until all content fits
                while (true) {{
                    let totalHeight = 0;
                    animals.forEach(animal => {{
                        animal.style.fontSize = fontSize + 'em';
                        totalHeight += animal.offsetHeight;
                    }});
                    
                    if (totalHeight <= containerHeight && 
                        Math.max(...Array.from(animals).map(a => a.offsetWidth)) <= containerWidth) {{
                        break;
                    }}
                    
                    fontSize -= 0.1;
                    if (fontSize <= 0.5) break; // Don't go smaller than 0.5em
                }}
            }});
        }}
        
        // Run on load and resize
        window.addEventListener('load', scaleText);
        window.addEventListener('resize', scaleText);
        </script>
        {grid_html}
        """,
        height=2000,
        scrolling=False
    ) 

def file_hash(filepath):
    with open(filepath, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()

animal_path = Path('AnimalInventory.csv')
csv_hash = file_hash(animal_path)

# --- Filter for animals needing clear dates ---
clear_date_needed = animal_df[
    animal_df['Stage'].str.contains('Bite/Scratch|Stray|Legal', case=False, na=False)
].copy()

st.write(clear_date_needed)  # DEBUG: See if you have any animals needing clear dates

show_clear_date_form = not st.session_state.clear_dates_completed and not clear_date_needed.empty

if show_clear_date_form:
    st.subheader("Animals Needing Clear Dates")
    with st.form("clear_dates_form"):
        stages = {
            'Bite/Scratch': clear_date_needed[clear_date_needed['Stage'].str.contains('Bite/Scratch', case=False)],
            'Stray': clear_date_needed[clear_date_needed['Stage'].str.contains('Stray', case=False)],
            'Legal': clear_date_needed[clear_date_needed['Stage'].str.contains('Legal', case=False)]
        }
        all_filled = True
        for stage_name, stage_df in stages.items():
            if not stage_df.empty:
                st.markdown(f'<div class="stage-header"><h3>{stage_name}</h3></div>', unsafe_allow_html=True)
                cols = st.columns([1, 2, 2, 2, 2, 1])
                cols[0].write("**Animal #**")
                cols[1].write("**Name**")
                cols[2].write("**Location**")
                cols[3].write("**SubLocation**")
                cols[4].write("**Stage**")
                cols[5].write("**Clear Date**")
                for idx, row in stage_df.iterrows():
                    animal_id = str(row['AnimalNumber'])
                    cols = st.columns([1, 2, 2, 2, 2, 1])
                    cols[0].write(animal_id)
                    cols[1].write(row['AnimalName'])
                    cols[2].write(row['Location_1'])
                    cols[3].write(row['SubLocation'])
                    cols[4].write(row['Stage'])
                    clear_date = clear_dates_dict.get(str(row['AnimalNumber']), "")
                    clear_date = format_clear_date(clear_date)
                    new_date = cols[5].text_input(
                        "Clear Date",
                        value=clear_date,
                        key=f"clear_date_{animal_id}",
                        label_visibility="collapsed"
                    )
                    if new_date != clear_date:
                        st.session_state.clear_dates[animal_id] = new_date
                    if not new_date.strip():
                        all_filled = False
        submitted = st.form_submit_button("Update Clear Dates")
        if submitted and all_filled:
            st.session_state.clear_dates_completed = True
            st.success("Clear dates saved! You may proceed.")
            st.experimental_rerun()
        elif submitted and not all_filled:
            st.warning("Please fill in all clear dates before proceeding.")
            st.stop()
    st.stop()  # Prevent dashboard from rendering until form is done

# --- CSS for clear dates (put this once, anywhere after st.set_page_config) ---
st.markdown("""
<style>
.clear-date {
    color: #008000;
    font-weight: bold;
    margin-left: 0.25em;
}
.stage-header {
    background-color: #f0f2f6;
    padding: 10px;
    border-radius: 5px;
    margin: 10px 0;
}
</style>
""", unsafe_allow_html=True)