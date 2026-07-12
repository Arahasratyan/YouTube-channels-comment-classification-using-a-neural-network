#pip install yt_dlp
import os
import re
import time
import yt_dlp


def extract_video_id(url):
    pattern = r"(?:v=|\/v\/|youtu\.be\/|\/embed\/)([a-zA-Z0-9_-]{11})"
    match = re.search(pattern, url)
    return match.group(1) if match else None


def get_video_comments(url, video_id):
    comments = []
    

    ydl_opts = {
        'get_comments': True,
        'skip_download': True,
        'quiet': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extract video info dictionary
            info_dict = ydl.extract_info(url, download=False)
            
            # Fetch comments from the extracted info dictionary
            extracted_comments = info_dict.get('comments', [])
            
            for comment_obj in extracted_comments:
                comment_text = comment_obj.get('text')
                if comment_text:
                    # Keep it to one single row by replacing newlines with spaces
                    comment_text = comment_text.replace("\r\n", " ").replace("\n", " ")
                    comments.append(comment_text)

    except yt_dlp.utils.DownloadError as e:
        print(f"yt_dlp error with video {video_id}: {e}")
    except (TimeoutError, Exception) as e:
        print(f"Network error or timeout occurred for video {video_id}. Skipping. Error: {e}")

    return comments


def save_comments_to_txt(comments, folder_name, video_id):
    if not comments:
        return

    os.makedirs(folder_name, exist_ok=True)
    filename = os.path.join(folder_name, f"{video_id}.txt")

    with open(filename, "w", encoding="utf-8") as txtfile:
        for comment in comments:
            txtfile.write(comment + "\n")


def process_multiple_videos(video_urls, folder_name):
    for url in video_urls:
        video_id = extract_video_id(url)
        if not video_id:
            print(f"Couldn't process URL: {url}")
            continue

        print(f"Getting comments for video: {video_id}")
        
        comments = get_video_comments(url, video_id)
        comments.sort(key=len)
        save_comments_to_txt(comments, folder_name, video_id)
        
        # Polite delay to prevent aggressive rate limiting from YouTube
        time.sleep(1) 


if __name__ == "__main__":
    Vsauce_4_random = [
        "https://youtu.be/mMaBVfIedFw",
        "https://youtu.be/vjqt8T3tJIE",
        "https://youtu.be/s86-Z-CbaHA",
        "https://youtu.be/VNqNnUJVcVs",
    ]

    
    Veritasium_4_random = [
        "https://www.youtube.com/watch?v=AeJ9q45PfD0",
        "https://www.youtube.com/watch?v=w5ebcowAJD8",
        "https://www.youtube.com/watch?v=6akmv1bsz1M",
        "https://www.youtube.com/watch?v=SC2eSujzrUY",
    ]

    process_multiple_videos(Vsauce_4_random, folder_name="Vsauce")
    process_multiple_videos(Veritasium_4_random, folder_name="Veritasium")

    print("\nDone. All processing complete.")
