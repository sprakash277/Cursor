# Contest Scoring System

A modern web application for judges to enter scoring for contestants. The system automatically loads contestants and contest types from an Excel file.

## Features

- 📊 Load contestants from Excel file automatically
- 🎯 Easy-to-use scoring interface for judges
- 📈 Real-time results and rankings
- 💾 Persistent score storage (JSON file)
- 🎨 Modern, responsive UI
- 👥 Support for multiple judges per contestant

## Setup

1. **Install dependencies:**
   ```bash
   cd scoring_app
   pip3 install -r requirements.txt
   ```
   
   **Note:** On macOS, use `pip3` instead of `pip`. If you encounter network errors, check your internet connection and try again.

2. **Configure Excel file path:**
   - The app is configured to read from `/Users/sumit.prakash/Downloads/sanskriti-2.xlsx`
   - You can modify the `EXCEL_FILE_PATH` in `app.py` if needed

3. **Run the application:**
   ```bash
   python3 app.py
   ```
   
   Or use the run script:
   ```bash
   ./run.sh
   ```

4. **Access the application:**
   - Open your browser and go to `http://localhost:5000`

## How It Works

1. **Contest Type Detection:**
   - The app reads the "Order items" column from the Excel file
   - It automatically extracts contest names and maps them to standardized contest names
   - Each participant-contest combination is treated as a separate entry
   - Contestants are grouped by their contest type on the home page

2. **Standardized Contest Names:**
   - The app uses a predefined list of 29 standardized contest names
   - Order items from Excel are automatically mapped to these standardized names
   - If a participant is in multiple contests, they appear as separate entries for each contest

3. **Scoring:**
   - Judges can click on any contestant to enter scores
   - Each judge can submit one score per contestant-contest combination (updates if resubmitted)
   - Scores are stored with judge name, score value, comments, and timestamp

4. **Results:**
   - View all results sorted by average score
   - See detailed breakdown of scores from all judges
   - Rankings are automatically calculated per contest type

## File Structure

```
scoring_app/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── scores.json           # Score storage (created automatically)
├── templates/
│   ├── base.html         # Base template
│   ├── index.html        # Home page (contestants list)
│   ├── score.html        # Scoring form
│   └── results.html      # Results page
└── static/
    ├── css/
    │   └── style.css       # Modern styling
    └── js/
        └── main.js        # JavaScript functionality
```

## Notes

- Scores are stored in `scores.json` in the same directory as `app.py`
- The Excel file is read on each page load, so you can update the Excel file and refresh to see changes
- Make sure the Excel file has at least one column that can be identified as contest type (order/item column)
