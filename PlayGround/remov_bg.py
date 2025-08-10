from PIL import Image

# Load image
img = Image.open("input.png").convert("RGBA")

# Get pixel data
datas = img.getdata()

new_data = []
for item in datas:
    # If pixel is close to the blue background, make it transparent
    # Blue background RGB roughly (0, 51, 102) but we allow some tolerance
    if abs(item[0] - 0) < 50 and abs(item[1] - 51) < 50 and abs(item[2] - 102) < 50:
        new_data.append((255, 255, 255, 0))  # transparent
    else:
        new_data.append(item)

# Update and save image
img.putdata(new_data)
output_path = "karnaAGT_logo_transparent.png"
img.save(output_path, "PNG")

output_path
