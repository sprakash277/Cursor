"""
Flask application for judges to enter scoring for contestants
"""
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from jinja2 import Environment
from functools import wraps
import pandas as pd
import os
from datetime import datetime
import json
import hashlib

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Add Jinja2 filter for normalizing contest names in templates
@app.template_filter('normalize_contest')
def normalize_contest_filter(contest_name):
    """Jinja2 filter to normalize contest names in templates"""
    return normalize_contest_name(contest_name) if contest_name else contest_name

# Configuration
UPLOAD_FOLDER = 'uploads'
EXCEL_FILE_PATH = '/Users/sumit.prakash/Downloads/sanskriti-3.xlsx'
SCORES_FILE = 'scores.json'
JUDGES_FILE = 'judges.json'
WALKIN_PARTICIPANTS_FILE = 'walkin_participants.json'
PARTICIPANTS_MANAGEMENT_FILE = 'participants_management.json'
SPEECH_TOPICS_FILE = 'speech_topics.json'

# Ensure uploads directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Standardized contest names
STANDARD_CONTESTS = [
    "Instrument Playing Contest",
    "Prepared Speech Group",
    "Prepared speech Group",
    "Presentation",
    "Impromptu",
    "Fancy Dress",
    "Yoga",
    "Coloring",
    "Drawing",
    "Chalk Art",
    "Math",
    "SANSKRITI QUIZ",
    "IQ",
    "SUDOKU",
    "Carrom",
    "Chess",
    "Dance Classical",
    "Dance Classical solo",
    "Dance Classical Solo",
    "Singing Classical Solo",
    "Prepared Speech hindi",
    "Prepared speech (Gujarati)",
    "Prepared speech (Telugu)",
    "Singing classical group",
    "Singing Lite Solo",
    "Singing Lite group",
    "Folk Dance (Group) Contest",
    "Folk Dance (Solo) Contest",
    "Rangoli Contest",
    "Unknown Contest"  # Fallback for unmapped contests
]

# Mapping from Excel order items to standardized contest names
def map_order_item_to_contest(order_item):
    """Map order item text to standardized contest name"""
    if pd.isna(order_item) or not order_item:
        return None
    
    order_item_lower = str(order_item).lower().strip()
    
    # Remove common prefixes like "1 x", "2 x", etc.
    import re
    order_item_lower = re.sub(r'^\d+\s*x\s*', '', order_item_lower)
    
    # Mapping rules based on common patterns in Excel
    # Order matters - more specific matches first
    mappings = [
        # Instrument
        ('instrument playing contest', 'Instrument Playing Contest'),
        ('instrument playing', 'Instrument Playing Contest'),
        ('instrument', 'Instrument Playing Contest'),
        
        # Prepared Speech variations - more specific first
        ('prepared speech hindi', 'Prepared Speech hindi'),
        ('prepared speech (hindi)', 'Prepared Speech hindi'),
        ('prepared speech gujarati', 'Prepared speech (Gujarati)'),
        ('prepared speech (gujarati)', 'Prepared speech (Gujarati)'),
        ('prepared speech telugu', 'Prepared speech (Telugu)'),
        ('prepared speech (telugu)', 'Prepared speech (Telugu)'),
        ('prepared speech group 1 & 2', 'Prepared Speech Group'),
        ('prepared speech grp 1 & 2', 'Prepared Speech Group'),
        ('prepared speech group 1 and 2', 'Prepared Speech Group'),
        ('prepared speech grp 3 & 4', 'Prepared speech Group'),
        ('prepared speech group 3 & 4', 'Prepared speech Group'),
        ('prepared speech group 3 and 4', 'Prepared speech Group'),
        ('prepared speech group', 'Prepared Speech Group'),  # Default for capitalized
        ('prepared speech', 'Prepared Speech Group'),  # Default fallback
        
        # Presentation
        ('presentation', 'Presentation'),
        
        # Impromptu
        ('impromptu speech', 'Impromptu'),
        ('impromptu', 'Impromptu'),
        
        # Fancy Dress
        ('fancy dress', 'Fancy Dress'),
        
        # Yoga
        ('yoga', 'Yoga'),
        
        # Coloring
        ('coloring', 'Coloring'),
        
        # Drawing
        ('drawing/painting', 'Drawing'),
        ('drawing', 'Drawing'),
        ('painting', 'Drawing'),
        
        # Chalk Art
        ('chalk art', 'Chalk Art'),
        
        # Math
        ('math quiz', 'Math'),
        ('math', 'Math'),
        ('mathematics', 'Math'),
        
        # SANSKRITI QUIZ
        ('sanskriti quiz', 'SANSKRITI QUIZ'),
        ('sanskriti', 'SANSKRITI QUIZ'),
        
        # IQ
        ('iq', 'IQ'),
        ('iq contest', 'IQ'),
        
        # SUDOKU
        ('sudoko', 'SUDOKU'),  # Common misspelling
        ('sudoku', 'SUDOKU'),
        
        # Rangoli Contest - must come before Carrom to match "Rangoli Contest (inc. Nihira carrom)"
        ('rangoli contest (inc. nihira carrom)', 'Rangoli Contest'),
        ('rangoli contest inc. nihira carrom', 'Rangoli Contest'),
        ('rangoli contest (inc nihira carrom)', 'Rangoli Contest'),
        ('rangoli contest inc nihira carrom', 'Rangoli Contest'),
        ('rangoli contest', 'Rangoli Contest'),
        ('rangoli', 'Rangoli Contest'),
        
        # Carrom
        ('carrom', 'Carrom'),
        
        # Chess - simplified to just "Chess"
        ('chess group 1', 'Chess'),
        ('chess group 2', 'Chess'),
        ('chess (group 1)', 'Chess'),
        ('chess (group 2)', 'Chess'),
        ('chess', 'Chess'),  # Default fallback
        
        # Folk Dance variations - must come before general dance mappings
        ('dance solo (folk)', 'Folk Dance (Solo) Contest'),
        ('dance solo folk', 'Folk Dance (Solo) Contest'),
        ('dance group (folk)', 'Folk Dance (Group) Contest'),
        ('dance group folk', 'Folk Dance (Group) Contest'),
        ('folk dance (group)', 'Folk Dance (Group) Contest'),
        ('folk dance group', 'Folk Dance (Group) Contest'),
        ('folk dance (solo)', 'Folk Dance (Solo) Contest'),
        ('folk dance solo', 'Folk Dance (Solo) Contest'),
        ('folk dance', 'Folk Dance (Group) Contest'),  # Default fallback
        
        # Dance variations - simplified to "Dance Classical", "Dance Classical solo", "Dance Classical Solo"
        # Order matters: more specific matches first
        # Match "Dance Classical Solo" (capital S) - typically for Group 2 & 4
        ('dance classical solo - group 2 & 4', 'Dance Classical Solo'),
        ('dance classical solo - grp 2 & 4', 'Dance Classical Solo'),
        ('dance classical solo group 2 & 4', 'Dance Classical Solo'),
        ('dance classical solo grp 2 & 4', 'Dance Classical Solo'),
        ('dance classical solo group 2 and 4', 'Dance Classical Solo'),
        ('dance classical solo - group 2', 'Dance Classical Solo'),
        ('dance classical solo - grp 2', 'Dance Classical Solo'),
        # Match "Dance Classical solo" (lowercase s) - typically for Group 1 & 3
        ('dance classical solo - group 1 & 3', 'Dance Classical solo'),
        ('dance classical solo - grp 1 & 3', 'Dance Classical solo'),
        ('dance classical solo group 1 & 3', 'Dance Classical solo'),
        ('dance classical solo grp 1 & 3', 'Dance Classical solo'),
        ('dance classical solo group 1 and 3', 'Dance Classical solo'),
        ('dance classical solo - group 1', 'Dance Classical solo'),
        ('dance classical solo - grp 1', 'Dance Classical solo'),
        ('dance classical solo -', 'Dance Classical solo'),  # Default for solo with dash
        ('dance classical solo', 'Dance Classical solo'),  # Default for solo
        ('dance solo (classical)', 'Dance Classical solo'),
        ('dance solo classical', 'Dance Classical solo'),
        ('dance solo', 'Dance Classical solo'),  # Default for dance solo
        ('classical solo dance', 'Dance Classical solo'),  # Default fallback
        # Match general "Dance Classical" last
        ('dance classical', 'Dance Classical'),
        ('dance group (classical)', 'Dance Classical'),
        ('dance group classical', 'Dance Classical'),
        ('dance class group', 'Dance Classical'),
        ('dance class group grp', 'Dance Classical'),
        ('dance class group group', 'Dance Classical'),
        
        # Singing variations - Classical Solo - simplified to "Singing Classical Solo"
        ('singing classical solo group', 'Singing Classical Solo'),
        ('singing classical solo grp', 'Singing Classical Solo'),
        ('singing solo contest (classical)', 'Singing Classical Solo'),
        ('singing solo contest classical', 'Singing Classical Solo'),
        ('singing classical solo', 'Singing Classical Solo'),  # Default fallback
        
        # Singing variations - Classical Group - simplified to "Singing classical group"
        ('singing classical group', 'Singing classical group'),
        ('singing classical group (group', 'Singing classical group'),
        ('singing classical group group', 'Singing classical group'),
        ('singing classical group grp', 'Singing classical group'),
        ('singing group (bhajan/devotional)', 'Singing classical group'),
        ('singing group bhajan', 'Singing classical group'),
        ('singing group devotional', 'Singing classical group'),
        ('singing group (classical)', 'Singing classical group'),  # Default fallback
        
        # Singing variations - Lite Solo - simplified to "Singing Lite Solo"
        ('singing lite solo', 'Singing Lite Solo'),
        ('singing lite solo-', 'Singing Lite Solo'),
        ('singing lite solo group', 'Singing Lite Solo'),
        ('singing lite solo grp', 'Singing Lite Solo'),
        ('singing lite solo- (group', 'Singing Lite Solo'),
        ('singing lite solo- (grp', 'Singing Lite Solo'),
        ('singing lite solo- group', 'Singing Lite Solo'),
        ('singing lite solo- grp', 'Singing Lite Solo'),
        ('singing lite solo', 'Singing Lite Solo'),  # Default fallback
        
        # Singing variations - Lite Group - simplified to "Singing Lite group"
        ('singing lite group', 'Singing Lite group'),
        ('group singing lite', 'Singing Lite group'),
        ('group singing lite group singing', 'Singing Lite group'),
        ('group singing lite group singing-', 'Singing Lite group'),
        ('singing group (lite music)', 'Singing Lite group'),  # Default fallback
    ]
    
    # Try to match order item to standardized contest
    for key, contest_name in mappings:
        if key in order_item_lower:
            return contest_name
    
    # If no match found, try to extract contest name from order item format
    # Format is usually: "On-Stage Solo Contests - Contest Name" or "Off- Stage Contest - Contest Name"
    match = re.search(r'(?:contest|contests)\s*-\s*([^\n]+)', order_item_lower, re.IGNORECASE)
    if match:
        extracted = match.group(1).strip()
        # Try to match extracted name to standardized contests
        for contest in STANDARD_CONTESTS:
            if extracted.lower() in contest.lower() or contest.lower() in extracted.lower():
                return contest
        # Try fuzzy matching with the mappings again on the extracted text
        extracted_lower = extracted.lower()
        for key, contest_name in mappings:
            if key in extracted_lower:
                return contest_name
    
    # Last resort: try to find any keyword match in STANDARD_CONTESTS
    for contest in STANDARD_CONTESTS:
        contest_lower = contest.lower()
        # Check if any significant word from order_item appears in contest name
        words = [w for w in order_item_lower.split() if len(w) > 3]  # Words longer than 3 chars
        for word in words:
            if word in contest_lower:
                return contest
    
    return None

def extract_contests_from_order_items(order_items_text):
    """Extract all contest names from order items column"""
    if pd.isna(order_items_text) or not order_items_text:
        return []
    
    contests = []
    # Split by newlines to get individual contest entries
    items = str(order_items_text).split('\n')
    
    for item in items:
        item = item.strip()
        if not item or 'accompanying guest' in item.lower() or 'parent' in item.lower():
            continue  # Skip non-contest items
        
        contest = map_order_item_to_contest(item)
        if contest and contest not in contests:
            contests.append(contest)
    
    return contests

def normalize_contest_name(contest_name):
    """
    Centralized function to normalize contest names consistently across all pages.
    Handles:
    - "Instrument" -> "Instrument Playing Contest"
    - "Rangoli Contest (inc. Nihira carrom)" -> "Rangoli Contest"
    - Appends " Contest" if not present (except for specific cases)
    """
    if not contest_name:
        return contest_name
    
    contest_name = str(contest_name).strip()
    contest_name_lower = contest_name.lower()
    
    # Normalize specific contest name variations
    if contest_name == 'Instrument' or contest_name_lower == 'instrument':
        return 'Instrument Playing Contest'
    if 'instrument playing contest' in contest_name_lower:
        return 'Instrument Playing Contest'
    
    if 'rangoli contest (inc. nihira carrom)' in contest_name_lower or 'rangoli contest (inc nihira carrom)' in contest_name_lower:
        return 'Rangoli Contest'
    
    # Append " Contest" if not already in the name (but not for contests that already have it or specific exceptions)
    if 'contest' not in contest_name_lower:
        contest_name = contest_name + ' Contest'
    
    return contest_name

def extract_group_number(age_group):
    """Extract group number from age group string (e.g., 'Group 1: 5-7 yrs' -> 1)"""
    if not age_group:
        return None
    
    import re
    match = re.search(r'group\s*(\d+)', str(age_group).lower())
    if match:
        return int(match.group(1))
    return None

def assign_age_group_from_age(age):
    """Auto-assign age group based on age (as of Jan 23rd, 2026)"""
    if age is None:
        return None
    
    try:
        age_int = int(age)
        if age_int < 5:
            return "Group 0: Below 5 yrs"
        elif 5 <= age_int <= 7:
            return "Group 1: 5-7 yrs"
        elif 8 <= age_int <= 10:
            return "Group 2: 8-10 yrs"
        elif 11 <= age_int <= 14:
            return "Group 3: 11-14 yrs"
        elif 15 <= age_int <= 18:
            return "Group 4: 15-18 yrs"
        else:
            return "Group 4: 15-18 yrs"  # Default for ages above 18
    except (ValueError, TypeError):
        return None

def group_number_to_letter(group_num):
    """Convert group number to letter (1 -> A, 2 -> B, 3 -> C, etc.)"""
    if group_num is None:
        return 'Z'  # Default for unknown groups
    
    if 1 <= group_num <= 26:
        return chr(64 + group_num)  # A=65, B=66, etc.
    # For groups beyond 26, use AA, AB, etc.
    if group_num > 26:
        first_letter = chr(64 + ((group_num - 1) // 26))
        second_letter = chr(64 + ((group_num - 1) % 26) + 1)
        return first_letter + second_letter
    return 'Z'

def is_group_contest(contest_type):
    """Check if contest type is a group contest (multiple participants performing together)"""
    if not contest_type:
        return False
    contest_lower = str(contest_type).lower()
    
    # Check for explicit group contest indicators
    group_indicators = [
        'dance class group',
        'singing class group',
        'singing classical group',
        'group singing',
        'singing group'
    ]
    
    # If it contains a group indicator, it's a group contest
    for indicator in group_indicators:
        if indicator in contest_lower:
            return True
    
    # If it says "solo", it's NOT a group contest (even if it mentions age groups)
    if 'solo' in contest_lower:
        return False
    
    # Check for "group" or "grp" but exclude age group references in solo contests
    # Age groups are typically "Group 1 & 2", "Grp 3 & 4", etc. in solo contests
    if 'group' in contest_lower or 'grp' in contest_lower:
        # If it's a prepared speech, chess, or other non-performance contest with group/grp,
        # it's referring to age groups, not a group contest
        if any(keyword in contest_lower for keyword in ['prepared speech', 'chess', 'carrom', 'math', 'quiz', 'iq', 'sudoku']):
            return False
        # Otherwise, if it has group/grp and is not solo, it's likely a group contest
        return True
    
    return False

def assign_participant_ids(contestants):
    """Assign IDs to contestants based on age group and contest type, sorted by participant ID.
    Walk-in participants are appended with auto-incremented IDs from the last value in their group."""
    # Separate walk-in and regular participants
    walkin_contestants = [c for c in contestants if c.get('is_walkin', False)]
    regular_contestants = [c for c in contestants if not c.get('is_walkin', False)]
    
    # Group contestants by contest type and age group
    contest_groups = {}
    
    # Process regular participants first
    for contestant in regular_contestants:
        contest_type = contestant['contest_type']
        age_group = contestant.get('age_group', '')
        group_num = extract_group_number(age_group)
        group_letter = group_number_to_letter(group_num)
        
        # Check if this is a group contest
        is_group = is_group_contest(contest_type)
        
        # Create key: contest_type + group_letter + is_group flag
        key = f"{contest_type}::{group_letter}::{is_group}"
        
        if key not in contest_groups:
            contest_groups[key] = {
                'contestants': [],
                'walkin_contestants': [],
                'group_letter': group_letter,
                'is_group': is_group,
                'max_id': 0  # Track max ID for walk-in appending
            }
        
        contest_groups[key]['contestants'].append(contestant)
    
    # Assign IDs to regular participants (sorted alphabetically)
    for key, group_data in contest_groups.items():
        group_contestants = group_data['contestants']
        group_letter = group_data['group_letter']
        is_group = group_data['is_group']
        
        # Sort by name (ascending) first to ensure consistent ordering
        group_contestants.sort(key=lambda x: x['name'].lower())
        
        # Assign IDs based on contest type
        if is_group:
            # Group contests: GA1, GB1, GC1, etc.
            prefix = f"G{group_letter}"
        else:
            # Solo contests: A1, B1, C1, etc.
            prefix = group_letter
        
        for idx, contestant in enumerate(group_contestants, start=1):
            contestant['participant_id'] = f"{prefix}{idx}"
            group_data['max_id'] = max(group_data['max_id'], idx)
    
    # Now process walk-in participants - append to existing groups with auto-increment
    for walkin in walkin_contestants:
        contest_type = walkin['contest_type']
        age_group = walkin.get('age_group', '')
        group_num = extract_group_number(age_group)
        group_letter = group_number_to_letter(group_num)
        is_group = is_group_contest(contest_type)
        
        key = f"{contest_type}::{group_letter}::{is_group}"
        
        # If group doesn't exist, create it
        if key not in contest_groups:
            contest_groups[key] = {
                'contestants': [],
                'walkin_contestants': [],
                'group_letter': group_letter,
                'is_group': is_group,
                'max_id': 0
            }
        
        # Determine prefix
        if is_group:
            prefix = f"G{group_letter}"
        else:
            prefix = group_letter
        
        # Increment from the last ID in this group
        group_data = contest_groups[key]
        next_id = group_data['max_id'] + 1
        walkin['participant_id'] = f"{prefix}{next_id}"
        group_data['max_id'] = next_id
        group_data['walkin_contestants'].append(walkin)
    
    # Combine all contestants back
    all_contestants = []
    for group_data in contest_groups.values():
        all_contestants.extend(group_data['contestants'])
        all_contestants.extend(group_data['walkin_contestants'])
    
    # Sort all contestants by participant_id (alphanumeric sorting)
    def sort_key(contestant):
        """Sort key for participant IDs: handles GA1, GA2, GA10 correctly"""
        pid = contestant.get('participant_id', '')
        if not pid:
            return ('', '', 0)
        # Extract prefix (G or empty) and the rest
        if pid.startswith('G'):
            prefix = 'G'
            rest = pid[1:]
        else:
            prefix = ''
            rest = pid
        # Extract letter and number
        import re
        match = re.match(r'([A-Z]+)(\d+)', rest)
        if match:
            letter = match.group(1)
            number = int(match.group(2))
            return (prefix, letter, number)
        return (prefix, rest, 0)
    
    all_contestants.sort(key=sort_key)
    
    return all_contestants

# Load contestants data from Excel
def load_contestants():
    """Load contestants and contest types from Excel file"""
    try:
        df = pd.read_excel(EXCEL_FILE_PATH)
        
        # Find contest name column (new structure)
        contest_name_col = None
        for col in df.columns:
            col_lower = str(col).lower()
            if 'contest name' in col_lower or col_lower == 'contest name':
                contest_name_col = col
                break
        
        # Find the order items column (fallback for old structure)
        order_items_col = None
        for col in df.columns:
            col_lower = str(col).lower()
            if 'order' in col_lower and 'item' in col_lower:
                order_items_col = col
                break
        
        # Find participant name column
        participant_col = None
        for col in df.columns:
            col_lower = str(col).lower()
            if 'participant' in col_lower and 'name' in col_lower:
                participant_col = col
                break
        
        if participant_col is None:
            raise ValueError("Could not find 'Participant's Name' column in Excel file")
        
        # Find age column
        age_col = None
        for col in df.columns:
            col_lower = str(col).lower()
            if 'age' in col_lower and '23rd' in col_lower:
                age_col = col
                break
        
        # Find age group column
        age_group_col = None
        for col in df.columns:
            col_lower = str(col).lower()
            if 'age group' in col_lower:
                age_group_col = col
                break
        
        contestants = []
        contestant_id = 1
        
        # Load participant edits/overrides
        participant_edits = load_participant_edits()
        
        # Process each row
        for _, row in df.iterrows():
            participant_name = str(row[participant_col]).strip() if pd.notna(row[participant_col]) else None
            if not participant_name or participant_name.lower() in ['nan', 'none', '']:
                continue
            
            # Get original values
            original_name = participant_name
            original_age = row[age_col] if age_col and pd.notna(row[age_col]) else None
            original_age_group = str(row[age_group_col]).strip() if age_group_col and pd.notna(row[age_group_col]) else None
            
            # Apply edits if any
            edit_key = original_name.lower()
            if edit_key in participant_edits:
                edits = participant_edits[edit_key]
                participant_name = edits.get('name', participant_name)
                original_age = edits.get('age', original_age)
                original_age_group = edits.get('age_group', original_age_group)
            
            # Get contest name(s) - use contest name column directly
            contests = []
            if contest_name_col and pd.notna(row[contest_name_col]):
                # Use contest name directly from the column
                contest_name = str(row[contest_name_col]).strip()
                if contest_name and contest_name.lower() not in ['nan', 'none', '']:
                    # Normalize using centralized function
                    contest_name = normalize_contest_name(contest_name)
                    contests = [contest_name]
            elif order_items_col and pd.notna(row[order_items_col]):
                # Fallback: extract from order items if contest name column not available
                order_items = row[order_items_col]
                contests = extract_contests_from_order_items(order_items)
            
            # Normalize all contest names using centralized function
            normalized_contests = []
            for contest in contests:
                normalized_contest = normalize_contest_name(contest)
                normalized_contests.append(normalized_contest)
            contests = normalized_contests
            
            # If no contests found, skip or assign to "Unknown"
            if not contests:
                contests = ["Unknown Contest"]
            
            # Get order item for this row
            order_item = None
            if order_items_col and pd.notna(row[order_items_col]):
                order_item = str(row[order_items_col]).strip()
            elif contest_name_col and pd.notna(row[contest_name_col]):
                order_item = str(row[contest_name_col]).strip()
            
            # Create a contestant entry for each contest they're participating in
            for contest in contests:
                # Contest is already normalized by normalize_contest_name() above
                contestants.append({
                    'id': contestant_id,
                    'name': participant_name,
                    'contest_type': contest,
                    'age': original_age,
                    'age_group': original_age_group,
                    'original_name': original_name,  # Keep original for reference
                    'order_item': order_item,  # Store order item for display
                    'is_walkin': False
                })
                contestant_id += 1
        
        # Load walk-in participants and add them
        walkin_participants = load_walkin_participants()
        max_id = max([c['id'] for c in contestants]) if contestants else 0
        
        # Normalize walk-in participants' contest types using centralized function
        for walkin in walkin_participants:
            if walkin.get('contest_type'):
                walkin['contest_type'] = normalize_contest_name(walkin['contest_type'])
        
        for walkin in walkin_participants:
            max_id += 1
            # Try to get age group from walk-in data if available
            walkin_age_group = walkin.get('age_group', '')
            walkin_age = walkin.get('age', None)
            
            contestants.append({
                'id': max_id,
                'name': walkin['name'],
                'contest_type': walkin['contest_type'],
                'age': walkin_age,
                'age_group': walkin_age_group,
                'original_name': walkin['name'],
                'order_item': None,  # Walk-in participants don't have order items
                'is_walkin': True
            })
        
        # Assign participant IDs based on age group and contest type
        contestants = assign_participant_ids(contestants)
        
        # Group contestants by contest type for return
        grouped_by_contest = {}
        for contestant in contestants:
            contest_type = contestant['contest_type']
            if contest_type not in grouped_by_contest:
                grouped_by_contest[contest_type] = []
            grouped_by_contest[contest_type].append(contestant)
        
        return contestants, grouped_by_contest
    except Exception as e:
        print(f"Error loading Excel file: {e}")
        import traceback
        traceback.print_exc()
        # Return sample data if Excel can't be loaded
        contestants = [
            {'id': 1, 'name': 'Sample Contestant 1', 'contest_type': 'Type A'},
            {'id': 2, 'name': 'Sample Contestant 2', 'contest_type': 'Type B'},
        ]
        # Add walk-in participants
        walkin_participants = load_walkin_participants()
        max_id = max([c['id'] for c in contestants]) if contestants else 0
        for walkin in walkin_participants:
            max_id += 1
            contestants.append({
                'id': max_id,
                'name': walkin['name'],
                'contest_type': walkin['contest_type'],
                'is_walkin': True
            })
        # Group contestants by contest type for return
        grouped_by_contest = {}
        for contestant in contestants:
            contest_type = contestant.get('contest_type', 'Unknown')
            if contest_type not in grouped_by_contest:
                grouped_by_contest[contest_type] = []
            grouped_by_contest[contest_type].append(contestant)
        
        return contestants, grouped_by_contest

# Load scores from JSON file
def load_scores():
    """Load existing scores from JSON file"""
    if os.path.exists(SCORES_FILE):
        try:
            with open(SCORES_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

# Save scores to JSON file
def save_scores(scores):
    """Save scores to JSON file"""
    with open(SCORES_FILE, 'w') as f:
        json.dump(scores, f, indent=2)

# Walk-in participant functions
def load_walkin_participants():
    """Load walk-in participants from JSON file"""
    if os.path.exists(WALKIN_PARTICIPANTS_FILE):
        try:
            with open(WALKIN_PARTICIPANTS_FILE, 'r') as f:
                return json.load(f)
        except:
            return []
    return []

def save_walkin_participants(participants):
    """Save walk-in participants to JSON file"""
    with open(WALKIN_PARTICIPANTS_FILE, 'w') as f:
        json.dump(participants, f, indent=2)

def load_speech_topics():
    """Load speech topics from JSON file (supports Unicode: English, Hindi, Gujarati, Telugu)"""
    if os.path.exists(SPEECH_TOPICS_FILE):
        try:
            with open(SPEECH_TOPICS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_speech_topics(topics):
    """Save speech topics to JSON file (supports Unicode: English, Hindi, Gujarati, Telugu)"""
    with open(SPEECH_TOPICS_FILE, 'w', encoding='utf-8') as f:
        json.dump(topics, f, indent=2, ensure_ascii=False)

def get_speech_topic(contest_type, age_group):
    """Get speech topic for a contest type and age group"""
    topics = load_speech_topics()
    # Create key from contest type and age group
    key = f"{contest_type}::{age_group}" if age_group else f"{contest_type}::"
    return topics.get(key, '')

def add_walkin_participant(name, contest_type, age=None, age_group=None):
    """Add a new walk-in participant - normalize contest_type before adding"""
    contest_type = normalize_contest_name(contest_type) if contest_type else contest_type
    participants = load_walkin_participants()
    participants.append({
        'name': name,
        'contest_type': contest_type,
        'age': age,
        'age_group': age_group,
        'added_at': datetime.now().isoformat(),
        'added_by': session.get('judge_username', 'unknown')
    })
    save_walkin_participants(participants)
    return True

# Participant management functions
def load_participant_edits():
    """Load participant edits/overrides from JSON file"""
    if os.path.exists(PARTICIPANTS_MANAGEMENT_FILE):
        try:
            with open(PARTICIPANTS_MANAGEMENT_FILE, 'r') as f:
                data = json.load(f)
                # Convert to lowercase keys for lookup
                return {k.lower(): v for k, v in data.items()}
        except:
            return {}
    return {}

def save_participant_edits(edits):
    """Save participant edits to JSON file"""
    with open(PARTICIPANTS_MANAGEMENT_FILE, 'w') as f:
        json.dump(edits, f, indent=2)

def update_participant_info(original_name, new_name=None, age=None, age_group=None):
    """Update participant information and propagate to all associated contests"""
    edits = load_participant_edits()
    edit_key = original_name.lower()
    
    if edit_key not in edits:
        edits[edit_key] = {
            'original_name': original_name,
            'name': original_name,
            'age': None,
            'age_group': None,
            'updated_at': datetime.now().isoformat(),
            'updated_by': session.get('judge_username', 'unknown')
        }
    
    # Update fields
    if new_name is not None and new_name.strip():
        edits[edit_key]['name'] = new_name.strip()
    if age is not None:
        try:
            age_int = int(age) if age else None
            edits[edit_key]['age'] = age_int
            # Auto-assign age group if age is provided
            if age_int is not None:
                auto_age_group = assign_age_group_from_age(age_int)
                if auto_age_group:
                    edits[edit_key]['age_group'] = auto_age_group
        except (ValueError, TypeError):
            edits[edit_key]['age'] = None
    # Only update age_group manually if age is not provided
    if age_group is not None and age is None:
        edits[edit_key]['age_group'] = age_group.strip() if age_group else None
    
    edits[edit_key]['updated_at'] = datetime.now().isoformat()
    edits[edit_key]['updated_by'] = session.get('judge_username', 'unknown')
    
    save_participant_edits(edits)
    
    # If name changed, the load_contestants function will automatically use the new name
    # because it checks participant_edits first
    
    return True

def get_all_participants_data():
    """Get all unique participants with their data"""
    contestants, _ = load_contestants()
    participants_dict = {}
    
    for contestant in contestants:
        # Use original_name as key to group all contests for same participant
        original_name = contestant.get('original_name', contestant['name'])
        key_name = original_name.lower()
        current_name = contestant['name']  # This may be edited
        
        if key_name not in participants_dict:
            participants_dict[key_name] = {
                'original_name': original_name,
                'current_name': current_name,
                'age': contestant.get('age'),
                'age_group': contestant.get('age_group'),
                'contests': [],
                'participant_ids': {}  # Store participant IDs by contest type
            }
        
        # Add contest if not already in list
        if contestant['contest_type'] not in participants_dict[key_name]['contests']:
            participants_dict[key_name]['contests'].append(contestant['contest_type'])
        
        # Store participant ID for this contest type
        if contestant.get('participant_id'):
            participants_dict[key_name]['participant_ids'][contestant['contest_type']] = contestant['participant_id']
    
    # Convert to list
    participants_list = []
    for key, data in participants_dict.items():
        # Get the first participant ID (or create a summary)
        participant_id = None
        if data['participant_ids']:
            # Use the first ID found, or show multiple if different
            ids_list = list(data['participant_ids'].values())
            if len(set(ids_list)) == 1:
                participant_id = ids_list[0]
            else:
                # Multiple different IDs - show first one
                participant_id = ids_list[0]
        
        participants_list.append({
            'name': data['current_name'],  # Show current (possibly edited) name
            'original_name': data['original_name'],  # Keep original for reference
            'age': data['age'],
            'age_group': data['age_group'],
            'contests': sorted(data['contests']),
            'participant_id': participant_id,
            'participant_ids': data['participant_ids']  # All IDs by contest
        })
    
    return sorted(participants_list, key=lambda x: x['name'].lower())

# Authentication functions
def load_judges():
    """Load judges from JSON file"""
    if os.path.exists(JUDGES_FILE):
        try:
            with open(JUDGES_FILE, 'r') as f:
                judges = json.load(f)
                # Add default contests if missing
                default_contests = {
                    'judge1': [
                        'Instrument Playing Contest',
                        'Prepared Speech Group',
                        'Presentation',
                        'Impromptu',
                        'Fancy Dress'
                    ],
                    'judge2': [
                        'Yoga Contest',
                        'Coloring Contest',
                        'Drawing Contest',
                        'Chalk Art Contest',
                        'MATH Contest',
                        'Poster Making Contest',
                        'Rangoli'
                    ],
                    'judge3': [
                        'Classical Solo Singing Contest',
                        'Classical Solo Dance Contest',
                        'Classical Dance (Group) Contest',
                        'Lite Music Singing (Solo) Contest',
                        'Lite Music Singing (Group) Contest',
                        'Shloka Recitation Contest',
                        'Folk Dance (Group) Contest',
                        'Folk Dance (Solo) Contest',
                        'Singing - Classical (Group) Grp 1 & 4 Contest'
                    ]
                }
                # Update judges with default contests and role flag if missing
                updated = False
                for username, contests in default_contests.items():
                    if username in judges:
                        if 'assigned_contests' not in judges[username]:
                            judges[username]['assigned_contests'] = contests
                            updated = True
                        # Set role based on is_admin or default
                        if 'role' not in judges[username]:
                            if judges[username].get('is_admin', False) or username.startswith('admin'):
                                judges[username]['role'] = 'admin'
                            else:
                                judges[username]['role'] = 'judge'
                            updated = True
                        if 'is_admin' not in judges[username]:
                            judges[username]['is_admin'] = username.startswith('admin')
                            updated = True
                
                # Add admin users if they don't exist
                admin_users = ['admin1', 'admin2', 'admin3', 'admin4']
                for admin_user in admin_users:
                    if admin_user not in judges:
                        judges[admin_user] = {
                            'username': admin_user,
                            'password': 'admin123',
                            'name': f'Admin {admin_user[-1]}',
                            'role': 'admin',
                            'is_admin': True,
                            'assigned_contests': []
                        }
                        updated = True
                
                if updated:
                    save_judges(judges)
                return judges
        except:
            return {}
    # Create default judges if file doesn't exist
    default_judges = {
        'admin1': {
            'username': 'admin1',
            'password': 'admin123',
            'name': 'Admin 1',
            'role': 'admin',
            'is_admin': True,
            'assigned_contests': []  # Admins see all contests
        },
        'admin2': {
            'username': 'admin2',
            'password': 'admin123',
            'name': 'Admin 2',
            'role': 'admin',
            'is_admin': True,
            'assigned_contests': []
        },
        'admin3': {
            'username': 'admin3',
            'password': 'admin123',
            'name': 'Admin 3',
            'role': 'admin',
            'is_admin': True,
            'assigned_contests': []
        },
        'admin4': {
            'username': 'admin4',
            'password': 'admin123',
            'name': 'Admin 4',
            'role': 'admin',
            'is_admin': True,
            'assigned_contests': []
        },
        'judge1': {
            'username': 'judge1',
            'password': 'judge123',  # In production, use hashed passwords
            'name': 'Judge 1',
            'role': 'judge',
            'is_admin': False,
            'assigned_contests': [
                'Instrument Playing Contest',
                'Prepared Speech contest',
                'Presentation',
                'Impromptu',
                'Fancy Dress'
            ]
        },
        'judge2': {
            'username': 'judge2',
            'password': 'judge123',
            'name': 'Judge 2',
            'role': 'judge',
            'is_admin': False,
            'assigned_contests': [
                'Yoga',
                'Coloring',
                'Drawing',
                'Chalk Art',
                'Math',
                'Poster Making Contest',
                'Rangoli'
            ]
        },
        'judge3': {
            'username': 'judge3',
            'password': 'judge123',
            'name': 'Judge 3',
            'role': 'judge',
            'is_admin': False,
            'assigned_contests': [
                'Singing Class solo grp 1 & 4',
                'Dance Classical solo - Group 1 & 3',
                'Dance Class Group grp (all)',
                'Singing Lite Solo- (Grp 1)',
                'Group Singing Lite Group  (all)',
                'Shloka Recitation Contest',
                'Dance Class Group grp 1 &3',
                'Dance Class Group grp 2 & 4',
                'Singing Classical Group (grp 1 & 4)'
            ]
        }
    }
    save_judges(default_judges)
    return default_judges

def save_judges(judges):
    """Save judges to JSON file"""
    with open(JUDGES_FILE, 'w') as f:
        json.dump(judges, f, indent=2)

def verify_judge(username, password):
    """Verify judge credentials"""
    judges = load_judges()
    judge = judges.get(username)
    if judge and judge.get('password') == password:
        return judge
    return None

def get_judge_assigned_contests(username):
    """Get list of contest types assigned to a judge"""
    judges = load_judges()
    judge = judges.get(username)
    if judge:
        return judge.get('assigned_contests', [])
    return []

def is_admin(username):
    """Check if user is an admin"""
    judges = load_judges()
    judge = judges.get(username)
    if judge:
        role = judge.get('role', 'judge')
        return role == 'admin' or judge.get('is_admin', False)  # Support both old and new format
    return False

def get_user_role(username):
    """Get user role (admin, judge, or checkin)"""
    judges = load_judges()
    judge = judges.get(username)
    if judge:
        # Support both old format (is_admin) and new format (role)
        if judge.get('role'):
            return judge.get('role')
        elif judge.get('is_admin', False):
            return 'admin'
        else:
            return 'judge'
    return None

def is_checkin_user(username):
    """Check if user is a checkin user"""
    return get_user_role(username) == 'checkin'

def filter_contestants_by_judge(contestants, judge_username):
    """Filter contestants to only show those assigned to the judge"""
    if not judge_username:
        return []
    
    role = get_user_role(judge_username)
    
    # Admins see all contestants
    if role == 'admin':
        return contestants
    
    # Check-in users might have limited access (can be customized)
    if role == 'checkin':
        # For now, check-in users see all (can be restricted later)
        return contestants
    
    # Judges see only their assigned contests
    assigned_contests = get_judge_assigned_contests(judge_username)
    if not assigned_contests:
        # If judge has no assigned contests, return empty
        return []
    
    # Filter contestants by assigned contest types
    filtered = [c for c in contestants if c['contest_type'] in assigned_contests]
    return filtered

def login_required(f):
    """Decorator to require login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'judge_username' not in session:
            flash('Please login to access this page', 'error')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page for judges"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        next_page = request.args.get('next', url_for('index'))
        
        if not username or not password:
            flash('Please enter both username and password', 'error')
            return render_template('login.html', next=next_page)
        
        judge = verify_judge(username, password)
        if judge:
            session['judge_username'] = username
            session['judge_name'] = judge.get('name', username)
            # Support both old format (is_admin) and new format (role)
            role = judge.get('role')
            if role:
                session['role'] = role
                session['is_admin'] = (role == 'admin')
            else:
                session['is_admin'] = judge.get('is_admin', False)
                session['role'] = 'admin' if session['is_admin'] else 'judge'
            flash(f'Welcome, {session["judge_name"]}!', 'success')
            return redirect(next_page)
        else:
            flash('Invalid username or password', 'error')
            return render_template('login.html', next=next_page)
    
    # GET request
    next_page = request.args.get('next', url_for('index'))
    return render_template('login.html', next=next_page)

@app.route('/logout')
def logout():
    """Logout route"""
    judge_name = session.get('judge_name', 'Judge')
    session.clear()
    flash(f'Goodbye, {judge_name}! You have been logged out.', 'success')
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    """Main page - show list of contestants grouped by contest type"""
    contestants, contest_type_col = load_contestants()
    scores = load_scores()
    
    # Filter contestants based on logged-in judge's assignments
    judge_username = session.get('judge_username')
    if judge_username:
        contestants = filter_contestants_by_judge(contestants, judge_username)
    
    # Calculate averages for each contestant
    contestant_stats = {}
    for contestant in contestants:
        contestant_id = str(contestant['id'])
        contestant_scores = scores.get(contestant_id, {})
        score_values = [s['score'] for s in contestant_scores.values() if isinstance(s, dict) and 'score' in s]
        contestant_stats[contestant_id] = {
            'average': sum(score_values) / len(score_values) if score_values else 0,
            'count': len(score_values)
        }
    
    # Group contestants by contest type
    grouped = {}
    for contestant in contestants:
        contest_type = contestant['contest_type']
        if contest_type not in grouped:
            grouped[contest_type] = []
        grouped[contest_type].append(contestant)
    
    # Sort contestants within each group by participant_id (proper alphanumeric sorting)
    def participant_id_sort_key(contestant):
        """Sort key for participant IDs: handles GA1, GA2, GA10 correctly"""
        pid = contestant.get('participant_id', '')
        if not pid:
            return ('', '', 0)
        # Extract prefix (G or empty) and the rest
        if pid.startswith('G'):
            prefix = 'G'
            rest = pid[1:]
        else:
            prefix = ''
            rest = pid
        # Extract letter and number
        import re
        match = re.match(r'([A-Z]+)(\d+)', rest)
        if match:
            letter = match.group(1)
            number = int(match.group(2))
            return (prefix, letter, number)
        return (prefix, rest, 0)
    
    for contest_type in grouped:
        grouped[contest_type].sort(key=participant_id_sort_key)
    
    # Sort contest types alphabetically for better tab organization
    grouped = dict(sorted(grouped.items()))
    
    # Group by age groups for table view
    grouped_by_age = {}
    for contest_type, contestant_list in grouped.items():
        age_groups_dict = {}
        for contestant in contestant_list:
            age_group = contestant.get('age_group', 'Unknown Group')
            if age_group not in age_groups_dict:
                age_groups_dict[age_group] = {
                    'group_num': extract_group_number(age_group) if age_group != 'Unknown Group' else 99,
                    'contestants': []
                }
            age_groups_dict[age_group]['contestants'].append(contestant)
        # Sort age groups and contestants within each group
        # Sort by group number first, then by age group name
        sorted_age_groups = sorted(age_groups_dict.items(), key=lambda x: (x[1]['group_num'], x[0]))
        grouped_by_age[contest_type] = {}
        
        def participant_id_sort_key(contestant):
            """Sort key for participant IDs: handles GA1, GA2, GA10 correctly"""
            pid = contestant.get('participant_id', '')
            if not pid:
                return ('', '', 0)
            # Extract prefix (G or empty) and the rest
            if pid.startswith('G'):
                prefix = 'G'
                rest = pid[1:]
            else:
                prefix = ''
                rest = pid
            # Extract letter and number
            import re
            match = re.match(r'([A-Z]+)(\d+)', rest)
            if match:
                letter = match.group(1)
                number = int(match.group(2))
                return (prefix, letter, number)
            return (prefix, rest, 0)
        
        for age_group, data in sorted_age_groups:
            data['contestants'].sort(key=participant_id_sort_key)
            grouped_by_age[contest_type][age_group] = data
    
    is_admin_user = is_admin(judge_username) if judge_username else False
    
    return render_template('index.html', 
                         grouped_contestants=grouped,
                         grouped_by_age=grouped_by_age,
                         scores=scores,
                         contestant_stats=contestant_stats,
                         contest_type_col=contest_type_col,
                         judge_username=judge_username,
                         is_admin_user=is_admin_user)

@app.route('/score/<int:contestant_id>')
@login_required
def score_contestant(contestant_id):
    """Page for entering score for a specific contestant"""
    contestants, _ = load_contestants()
    contestant = next((c for c in contestants if c['id'] == contestant_id), None)
    
    if not contestant:
        flash('Contestant not found', 'error')
        return redirect(url_for('index'))
    
    scores = load_scores()
    all_scores = scores.get(str(contestant_id), {})
    
    # Get current judge's existing score if any
    judge_username = session.get('judge_username')
    judge_existing_score = all_scores.get(judge_username) if judge_username else None
    
    # Normalize contest type using centralized function
    if contestant.get('contest_type'):
        contestant['contest_type'] = normalize_contest_name(contestant['contest_type'])
    
    # Ensure detailed_scores is accessible in template for Instrument and Fancy Dress contests
    if judge_existing_score and isinstance(judge_existing_score, dict):
        if 'detailed_scores' not in judge_existing_score:
            judge_existing_score['detailed_scores'] = {}
    
    # Find all contestants with the same name (same participant in different contests)
    participant_name = contestant['name']
    all_participant_contestants = [c for c in contestants if c['name'] == participant_name]
    
    # Get all scores given by this judge to this participant across all contests
    judge_all_scores = []
    for part_contestant in all_participant_contestants:
        part_scores = scores.get(str(part_contestant['id']), {})
        judge_score = part_scores.get(judge_username) if judge_username else None
        if judge_score and isinstance(judge_score, dict) and 'score' in judge_score:
            score_entry = {
                'contest_type': part_contestant['contest_type'],
                'contestant_id': part_contestant['id'],
                'score': judge_score['score'],
                'comments': judge_score.get('comments', ''),
                'timestamp': judge_score.get('timestamp', '')
            }
            # Include detailed scores for Instrument contest
            if 'detailed_scores' in judge_score:
                score_entry['detailed_scores'] = judge_score['detailed_scores']
            judge_all_scores.append(score_entry)
    
    # Sort by contest type
    judge_all_scores.sort(key=lambda x: x['contest_type'])
    
    # Calculate statistics for current contest
    score_values = [s['score'] for s in all_scores.values() if isinstance(s, dict) and 'score' in s]
    stats = {
        'count': len(score_values),
        'average': sum(score_values) / len(score_values) if score_values else 0,
        'total': sum(score_values)
    }
    
    # Calculate judge's average across all contests for this participant
    judge_avg_score = 0
    if judge_all_scores:
        judge_avg_score = sum([s['score'] for s in judge_all_scores]) / len(judge_all_scores)
    
    is_admin_user = is_admin(judge_username) if judge_username else False
    
    # Get speech topic for prepared speech contests (by age group)
    speech_topic = ''
    is_prepared_speech = any(keyword in contestant.get('contest_type', '').lower() for keyword in ['prepared speech'])
    if is_prepared_speech:
        contest_type = contestant.get('contest_type', '')
        age_group = contestant.get('age_group', '')
        speech_topic = get_speech_topic(contest_type, age_group)
    
    # Check if this is a singing contest
    is_singing_contest = any(keyword in contestant.get('contest_type', '').lower() for keyword in ['singing'])
    
    return render_template('score.html', 
                         contestant=contestant,
                         all_scores=all_scores,
                         stats=stats,
                         judge_existing_score=judge_existing_score,
                         judge_name=session.get('judge_name', ''),
                         judge_all_scores=judge_all_scores,
                         participant_name=participant_name,
                         judge_avg_score=judge_avg_score,
                         is_admin_user=is_admin_user,
                         speech_topic=speech_topic,
                         is_prepared_speech=is_prepared_speech,
                         is_singing_contest=is_singing_contest)

@app.route('/api/submit_score', methods=['POST'])
@login_required
def submit_score():
    """API endpoint to submit a score"""
    data = request.json
    
    contestant_id = data.get('contestant_id')
    # Use logged-in judge's name from session
    judge_name = session.get('judge_name', data.get('judge_name', 'Anonymous'))
    judge_username = session.get('judge_username', 'anonymous')
    score = data.get('score')
    comments = data.get('comments', '')
    
    if not contestant_id or score is None:
        return jsonify({'success': False, 'error': 'Missing required fields'}), 400
    
    try:
        score = float(score)
    except (ValueError, TypeError):
        return jsonify({'success': False, 'error': 'Invalid score format'}), 400
    
    scores = load_scores()
    contestant_key = str(contestant_id)
    
    if contestant_key not in scores:
        scores[contestant_key] = {}
    
    # Store score with timestamp - use username as key to prevent duplicates
    score_entry = {
        'judge_name': judge_name,
        'judge_username': judge_username,
        'score': score,
        'comments': comments,
        'timestamp': datetime.now().isoformat()
    }
    
    # Add detailed scores for Instrument contest
    detailed_scores = data.get('detailed_scores')
    if detailed_scores:
        score_entry['detailed_scores'] = detailed_scores
    
    # If judge already scored, update their score (use username as key)
    scores[contestant_key][judge_username] = score_entry
    
    save_scores(scores)
    
    return jsonify({'success': True, 'message': 'Score submitted successfully'})

@app.route('/api/scores/<int:contestant_id>')
def get_scores(contestant_id):
    """API endpoint to get scores for a contestant"""
    scores = load_scores()
    contestant_scores = scores.get(str(contestant_id), {})
    return jsonify(contestant_scores)

@app.route('/results')
@login_required
def results():
    """Page showing all results grouped by contest type"""
    contestants, _ = load_contestants()
    scores = load_scores()
    
    # Filter contestants based on logged-in judge's assignments
    judge_username = session.get('judge_username')
    if judge_username:
        contestants = filter_contestants_by_judge(contestants, judge_username)
    
    # Calculate totals and averages for each contestant
    results = []
    for contestant in contestants:
        contestant_scores = scores.get(str(contestant['id']), {})
        score_values = [s['score'] for s in contestant_scores.values() if isinstance(s, dict) and 'score' in s]
        
        results.append({
            'contestant': contestant,
            'scores': contestant_scores,
            'total': sum(score_values),
            'average': sum(score_values) / len(score_values) if score_values else 0,
            'count': len(score_values)
        })
    
    # Group results by contest type
    grouped_results = {}
    for result in results:
        contest_type = result['contestant']['contest_type']
        if contest_type not in grouped_results:
            grouped_results[contest_type] = []
        grouped_results[contest_type].append(result)
    
    # Sort each group by average score (descending) and sort contest types alphabetically
    for contest_type in grouped_results:
        grouped_results[contest_type].sort(key=lambda x: x['average'], reverse=True)
    grouped_results = dict(sorted(grouped_results.items()))
    
    is_admin_user = is_admin(judge_username) if judge_username else False
    
    return render_template('results.html', 
                         grouped_results=grouped_results,
                         judge_username=judge_username,
                         is_admin_user=is_admin_user)

@app.route('/walkin', methods=['GET', 'POST'])
@login_required
def walkin_participant():
    """Page for adding walk-in participants (admin only)"""
    judge_username = session.get('judge_username')
    
    # Only admins can add walk-in participants
    if not is_admin(judge_username):
        flash('Only administrators can add walk-in participants', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        contest_type = request.form.get('contest_type', '').strip()
        # Normalize contest type before processing
        contest_type = normalize_contest_name(contest_type) if contest_type else contest_type
        age = request.form.get('age', '').strip() or None
        age_group = request.form.get('age_group', '').strip() or None
        
        if not name or not contest_type:
            flash('Please fill in all required fields', 'error')
            return render_template('walkin.html', 
                                 contest_types=STANDARD_CONTESTS,
                                 walkin_participants=load_walkin_participants())
        
        try:
            # Convert age to int if provided
            if age:
                try:
                    age = int(age)
                except ValueError:
                    flash('Invalid age format. Please enter a valid number.', 'error')
                    return render_template('walkin.html', 
                                         contest_types=STANDARD_CONTESTS,
                                         walkin_participants=load_walkin_participants())
            
            # Auto-assign age group based on age
            if age is not None:
                age_group = assign_age_group_from_age(age)
            elif not age_group:
                flash('Age is required to auto-assign age group', 'error')
                return render_template('walkin.html', 
                                     contest_types=STANDARD_CONTESTS,
                                     walkin_participants=load_walkin_participants())
            
            add_walkin_participant(name, contest_type, age, age_group)
            flash(f'Walk-in participant "{name}" added to "{contest_type}" successfully!', 'success')
            return redirect(url_for('walkin_participant'))
        except Exception as e:
            flash(f'Error adding participant: {str(e)}', 'error')
    
    return render_template('walkin.html', 
                         contest_types=STANDARD_CONTESTS,
                         walkin_participants=load_walkin_participants())

@app.route('/api/delete_walkin', methods=['POST'])
@login_required
def delete_walkin_participant():
    """API endpoint to delete a walk-in participant (admin only)"""
    judge_username = session.get('judge_username')
    
    if not is_admin(judge_username):
        return jsonify({'success': False, 'error': 'Only administrators can delete participants'}), 403
    
    data = request.json
    participant_name = data.get('name')
    contest_type = data.get('contest_type')
    # Normalize contest type
    contest_type = normalize_contest_name(contest_type) if contest_type else contest_type
    
    if not participant_name or not contest_type:
        return jsonify({'success': False, 'error': 'Missing required fields'}), 400
    
    participants = load_walkin_participants()
    participants = [p for p in participants if not (p['name'] == participant_name and p['contest_type'] == contest_type)]
    save_walkin_participants(participants)
    
    return jsonify({'success': True, 'message': 'Participant deleted successfully'})

@app.route('/admin/participants')
@login_required
def admin_participants():
    """Admin page for managing all participants, grouped by contest"""
    judge_username = session.get('judge_username')
    
    if not is_admin(judge_username):
        flash('Only administrators can access this page', 'error')
        return redirect(url_for('index'))
    
    contestants, _ = load_contestants()
    
    # Group contestants by contest type
    grouped_by_contest = {}
    for contestant in contestants:
        contest_type = contestant.get('contest_type', 'Unknown')
        if contest_type not in grouped_by_contest:
            grouped_by_contest[contest_type] = []
        grouped_by_contest[contest_type].append(contestant)
    
    # Sort contestants within each contest by participant ID
    def participant_id_sort_key(contestant):
        """Sort key for participant IDs: handles GA1, GA2, GA10 correctly"""
        pid = contestant.get('participant_id', '')
        if not pid:
            return ('', '', 0)
        if pid.startswith('G'):
            prefix = 'G'
            rest = pid[1:]
        else:
            prefix = ''
            rest = pid
        import re
        match = re.match(r'([A-Z]+)(\d+)', rest)
        if match:
            letter = match.group(1)
            number = int(match.group(2))
            return (prefix, letter, number)
        return (prefix, rest, 0)
    
    for contest_type in grouped_by_contest:
        grouped_by_contest[contest_type].sort(key=participant_id_sort_key)
    
    # Sort contest types alphabetically
    grouped_by_contest = dict(sorted(grouped_by_contest.items()))
    
    return render_template('admin_participants.html', 
                         grouped_by_contest=grouped_by_contest,
                         contest_types=STANDARD_CONTESTS)

@app.route('/admin/speech-topics')
@login_required
def admin_speech_topics():
    """Admin page for managing speech topics for prepared speech contests (by age group)"""
    judge_username = session.get('judge_username')
    
    if not is_admin(judge_username):
        flash('Only administrators can access this page', 'error')
        return redirect(url_for('index'))
    
    contestants, _ = load_contestants()
    # Filter only prepared speech contestants
    prepared_speech_contestants = [
        c for c in contestants 
        if any(keyword in c.get('contest_type', '').lower() for keyword in ['prepared speech'])
    ]
    
    # Load existing topics
    topics = load_speech_topics()
    
    # Group by contest type, then by age group
    grouped_by_contest_and_age = {}
    for contestant in prepared_speech_contestants:
        contest_type = contestant['contest_type']
        age_group = contestant.get('age_group', 'Unknown')
        
        if contest_type not in grouped_by_contest_and_age:
            grouped_by_contest_and_age[contest_type] = {}
        
        if age_group not in grouped_by_contest_and_age[contest_type]:
            # Get topic for this contest type + age group
            key = f"{contest_type}::{age_group}" if age_group else f"{contest_type}::"
            topic = topics.get(key, '')
            
            # Count participants in this age group
            participants = [c for c in prepared_speech_contestants 
                          if c['contest_type'] == contest_type and c.get('age_group') == age_group]
            
            grouped_by_contest_and_age[contest_type][age_group] = {
                'topic': topic,
                'participant_count': len(participants),
                'participants': participants[:5]  # Show first 5 as examples
            }
    
    return render_template('admin_speech_topics.html', 
                         grouped_by_age=grouped_by_contest_and_age)

@app.route('/api/update_speech_topic', methods=['POST'])
@login_required
def update_speech_topic():
    """API endpoint to update speech topic by age group (admin only)"""
    judge_username = session.get('judge_username')
    
    if not is_admin(judge_username):
        return jsonify({'success': False, 'error': 'Only administrators can update speech topics'}), 403
    
    data = request.json
    contest_type = data.get('contest_type')
    # Normalize contest type
    contest_type = normalize_contest_name(contest_type) if contest_type else contest_type
    age_group = data.get('age_group', '')
    topic = data.get('topic', '').strip()
    
    if not contest_type:
        return jsonify({'success': False, 'error': 'Missing contest_type'}), 400
    
    # Ensure proper encoding for multilingual support (English, Hindi, Gujarati, Telugu)
    # Python's json module handles Unicode by default, but we ensure it's a string
    if not isinstance(topic, str):
        topic = str(topic)
    
    topics = load_speech_topics()
    # Create key from contest type and age group
    key = f"{contest_type}::{age_group}" if age_group else f"{contest_type}::"
    topics[key] = topic
    save_speech_topics(topics)
    
    return jsonify({'success': True, 'message': 'Speech topic updated successfully'})

@app.route('/api/update_participant', methods=['POST'])
@login_required
def update_participant():
    """API endpoint to update participant information (admin only)"""
    judge_username = session.get('judge_username')
    
    if not is_admin(judge_username):
        return jsonify({'success': False, 'error': 'Only administrators can update participants'}), 403
    
    data = request.json
    original_name = data.get('original_name')
    new_name = data.get('name')
    age = data.get('age')
    age_group = data.get('age_group')
    
    if not original_name:
        return jsonify({'success': False, 'error': 'Original name is required'}), 400
    
    try:
        # Convert age to int if provided
        if age is not None and age != '':
            age = int(age)
        else:
            age = None
        
        update_participant_info(original_name, new_name, age, age_group)
        return jsonify({'success': True, 'message': 'Participant updated successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/add_participant_to_contest', methods=['POST'])
@login_required
def add_participant_to_contest():
    """API endpoint to add a new participant to a specific contest (admin only)"""
    judge_username = session.get('judge_username')
    
    if not is_admin(judge_username):
        return jsonify({'success': False, 'error': 'Only administrators can add participants'}), 403
    
    data = request.json
    name = data.get('name', '').strip()
    contest_type = data.get('contest_type', '').strip()
    # Normalize contest type before processing
    contest_type = normalize_contest_name(contest_type) if contest_type else contest_type
    age = data.get('age')
    age_group = data.get('age_group', '').strip()
    
    if not name or not contest_type:
        return jsonify({'success': False, 'error': 'Name and contest type are required'}), 400
    
    # Auto-assign age group if age is provided
    if age and not age_group:
        try:
            age_int = int(age)
            age_group = assign_age_group_from_age(age_int)
        except (ValueError, TypeError):
            pass
    
    # Add as walk-in participant (which will be included in load_contestants)
    try:
        add_walkin_participant(name, contest_type, age, age_group)
        return jsonify({'success': True, 'message': 'Participant added successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/users')
@login_required
def admin_users():
    """Admin page for managing users (admin only)"""
    judge_username = session.get('judge_username')
    
    if not is_admin(judge_username):
        flash('Only administrators can access this page', 'error')
        return redirect(url_for('index'))
    
    judges = load_judges()
    # Convert to list for template
    users_list = []
    for username, user_data in judges.items():
        role = get_user_role(username)
        users_list.append({
            'username': username,
            'name': user_data.get('name', username),
            'role': role,
            'assigned_contests': user_data.get('assigned_contests', []),
            'is_admin': user_data.get('is_admin', False)  # Keep for backward compatibility
        })
    
    # Sort by role, then by name
    users_list.sort(key=lambda x: (x['role'] != 'admin', x['role'] != 'judge', x['name'].lower()))
    
    return render_template('admin_users.html', 
                         users=users_list,
                         contest_types=STANDARD_CONTESTS,
                         roles=['admin', 'judge', 'checkin'])

@app.route('/api/create_user', methods=['POST'])
@login_required
def create_user():
    """API endpoint to create a new user (admin only)"""
    judge_username = session.get('judge_username')
    
    if not is_admin(judge_username):
        return jsonify({'success': False, 'error': 'Only administrators can create users'}), 403
    
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    name = data.get('name', '').strip()
    role = data.get('role', 'judge').strip()
    assigned_contests = data.get('assigned_contests', [])
    
    if not username or not password or not name or not role:
        return jsonify({'success': False, 'error': 'Username, password, name, and role are required'}), 400
    
    if role not in ['admin', 'judge', 'checkin']:
        return jsonify({'success': False, 'error': 'Invalid role. Must be admin, judge, or checkin'}), 400
    
    judges = load_judges()
    
    # Check if username already exists
    if username in judges:
        return jsonify({'success': False, 'error': 'Username already exists'}), 400
    
    # Create new user
    new_user = {
        'username': username,
        'password': password,  # In production, hash this password
        'name': name,
        'role': role,
        'is_admin': (role == 'admin'),  # Keep for backward compatibility
        'assigned_contests': assigned_contests if role != 'admin' else [],
        'created_at': datetime.now().isoformat(),
        'created_by': judge_username
    }
    
    judges[username] = new_user
    save_judges(judges)
    
    return jsonify({'success': True, 'message': 'User created successfully'})

@app.route('/api/update_user', methods=['POST'])
@login_required
def update_user():
    """API endpoint to update user information (admin only)"""
    judge_username = session.get('judge_username')
    
    if not is_admin(judge_username):
        return jsonify({'success': False, 'error': 'Only administrators can update users'}), 403
    
    data = request.json
    username = data.get('username', '').strip()
    name = data.get('name', '').strip()
    role = data.get('role', '').strip()
    assigned_contests = data.get('assigned_contests', [])
    password = data.get('password', '').strip()  # Optional password update
    
    if not username:
        return jsonify({'success': False, 'error': 'Username is required'}), 400
    
    if role and role not in ['admin', 'judge', 'checkin']:
        return jsonify({'success': False, 'error': 'Invalid role. Must be admin, judge, or checkin'}), 400
    
    judges = load_judges()
    
    if username not in judges:
        return jsonify({'success': False, 'error': 'User not found'}), 404
    
    # Update user
    if name:
        judges[username]['name'] = name
    if role:
        judges[username]['role'] = role
        judges[username]['is_admin'] = (role == 'admin')  # Update is_admin flag
        # Admins don't have assigned contests
        if role == 'admin':
            judges[username]['assigned_contests'] = []
    if assigned_contests is not None:
        if judges[username].get('role') != 'admin':  # Don't update contests for admins
            judges[username]['assigned_contests'] = assigned_contests
    if password:
        judges[username]['password'] = password  # In production, hash this password
    
    judges[username]['updated_at'] = datetime.now().isoformat()
    judges[username]['updated_by'] = judge_username
    
    save_judges(judges)
    
    return jsonify({'success': True, 'message': 'User updated successfully'})

@app.route('/api/get_user', methods=['GET'])
@login_required
def get_user():
    """API endpoint to get user information (admin only)"""
    judge_username = session.get('judge_username')
    
    if not is_admin(judge_username):
        return jsonify({'success': False, 'error': 'Only administrators can view user details'}), 403
    
    username = request.args.get('username', '').strip()
    
    if not username:
        return jsonify({'success': False, 'error': 'Username is required'}), 400
    
    judges = load_judges()
    
    if username not in judges:
        return jsonify({'success': False, 'error': 'User not found'}), 404
    
    user = judges[username].copy()
    # Don't send password
    if 'password' in user:
        del user['password']
    
    return jsonify({'success': True, 'user': user})

@app.route('/api/delete_user', methods=['POST'])
@login_required
def delete_user():
    """API endpoint to delete a user (admin only)"""
    judge_username = session.get('judge_username')
    
    if not is_admin(judge_username):
        return jsonify({'success': False, 'error': 'Only administrators can delete users'}), 403
    
    data = request.json
    username = data.get('username', '').strip()
    
    if not username:
        return jsonify({'success': False, 'error': 'Username is required'}), 400
    
    # Prevent deleting yourself
    if username == judge_username:
        return jsonify({'success': False, 'error': 'Cannot delete your own account'}), 400
    
    judges = load_judges()
    
    if username not in judges:
        return jsonify({'success': False, 'error': 'User not found'}), 404
    
    # Prevent deleting the last admin
    admin_count = sum(1 for u, d in judges.items() if get_user_role(u) == 'admin')
    if get_user_role(username) == 'admin' and admin_count <= 1:
        return jsonify({'success': False, 'error': 'Cannot delete the last admin user'}), 400
    
    del judges[username]
    save_judges(judges)
    
    return jsonify({'success': True, 'message': 'User deleted successfully'})

@app.route('/api/delete_participant_from_contest', methods=['POST'])
@login_required
def delete_participant_from_contest():
    """API endpoint to delete a participant from a specific contest (admin only)"""
    judge_username = session.get('judge_username')
    
    if not is_admin(judge_username):
        return jsonify({'success': False, 'error': 'Only administrators can delete participants'}), 403
    
    data = request.json
    contestant_id = data.get('contestant_id')
    
    if not contestant_id:
        return jsonify({'success': False, 'error': 'Missing contestant_id'}), 400
    
    try:
        # Load contestants to find the one to delete
        contestants, _ = load_contestants()
        contestant = next((c for c in contestants if c['id'] == contestant_id), None)
        
        if not contestant:
            return jsonify({'success': False, 'error': 'Contestant not found'}), 404
        
        # If it's a walk-in participant, remove from walk-in list
        if contestant.get('is_walkin'):
            walkin_participants = load_walkin_participants()
            walkin_participants = [
                w for w in walkin_participants 
                if not (w['name'] == contestant['name'] and w.get('contest_type') == contestant.get('contest_type'))
            ]
            save_walkin_participants(walkin_participants)
            return jsonify({'success': True, 'message': 'Participant deleted successfully'})
        else:
            # For regular participants from Excel, we can't delete them directly
            # Instead, we can mark them as deleted in a separate file
            # For now, return an error suggesting to use participant edits
            return jsonify({
                'success': False, 
                'error': 'Cannot delete participants from Excel file. Use participant management to edit instead.'
            }), 400
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
