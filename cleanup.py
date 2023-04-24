import os
from datetime import datetime
import json

# load config from config.json
with open('config.json', 'r') as file:
    config = json.load(file)

OBSIDIAN_DIR = config['obsidian-dir']

def is_valid_date(date_string):
    try:
        date = datetime.strptime(date_string, '%Y-%m-%d')
        return date
    except ValueError:
        return False

def contains_date(file_path):
    with open(file_path, "r") as file:
        for line in file:
            if "After " in line:
                date_string = line.split("After ")[1].strip().replace('[',"").replace(']',"").replace('.',"")
                try:
                    datetime.strptime(date_string, '%Y-%m-%d')
                    return True
                except ValueError:
                    pass
    return False

def move_daily_notes():
    files = os.listdir(OBSIDIAN_DIR)

    # move date files to Daily Notes directory
    for file in files:
        filename = file.split(".")[0]
        if is_valid_date(filename):
            os.rename(OBSIDIAN_DIR + file, OBSIDIAN_DIR + "Daily Notes/" + file) 
            print(f"Moved {file} to Daily Notes directory.")  
    

def link_daily_notes():
    daily_notes = os.listdir(OBSIDIAN_DIR + "Daily Notes/")
    daily_note_dates = [is_valid_date(file.split('.')[0]) for file in daily_notes]
    daily_note_dates = [date for date in daily_note_dates if date]
    daily_note_dates = sorted(daily_note_dates, key=lambda x: x)
    for file in daily_notes:
        if not contains_date(OBSIDIAN_DIR + "Daily Notes/" + file):
            with open(OBSIDIAN_DIR + "Daily Notes/" + file, "r+") as f:
                content = f.read()
                f.seek(0, 0)
                for i in range(len(daily_note_dates)):
                    if daily_note_dates[i] == is_valid_date(file.split('.')[0]):
                        if i > 0:
                            f.write(f"After [[{daily_note_dates[i-1].strftime('%Y-%m-%d')}]].\n\n")
                            print(f"Linked {file} to previous daily note.")
                f.write(content)

def main():
    
    move_daily_notes()

    link_daily_notes()

if __name__ == "__main__":
    main()