import os
import re
import sqlite3
import argparse
import logging
from bs4 import BeautifulSoup
from concurrent.futures import ProcessPoolExecutor, as_completed

logging.basicConfig(level=logging.INFO, format='%(asctime)s - PARSER - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ID extraction regexes
PLAYER_ID_RE = re.compile(r'/Players/\d+/(\d+)/(\d+)\.html')
TEAM_ID_RE = re.compile(r'/Teams/\d+/(\d+)/(\d+)\.html')
TOURNAMENT_ID_RE = re.compile(r'/Events/\d+/([A-Za-z0-9_]+)\.html')
GROUND_ID_RE = re.compile(r'/Grounds/\d+/(\d+)\.html')
DOB_RE = re.compile(r"dob:\s*([^']+)")

def clean_text(text):
    if not text:
        return ""
    return text.strip().replace(u'\xa0', u' ')

def parse_int(val):
    if not val:
        return 0
    val_clean = val.strip().replace('-', '').replace(',', '')
    if not val_clean or val_clean == '':
        return 0
    try:
        return int(val_clean)
    except ValueError:
        return 0

def parse_float(val):
    if not val:
        return 0.0
    val_clean = val.strip().replace('-', '').replace(',', '')
    if not val_clean or val_clean == '':
        return 0.0
    try:
        return float(val_clean)
    except ValueError:
        return 0.0

def get_id_from_url(url, regex_type):
    if not url:
        return None
    if regex_type == 'player':
        match = re.search(r'/Players/\d+/\d+/(\d+)\.html', url)
        if not match:
            match = re.search(r'/Players/\d+/(\d+)\.html', url)
        return match.group(1) if match else None
    elif regex_type == 'team':
        match = re.search(r'/Teams/\d+/\d+/(\d+)\.html', url)
        if not match:
            match = re.search(r'/Teams/\d+/(\d+)\.html', url)
        return match.group(1) if match else None
    elif regex_type == 'tournament':
        match = re.search(r'/Events/(\d+)/', url)
        if not match:
            match = re.search(r'/Events/([^/]+)\.html', url)
        return match.group(1) if match else None
    elif regex_type == 'ground':
        match = re.search(r'/Grounds/\d+/(\d+)\.html', url)
        return match.group(1) if match else None
    return None

def parse_scorecard_html(file_path_or_html, match_id=None):
    """
    Parses HTML and returns structured match data dictionary.
    """
    if match_id is None:
        match_id = os.path.basename(file_path_or_html).replace('.html', '')
        with open(file_path_or_html, 'r', encoding='utf-8', errors='ignore') as f:
            html_content = f.read()
    else:
        html_content = file_path_or_html
        
    soup = BeautifulSoup(html_content, 'lxml')
    
    # 1. Page Title
    title_tag = soup.find('title')
    title = clean_text(title_tag.text) if title_tag else ""
    if title == "The Home of CricketArchive":
        # Fallback to H1 or script document.title
        script_title = re.search(r'document\.title\s*=\s*"([^"]+)"', html_content)
        if script_title:
            title = script_title.group(1)
            
    # 2. Main details table
    # Typically table 1 contains Teams, Tournament, Venue, Umpires etc.
    main_table = None
    tables = soup.find_all('table')
    if not tables:
        return None
        
    # We find the table containing "Venue" or "Toss"
    for table in tables:
        if "Venue" in table.text or "Toss" in table.text or "Result" in table.text:
            main_table = table
            break
            
    if not main_table:
        return None
        
    match_meta = {
        'match_id': match_id,
        'title': title,
        'tournament_id': None,
        'tournament_name': None,
        'tournament_url': None,
        'date': None,
        'venue': None,
        'ground_id': None,
        'format': 'Other',
        'team1_id': None,
        'team1_name': None,
        'team1_url': None,
        'team2_id': None,
        'team2_name': None,
        'team2_url': None,
        'toss_winner_id': None,
        'toss_decision': None,
        'result': None,
        'win_margin_runs': 0,
        'win_margin_wickets': 0,
        'win_margin_text': None,
        'umpire1_id': None,
        'umpire1_name': None,
        'umpire1_url': None,
        'umpire2_id': None,
        'umpire2_name': None,
        'umpire2_url': None,
        'tv_umpire_id': None,
        'tv_umpire_name': None,
        'tv_umpire_url': None,
        'referee_id': None,
        'referee_name': None,
        'referee_url': None,
        'reserve_umpire_id': None,
        'reserve_umpire_name': None,
        'reserve_umpire_url': None,
        'player_of_match_id': None,
        'player_of_match_name': None,
        'player_of_match_url': None,
        'points': None
    }
    
    # Store temporary lists of players, teams, tournaments to insert into lookup tables
    discovered_players = [] # list of dicts: id, name, dob, url
    discovered_teams = []
    discovered_tournaments = []
    
    # Parse main metadata table rows
    rows = main_table.find_all('tr')
    for row in rows:
        tds = row.find_all('td')
        if len(tds) < 2:
            continue
        key = clean_text(tds[0].text)
        val_td = tds[1]
        val_text = clean_text(val_td.text)
        
        # Check team headers in first row or bold center row
        bold_center = val_td.find('center')
        if bold_center and " v " in bold_center.text:
            anchors = bold_center.find_all('a')
            if len(anchors) >= 2:
                match_meta['team1_name'] = clean_text(anchors[0].text)
                match_meta['team1_url'] = anchors[0].get('href')
                match_meta['team1_id'] = get_id_from_url(match_meta['team1_url'], 'team')
                
                match_meta['team2_name'] = clean_text(anchors[1].text)
                match_meta['team2_url'] = anchors[1].get('href')
                match_meta['team2_id'] = get_id_from_url(match_meta['team2_url'], 'team')
                
                discovered_teams.append({'id': match_meta['team1_id'], 'name': match_meta['team1_name'], 'url': match_meta['team1_url']})
                discovered_teams.append({'id': match_meta['team2_id'], 'name': match_meta['team2_name'], 'url': match_meta['team2_url']})
        
        if not key:
            # Maybe Tournament name row
            center_tourney = val_td.find('center')
            if center_tourney:
                anchor = center_tourney.find('a')
                if anchor:
                    match_meta['tournament_name'] = clean_text(anchor.text)
                    match_meta['tournament_url'] = anchor.get('href')
                    match_meta['tournament_id'] = get_id_from_url(match_meta['tournament_url'], 'tournament')
                    discovered_tournaments.append({'id': match_meta['tournament_id'], 'name': match_meta['tournament_name'], 'url': match_meta['tournament_url']})
                    
        elif key == "Venue":
            # Venue text e.g., Alokozay Kabul on 26th July 2025 (20-over match)
            anchor = val_td.find('a')
            if anchor:
                match_meta['venue'] = clean_text(anchor.text)
                match_meta['ground_id'] = get_id_from_url(anchor.get('href'), 'ground')
            
            # Extract date and format
            date_match = re.search(r'on\s+([0-9a-zA-Z\s,]+)(?:\s+\(|\s*$)', val_text)
            if date_match:
                match_meta['date'] = date_match.group(1).strip()
            
            # Format
            if "20-over" in val_text or "Twenty20" in val_text:
                match_meta['format'] = "T20"
            elif "50-over" in val_text or "45-over" in val_text or "40-over" in val_text or "One-Day" in val_text:
                match_meta['format'] = "List A"
            elif "three-day" in val_text or "four-day" in val_text or "five-day" in val_text or "First-Class" in val_text or "Test" in val_text:
                match_meta['format'] = "First-Class"
                
        elif key == "Toss":
            match_meta['toss_decision'] = "bat" if "bat" in val_text.lower() else ("field" if "field" in val_text.lower() else None)
            # Find which team won the toss
            if match_meta['team1_name'] and match_meta['team1_name'].lower() in val_text.lower():
                match_meta['toss_winner_id'] = match_meta['team1_id']
            elif match_meta['team2_name'] and match_meta['team2_name'].lower() in val_text.lower():
                match_meta['toss_winner_id'] = match_meta['team2_id']
                
        elif key == "Result":
            match_meta['result'] = val_text
            # Parse margins
            runs_match = re.search(r'won by (\d+) run', val_text)
            wickets_match = re.search(r'won by (\d+) wicket', val_text)
            if runs_match:
                match_meta['win_margin_runs'] = int(runs_match.group(1))
                match_meta['win_margin_text'] = f"{runs_match.group(1)} runs"
            elif wickets_match:
                match_meta['win_margin_wickets'] = int(wickets_match.group(1))
                match_meta['win_margin_text'] = f"{wickets_match.group(1)} wickets"
            
        elif key == "Umpires":
            anchors = val_td.find_all('a')
            if len(anchors) >= 1:
                match_meta['umpire1_name'] = clean_text(anchors[0].text)
                match_meta['umpire1_url'] = anchors[0].get('href')
                match_meta['umpire1_id'] = get_id_from_url(match_meta['umpire1_url'], 'player')
                discovered_players.append({'id': match_meta['umpire1_id'], 'name': match_meta['umpire1_name'], 'url': match_meta['umpire1_url'], 'dob': None})
            if len(anchors) >= 2:
                match_meta['umpire2_name'] = clean_text(anchors[1].text)
                match_meta['umpire2_url'] = anchors[1].get('href')
                match_meta['umpire2_id'] = get_id_from_url(match_meta['umpire2_url'], 'player')
                discovered_players.append({'id': match_meta['umpire2_id'], 'name': match_meta['umpire2_name'], 'url': match_meta['umpire2_url'], 'dob': None})
                
        elif key == "TV umpire":
            anchor = val_td.find('a')
            if anchor:
                match_meta['tv_umpire_name'] = clean_text(anchor.text)
                match_meta['tv_umpire_url'] = anchor.get('href')
                match_meta['tv_umpire_id'] = get_id_from_url(match_meta['tv_umpire_url'], 'player')
                discovered_players.append({'id': match_meta['tv_umpire_id'], 'name': match_meta['tv_umpire_name'], 'url': match_meta['tv_umpire_url'], 'dob': None})
                
        elif key == "Referee":
            anchor = val_td.find('a')
            if anchor:
                match_meta['referee_name'] = clean_text(anchor.text)
                match_meta['referee_url'] = anchor.get('href')
                match_meta['referee_id'] = get_id_from_url(match_meta['referee_url'], 'player')
                discovered_players.append({'id': match_meta['referee_id'], 'name': match_meta['referee_name'], 'url': match_meta['referee_url'], 'dob': None})
                
        elif key == "Reserve Umpire":
            anchor = val_td.find('a')
            if anchor:
                match_meta['reserve_umpire_name'] = clean_text(anchor.text)
                match_meta['reserve_umpire_url'] = anchor.get('href')
                match_meta['reserve_umpire_id'] = get_id_from_url(match_meta['reserve_umpire_url'], 'player')
                discovered_players.append({'id': match_meta['reserve_umpire_id'], 'name': match_meta['reserve_umpire_name'], 'url': match_meta['reserve_umpire_url'], 'dob': None})
                
        elif key == "Player of the Match":
            anchor = val_td.find('a')
            if anchor:
                match_meta['player_of_match_name'] = clean_text(anchor.text)
                match_meta['player_of_match_url'] = anchor.get('href')
                match_meta['player_of_match_id'] = get_id_from_url(match_meta['player_of_match_url'], 'player')
                discovered_players.append({'id': match_meta['player_of_match_id'], 'name': match_meta['player_of_match_name'], 'url': match_meta['player_of_match_url'], 'dob': None})
                
        elif key == "Points":
            match_meta['points'] = val_text
            
    # Try to refine format based on tournament name
    tname = match_meta['tournament_name'] or ""
    if match_meta['format'] == 'Other':
        if "T20" in tname or "Twenty20" in tname:
            match_meta['format'] = "T20"
        elif "ODI" in tname or "One-Day" in tname or "One Day" in tname or "List A" in tname or "List-A" in tname:
            match_meta['format'] = "List A"
        elif "Test" in tname or "First-Class" in tname or "Ranji" in tname or "County" in tname or "Shield" in tname:
            match_meta['format'] = "First-Class"

    # Innings and scorecard details
    innings_list = [] # List of innings dicts
    batting_scorecards = [] # List of batting dicts
    bowling_scorecards = [] # List of bowling dicts
    fall_of_wickets = [] # List of FoW dicts
    match_notes = [] # List of strings

    # Loop through tables to parse scorecards
    innings_counter = 0
    
    # We find notes from footnotes/text at the end
    notes_section = soup.find('b', text=re.compile('Notes|Footnotes', re.I))
    if notes_section:
        # Find subsequent text or siblings until hr or table
        sibling = notes_section.next_sibling
        while sibling:
            if sibling.name == 'hr' or sibling.name == 'table':
                break
            if isinstance(sibling, str):
                cleaned_note = clean_text(sibling)
                if cleaned_note and cleaned_note.startswith('-->'):
                    match_notes.append(cleaned_note.replace('-->', '').strip())
            elif sibling.name == 'br':
                pass
            else:
                cleaned_note = clean_text(sibling.text)
                if cleaned_note and cleaned_note.startswith('-->'):
                    # Some notes contain links (milestones), extract actual text
                    match_notes.append(cleaned_note.replace('-->', '').strip())
            sibling = sibling.next_sibling

    for table in tables:
        text = table.text
        # We identify innings tables
        # A table with a header like "Speen Ghar Tigers innings" or "Amo Sharks bowling"
        first_row = table.find('tr')
        if not first_row:
            continue
            
        header_text = clean_text(first_row.text)
        
        # Batting Innings Table Check
        if " innings" in header_text.lower():
            innings_counter += 1
            
            # Find batting team
            batting_team_id = None
            batting_team_name = None
            anchor = first_row.find('a')
            if anchor:
                batting_team_name = clean_text(anchor.text)
                batting_team_id = get_id_from_url(anchor.get('href'), 'team')
                discovered_teams.append({'id': batting_team_id, 'name': batting_team_name, 'url': anchor.get('href')})
                
            # Determine bowling team
            bowling_team_id = match_meta['team2_id'] if batting_team_id == match_meta['team1_id'] else match_meta['team1_id']
            
            # Create Innings object
            innings_data = {
                'innings_num': innings_counter,
                'batting_team_id': batting_team_id,
                'bowling_team_id': bowling_team_id,
                'runs': 0,
                'wickets': 0,
                'overs': "",
                'extras_b': 0,
                'extras_lb': 0,
                'extras_nb': 0,
                'extras_wd': 0,
                'extras_total': 0
            }
            
            # Now parse batting rows
            rows = table.find_all('tr')
            for i in range(1, len(rows)):
                r = rows[i]
                tds = r.find_all('td')
                if not tds:
                    continue
                first_td_text = clean_text(tds[0].text)
                
                # Check for Extras row
                if first_td_text == "Extras":
                    if len(tds) >= 3:
                        innings_data['extras_total'] = parse_int(tds[2].text)
                        
                    extras_desc = clean_text(tds[1].text) if len(tds) >= 2 else ""
                    # Parse (2 b, 9 lb, 1 nb, 2 w)
                    b_m = re.search(r'(\d+)\s+b', extras_desc)
                    lb_m = re.search(r'(\d+)\s+lb', extras_desc)
                    nb_m = re.search(r'(\d+)\s+nb', extras_desc)
                    wd_m = re.search(r'(\d+)\s+w', extras_desc)
                    
                    innings_data['extras_b'] = int(b_m.group(1)) if b_m else 0
                    innings_data['extras_lb'] = int(lb_m.group(1)) if lb_m else 0
                    innings_data['extras_nb'] = int(nb_m.group(1)) if nb_m else 0
                    innings_data['extras_wd'] = int(wd_m.group(1)) if wd_m else 0
                    
                # Check for Total row
                elif first_td_text == "Total":
                    if len(tds) >= 3:
                        innings_data['runs'] = parse_int(tds[2].text)
                    
                    total_desc = clean_text(tds[1].text) if len(tds) >= 2 else ""
                    # Parse (6 wickets, innings closed, 20 overs) or (4 wickets, 18.4 overs)
                    w_m = re.search(r'(\d+)\s+wicket', total_desc)
                    o_m = re.search(r'(\d+\.?\d*)\s+over', total_desc)
                    
                    innings_data['wickets'] = int(w_m.group(1)) if w_m else 0
                    if "all out" in total_desc.lower():
                        innings_data['wickets'] = 10
                    innings_data['overs'] = o_m.group(1) if o_m else ""
                    
                # Check for Fall of wickets row
                elif "fall of wickets" in first_td_text.lower():
                    # Parse Fall of Wickets cell
                    # It contains links and text
                    fow_td = tds[0]
                    fow_anchors = fow_td.find_all('a')
                    # If this row doesn't contain player links, look in the next row
                    if not fow_anchors and i + 1 < len(rows):
                        next_row = rows[i + 1]
                        next_tds = next_row.find_all('td')
                        if next_tds:
                            fow_td = next_tds[0]
                            fow_anchors = fow_td.find_all('a')
                            
                    fow_text = clean_text(fow_td.text).replace('Fall of wickets:', '').strip()
                    # Split td text by comma
                    parts = fow_text.split('),')
                    for idx, part in enumerate(parts):
                        part = part.strip()
                        if not part:
                            continue
                        # E.g. "1-47 (Zubaid Akbari, 5.5 ov" or "2-77 (Yousuf Shah, 9.1 ov)"
                        # Extracted wicket-score:
                        m_score = re.match(r'^(\d+)-(\d+)', part)
                        if m_score:
                            w_num = int(m_score.group(1))
                            score = int(m_score.group(2))
                            
                            # Match corresponding anchor
                            p_id = None
                            if idx < len(fow_anchors):
                                p_id = get_id_from_url(fow_anchors[idx].get('href'), 'player')
                                discovered_players.append({
                                    'id': p_id,
                                    'name': clean_text(fow_anchors[idx].text),
                                    'url': fow_anchors[idx].get('href'),
                                    'dob': None
                                })
                            
                            # Parse overs
                            ov_m = re.search(r'(\d+\.?\d*)\s+ov', part)
                            overs = parse_float(ov_m.group(1)) if ov_m else 0.0
                            
                            fall_of_wickets.append({
                                'innings_num': innings_counter,
                                'wicket_num': w_num,
                                'score': score,
                                'player_out_id': p_id,
                                'overs': overs
                            })
                            
                # Check for regular Batsman row (has a link to a player profile)
                else:
                    anchor = tds[0].find('a')
                    if anchor and '/Players/' in anchor.get('href', ''):
                        p_name = clean_text(anchor.text)
                        p_url = anchor.get('href')
                        p_id = get_id_from_url(p_url, 'player')
                        
                        # Extract DOB from mouseover tooltip
                        dob = None
                        mouseover = tds[0].get('onmouseover')
                        if mouseover:
                            dob_m = DOB_RE.search(mouseover)
                            if dob_m:
                                dob = dob_m.group(1).replace('<br>', '').strip()
                                
                        discovered_players.append({
                            'id': p_id,
                            'name': p_name,
                            'url': p_url,
                            'dob': dob
                        })
                        
                        # Batting Stats columns:
                        # 0: Batter name & link
                        # 1: Dismissal details
                        # 2: Runs, 3: Balls, 4: Mins, 5: 4s, 6: 6s, 7: Dots, 8: S-Rate
                        dismissal = clean_text(tds[1].text) if len(tds) >= 2 else ""
                        
                        # If the player did not bat, their stats will parse as 0 or None, but they will still be stored as 'did not bat' in the batting table.
                            
                        runs = parse_int(tds[2].text) if len(tds) >= 3 else 0
                        balls = parse_int(tds[3].text) if len(tds) >= 4 else 0
                        mins = parse_int(tds[4].text) if len(tds) >= 5 else None
                        fours = parse_int(tds[5].text) if len(tds) >= 6 else 0
                        sixes = parse_int(tds[6].text) if len(tds) >= 7 else 0
                        dots = parse_int(tds[7].text) if len(tds) >= 8 else 0
                        sr = parse_float(tds[8].text) if len(tds) >= 9 else 0.0
                        
                        batting_scorecards.append({
                            'innings_num': innings_counter,
                            'player_id': p_id,
                            'dismissal': dismissal,
                            'runs': runs,
                            'balls': balls,
                            'mins': mins,
                            'fours': fours,
                            'sixes': sixes,
                            'dots': dots,
                            'sr': sr
                        })
                        
            innings_list.append(innings_data)

        # Bowling Innings Table Check
        elif " bowling" in header_text.lower():
            # Find bowling team ID from header
            bowling_team_id = None
            anchor = first_row.find('a')
            if anchor:
                bowling_team_id = get_id_from_url(anchor.get('href'), 'team')
                discovered_teams.append({'id': bowling_team_id, 'name': clean_text(anchor.text), 'url': anchor.get('href')})
                
            # Parse bowling rows
            rows = table.find_all('tr')
            for r in rows[1:]: # Skip header row
                tds = r.find_all('td')
                if not tds or len(tds) < 2:
                    continue
                first_td = tds[0]
                anchor = first_td.find('a')
                if anchor and '/Players/' in anchor.get('href', ''):
                    p_name = clean_text(anchor.text)
                    p_url = anchor.get('href')
                    p_id = get_id_from_url(p_url, 'player')
                    
                    discovered_players.append({
                        'id': p_id,
                        'name': p_name,
                        'url': p_url,
                        'dob': None
                    })
                    
                    # Bowling Stats columns:
                    # 0: Bowler
                    # 1: Overs, 2: Mdns, 3: Runs, 4: Wkts, 5: Wides, 6: No-Balls, 7: Dots, 8: 4s, 9: 6s, 10: S-Rate, 11: Econ
                    overs = parse_float(tds[1].text) if len(tds) >= 2 else 0.0
                    maidens = parse_int(tds[2].text) if len(tds) >= 3 else 0
                    runs = parse_int(tds[3].text) if len(tds) >= 4 else 0
                    wickets = parse_int(tds[4].text) if len(tds) >= 5 else 0
                    wides = parse_int(tds[5].text) if len(tds) >= 6 else 0
                    noballs = parse_int(tds[6].text) if len(tds) >= 7 else 0
                    dots = parse_int(tds[7].text) if len(tds) >= 8 else 0
                    fours = parse_int(tds[8].text) if len(tds) >= 9 else 0
                    sixes = parse_int(tds[9].text) if len(tds) >= 10 else 0
                    econ = parse_float(tds[11].text) if len(tds) >= 12 else (parse_float(tds[10].text) if len(tds) >= 11 else 0.0)
                    
                    # Store bowling entry. Since we don't know the exact innings number for bowling, 
                    # we match it by checking which innings batting team is NOT the bowling team.
                    # Since we insert it, we'll associate it with the correct innings ID.
                    bowling_scorecards.append({
                        'bowling_team_id': bowling_team_id,
                        'player_id': p_id,
                        'overs': overs,
                        'maidens': maidens,
                        'runs': runs,
                        'wickets': wickets,
                        'wides': wides,
                        'noballs': noballs,
                        'dots': dots,
                        'fours': fours,
                        'sixes': sixes,
                        'econ': econ
                    })

    # Clean up lists (remove duplicate player/team/tournament details to keep it efficient)
    unique_players = {}
    for p in discovered_players:
        if p['id']:
            if p['id'] not in unique_players or (p['dob'] and not unique_players[p['id']]['dob']):
                unique_players[p['id']] = p
                
    unique_teams = {t['id']: t for t in discovered_teams if t['id']}
    unique_tournaments = {to['id']: to for to in discovered_tournaments if to['id']}
    
    return {
        'match': match_meta,
        'players': list(unique_players.values()),
        'teams': list(unique_teams.values()),
        'tournaments': list(unique_tournaments.values()),
        'innings': innings_list,
        'batting': batting_scorecards,
        'bowling': bowling_scorecards,
        'fow': fall_of_wickets,
        'notes': match_notes
    }

def save_parsed_match(conn, data):
    """
    Saves parsed scorecard data to the relational SQLite database.
    """
    if not data:
        return False
        
    m = data['match']
    
    # Call Orchestrator to Deduplicate across APIs
    import orchestrator
    is_new = orchestrator.register_match(m['team1_name'], m['team2_name'], m['date'], m['format'], 'ca', m['match_id'])
    if not is_new:
        # It's a duplicate, orchestrator has linked it. Skip parsing.
        return False
        
    cursor = conn.cursor()
    
    # 1. Insert Tournaments
    for t in data['tournaments']:
        cursor.execute("INSERT OR IGNORE INTO CATournaments (tournament_id, name, url) VALUES (?, ?, ?)", 
                       (t['id'], t['name'], t['url']))
                       
    # 2. Insert Teams
    for tm in data['teams']:
        cursor.execute("INSERT OR IGNORE INTO CATeams (team_id, name, url) VALUES (?, ?, ?)", 
                       (tm['id'], tm['name'], tm['url']))
                       
    # 3. Insert Players
    for p in data['players']:
        cursor.execute("INSERT OR IGNORE INTO CAPlayers (player_id, name, dob, url) VALUES (?, ?, ?, ?)", 
                       (p['id'], p['name'], p['dob'], p['url']))
        # Update DOB if it was previously NULL
        if p['dob']:
            cursor.execute("UPDATE CAPlayers SET dob = ? WHERE player_id = ? AND dob IS NULL", (p['dob'], p['id']))
            
    # 4. Insert Matches
    m = data['match']
    cursor.execute('''
        INSERT OR REPLACE INTO CAMatches 
        (match_id, title, tournament_id, date, venue, ground_id, format, team1_id, team2_id, 
         toss_winner_id, toss_decision, result, win_margin_runs, win_margin_wickets, win_margin_text,
         umpire1_id, umpire2_id, tv_umpire_id, referee_id, reserve_umpire_id, player_of_match_id, points)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        m['match_id'], m['title'], m['tournament_id'], m['date'], m['venue'], m['ground_id'], m['format'],
        m['team1_id'], m['team2_id'], m['toss_winner_id'], m['toss_decision'], m['result'],
        m['win_margin_runs'], m['win_margin_wickets'], m['win_margin_text'],
        m['umpire1_id'], m['umpire2_id'], m['tv_umpire_id'], m['referee_id'], m['reserve_umpire_id'],
        m['player_of_match_id'], m['points']
    ))
    
    # 5. Insert Innings and Scorecards
    for inn in data['innings']:
        # Insert Innings
        cursor.execute('''
            INSERT INTO CAInnings 
            (match_id, innings_number, batting_team_id, bowling_team_id, runs, wickets, overs, 
             extras_b, extras_lb, extras_nb, extras_wd, extras_total)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            m['match_id'], inn['innings_num'], inn['batting_team_id'], inn['bowling_team_id'],
            inn['runs'], inn['wickets'], inn['overs'], inn['extras_b'], inn['extras_lb'],
            inn['extras_nb'], inn['extras_wd'], inn['extras_total']
        ))
        innings_id = cursor.lastrowid
        
        # Batting scorecards for this innings
        inn_bat = [b for b in data['batting'] if b['innings_num'] == inn['innings_num']]
        for b in inn_bat:
            cursor.execute('''
                INSERT INTO CAPlayerBattingScorecard 
                (innings_id, player_id, dismissal_text, runs, balls, mins, fours, sixes, dots, strike_rate)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                innings_id, b['player_id'], b['dismissal'], b['runs'], b['balls'], b['mins'],
                b['fours'], b['sixes'], b['dots'], b['sr']
            ))
            
        # Bowling scorecards for this innings (bowler's team is inn's bowling team)
        inn_bowl = [bw for bw in data['bowling'] if bw['bowling_team_id'] == inn['bowling_team_id']]
        for bw in inn_bowl:
            cursor.execute('''
                INSERT INTO CAPlayerBowlingScorecard 
                (innings_id, player_id, overs, maidens, runs, wickets, wides, no_balls, dots, fours, sixes, econ)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                innings_id, bw['player_id'], bw['overs'], bw['maidens'], bw['runs'], bw['wickets'],
                bw['wides'], bw['noballs'], bw['dots'], bw['fours'], bw['sixes'], bw['econ']
            ))
            
        # Fall of wickets for this innings
        inn_fow = [f for f in data['fow'] if f['innings_num'] == inn['innings_num']]
        for f in inn_fow:
            cursor.execute('''
                INSERT INTO CAFallOfWickets 
                (innings_id, wicket_num, score, player_out_id, overs)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                innings_id, f['wicket_num'], f['score'], f['player_out_id'], f['overs']
            ))
            
    # 6. Insert notes
    for note in data['notes']:
        cursor.execute("INSERT INTO CAMatchNotes (match_id, note_text) VALUES (?, ?)", (m['match_id'], note))
        
    return True

def process_file_worker(file_path):
    """Worker function for parallel processing."""
    try:
        data = parse_scorecard_html(file_path)
        return file_path, data, None
    except Exception as e:
        return file_path, None, str(e)

def run_pipeline(db_path, raw_dir, limit=None):
    """
    Scans the raw HTML directory, parses all files in parallel, and saves them to the DB.
    """
    logger.info("Initializing SQLite schemas...")
    conn = sqlite3.connect(db_path, timeout=60.0)
    
    # Enable schema initialization by calling the script
    schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
    if os.path.exists(schema_path):
        with open(schema_path, 'r', encoding='utf-8') as sf:
            conn.executescript(sf.read())
            
    conn.commit()
    
    # Gather HTML files
    all_files = [os.path.join(raw_dir, f) for f in os.listdir(raw_dir) if f.endswith('.html')]
    if limit:
        all_files = all_files[:limit]
        
    logger.info(f"Found {len(all_files)} raw HTML scorecards to parse...")
    
    # Process files in parallel to save time
    success_count = 0
    fail_count = 0
    
    # We use ThreadPool for DB inserts and multiprocessing for parsing
    # Or simple chunked execution
    cpu_count = os.cpu_count() or 4
    logger.info(f"Utilizing {cpu_count} CPU cores for parsing...")
    
    with ProcessPoolExecutor(max_workers=cpu_count) as executor:
        futures = {executor.submit(process_file_worker, f): f for f in all_files}
        
        # We will commit changes in transactions of 100 matches
        batch_size = 100
        batch_data = []
        
        for future in as_completed(futures):
            f_path, parsed_data, err = future.result()
            if err:
                logger.error(f"Error parsing {os.path.basename(f_path)}: {err}")
                fail_count += 1
            elif parsed_data:
                batch_data.append(parsed_data)
                success_count += 1
            else:
                fail_count += 1
                
            if len(batch_data) >= batch_size:
                # Save batch
                try:
                    for data in batch_data:
                        save_parsed_match(conn, data)
                    conn.commit()
                    logger.info(f"Saved batch of {len(batch_data)} matches. Progress: {success_count}/{len(all_files)}")
                except Exception as e:
                    conn.rollback()
                    logger.error(f"Failed to save batch: {e}")
                batch_data = []
                
        # Save remaining matches
        if batch_data:
            try:
                for data in batch_data:
                    save_parsed_match(conn, data)
                conn.commit()
                logger.info(f"Saved remaining {len(batch_data)} matches.")
            except Exception as e:
                conn.rollback()
                logger.error(f"Failed to save remaining batch: {e}")
                
    conn.close()
    logger.info(f"ETL pipeline complete! Success: {success_count}, Failed: {fail_count}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parse raw CricketArchive scorecards into SQLite DB.")
    parser.add_argument('--test', action='store_true', help='Test parsing a single scorecard file.')
    parser.add_argument('--limit', type=int, default=None, help='Limit number of matches processed.')
    parser.add_argument('--db', type=str, default='data/cricket_db.sqlite', help='Path to SQLite database.')
    parser.add_argument('--raw-dir', type=str, default='data/raw_ca', help='Directory with raw CA html files.')
    
    args = parser.parse_args()
    
    if args.test:
        test_file = None
        if os.path.exists(args.raw_dir):
            files = [f for f in os.listdir(args.raw_dir) if f.endswith('.html')]
            if files:
                test_file = os.path.join(args.raw_dir, files[0])
                
        if not test_file or not os.path.exists(test_file):
            logger.error("No test HTML file found in raw directory!")
        else:
            logger.info(f"Testing parser on file: {test_file}")
            res = parse_scorecard_html(test_file)
            import pprint
            pprint.pprint(res)
    else:
        run_pipeline(args.db, args.raw_dir, args.limit)
