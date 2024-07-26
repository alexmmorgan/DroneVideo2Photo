# this script gets the metadata from each second of the SRT file that accompanies each MPEG file
# use it to assign the metadata to the stills extracted in the other script

import re
import pandas as pd
import os

# these arent used until step 3:
import piexif
from PIL import Image

# get all of the files
# each MP4 must have an accompanying SRT
folder = "H:/_iceland/mini_drone/0705"
files = [f.replace(".SRT", "") for f in os.listdir(folder) if f.endswith(".SRT")]


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

####################################
# FOR STEP 3
def deg_to_dms_rational(deg):
    """Convert degrees to (degree, minute, second) tuple."""
    d = int(deg)
    m = int((deg - d) * 60)
    s = round((deg - d - m / 60) * 3600, 2)
    return (d, m, s)

def decimal_to_dms_coordinates(lat, lon):
    """Convert decimal degrees to EXIF-appropriate format."""
    lat_deg = deg_to_dms_rational(abs(lat))
    lon_deg = deg_to_dms_rational(abs(lon))

    lat_ref = 'N' if lat >= 0 else 'S'
    lon_ref = 'E' if lon >= 0 else 'W'

    return {
        piexif.GPSIFD.GPSLatitudeRef: lat_ref,
        piexif.GPSIFD.GPSLatitude: ((lat_deg[0], 1), (lat_deg[1], 1), (int(lat_deg[2] * 100), 100)),
        piexif.GPSIFD.GPSLongitudeRef: lon_ref,
        piexif.GPSIFD.GPSLongitude: ((lon_deg[0], 1), (lon_deg[1], 1), (int(lon_deg[2] * 100), 100)),
        piexif.GPSIFD.GPSAltitudeRef: 0,
        piexif.GPSIFD.GPSAltitude: (int(df_filtered.iloc[0]['altitude'] * 100), 100)
    }


#######################################################################
# Now loop over all of the video files
#######################################################################

for file in files:

    print("\n\n Starting " + file + "\n\n")

    #######################################################################
    # STEP 1: extract the lat/lon/alt from the SRT file
    #######################################################################

    SRT_filepath = os.path.join(folder, file + ".SRT")

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

    # update the row numbers
    df_filtered = df_filtered.reset_index(drop = True)

    # add a column for the image number
    df_filtered["image_name"] = file + "_" + df_filtered["frame_number"].astype(str).apply(lambda x: x.zfill(5)) + ".png"

    csv_file_path = SRT_filepath.replace(".SRT", ".csv")
    df_filtered.to_csv(csv_file_path, index = False)

    print("\n Done with step 1 - lat/lon from SRT files \n")

    #######################################################################
    # STEP 2: extract the stills from the video. One each second
    #######################################################################
    # create images from every frame of the video. Keep only those frames that match the filtered df from above
    # this probably isnt the bext approach (slow and high data volume), but it is fast enough and the extra volume gets immediately deleted

    MP4_filepath = os.path.join(folder, file + ".MP4")
    os.system("ffmpeg -i " + MP4_filepath + " " + MP4_filepath.replace(".MP4", "") + "_%05d.png")

    # get a list of all the created PNG files
    new_PNG_files = [f for f in os.listdir(folder) if f.startswith(file) and f.endswith('.png')]

    numbers_to_keep = df_filtered["frame_number"].astype(str).tolist()
    numbers_to_keep = [f.zfill(5) for f in numbers_to_keep]

    # remove the extra files (i.e., those that dont have matches in df_filtered)
    for new_PNG_file in new_PNG_files:
        number = new_PNG_file[-9:-4]
        if number not in numbers_to_keep:
            os.remove(os.path.join(folder, new_PNG_file))

    print("\n Done with step 2 - frame each second \n")

    #######################################################################
    # STEP 3: geotag the frames
    #######################################################################


    # Loop over each image and add the geotagging data
    for index, row in df_filtered.iterrows():
        image_name = row['image_name']

        lat, lon, alt = row['latitude'], row['longitude'], row['altitude']
        
        # Convert latitude and longitude to EXIF format
        gps_info = decimal_to_dms_coordinates(lat, lon)
        
        # Load image and insert EXIF data
        image = Image.open(os.path.join(folder, image_name))
        exif_dict = piexif.load(image.info['exif']) if 'exif' in image.info else {"0th": {}, "Exif": {}, "GPS": {}, "Interop": {}, "1st": {}, "thumbnail": None}
        exif_dict['GPS'] = gps_info
        exif_bytes = piexif.dump(exif_dict)
        
        # Save the image with the new EXIF data
        image.save(os.path.join(folder, image_name.replace(".png", "_GPS.jpg")), "jpeg", exif = exif_bytes)

    print("\n Done with step 3 - geotagging \n")
    print("\n*********************************\n*********************************\n")
