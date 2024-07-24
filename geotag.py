folder = "H:/_iceland/mini_drone/test_geotag"

import os
from PIL import Image
from PIL.ExifTags import TAGS

pil_img = Image.open(os.path.join(folder, "DJI_0193.JPG"))
exif_info = pil_img._getexif()
exif = {TAGS.get(k, k): v for k, v in exif_info.items()}
print(exif)