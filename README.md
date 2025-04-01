# get_pixiv
A Python-based Pixiv artwork downloader (v1.03). Search by user ID or artwork URL, download all images, specific pages, or single artworks.

## Requirements
1. **Install Python**: Download from [python.org](https://www.python.org/). Check "Add to PATH" during installation.
2. **Install Google Chrome**: Get it from [google.com/chrome/](https://www.google.com/chrome/).

## Option 1: Running from Source (GitHub Open-Source)
For developers or those who want to run the Python script directly.

1. **Create a Virtual Environment**:
   - Open a terminal in the project folder.
   - Run:
     ```
     python -m venv venv
     ```
   - Activate it:
     - Windows: `venv\Scripts\activate`
     - macOS/Linux: `source venv/bin/activate`

2. **Install Dependencies**:
   - Run:
     ```
     pip install -r requirements.txt
     ```

3. **Run the App**:
   - Run:
     ```
     python get_pixiv.py
     ```

## Option 2: Running the EXE (End-User)
For users who just want to download artworks without setup.

1. **Run the App**:
   - Double-click `get_pixiv.exe` (download from [Releases](https://github.com/kakao90g/get_pixiv/releases)).
   - **Note: Microsoft Defender SmartScreen**: If you see a warning:
     1. Click "More info".
     2. Click "Run anyway".
     This is a new app—safe, open-source, and submitted for Microsoft review.

## Usage
- **Cookies**: Paste your Pixiv cookies into "Cookie String" and click "Save Cookies".
- **Search**: Enter a User ID and click "Search".
- **Download**: 
  - "Download All" or "Download Page": Saves to `pixiv_images/pixiv_[user_id]_images/`.
  - "Download URL" (e.g., `https://www.pixiv.net/en/artworks/12345678`): Saves to `pixiv_images/pixiv_artwork_[artwork_id]_images/` (e.g., `pixiv_artwork_12345678_images`).
- **Options**: Enable "Show browser" to view real-time automation progress.

## Support the Developer
If you enjoy get_pixiv, please consider donating at [https://paypal.me/kakao90g](https://paypal.me/kakao90g). This keeps the project alive—don’t remove this link!

## Changelog
- **v1.03 (2025-04-02)**:
  - Added: "Verify Cookie" feature to accurately detect login state.
  - Removed: Cookie authentication on startup for simpler setup.
  - Changed: Browser no longer auto-restarts on close, enabling graceful exits.
  - Improved: "About" window now uses custom dialogs.
  - Added: "Check for Updates" in About window with universal `updater.exe` for auto-fetching latest releases from GitHub.
  - Improved: App window now opens in the upper-right corner of the screen.
- **v1.02 (2025-03-27)**:
  - Added: "Show Browser" toggle now reuses the open browser instance instead of restarting.
  - Changed: "Download URL" saves to `pixiv_images/pixiv_artwork_[artwork_id]_images/` (e.g., `pixiv_artwork_12345678_images`).
  - Improved: Increased log window width to fit longer folder names.
  - Improved: Silenced noisy WebDriver logs in "Download All" and "Download Page" for cleaner output.
- **v1.01 (2025-03-26)**:
  - Fixed: First artwork in "Download All" now detects all pages via Preview div.
  - Improved: Removed noisy `og:image` logs.
- **v1.00 (2025-03-25)**:
  - Initial release with user ID and URL-based downloading.

## License
MIT License—see [LICENSE](LICENSE) file.

## Credits
© 2025 @kakao90g