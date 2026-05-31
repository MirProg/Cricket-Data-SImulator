import json
import os

db_path = 'data/cricbuzz_history_db.jsonl'
temp_path = 'data/cricbuzz_history_db_clean.jsonl'

if not os.path.exists(db_path):
    print("No history file found to organize.")
    exit(0)

cricbuzz_entries = {}
cricketarchive_entries = {}
other_entries = {}

total_lines = 0
malformed_lines = 0

with open(db_path, 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        total_lines += 1
        try:
            data = json.loads(line)
            source = data.get('source', '')
            
            if source == 'cricbuzz':
                match_id = data.get('match_id')
                if match_id:
                    # Keep the first/oldest or last/newest? Let's keep the newest or the one that has a title
                    if match_id not in cricbuzz_entries:
                        cricbuzz_entries[match_id] = data
                    else:
                        # Update if the existing one doesn't have a title or is generic
                        existing = cricbuzz_entries[match_id]
                        if "Live Cricket Score" in existing.get('title', '') and "Live Cricket Score" not in data.get('title', ''):
                            cricbuzz_entries[match_id] = data
            elif source == 'cricketarchive':
                ca_id = data.get('id')
                if ca_id:
                    cricketarchive_entries[ca_id] = data
            else:
                # Other sources (e.g. espn or other keys)
                key = (source, data.get('id') or data.get('match_id') or str(len(other_entries)))
                other_entries[key] = data
        except Exception as e:
            malformed_lines += 1

print(f"Total lines read: {total_lines}")
print(f"Malformed lines: {malformed_lines}")
print(f"Unique Cricbuzz entries: {len(cricbuzz_entries)}")
print(f"Unique CricketArchive entries: {len(cricketarchive_entries)}")
print(f"Unique other entries: {len(other_entries)}")

# Sort entries
# Sort cricbuzz by ID (as integer)
sorted_cricbuzz = sorted(cricbuzz_entries.values(), key=lambda x: int(x['match_id']) if x['match_id'].isdigit() else 0)

# Sort cricketarchive by ID (as integer)
sorted_ca = sorted(cricketarchive_entries.values(), key=lambda x: int(x['id']) if x['id'].isdigit() else 0)

# Sort other entries
sorted_other = sorted(other_entries.values(), key=lambda x: (x.get('source', ''), x.get('id') or x.get('match_id') or ''))

# Write back in order
with open(temp_path, 'w', encoding='utf-8') as f:
    # Write other entries first
    for entry in sorted_other:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    # Write Cricbuzz entries
    for entry in sorted_cricbuzz:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    # Write CricketArchive entries
    for entry in sorted_ca:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')

# Overwrite original file
os.replace(temp_path, db_path)
print("Deduplication and organization complete!")
