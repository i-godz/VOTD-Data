import os
import pandas as pd
from datetime import datetime
from votd_to_csv import download_image, get_last_image_number

def fetch_latest_votd():
    import requests
    url = "https://public.tableau.com/public/apis/bff/discover/v1/vizzes/viz-of-the-day?page=0&limit=1"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    data = response.json()
    if isinstance(data, dict) and 'vizzes' in data:
        vizzes = data['vizzes']
    elif isinstance(data, list):
        vizzes = data
    else:
        raise Exception("Unexpected API response format")
    return vizzes[0] if vizzes else None

def update_votd_csv_and_image():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(script_dir, "votd_data.csv")
    images_dir = os.path.join(script_dir, "votd_images")
    os.makedirs(images_dir, exist_ok=True)

    # Fetch the latest VOTD
    latest_viz = fetch_latest_votd()
    if not latest_viz:
        print("No new VOTD found.")
        return

    # Load existing CSV
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
    else:
        df = pd.DataFrame(columns=[
            "date", "authorDisplayName", "title", "viewCount",
            "numberOfFavorites", "vizLink", "shapeReference"
        ])

    # Check if today's VOTD is already present
    today_str = datetime.now().date().strftime('%Y-%m-%d')
    if not df.empty and (df['date'] == today_str).any():
        print("Today's VOTD already exists in the CSV.")
        return

    # Increment shape reference
    last_shape_ref = get_last_image_number(images_dir)
    new_shape_ref = last_shape_ref + 1
    image_filename = f"{new_shape_ref:03d}"
    image_path = os.path.join(images_dir, f"{image_filename}.png")

    # Get image URL
    image_url = (
        latest_viz.get("curatedImageUrl") or
        latest_viz.get("imageUrl") or
        (f"https://public.tableau.com/views/{latest_viz.get('workbookRepoUrl')}/{latest_viz.get('defaultViewRepoUrl').split('/')[-1]}.png?:display_static_image=y&:showVizHome=n"
         if latest_viz.get('workbookRepoUrl') and latest_viz.get('defaultViewRepoUrl') else None)
    )

    # Download image
    if image_url:
        print(f"Downloading image {image_filename}.png...")
        download_image(image_url, image_path)
    else:
        print("No image URL found for the latest VOTD.")

    # Prepare new row
    row = {
        "date": today_str,
        "authorDisplayName": latest_viz.get("authorDisplayName"),
        "title": latest_viz.get("title"),
        "viewCount": latest_viz.get("viewCount"),
        "numberOfFavorites": latest_viz.get("numberOfFavorites"),
        "vizLink": latest_viz.get("publicUrl") or (
            f"https://public.tableau.com/views/{latest_viz.get('workbookRepoUrl')}/{latest_viz.get('defaultViewRepoUrl').split('/')[-1]}"
            if latest_viz.get("workbookRepoUrl") and latest_viz.get("defaultViewRepoUrl") else None
        ),
        "shapeReference": image_filename
    }

    # Insert new row at the top (newest first)
    df = pd.concat([pd.DataFrame([row]), df], ignore_index=True)
    df.to_csv(csv_path, index=False)
    print(f"Added today's VOTD to {csv_path} with shapeReference {image_filename}")

if __name__ == "__main__":
    update_votd_csv_and_image() 