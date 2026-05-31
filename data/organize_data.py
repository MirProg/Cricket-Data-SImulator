import json
import os

def organize_file(db_path, id_key='match_id', source_name=None):
    if not os.path.exists(db_path):
        print(f"File {db_path} not found.")
        return
        
    temp_path = db_path + '.tmp'
    entries = {}
    total_lines = 0
    
    with open(db_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            total_lines += 1
            try:
                data = json.loads(line)
                source = data.get('source', source_name)
                
                # Retrieve match ID
                match_id = data.get(id_key) or data.get('match_id') or data.get('id')
                if match_id:
                    match_id_str = str(match_id)
                    key = (source, match_id_str)
                    
                    if key not in entries:
                        entries[key] = data
                    else:
                        # Deduplicate: keep the one with a more descriptive title if available
                        existing = entries[key]
                        existing_title = existing.get('title', '')
                        new_title = data.get('title', '')
                        if len(new_title) > len(existing_title) and "Live Cricket Score" not in new_title:
                            entries[key] = data
            except Exception:
                pass
                
    # Sort entries by ID numerically
    sorted_entries = sorted(
        entries.values(),
        key=lambda x: int(x.get(id_key) or x.get('match_id') or x.get('id')) if str(x.get(id_key) or x.get('match_id') or x.get('id')).isdigit() else 0
    )
    
    # Write back
    with open(temp_path, 'w', encoding='utf-8') as f:
        for entry in sorted_entries:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
            
    os.replace(temp_path, db_path)
    print(f"Organized {db_path}: read {total_lines} lines -> wrote {len(sorted_entries)} unique sorted entries. Removed {total_lines - len(sorted_entries)} duplicates.")

if __name__ == "__main__":
    # Organize Cricbuzz history
    organize_file('data/cricbuzz_history_db.jsonl', id_key='match_id', source_name='cricbuzz')
    
    # Organize ESPN history
    organize_file('data/espn_history_db.jsonl', id_key='match_id', source_name='espn')
    
    print("Deduplication and organization complete for all histories!")
