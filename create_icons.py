from PIL import Image, ImageDraw

def create_icon(size):
    # Create a new image with a white background
    image = Image.new('RGB', (size, size), 'white')
    draw = ImageDraw.Draw(image)
    
    # Draw a simple colored rectangle
    draw.rectangle([size/4, size/4, size*3/4, size*3/4], fill='blue')
    
    # Save the image
    image.save(f'icons/icon{size}.png')

# Create icons of required sizes
create_icon(16)
create_icon(48)
create_icon(128) 