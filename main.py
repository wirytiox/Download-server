from flask import Flask, request, jsonify
from qbittorrent import Client
import nhentaidownloader
import os
import cbzconversion
import bencodepy #fine i'll do it myself.
import hashlib
import time
import sys
infohash = None
qb=None
app = Flask(__name__)

def get_torrent_hash(torrent_file_path): # 
    try:
        # Read and decode the .torrent file
        with open(torrent_file_path, 'rb') as torrent_file:
            torrent_data = bencodepy.decode(torrent_file.read())

        # Extract the info dictionary
        info = torrent_data[b'info']

        # Calculate the SHA-1 hash of the info dictionary
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

# Torrent download handler with CBZ conversion
def download_torrent_and_convert(url, sessionid, qb_url, qb_username, qb_password):
    global infohash
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
                    
                while torrent_info['completion_date'] is None or torrent_info['completion_date'] == -1:
                    
                    print("Retrying...")
                    time.sleep(0.5)  # Wait before checking again
                    torrent_info = qb.get_torrent(infohash)  # Refresh torrent info

                    cbzconversion.convert_cbz(full_path, CBZ_OUTPUT_DIR)
            except Exception as e:
                print(f"Failed to add torrent to qBittorrent: {e}")
        if error:
            print(f"Download failed with error: {error}")
    print(f"Starting download of torrent file from: {url}")
    nhentaidownloader.downloadH(url, sessionid, callback=callback)          # this down loads the torrent from nhentai. not the folder itself.
    
    
    # i know this is not efficient. it should use threading and so on.
    


@app.route('/download', methods=['POST'])
def handle_download_request():
    data = request.json
    required_keys = ["url", "sessionid", "qbusername", "qbpassword", "qbServer"]

    for key in required_keys:
        if key not in data:
            return jsonify({"error": f"Missing required field: {key}"}), 400

    url = data["url"]
    sessionid = data["sessionid"]
    qb_username = data["qbusername"]
    qb_password = data["qbpassword"]
    qb_server = data["qbServer"]

    if not url.endswith("/download"):
        url = url.rstrip("/") + "/download"

    try:
        download_torrent_and_convert(url, sessionid, qb_server, qb_username, qb_password)
        return jsonify({"message": "Download and CBZ conversion started successfully."}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5050)
