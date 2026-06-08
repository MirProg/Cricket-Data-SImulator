import { getDb } from '@/lib/db';
import { NextResponse } from 'next/server';

export async function GET(request, { params }) {
  const { id } = params;
  if (!id) return NextResponse.json({ error: 'Missing match ID' }, { status: 400 });

  const db = getDb();

  try {
    const matchStmt = db.prepare(`
      SELECT m.*, v.name as venue_name, v.image_url as venue_image
      FROM ScrapedMatches m
      LEFT JOIN Venues v ON m.venue_id = v.venue_id
      WHERE m.id = ?
    `);
    const match = matchStmt.get(id);

    if (!match) {
      return NextResponse.json({ error: 'Match not found' }, { status: 404 });
    }

    const inningsStmt = db.prepare(`SELECT * FROM ScrapedInnings WHERE match_id = ? ORDER BY innings_number ASC`);
    const innings = inningsStmt.all(id);

    const battingStmt = db.prepare(`SELECT * FROM ScrapedBatting WHERE match_id = ? ORDER BY innings_number ASC, id ASC`);
    const batting = battingStmt.all(id);

    const bowlingStmt = db.prepare(`SELECT * FROM ScrapedBowling WHERE match_id = ? ORDER BY innings_number ASC, id ASC`);
    const bowling = bowlingStmt.all(id);

    const fowStmt = db.prepare(`SELECT * FROM ScrapedFOW WHERE match_id = ? ORDER BY innings_number ASC, id ASC`);
    const fow = fowStmt.all(id);

    return NextResponse.json({
      match,
      innings,
      batting,
      bowling,
      fow
    });
  } catch (err) {
    console.error('Match fetch error:', err);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}
