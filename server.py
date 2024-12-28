from flask import Flask, request, jsonify
from flask_cors import CORS  # Import CORS
import asyncio
import re
import requests
import requests
from urllib.parse import urlsplit
import os

import urllib
def sanitize_filename(filename):
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, "_")
    return filename.strip()
app = Flask(__name__)

# Enable CORS for the specific Chrome extension origin
CORS(app)
save_dir="."

@app.route('/fabdownload', methods=['POST'])
async def handle_download_request():
    try:
        # Your existing code here...
        data = request.json

        
        required_keys = ["url", "cookies", "headers"]
        
        # Validate required keys
        for key in required_keys:
            if key not in data:
                return jsonify({"error": f"Missing required field: {key}"}), 400
        
        # Extract data
        url = data["url"]
        cookies = data["cookies"]
        headers = data["headers"]
        csrftoken = cookies.get("csrftoken")
        sessionid = cookies.get("sessionid")
        downloadurl = f"{url}download"
        
        
        cookies2 = {"sessionid": sessionid}

        # Headers to simulate a browser
        headers2 = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Referer": "https://nhentai.net/",
        }

        try:
            # Send a GET request to download the file
            response = requests.get(downloadurl, cookies=cookies2, headers=headers2, stream=True)

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
        except Exception as e:
            print(f"An error occurred: {e}")

        
        
        
        
        
        
        
        
        
        # Extract the 6-digit gallery ID from the original URL
        match = re.search(r'/g/(\d+)/', url)
        if not match:
            return jsonify({"error": "Invalid URL format. Could not extract gallery ID."}), 400

        gallery_id = match.group(1)

        # Construct the API request URL
        api_request_url = f"https://nhentai.net/api/gallery/{gallery_id}/favorite"

        # Ensure CSRF token is present
        if not csrftoken:
            return jsonify({"error": "CSRF token is missing"}), 400

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
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=True, port=9998, threaded=True)
