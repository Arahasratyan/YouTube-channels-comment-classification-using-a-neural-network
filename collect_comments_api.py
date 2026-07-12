import os
import re
import time
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

API_KEY = "Your API code"

youtube = build("youtube", "v3", developerKey=API_KEY)


QUOTA_USED = 0
DAILY_QUOTA_LIMIT = 10_000


def extract_video_id(url):
    pattern = r"(?:v=|\/v\/|youtu\.be\/|\/embed\/)([a-zA-Z0-9_-]{11})"
    match = re.search(pattern, url)
    return match.group(1) if match else None


def get_video_comments(video_id):
    global QUOTA_USED
    comments = []
    next_page_token = None

    while QUOTA_USED < DAILY_QUOTA_LIMIT:
        try:
            request = youtube.commentThreads().list(
                part="snippet",
                videoId=video_id,
                maxResults=100,
                pageToken=next_page_token,
                textFormat="plainText",
            )
            response = request.execute()
            QUOTA_USED += 1

        except HttpError as e:
            if e.resp.status == 403 and "quotaExceeded" in str(e):
                print("No more quota left")
                exit()
            else:
                print(f"API Error with video {video_id}: {e}")
                break

        except (TimeoutError, Exception) as e:
            print(f"Network error, Timeout occurred for video {video_id}. Skipping remaining comments. Error: {e}")
            break

        for item in response.get("items", []):
            snippet = item["snippet"]["topLevelComment"]["snippet"]
            comment_text = snippet["textDisplay"]
            # Keep it to one single row by replacing newlines with spaces
            comment_text = comment_text.replace("\r\n", " ").replace("\n", " ")
            comments.append(comment_text)

        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break

        time.sleep(0.1)

    return comments

def save_comments_to_txt(comments, folder_name, video_id, ):
    if not comments:
        return

    os.makedirs(folder_name, exist_ok=True)

    filename = os.path.join(folder_name, f"{video_id}.txt")

    with open(filename, "w", encoding="utf-8") as txtfile:
        for comment in comments:
            txtfile.write(comment + "\n")

    #print(f"Saved {len(comments)} comments to {filename}")


def process_multiple_videos(video_urls, folder_name):
    global QUOTA_USED

    for url in video_urls:
        video_id = extract_video_id(url)
        if not video_id:
            print(f"Couldn't process URL: {url}")
            continue

        print(
            f"Getting comments for video: {video_id} (Quota: {QUOTA_USED}/{DAILY_QUOTA_LIMIT})"
        )
        comments = get_video_comments(video_id)
        comments.sort(key=len)
        save_comments_to_txt(comments, folder_name, video_id)


        if QUOTA_USED >= DAILY_QUOTA_LIMIT:
            print("No more quota left")
            break


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

    print(f"\nDone. Total used quota: {QUOTA_USED}")
