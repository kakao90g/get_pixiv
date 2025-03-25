# get_pixiv
A Python-based Pixiv artwork downloader (v1.00). Search by user ID or artwork URL, download all images, specific pages, or single artworks.

## Requirements
1. **Install Python**: Download from [python.org](https://www.python.org/). Check "Add to PATH" during installation.
2. **Install Google Chrome**: Get it from [google.com/chrome/](https://www.google.com/chrome/).

## Option 1: Running from Source (GitHub Open-Source)
For developers or those who want to run the Python script directly.

3. **Create a Virtual Environment**:
   - Open a terminal in the project folder.
   - Run:
     ```
     python -m venv venv
     ```
   - Activate it:
     - Windows: `venv\Scripts\activate`
     - macOS/Linux: `source venv/bin/activate`

4. **Install Dependencies**:
   - Run:
     ```
     pip install -r requirements.txt
     ```

5. **Run the App**:
   - Run:
     ```
     python get_pixiv.py
     ```

## Option 2: Running the EXE (End-User)
For users who just want to download artworks without setup.

3. **Run the App**:
   - Double-click `get_pixiv.exe` (download from [Releases](https://github.com/kakao90g/get_pixiv/releases)).

## Usage
- **Cookies**: Paste your Pixiv cookies into "Cookie String" and click "Save Cookies".
- **Search**: Enter a User ID and click "Search".
- **Download**: Use "Download All", "Download Page", or "Download URL" (e.g., `https://www.pixiv.net/en/artworks/12345678`).
- Images save to `pixiv_images/pixiv_[user_id]_images/`.

## Support the Developer
If you enjoy get_pixiv, please consider donating at [https://paypal.me/kakao90g](https://paypal.me/kakao90g). This keeps the project alive—don’t remove this link!

## License
MIT License—see [LICENSE](LICENSE) file.

## Credits
© 2025 @kakao90g