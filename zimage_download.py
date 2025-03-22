from bing_image_downloader import downloader
import concurrent.futures

# Define your search queries
search_queries = ["Video Games", "Sports", "Video", "Music", "Software", "Toy", 
                  "Baby Product", "Book", "DVD", "CE"]

# Function to download images
def download_images(query):
    try:
        downloader.download(
            query, 
            limit=100,               # Number of images to download per query
            output_dir='ImageData',  # Output directory
            adult_filter_off=True,   # Disable adult content filter
            force_replace=False,     # Don't replace existing files
            timeout=10,              # Reduce timeout (default was 60)
            filter="",               # Optional filter (photo, clipart, etc.)
            verbose=False            # Reduce console clutter
        )
        print(f"[✅] Finished downloading images for: {query}")
    except Exception as e:
        print(f"[❌] Error downloading {query}: {e}")

# Use ThreadPoolExecutor for parallel downloads
with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
    executor.map(download_images, search_queries)