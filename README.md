# CiefpIPTVBouquets

A plugin for Enigma2-based set-top boxes (e.g., Dreambox, VU+, etc.) that enables the management and creation of IPTV bouquets. This allows users to easily import and organize IPTV channels into Enigma2's EPG and channel list system.

## Features

- **IPTV Bouquet Creation**: Automatically generates bouquets from IPTV playlists (M3U format).
- **Channel Integration**: Seamlessly integrates IPTV channels into the Enigma2 interface.
- **EPG Support**: Compatible with XMLTV EPG sources for enhanced program guides.
- **Customizable**: Options to filter, sort, and categorize channels based on user preferences.
- **Easy Updates**: Supports remote playlist updates for fresh channel lists.

*(Note: Specific features may vary based on the plugin version. For detailed functionality, refer to the plugin's Python code or in-plugin help.)*

## Requirements

- Enigma2-based receiver (e.g., OpenATV, OpenPLi, BlackHole images).
- Python 2.7 or 3.x (as per Enigma2 environment).
- Internet connection for downloading IPTV playlists.
- Optional: XMLTV EPG provider for full functionality.

No additional Python packages are required beyond the standard Enigma2 environment.

## Installation

1. **Download the Plugin**:
   - Clone this repository or download the ZIP file from GitHub.
   - Extract the contents to a temporary folder on your computer.

2. **Transfer to Receiver**:
   - Use FTP (e.g., FileZilla) to connect to your Enigma2 device.
   - Navigate to `/usr/lib/enigma2/python/Plugins/Extensions/`.
   - Create a new folder named `CiefpIPTVBouquets` if it doesn't exist.
   - Upload all files from the plugin folder (e.g., `plugin.py`, `*.py` files, icons, etc.) into this directory.

3. **Restart Enigma2**:
   - Reboot your receiver or run `init 4 && init 3` via telnet/SSH to reload plugins.
   - The plugin should now appear under **Plugins > Extensions > CiefpIPTVBouquets**.

4. **Alternative via IPK** (if available):
   - If an `.ipk` package is provided in releases, install it via the Enigma2 software manager or Opkg.

## Usage

1. **Launch the Plugin**:
   - Go to **Plugins > Extensions > CiefpIPTVBouquets**.
   - Select **Setup** to configure your IPTV playlist URL and EPG source.

2. **Add IPTV Playlist**:
   - Enter the M3U playlist URL (e.g., from your IPTV provider).
   - Choose options for channel grouping (by category, language, etc.).
   - Click **Download and Create Bouquets**.

3. **Update Bouquets**:
   - Use the **Update** option to refresh channels periodically.
   - Enable auto-update in settings for scheduled refreshes.

4. **EPG Configuration**:
   - Provide an XMLTV URL for EPG data.
   - The plugin will map EPG to channels automatically.

For troubleshooting, check the Enigma2 crash logs if issues arise.

## Configuration Options

- **Playlist URL**: Remote M3U link for channels.
- **EPG URL**: XMLTV source for program guides.
- **Auto-Update Interval**: Set refresh frequency (e.g., daily).
- **Channel Filters**: Exclude adult content, HD only, etc.
- **Bouquet Name**: Customize the main bouquet title.

Access these via the plugin's setup screen.

## Known Issues

- Some playlists may require authentication (username/password support coming soon).
- Large playlists (>5000 channels) may take time to process.
- Compatibility varies by Enigma2 image; test on your setup.

## Contributing

Contributions are welcome! Please fork the repository and submit pull requests for bug fixes or new features.

1. Fork the project.
2. Create a feature branch (`git checkout -b feature/AmazingFeature`).
3. Commit changes (`git commit -m 'Add some AmazingFeature'`).
4. Push to the branch (`git push origin feature/AmazingFeature`).
5. Open a Pull Request.

## License

This project is licensed under the GNU General Public License v3.0 (GPL-3.0) - see the [LICENSE](LICENSE) file for details.

## Support

- Report issues on the [GitHub Issues](https://github.com/ciefp/CiefpIPTVBouquets/issues) page.
- For community help, check Enigma2 forums like openpli.org or dream-elite.net.

## Acknowledgments

- Thanks to the Enigma2 community for the open-source foundation.
- IPTV playlist providers for sample data.

---
