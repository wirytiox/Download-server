from flask import Flask, request, jsonify
from qbittorrent import Client
import nhentaidownloader
import os
import cbzconversion
import bencodepy #fine i'll do it myself.
import hashlib
import time
import sys
import re
import requests
import threading
infohash = None
qb=None
app = Flask(__name__)

def get_torrent_hash(torrent_file_path):
    try:
        with open(torrent_file_path, 'rb') as torrent_file:
            torrent_data = bencodepy.decode(torrent_file.read())
        info = torrent_data[b'info']
        info_hash = hashlib.sha1(bencodepy.encode(info)).hexdigest()
        return info_hash
    except Exception as e:
        print(f"Error extracting hash from {torrent_file_path}: {e}")
        return None


# Set the base directory to the script's location
if getattr(sys, 'frozen', False):  # If the application is running as a PyInstaller bundle
    BASE_DIR = os.path.dirname(sys.executable)  # The directory of the bundled executable
else:  # If running as a normal Python script
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TORRENT_DOWNLOAD_DIR = os.path.join(BASE_DIR, "torrents")
CBZ_OUTPUT_DIR = os.path.join(BASE_DIR, "output")

# Ensure directories exist
os.makedirs(TORRENT_DOWNLOAD_DIR, exist_ok=True)
os.makedirs(CBZ_OUTPUT_DIR, exist_ok=True)

# qBittorrent setup
def setup_qbittorrent(qb_url, qb_username, qb_password):
    qb = Client(qb_url)
    qb.login(qb_username, qb_password)
    print("Connected to qBittorrent Web UI.")
    return qb
def run_cbz_conversion(source_path, output_dir):
    """
    Thread target for running CBZ conversion.
    """
    try:
        print(f"Starting CBZ conversion for: {source_path}")
        cbzconversion.convert_cbz(source_path, output_dir)
        print(f"CBZ conversion completed for: {source_path}")
    except Exception as e:
        print(f"Error during CBZ conversion for {source_path}: {e}")
# Torrent download handler with CBZ conversion
def download_torrent_and_convert(url, sessionid, qb_url, qb_username, qb_password):
    global qb
    def callback(file_path, error):
        if file_path:
            torrent_path = file_path if file_path.endswith(".torrent") else f"{file_path}.torrent"
            if not file_path.endswith(".torrent"):
                os.rename(file_path, torrent_path)

            print(f"Download completed successfully: {torrent_path}")
            qb = setup_qbittorrent(qb_url, qb_username, qb_password)
            try:
                with open(torrent_path, "rb") as torrent_file:              # this motherfucker does the real deal, big boi job.
                    qb.download_from_file(
                        torrent_file,
                        savepath=TORRENT_DOWNLOAD_DIR,
                        is_paused=False
                    )
                    
                print("Torrent added to qBittorrent successfully.")
                infohash=get_torrent_hash(torrent_path)
                print(infohash)

                torrent_info = qb.get_torrent(infohash)
                print(torrent_info)
                # Get and print the save path
                if torrent_info:
                    save_path = torrent_info['save_path']  # Base directory where the torrent is saved
                    folder_name = torrent_info['name'] 
                    full_path = f"{save_path}/{folder_name}"
                    print(f"Full Path: {full_path}")
                    
                while torrent_info['completion_date'] == -1:
                    print("Retrying...")
                    time.sleep(0.5)
                    torrent_info = qb.get_torrent(infohash)


                threading.Thread(target=run_cbz_conversion, args=(full_path, CBZ_OUTPUT_DIR)).start()
            except Exception as e:
                print(f"Failed to add torrent to qBittorrent: {e}")
        if error:
            print(f"Download failed with error: {error}")
    print(f"Starting download of torrent file from: {url}")
    nhentaidownloader.downloadH(url, sessionid, callback=callback)          # this down loads the torrent from nhentai. not the folder itself.
    
    
    # i know this is not efficient. it should use threading and so on.
    


@app.route('/download', methods=['POST'])
def handle_download_request():
    try:
        # Parse the incoming JSON data
        data = request.json
        required_keys = ["url", "sessionid", "qbusername", "qbpassword", "qbServer"]

        # Validate required keys
        for key in required_keys:
            if key not in data:
                return jsonify({"error": f"Missing required field: {key}"}), 400

        # Extract data
        url = data["url"]
        sessionid = data["sessionid"]
        qb_username = data["qbusername"]
        qb_password = data["qbpassword"]
        qb_server = data["qbServer"]

        # Ensure URL ends with "/download"
        if not url.endswith("/download"):
            url = url.rstrip("/") + "/download"

        # Call the first process (download and convert)
        threading.Thread(target=download_torrent_and_convert, args=(url, sessionid, qb_server, qb_username, qb_password)).start()




        # Extract the 6-digit gallery ID from the original URL
        match = re.search(r'/g/(\d+)/', data["url"])
        if not match:
            return jsonify({"error": "Invalid URL format. Could not extract gallery ID."}), 400

        gallery_id = match.group(1)

        # Construct the API request URL
        api_request_url = f"https://nhentai.net/api/gallery/{gallery_id}/favorite"

        # Prepare headers and cookies for the nhentai request
        csrf_token = request.headers.get('x-csrftoken')
        if not csrf_token:
            return jsonify({"error": "CSRF token is missing"}), 400

        headers = {
            "accept": "*/*",
            "accept-language": "en-US,en;q=0.8",
            "priority": "u=1, i",
            "sec-ch-ua": "\"Brave\";v=\"131\", \"Chromium\";v=\"131\", \"Not_A Brand\";v=\"24\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Windows\"",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "sec-gpc": "1",
            "x-csrftoken": csrf_token,
            "x-requested-with": "XMLHttpRequest",
            "referer": data["url"]
        }

        cookies = {
            "csrftoken": csrf_token,
            "sessionid": sessionid
        }

        # Make the nhentai API request
        session = requests.Session()
        session.cookies.update(cookies)
        response = session.post(api_request_url, headers=headers)

        # Check and return the nhentai API response
        if response.status_code == 200:
            return jsonify({"message": "Download, conversion, and API request completed successfully.", "response": response.json()}), 200
        else:
            return jsonify({
                "error": "API request failed",
                "status_code": response.status_code,
                "response_text": response.text
            }), response.status_code

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0",debug=True, port=5050,threaded=True)
