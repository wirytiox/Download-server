import requests
import urllib.parse
import os
import threading

# Function to sanitize the filename
def sanitize_filename(filename):
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, "_")
    return filename.strip()

def downloadH(url, sessionid, save_dir=".", callback=None):
    """
    Downloads a file from the given nhentai URL using the provided session ID
    in a separate thread.

    Args:
        url (str): The URL to download.
        sessionid (str): The session ID for authentication.
        save_dir (str): The directory to save the file. Defaults to the current directory.
        callback (function): Optional callback to execute after download completes.

    Returns:
        None: As the function runs in a thread, results are handled by the callback.
    """
    def _download():
        # Only the sessionid cookie
        cookies = {"sessionid": sessionid}

        # Headers to simulate a browser
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Referer": "https://nhentai.net/",
        }

        try:
            # Send a GET request to download the file
            response = requests.get(url, cookies=cookies, headers=headers, stream=True)

            # Check if the request was successful
            if response.status_code == 200:
                # Get the filename from the Content-Disposition header
                content_disposition = response.headers.get("Content-Disposition", "")
                if "filename*" in content_disposition:
                    filename = urllib.parse.unquote(
                        content_disposition.split("filename*=UTF-8''")[-1]
                    )
                elif "filename=" in content_disposition:
                    filename = content_disposition.split("filename=")[-1].strip('"')
                else:
                    filename = "downloaded_file"

                # Sanitize the filename
                filename = sanitize_filename(filename)
                full_path = os.path.join(save_dir, filename)

                # Save the file
                with open(full_path, "wb") as file:
                    for chunk in response.iter_content(chunk_size=8192):
                        file.write(chunk)

                print(f"File downloaded and saved as: {full_path}")
                if callback:
                    callback(full_path, None)  # Call the callback with success
            else:
                print(f"Failed to download file. Status code: {response.status_code}")
                print(response.text)
                if callback:
                    callback(None, f"Failed with status code {response.status_code}")
        except Exception as e:
            print(f"An error occurred: {e}")
            if callback:
                callback(None, str(e))

    # Run the download process in a separate thread
    thread = threading.Thread(target=_download)
    thread.start()
