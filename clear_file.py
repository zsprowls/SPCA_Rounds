import csv
import pandas as pd
import datetime

# Define the stages we want to filter for
HOLD_STAGES = [
    'Hold - Bite/Scratch',
    'Hold - Legal Notice',
    'Hold - Stray'
]

def extract_date(date_str):
    if pd.isna(date_str) or not date_str:
        return ''
    try:
        # Try to parse the date string with AM/PM
        for fmt in ("%m/%d/%Y %I:%M %p", "%m/%d/%Y %I:%M%p", "%m/%d/%y %I:%M %p", "%m/%d/%y %I:%M%p"):
            try:
                dt = datetime.datetime.strptime(str(date_str), fmt)
                return dt.strftime("%m/%d/%y")  # Return only the date portion
            except Exception:
                continue
        # If the above formats fail, try date-only formats
        for fmt in ("%m/%d/%y", "%m/%d/%Y", "%-m/%-d/%y", "%-m/%-d/%Y"):
            try:
                dt = datetime.datetime.strptime(str(date_str), fmt)
                return dt.strftime("%m/%d/%y")
            except Exception:
                continue
        return str(date_str)  # Return original if parsing fails
    except Exception:
        return str(date_str)  # Return original if any error occurs

def process_inventory():
    try:
        # Read the AnimalInventory.csv file, skipping the first 4 rows
        # Row 5 becomes the data, with Row 4 as headers
        df = pd.read_csv('AnimalInventory.csv', skiprows=3)
        
        # Read the StageReview.csv file, also skipping first 3 rows
        # Row 4 becomes headers, Row 5 starts data
        review_df = pd.read_csv('StageReview.csv', skiprows=3)
        
        # Print column names to debug
        print("AnimalInventory columns:", df.columns.tolist())
        print("StageReview columns:", review_df.columns.tolist())
        
        # Filter for the required stages and select only needed columns
        filtered_df = df[df['Stage'].isin(HOLD_STAGES)][
            ['AnimalNumber', 'AnimalName', 'AnimalType', 'Stage']
        ]
        
        # Sort by Stage to group similar holds together
        filtered_df = filtered_df.sort_values('Stage')
        
        # Create ClearDate column by matching AnimalNumbers with StageReview
        filtered_df = filtered_df.merge(
            review_df[['textbox89', 'ReviewDate']], 
            left_on='AnimalNumber',
            right_on='textbox89',
            how='left'
        ).rename(columns={'ReviewDate': 'ClearDate'})
        
        # Drop the textbox89 column as we don't need it in the output
        filtered_df = filtered_df.drop('textbox89', axis=1)
        
        # Extract only the date from ClearDate
        filtered_df['ClearDate'] = filtered_df['ClearDate'].apply(extract_date)
        
        # Write the filtered data to clear.csv
        filtered_df.to_csv('clear.csv', index=False)
        print("Successfully created clear.csv with filtered data")
        
    except FileNotFoundError as e:
        print(f"Error: {str(e)}")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    process_inventory()
