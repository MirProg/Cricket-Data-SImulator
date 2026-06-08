import { getDb } from '@/lib/db';
import { NextResponse } from 'next/server';

export async function GET(request) {
  const { searchParams } = new URL(request.url);
  const q = searchParams.get('q');
  const type = searchParams.get('type') || 'player';

  if (!q || q.length < 3) {
    return NextResponse.json({ error: 'Search query must be at least 3 characters long.' }, { status: 400 });
  }

  const db = getDb();
  let results = [];

  try {
    if (type === 'player') {
      const stmt = db.prepare(`
        SELECT player_id, player_name as name, bio_summary, image_url 
        FROM Players 
        WHERE player_name LIKE ? 
        LIMIT 20
      `);
      results = stmt.all(`%${q}%`);
    } else if (type === 'venue') {
      const stmt = db.prepare(`
        SELECT venue_id, venue_name as name, bio_summary, image_url 
        FROM Venues 
        WHERE venue_name LIKE ? 
        LIMIT 20
      `);
      results = stmt.all(`%${q}%`);
    } else if (type === 'team') {
      const stmt = db.prepare(`
        SELECT 
            id as match_id,
            match_date,
            teams,
            venue_name,
            series,
            result_string,
            toss_winner
        FROM ScrapedMatches
        WHERE 
            teams LIKE '%' || ? || '%' 
            OR venue_name LIKE '%' || ? || '%'
            OR series LIKE '%' || ? || '%'
            OR match_date LIKE '%' || ? || '%'
        LIMIT 20
      `);
      results = stmt.all(q, q, q, q);
    } else if (type === 'date') {
      const stmt = db.prepare(`
        SELECT m.id, m.url, m.teams, m.match_date, m.season, v.venue_name
        FROM ScrapedMatches m
        LEFT JOIN Venues v ON m.venue_id = v.venue_id
        WHERE m.match_date LIKE ? OR m.season LIKE ?
        LIMIT 50
      `);
      results = stmt.all(`%${q}%`, `%${q}%`);
    } else {
      return NextResponse.json({ error: 'Invalid search type.' }, { status: 400 });
    }

    return NextResponse.json({ results });
  } catch (err) {
    console.error('Search error:', err);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}
