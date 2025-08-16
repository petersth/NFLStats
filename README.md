# NFL Statistics Application

An easy-to-use application for analyzing NFL team statistics and performance metrics.

## Getting the Application

### Option 1: Download ZIP from GitHub (Simplest Start)
1. Download ZIP from GitHub and extract to a folder
2. Run the setup script to enable updates (optional):
   - **Windows**: Double-click `setup.bat`
   - **Mac/Linux**: Double-click `setup.sh`
   - The setup script will offer to enable automatic updates
3. Start the app:
   - **Windows**: Double-click `start.bat`
   - **Mac/Linux**: Double-click `start.sh`

### Option 2: Git Clone (For Technical Users)
If you have Git installed and prefer command line:
```bash
git clone https://github.com/petersth/NFLStats.git Stats
cd Stats
```
This method includes automatic updates from the start.

### What the Setup Script Does
The `setup.bat`/`setup.sh` scripts are smart helpers that:
- **If you downloaded the ZIP**: Offers to convert it to a Git repository for automatic updates
- **If you downloaded just the script**: Downloads the full app with Git enabled
- **If Git is already configured**: Tells you you're all set
- **If Git isn't installed**: Guides you to install it (optional for updates)

## Quick Start

### For Windows Users:
1. Double-click `start.bat` to run the app
   - First time: Will automatically install everything needed
   - Every time: Checks for updates (if cloned with Git) and starts the app
2. Your browser will open automatically

### For Mac/Linux Users:
1. Double-click `start.sh` to run the app
   - If that doesn't work, right-click → Open With → Terminal
   - First time: Will automatically install everything needed
   - Every time: Checks for updates (if cloned with Git) and starts the app
2. Your browser will open automatically

## Prerequisites

### Required:
**Python 3.12** (download from [python.org](https://www.python.org/downloads/))
- **Recommended**: Python 3.12 for best compatibility
- **Known issues**: Python 3.13+ may have dependency issues
- When installing on Windows, check "Add Python to PATH"
- To verify: Open Terminal/Command Prompt and type `python --version`

### Optional (but recommended):
**Git** (download from [git-scm.com](https://git-scm.com/downloads))
- Enables automatic updates when you start the app
- Without Git: App works fine but won't check for updates
- No GitHub account needed for updates (public repository)
- To verify: Open Terminal/Command Prompt and type `git --version`

**Important:** Use standard Git, not GitHub Desktop or GitHub CLI, which may require login

**Note:** The app automatically creates an isolated Python environment (virtual environment) to avoid conflicts with other Python projects on your system

## Manual Installation (Alternative Method)

If the quick start scripts don't work, follow these steps:

### Step 1: Open Terminal/Command Prompt
- **Mac**: Press Cmd+Space, type "Terminal", press Enter
- **Windows**: Press Windows key, type "cmd", press Enter

### Step 2: Navigate to the Application Folder
```bash
cd path/to/Stats
```
Replace `path/to/Stats` with the actual path where you extracted the files.
- **Tip**: Drag and drop the folder into Terminal after typing `cd ` (with a space)

### Step 3: Create Virtual Environment
```bash
python -m venv venv
```

### Step 4: Activate Virtual Environment
**Windows:**
```bash
venv\Scripts\activate
```
**Mac/Linux:**
```bash
source venv/bin/activate
```

### Step 5: Install Required Components
```bash
pip install -r requirements.txt
```

### Step 6: Run the Application
```bash
streamlit run app.py
```

The app will open at `http://localhost:8501` in your browser

## Updating the Application

### Automatic Updates (If Git is configured)
The app **automatically checks for updates** every time you start it.

To enable automatic updates on a ZIP download:
- Run `setup.bat` (Windows) or `setup.sh` (Mac/Linux)
- Choose "Yes" when asked to convert to Git repository

### Manual Update Options

**With Git configured:**
- **Windows**: Double-click `update.bat`
- **Mac/Linux**: Double-click `update.sh`
- **Command line**: `git pull`

**Without Git (ZIP download):**
1. Download the latest ZIP file from GitHub
2. Extract and replace your existing files
3. Keep your `.requirements.hash` and `venv` folder to avoid reinstalling

## Using the Application

1. **Select a Team**: Use the dropdown menu in the sidebar to choose an NFL team
2. **Choose Season**: Select which season's data you want to analyze
3. **View Statistics**: Navigate through different tabs to see various performance metrics
4. **Export Data**: Use the export buttons to save data in different formats

## Troubleshooting

### "Command not found" errors
- Make sure Python is installed and added to your system PATH
- Try using `python3` instead of `python`
- Try using `pip3` instead of `pip`

### Installation fails
- Make sure you have an internet connection
- Try upgrading pip first: `python -m pip install --upgrade pip`
- On Mac, you might need to use: `pip install --user -r requirements.txt`

### Application won't start
- Make sure you're in the correct folder (Stats)
- Check that all files were downloaded/extracted properly
- Try closing and reopening your Terminal/Command Prompt

### Browser doesn't open
- Manually open your browser and go to: `http://localhost:8501`
- If that doesn't work, try: `http://127.0.0.1:8501`

### Data loading issues
- The app needs internet access to download NFL data
- First-time data loading may take a few minutes
- Check your internet connection

## Stopping the Application

To stop the application:
- Press `Ctrl+C` in the Terminal/Command Prompt
- Or simply close the Terminal/Command Prompt window

## Need More Help?

If you encounter issues not covered here, you may need assistance from someone with technical experience or the application developer.