# This script extracts stills from video and geotags them using the video's caption file (.SRT)
# This was written as a first step to processing data from drones without flight planning control (e.g., DJI Mini 3 Pro)
# there are three steps:
#   1: parse the SRT file to get the lat/lon/alt for every frame
#   2: extract stills using ffmpeg (this is the only external dependency)
#   3: geotag the stills from 2 using the parsed data from 1
# there are only two inputs:
#   working_directory: where the input MP4 and SRT files are and where the output JPG files will go
#   seconds_between: How many seconds should there be between stills?


# Alex Morgan, Planetary Science Institute. amorgan@psi.edu
# July 26, 2024

####################################
# Define the input parameters
# each MP4 in the working directory must have an accompanying SRT
working_directory = "H:/_iceland/mini_drone/0705"
seconds_between = 2 # how many seconds between output images?

####################################
# Load packages
# ffmpeg must be installed
import pandas as pd
import os

# used in step 1:
import re

# these arent used until step 3:
import piexif
from PIL import Image
import glob

####################################
# get all of the files
files_SRT = [f.replace(".SRT", "") for f in os.listdir(working_directory) if f.endswith(".SRT")]
files_MP4 = [f.replace(".MP4", "") for f in os.listdir(working_directory) if f.endswith(".MP4")]

# each SRT needs to have a matching MP4
files = list(set(files_SRT) & set(files_MP4))

# # TEMP: omit those I already did
# files_JPG = list(set(["DJI_" + f.split("_")[1] for f in os.listdir(working_directory) if f.endswith("_GPS.jpg")]))
# files = list(set(files) - set(files_JPG))

#######################################################################
# some functions for the steps below
#######################################################################

####################################
# FOR STEP 1
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

#######################################################################
# Now loop over all of the video files
#######################################################################

for file in files:

    print("\n\n Starting " + file + "\n\n")

    #######################################################################
    # STEP 1: extract the lat/lon/alt from the SRT file
    #######################################################################

    SRT_filepath = os.path.join(working_directory, file + ".SRT")

    with open(SRT_filepath, 'r', encoding='utf-8') as SRT_file:
        data = SRT_file.read()
    
    # Regular expressions to match the different parts of the data
    entry_pattern = re.compile(r'(\d+)\n(.+?)\n<font size="28">(.+?)\n(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})\n(.+?)</font>', re.DOTALL)
    variable_pattern = re.compile(r'\[([a-zA-Z_]+)\s*:\s*([\w\.\-/]+)(?:\s+([a-zA-Z_]+)\s*:\s*([\w\.\-/]+))?\]')

    # Parse data
    entries = []
    for entry in entry_pattern.finditer(data):
        number, time_range, header, timestamp, variables = entry.groups()
        variable_dict = {}
        for match in variable_pattern.finditer(variables):
            key1, value1, key2, value2 = match.groups()
            variable_dict[key1] = value1
            if key2:
                variable_dict[key2] = value2
        entries.append({
            'Number': int(number),
            'Time Range': time_range,
            'Header': header.strip(),
            'Timestamp': timestamp,
            **variable_dict
        })
    
    # Convert to pandas DataFrame
    df = pd.DataFrame(entries)
    df = df.rename(columns = {"Number": "frame_number", "abs_alt": "altitude"})

    df["latitude"] = df["latitude"].astype(float)
    df["longitude"] = df["longitude"].astype(float)
    df["altitude"] = df["altitude"].astype(float)

    # Apply the filter
    df_filtered = df[df["Time Range"].apply(includes_full_second)]

    # reset the index
    df_filtered = df_filtered.reset_index(drop = True)

    # Remove extras. This is controlled by seconds_between above
    df_filtered = df_filtered[df_filtered.index % seconds_between == 0]

    # add a column for the image number
    df_filtered["image_name"] = file + "_" + df_filtered["frame_number"].astype(str).apply(lambda x: x.zfill(5)) + ".png"

    csv_file_path = SRT_filepath.replace(".SRT", ".csv")
    df_filtered.to_csv(csv_file_path, index = False)

    print("\n Done with step 1 - lat/lon from SRT files \n")

    #######################################################################
    # STEP 2: extract the stills from the video
    #######################################################################
    # create images from every frame of the video. Keep only those frames that match the filtered df from above
    # this probably isnt the bext approach (slow and high data volume), but it is fast enough and the extra volume gets immediately deleted

    MP4_filepath = os.path.join(working_directory, file + ".MP4")
    os.system("ffmpeg -i " + MP4_filepath + " " + MP4_filepath.replace(".MP4", "") + "_%05d.png")

    # get a list of all the created PNG files
    new_PNG_files = [f for f in os.listdir(working_directory) if f.startswith(file) and f.endswith('.png')]

    numbers_to_keep = df_filtered["frame_number"].astype(str).tolist()
    numbers_to_keep = [f.zfill(5) for f in numbers_to_keep]

    # remove the extra files (i.e., those that dont have matches in df_filtered)
    for new_PNG_file in new_PNG_files:
        number = new_PNG_file[-9:-4]
        if number not in numbers_to_keep:
            os.remove(os.path.join(working_directory, new_PNG_file))

    print("\n Done with step 2 - frames extracted \n")

    


    #########################################################
    #########################################################
    #########################################################
    # delete below???

    # finally, delete all the un-geotagged png files

    files = glob.glob(os.path.join(working_directory, "*.png"))
    print(files)

    errors = []
    for file in files:
        try:
            os.remove(file)
        except:
            errors.append(file.replace(working_directory, ""))
    
    if len(errors) > 0:
        print("Could not delete the following:")
        print(errors)


    print("\n Done with step 3 - geotagging \n")
    print("\n*********************************\n*********************************\n")
