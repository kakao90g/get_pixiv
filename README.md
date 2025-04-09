# get_pixiv
A Python-based Pixiv artwork downloader (v1.04). Search by user ID or artwork URL to grab all images, specific pages, or single artworks with ease.

## Requirements
1. **Install Python**: Get it from [python.org](https://www.python.org/) and check "Add to PATH" during installation.
2. **Install Google Chrome**: Download from [google.com/chrome/](https://www.google.com/chrome/).

## Option 1: Running from Source (GitHub Open-Source)
For developers or anyone wanting to run the Python script directly.

1. **Create a Virtual Environment**:
   - Open a terminal in the project folder and run:
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
   - *Note*: `updater.py` is included for building `updater.exe`—compile with `pyinstaller --onefile --noconsole updater.py`.

## Option 2: Running the EXE (End-User)
For users who just want to download artworks without any setup.

1. **Run the App**:
   - Double-click `get_pixiv.exe` (download from [Releases](https://github.com/kakao90g/get_pixiv/releases)).
   - **Note**: If Microsoft Defender SmartScreen warns you:
     1. Click "More info".
     2. Click "Run anyway".
     - This is a new, safe, open-source app submitted for Microsoft review.

## Usage
- **Cookies**: Paste your Pixiv cookies into "Cookie String" and click "Save Cookies" (use "Verify Cookie" to confirm login).
- **Search**: Enter a User ID and click "Search".
- **Download**: 
  - "Download All" or "Download Page": Saves to `pixiv_images/pixiv_[user_id]_images/`.
  - "Download URL" (e.g., `https://www.pixiv.net/en/artworks/12345678` or `https://www.pixiv.net/artworks/12345678`): Saves to `pixiv_images/pixiv_artwork_[artwork_id]_images/` (e.g., `pixiv_artwork_12345678_images`).
- **Options**: 
  - Enable "Show browser" to watch automation in real time.
  - Use "Check for Updates" in the About window to fetch the latest version via `updater.exe`.

## Support the Developer
Love get_pixiv? Consider donating at [https://paypal.me/kakao90g](https://paypal.me/kakao90g) to keep this project alive—please don’t remove this link!

## Changelog
- **v1.04 (2025-04-10)**:
  - Added: Navigation keywords for Japanese site when user’s account language is Japanese.
  - Added: Support for Japanese URL structure (e.g., `https://www.pixiv.net/artworks/12345678`) in "Download URL".
  - Changed: UI text from "Artworks" to "Illustration and Manga" for consistency.
- **v1.03 (2025-04-02)**:
  - Added: "Verify Cookie" feature to accurately detect login state.
  - Removed: Cookie authentication on startup for simpler setup.
  - Changed: Browser now exits gracefully without auto-restart on close.
  - Improved: "About" window upgraded to custom dialogs.
  - Added: "Check for Updates" in About window with `updater.exe` for auto-fetching latest GitHub releases.
  - Improved: App window now opens in the upper-right corner.
- **v1.02 (2025-03-27)**:
  - Added: "Show Browser" toggle reuses the open browser instance.
  - Changed: "Download URL" saves to `pixiv_images/pixiv_artwork_[artwork_id]_images/` (e.g., `pixiv_artwork_12345678_images`).
  - Improved: Wider log window for longer folder names.
  - Improved: Cleaner WebDriver logs in "Download All" and "Download Page".
- **v1.01 (2025-03-26)**:
  - Fixed: "Download All" now detects all pages via Preview div.
  - Improved: Removed noisy `og:image` logs.
- **v1.00 (2025-03-25)**:
  - Initial release with user ID and URL-based downloading.

## License
MIT License—see [LICENSE](LICENSE) file.

## Credits
© 2025 @kakao90g