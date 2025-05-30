# Tableau VOTD Data Collector

A Python utility for collecting and processing Tableau's Viz of the Day (VOTD) data, including metadata and associated images.

## Overview

This tool automates the collection of Tableau's Viz of the Day data from the Tableau Public API. It fetches visualization metadata, downloads associated images, and organizes everything into a structured CSV format. The tool also manages image assets for use in Tableau dashboards.

## Features

- Fetches up to 50 most recent Viz of the Day entries
- Downloads and processes visualization thumbnails
- Maintains image assets in both local and Tableau Shapes directories
- Generates a structured CSV with visualization metadata
- Handles concurrent image downloads for improved performance
- Includes robust error handling and retry mechanisms
- Cleans and processes text data to remove HTML entities

## Requirements

- Python 3.x
- Required Python packages:
  - requests
  - pandas
  - Pillow (PIL)
  - pathlib
  - concurrent.futures

## Installation

1. Clone this repository or download the source code
2. Install the required dependencies:

```bash
pip install requests pandas Pillow
```

## Usage

Simply run the script:

```bash
python votd_to_csv.py
```

The script will:
1. Fetch the most recent VOTD data from Tableau Public
2. Download and process associated images
3. Generate a CSV file with the following columns:
   - date
   - authorDisplayName
   - title
   - viewCount
   - numberOfFavorites
   - vizLink
   - shapeReference

## Output

The script creates two main outputs:

1. **CSV File**: `votd_data.csv` containing all visualization metadata
2. **Image Directories**:
   - Local: `./votd_images/`
   - Tableau Shapes: `~/Documents/My Tableau Repository/Shapes/votd_images/`

## Image Processing

- Images are automatically resized to 1600x900 pixels while maintaining aspect ratio
- Transparent backgrounds are preserved
- Images are optimized for web display
- Failed downloads are automatically retried up to 3 times

## Error Handling

The script includes comprehensive error handling for:
- Network timeouts
- Invalid JSON responses
- Image processing errors
- File system operations

## Contributing

Feel free to submit issues and enhancement requests!

## License

This project is open source and available under the MIT License. 