# Dont use this script. Use geotag.py

import os
import csv
from PIL import Image
import exifread

def get_exif_data(image_path):
    with open(image_path, 'rb') as img_file:
        tags = exifread.process_file(img_file)
        return tags

def get_geotagging(exif_data):
    geotagging = {}
    for (k, v) in exif_data.items():
        if k.startswith('GPS'):
            geotagging[k] = v
    return geotagging

def get_decimal_from_dms(dms, ref):
    degrees = dms[0].num / dms[0].den
    minutes = dms[1].num / dms[1].den
    seconds = dms[2].num / dms[2].den
    decimal = degrees + (minutes / 60.0) + (seconds / 3600.0)
    if ref in ['S', 'W']:
        decimal = -decimal
    return decimal

def get_coordinates(geotags):
    latitude = None
    longitude = None
    altitude = None

    if 'GPS GPSLatitude' in geotags and 'GPS GPSLatitudeRef' in geotags:
        latitude = get_decimal_from_dms(geotags['GPS GPSLatitude'].values, geotags['GPS GPSLatitudeRef'].printable)

    if 'GPS GPSLongitude' in geotags and 'GPS GPSLongitudeRef' in geotags:
        longitude = get_decimal_from_dms(geotags['GPS GPSLongitude'].values, geotags['GPS GPSLongitudeRef'].printable)
    
    if 'GPS GPSAltitude' in geotags:
        altitude = float(geotags['GPS GPSAltitude'].values[0])

    return latitude, longitude, altitude

def extract_metadata(image_folder, output_csv):
    data = []

    for root, dirs, files in os.walk(image_folder):
        for file in files:
            if file.lower().endswith(".jpg"):
                image_path = os.path.join(root, file)
                exif_data = get_exif_data(image_path)
                geotags = get_geotagging(exif_data)
                latitude, longitude, altitude = get_coordinates(geotags)
                subdirectory = os.path.relpath(root, image_folder)
                data.append([subdirectory, file, latitude, longitude, altitude])

    with open(output_csv, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Subdirectory", "Image", "Latitude", "Longitude", "Altitude"])
        writer.writerows(data)

# Usage
image_folder = 'C:/Users/alexmorgan/Downloads/Iceland field-001/Iceland_field'
output_csv = 'C:/Users/alexmorgan/Downloads/Iceland field-001/Iceland_field/image_metadata.csv'
extract_metadata(image_folder, output_csv)



