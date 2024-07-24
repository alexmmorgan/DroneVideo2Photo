

import re
import pandas as pd
import os

# get all of the SRT files
folder = "H:/_iceland/mini_drone/0705"
extension = ".SRT"
SRT_files = [f for f in os.listdir(folder) if f.endswith(extension)]

# Function to convert time string to seconds
def time_to_seconds(time_str):
    h, m, s = time_str.split(':')
    s, ms = s.split(',')
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000

# Function to check if the range spans a full second
def includes_full_second(time_range):
    start_time, end_time = time_range.split(' --> ')
    start_seconds = time_to_seconds(start_time)
    end_seconds = time_to_seconds(end_time)
    
    # Check if the time range spans a full second
    return int(start_seconds) != int(end_seconds)

for SRT_file in SRT_files:

    filepath = os.path.join(folder, SRT_file)

    with open(filepath, 'r', encoding='utf-8') as file:
        data = file.read()


    # Regular expressions to match the different parts of the data
    entry_pattern = re.compile(r'(\d+)\n(.+?)\n<font size="28">(.+?)\n(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})\n(.+?)</font>', re.DOTALL)
    variable_pattern = re.compile(r'\[([a-zA-Z_]+) *: *([\w\.\-/]+)\]')

    # Parse data
    entries = []
    for entry in entry_pattern.finditer(data):
        number, time_range, header, timestamp, variables = entry.groups()
        variable_dict = {k: v for k, v in variable_pattern.findall(variables)}
        entries.append({
            'Number': int(number),
            'Time Range': time_range,
            'Header': header.strip(),
            'Timestamp': timestamp,
            **variable_dict
        })

    # Convert to pandas DataFrame
    df = pd.DataFrame(entries)

    # Apply the filter
    df_filtered = df[df['Time Range'].apply(includes_full_second)]

    # df.to_csv(os.path.join(folder, "df.csv"), index = False)
    # df_filtered.to_csv(os.path.join(folder, "df_filtered.csv"), index = False)

    csv_file_path = filepath.replace(".SRT", ".csv")
    df_filtered.to_csv(csv_file_path, index = False)

    # print(df)
