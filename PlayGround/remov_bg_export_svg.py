from PIL import Image, ImageFilter
import base64
import io
import numpy as np

def _smooth_alpha(img_array: np.ndarray, dilation_iterations: int = 1, blur_radius: float = 1.2) -> np.ndarray:
    """Feather and slightly expand the alpha edge for polished, anti-aliased borders."""
    alpha = img_array[:, :, 3]
    # Binary mask of current opaque region
    mask = (alpha > 0).astype(np.uint8) * 255
    pil_mask = Image.fromarray(mask, mode='L')
    # Slight dilation to cover colored fringe, then gentle blur for feathering
    for _ in range(max(0, dilation_iterations)):
        pil_mask = pil_mask.filter(ImageFilter.MaxFilter(size=3))
    pil_mask = pil_mask.filter(ImageFilter.GaussianBlur(radius=blur_radius))
    img_array[:, :, 3] = np.array(pil_mask, dtype=np.uint8)
    return img_array


def png_to_svg_embedded(input_path, output_path):
    """Convert PNG to SVG by embedding the PNG as base64 data"""
    # Load and process image
    img = Image.open(input_path).convert("RGBA")
    
    # Convert to numpy array for easier processing
    img_array = np.array(img)
    
    # Define white threshold (adjust if needed)
    white_threshold = 240
    
    # Create a mask for pixels that are NOT close to white
    # Check if all RGB values are below the white threshold
    non_white_mask = (img_array[:, :, 0] < white_threshold) | \
                     (img_array[:, :, 1] < white_threshold) | \
                     (img_array[:, :, 2] < white_threshold)
    
    # Make all non-white pixels transparent
    img_array[non_white_mask, 3] = 0  # Set alpha to 0 (transparent)

    # Smooth/feather the alpha edge to remove color fringing and jaggies
    img_array = _smooth_alpha(img_array, dilation_iterations=1, blur_radius=1.5)
    
    # Convert back to PIL Image
    img = Image.fromarray(img_array, 'RGBA')
    
    # Convert to base64
    img_buffer = io.BytesIO()
    img.save(img_buffer, format='PNG')
    img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
    
    # Create SVG with embedded PNG
    width, height = img.size
    svg_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" 
     width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <image x="0" y="0" width="{width}" height="{height}" 
         xlink:href="data:image/png;base64,{img_base64}"/>
</svg>'''
    
    with open(output_path, 'w') as f:
        f.write(svg_content)
    
    return output_path

def png_to_svg_traced(input_path, output_path):
    """Convert PNG to SVG using potrace (requires potrace to be installed)"""
    try:
        import subprocess
        import os
        
        # First create a temporary bitmap
        img = Image.open(input_path).convert("RGBA")
        
        # Convert to numpy array for easier processing
        img_array = np.array(img)
        
        # Define white threshold
        white_threshold = 240
        
        # Create a mask for pixels that are NOT close to white
        non_white_mask = (img_array[:, :, 0] < white_threshold) | \
                         (img_array[:, :, 1] < white_threshold) | \
                         (img_array[:, :, 2] < white_threshold)
        
        # Make all non-white pixels transparent
        img_array[non_white_mask, 3] = 0  # Set alpha to 0 (transparent)

        # Smooth/feather the alpha edge prior to tracing
        img_array = _smooth_alpha(img_array, dilation_iterations=1, blur_radius=1.5)
        
        # Convert back to PIL Image
        img = Image.fromarray(img_array, 'RGBA')
        
        # Convert to grayscale for potrace
        temp_bmp = "temp_trace.bmp"
        img_gray = img.convert('L')
        img_gray.save(temp_bmp, 'BMP')
        
        # Use potrace to convert to SVG
        result = subprocess.run(['potrace', '-s', '-o', output_path, temp_bmp], 
                              capture_output=True, text=True)
        
        # Clean up temp file
        if os.path.exists(temp_bmp):
            os.remove(temp_bmp)
            
        if result.returncode == 0:
            return output_path
        else:
            print(f"Potrace error: {result.stderr}")
            return None
            
    except Exception as e:
        print(f"Tracing method failed: {e}")
        return None

# Main execution
if __name__ == "__main__":
    input_file = "logo.PNG"
    
    # Method 1: Embed PNG in SVG (always works)
    svg_embedded = png_to_svg_embedded(input_file, "karnaAGT_logo_embedded.svg")
    print(f"Embedded SVG created: {svg_embedded}")
    
    # Method 2: Try vector tracing (requires potrace)
    svg_traced = png_to_svg_traced(input_file, "karnaAGT_logo_traced.svg")
    if svg_traced:
        print(f"Traced SVG created: {svg_traced}")
    else:
        print("Vector tracing failed. Install potrace for true vector conversion.")
        print("For Windows: Download from http://potrace.sourceforge.net/")
    
    print("\nNote: Embedded SVG contains the PNG as base64 data.")
    print("Traced SVG creates true vector paths (if potrace is available).")
