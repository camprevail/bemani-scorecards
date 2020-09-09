from PIL import Image
import os

# Decided to leave this in as an example - a much faster alternative to photoshop batch processing.
def resize(jacket):
    try:
        base = Image.open(jacket)
        filename = os.path.split(base.filename)[1]
        if not base.mode == 'RGBA':
            base = base.convert('RGBA')
        base = base.resize((223, 223), resample=Image.LANCZOS)
        base.save(f"museca/assets/jackets/{filename}")
    except Exception as e:
        print(e)
