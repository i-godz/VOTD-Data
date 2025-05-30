import os
import requests
import pandas as pd
from pathlib import Path
import shutil
import glob
from datetime import datetime, timedelta
from PIL import Image
import warnings
import html
import json
import concurrent.futures
from urllib.parse import urlparse
import time
import io

warnings.filterwarnings("ignore", category=UserWarning, module="urllib3")

# =================================================================================================================================================
# VOTD API Fetching
# =================================================================================================================================================
# Function: fetch_all_votd
# Fetches Viz of the Day (VOTD) data from Tableau Public API

def fetch_all_votd(limit=50):
    """Fetch up to 500 VOTDs from the API."""
    page = 0
    page_size = 12
    all_votds = []
    
    while len(all_votds) < limit:
        url = f"https://public.tableau.com/public/apis/bff/discover/v1/vizzes/viz-of-the-day?page={page}&limit={page_size}"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Extract vizzes from the response
            if isinstance(data, dict) and 'vizzes' in data:
                vizzes = data['vizzes']
            elif isinstance(data, list):
                vizzes = data
            else:
                print(f"Unexpected data format on page {page}")
                break

            if not vizzes:
                print(f"No more vizzes found on page {page}")
                break

            # Add each viz to our collection
            for viz in vizzes:
                if len(all_votds) >= limit:
                    break
                all_votds.append(viz)
            
            print(f"Fetched page {page}, total so far: {len(all_votds)}")
            page += 1
            
        except requests.RequestException as e:
            print(f"Network or HTTP error on page {page}: {e}")
            break
        except ValueError as e:
            print(f"Invalid JSON response on page {page}: {e}")
            break
        except Exception as e:
            print(f"Unexpected error on page {page}: {e}")
            break

    print(f"Total VOTDs fetched: {len(all_votds)}")
    return all_votds

# =================================================================================================================================================
# Text Cleaning Utilities
# =================================================================================================================================================
# Function: clean_text
# Cleans and decodes HTML entities from text

def clean_text(text):
    """Clean text by decoding HTML entities and removing unwanted characters."""
    if not isinstance(text, str):
        return text
    # Decode HTML entities
    text = html.unescape(text)
    # Remove any remaining HTML tags
    text = text.replace('&amp;', '&')
    text = text.replace('&#039;', "'")
    text = text.replace('&quot;', '"')
    return text.strip()

# =================================================================================================================================================
# Image Directory Utilities
# =================================================================================================================================================
# Function: get_last_image_number
# Gets the highest image number in a directory

def get_last_image_number(images_dir):
    """Get the highest number used in existing images"""
    if not os.path.exists(images_dir):
        return 0
    
    files = glob.glob(os.path.join(images_dir, '[0-9]*.png'))
    if not files:
        return 0
    
    numbers = [int(os.path.splitext(os.path.basename(f))[0]) for f in files]
    return max(numbers) if numbers else 0

# Function: clear_images_folder
# Clears all PNG files from a directory

def clear_images_folder(images_dir):
    """Clear all PNG files from the images directory."""
    if os.path.exists(images_dir):
        files = glob.glob(os.path.join(images_dir, '*.png'))
        for f in files:
            os.remove(f)
    else:
        os.makedirs(images_dir, exist_ok=True)

# =================================================================================================================================================
# Image Processing
# =================================================================================================================================================
# Function: resize_image
# Resizes an image to a target size while maintaining aspect ratio

def resize_image(image_data, target_size=(1600, 900)):
    """Resize image to target dimensions while maintaining aspect ratio."""
    try:
        # Open image from bytes
        img = Image.open(io.BytesIO(image_data))
        
        # Convert to RGBA if necessary
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        # Calculate new dimensions maintaining aspect ratio
        width, height = img.size
        target_width, target_height = target_size
        
        # Calculate scaling factor
        scale = min(target_width/width, target_height/height)
        new_size = (int(width * scale), int(height * scale))
        
        # Resize image
        img = img.resize(new_size, Image.Resampling.LANCZOS)
        
        # Create new image with transparent background
        new_img = Image.new('RGBA', target_size, (0, 0, 0, 0))
        
        # Calculate position to paste resized image (centered)
        paste_x = (target_width - new_size[0]) // 2
        paste_y = (target_height - new_size[1]) // 2
        
        # Paste resized image onto new image
        new_img.paste(img, (paste_x, paste_y), img)
        
        # Save to bytes
        output = io.BytesIO()
        new_img.save(output, format='PNG', optimize=True)
        return output.getvalue()
        
    except Exception as e:
        print(f"Error resizing image: {str(e)}")
        return None

# Function: download_image
# Downloads and resizes an image, saving to multiple paths

def download_image(url, save_paths, filename, max_retries=3):
    """Download image from URL, resize it, and save to multiple paths with retries."""
    for attempt in range(max_retries):
        try:
            # Increase timeout for larger images
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            # Get image data
            image_data = response.content
            
            # Resize image
            resized_data = resize_image(image_data)
            if not resized_data:
                raise Exception("Failed to resize image")
            
            # Save to multiple locations
            for path in save_paths:
                with open(path, 'wb') as f:
                    f.write(resized_data)
            
            print(f"✓ Successfully downloaded and resized: {filename}")
            return True
            
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 5  # Increasing wait time between retries
                print(f"! Timeout downloading {filename}, retrying in {wait_time} seconds... (Attempt {attempt + 1}/{max_retries})")
                time.sleep(wait_time)
            else:
                print(f"✗ Failed to download {filename} after {max_retries} attempts")
                return False
                
        except Exception as e:
            print(f"✗ Error processing {filename}: {str(e)}")
            return False

# Function: download_images_concurrently
# Downloads multiple images concurrently with progress tracking

def download_images_concurrently(image_tasks, max_workers=5):
    """Download multiple images concurrently with progress tracking."""
    successful_downloads = []
    failed_downloads = []
    
    print(f"\nStarting download of {len(image_tasks)} images...")
    print("Progress: [", end="")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for url, paths, filename in image_tasks:
            futures.append(executor.submit(download_image, url, paths, filename))
        
        # Process completed downloads
        for i, future in enumerate(concurrent.futures.as_completed(futures)):
            if future.result():
                successful_downloads.append(i)
            else:
                failed_downloads.append(i)
            
            # Update progress bar
            progress = (i + 1) / len(futures) * 100
            print("=", end="", flush=True)
    
    print("] 100%")
    print(f"\nDownload Summary:")
    print(f"✓ Successfully downloaded: {len(successful_downloads)} images")
    print(f"✗ Failed to download: {len(failed_downloads)} images")
    
    return len(successful_downloads)

# =================================================================================================================================================
# VOTD Data Extraction Utilities
# =================================================================================================================================================
# Function: get_image_url
# Extracts the image URL from a viz data dictionary

def get_image_url(viz):
    """Extract image URL from viz data."""
    # Try curated image first
    if viz.get("curatedImageUrl"):
        return viz["curatedImageUrl"]
    
    # Then try regular image
    if viz.get("imageUrl"):
        return viz["imageUrl"]
    
    # Finally, construct from workbook and view URLs
    if viz.get("workbookRepoUrl") and viz.get("defaultViewRepoUrl"):
        view_name = viz["defaultViewRepoUrl"].split('/')[-1]
        return f"https://public.tableau.com/views/{viz['workbookRepoUrl']}/{view_name}.png?:display_static_image=y&:showVizHome=n"
    
    return None

# Function: get_viz_link
# Extracts the viz link from a viz data dictionary

def get_viz_link(viz):
    """Extract viz link from viz data."""
    if viz.get("publicUrl"):
        return viz["publicUrl"]
    
    if viz.get("workbookRepoUrl") and viz.get("defaultViewRepoUrl"):
        view_name = viz["defaultViewRepoUrl"].split('/')[-1]
        return f"https://public.tableau.com/views/{viz['workbookRepoUrl']}/{view_name}"
    
    return None

# =================================================================================================================================================
# CSV and Data Saving
# =================================================================================================================================================
# Function: save_votd_to_csv
# Saves VOTD data to CSV and manages image downloads

def save_votd_to_csv(votds, filename="votd_data.csv"):
    """Save VOTD data to CSV and download images."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, filename)
    
    # Set up both image directories
    local_images_dir = os.path.join(script_dir, 'votd_images')
    tableau_shapes_dir = "/Users/godzilla/Documents/My Tableau Repository/Shapes/votd_images"
    
    # Clear both directories
    clear_images_folder(local_images_dir)
    clear_images_folder(tableau_shapes_dir)

    new_rows = []
    today = datetime.now().date()
    total_votds = len(votds)
    
    # Prepare image download tasks
    image_tasks = []

    for idx, viz in enumerate(votds):
        date = today - timedelta(days=idx)
        
        # Get image URL and prepare paths
        image_url = get_image_url(viz)
        image_filename = f"{total_votds - idx:03d}"
        local_image_path = os.path.join(local_images_dir, f"{image_filename}.png")
        tableau_image_path = os.path.join(tableau_shapes_dir, f"{image_filename}.png")
        
        if image_url:
            image_tasks.append((image_url, [local_image_path, tableau_image_path], image_filename))
            shape_reference = image_filename
        else:
            shape_reference = None

        # Create row with all viz data
        row = {
            "date": date.strftime('%Y-%m-%d'),
            "authorDisplayName": clean_text(viz.get("authorDisplayName", "")),
            "title": clean_text(viz.get("title", "")),
            "viewCount": viz.get("viewCount"),
            "numberOfFavorites": viz.get("numberOfFavorites"),
            "vizLink": get_viz_link(viz),
            "shapeReference": shape_reference
        }
        new_rows.append(row)

    # Download all images concurrently
    success_count = download_images_concurrently(image_tasks)

    # Create DataFrame and save to CSV
    df = pd.DataFrame(new_rows)
    df.to_csv(file_path, index=False)
    print(f"\nSaved {len(df)} VOTDs to {file_path}")
    print(f"Downloaded images are saved in:")
    print(f"- Local: {local_images_dir}")
    print(f"- Tableau Shapes: {tableau_shapes_dir}")

    # Display summary
    print("\nFirst few rows of the CSV (newest first):")
    print(df[['date', 'title', 'authorDisplayName', 'shapeReference']].head())

# =================================================================================================================================================
# Main Script Entry Point
# =================================================================================================================================================
if __name__ == "__main__":
    votds = fetch_all_votd(limit=50)
    if votds:
        save_votd_to_csv(votds)
    else:
        print("No VOTD data fetched.") 