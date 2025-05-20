import pandas as pd
import openpyxl
import os

def convert_animal_inventory(xlsx_path, csv_path):
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    ws = wb.worksheets[1]  # 2nd tab
    data = list(ws.values)
    print(f"Total rows in Excel: {len(data)}")

    # Find the header row in the CSV (from your sample)
    csv_header = [
        'Location_1','AVG_LOS','Distinct_Animals','AnimalNumber','AnimalName','AnimalType','PrimaryBreed','Age','Color','Declawed','PreAltered','IntakeType','Sex','Stage','Location','ARN','ChipNumber','Species','SecondaryBreed','DateOfBirth','ColorPattern','EmancipationDate','SpayedNeutered','IntakeDateTime','LOSInDays','StageChangeReason','SubLocation','AnimalWeight','Danger','DangerType','NumberOfPictures','Videos','HoldReason','HorForName','HoldStartDate','HoldPlacedBy','Total_Animals'
    ]
    output_rows = [csv_header]

    i = 0
    current_loc1 = current_los = current_count = None
    while i < len(data):
        row = data[i]
        # Print first few rows for debugging
        if i < 10:
            print(f"Row {i}: {row}")
            
        # Detect group header: first 3 columns are not empty, rest are empty or None
        if row[0] and row[1] and row[2] and all((x is None or x == '') for x in row[3:]):
            print(f"Found group header at row {i}: {row[0]}, {row[1]}, {row[2]}")
            current_loc1, current_los, current_count = row[0], row[1], row[2]
            i += 1
            continue
            
        # Only process animal rows if group header is set
        if current_loc1 is not None and i+2 < len(data):
            animal_rows = data[i:i+3]
            print(f"Processing animal rows starting at {i}:")
            for r in animal_rows:
                print(f"  {r}")
            flat = []
            for r in animal_rows:
                flat.extend([x if x is not None else '' for x in r])
            out_row = [current_loc1, current_los, current_count] + flat
            out_row = out_row[:len(csv_header)] + ['']*(len(csv_header)-len(out_row))
            output_rows.append(out_row)
            i += 3
        else:
            i += 1
            
    print(f"Total output rows (including header): {len(output_rows)}")
    # Write to CSV
    pd.DataFrame(output_rows[1:], columns=output_rows[0]).to_csv(csv_path, index=False)
    print(f"Converted {xlsx_path} to {csv_path}")

def convert_stage_review(xlsx_path, csv_path):
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    ws = wb.worksheets[1]  # 2nd tab
    data = list(ws.values)
    print(f"Total rows in Stage Review Excel: {len(data)}")

    # Find the header row in the CSV (from your sample)
    csv_header = [
        'Location','textbox39','textbox89','AnimalName','Species','PrimaryBreed','textbox90','PrimaryColour','Stage','ReviewDate','StageChangeReason','ARN','textbox61','textbox78','SecondaryBreed','Gender','SecondaryColour','textbox79','SubLocation','HoldReason','HorForName','HoldStartDate','HoldPlacedBy','textbox47'
    ]
    output_rows = [csv_header]

    i = 0
    while i < len(data):
        row = data[i]
        # Print first few rows for debugging
        if i < 10:
            print(f"Stage Review Row {i}: {row}")
            
        # Detect group header: 2 header rows, then 3 rows per animal (skip 3rd row)
        if row[0] and (i+2 < len(data)) and (data[i+1][0] is not None):
            print(f"Found stage review header at row {i}")
            i += 2
            continue
        if i+2 < len(data):
            animal_rows = data[i:i+2]
            print(f"Processing stage review animal rows starting at {i}:")
            for r in animal_rows:
                print(f"  {r}")
            flat = []
            for r in animal_rows:
                flat.extend([x if x is not None else '' for x in r])
            out_row = flat[:len(csv_header)] + ['']*(len(csv_header)-len(flat))
            output_rows.append(out_row)
            i += 3
        else:
            i += 1
            
    print(f"Total stage review output rows (including header): {len(output_rows)}")
    # Write to CSV
    pd.DataFrame(output_rows[1:], columns=output_rows[0]).to_csv(csv_path, index=False)
    print(f"Converted {xlsx_path} to {csv_path}")

if __name__ == "__main__":
    base = os.path.dirname(os.path.abspath(__file__))
    convert_animal_inventory(os.path.join(base, 'AnimalInventory.xlsx'), os.path.join(base, 'AnimalInventory.csv'))
    convert_stage_review(os.path.join(base, 'StageReview.xlsx'), os.path.join(base, 'StageReview.csv')) 