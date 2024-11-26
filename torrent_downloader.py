from qbittorrent import Client
import nhentaidownloader
import os

class TorrentDownloader:
    def __init__(self, qb_url="http://localhost:8081/", qb_username="admin", qb_password="adminadmin", default_savepath="C:\\downloads"):
        """
        Initialize the TorrentDownloader with qBittorrent connection details and default save path.
        Args:
            qb_url (str): The URL of the qBittorrent Web UI.
            qb_username (str): The username for qBittorrent.
            qb_password (str): The password for qBittorrent.
            default_savepath (str): Default save path for downloaded files.
        """
        self.qb_url = qb_url
        self.qb_username = qb_username
        self.qb_password = qb_password
        self.default_savepath = default_savepath

    def setup_qbittorrent(self):
        """
        Connect to the qBittorrent Web UI and authenticate.
        Returns:
            qb (Client): Authenticated qBittorrent Client instance.
        """
        qb = Client(self.qb_url)
        qb.login(self.qb_username, self.qb_password)
        print("Connected to qBittorrent Web UI.")
        return qb

    def download_torrent(self, url, sessionid, savepath=None):
        """
        Download a .torrent file from the specified URL and add it to qBittorrent for download.
        Args:
            url (str): URL to download the .torrent file.
            sessionid (str): Session ID for authentication.
            savepath (str): Optional custom save path for the downloaded content.
        """
        if savepath is None:
            savepath = self.default_savepath

        def callback(file_path, error):
            if file_path:
                print(f"Download completed successfully: {file_path}")
                qb = self.setup_qbittorrent()
                try:
                    with open(file_path, "rb") as torrent_file:
                        qb.download_from_file(torrent_file, savepath=savepath)
                    print("Torrent added to qBittorrent successfully.")
                except Exception as e:
                    print(f"Failed to add torrent to qBittorrent: {e}")
            if error:
                print(f"Download failed with error: {error}")

        print(f"Starting download of torrent file from: {url}")
        nhentaidownloader.downloadH(url, sessionid, callback=callback)

    def monitor_torrents(self):
        """
        Monitor active torrents in qBittorrent and display their progress.
        """
        qb = self.setup_qbittorrent()
        torrents = qb.torrents()
        if not torrents:
            print("No active torrents.")
        else:
            for torrent in torrents:
                print("Torrent Name:", torrent["name"])
                print("Progress:", f"{torrent['progress'] * 100:.2f}%")
                print("Download Speed:", f"{torrent['dlspeed'] / 1024:.2f} KB/s")
