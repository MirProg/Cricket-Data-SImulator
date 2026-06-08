import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

export async function GET(request) {
  const { searchParams } = new URL(request.url);
  const file_path = searchParams.get('path');

  if (!file_path) {
    return new NextResponse('Missing path parameter', { status: 400 });
  }

  // Ensure it's pointing to the D drive cricket_media folder to prevent LFI
  if (!file_path.startsWith('D:\\cricket_media')) {
     return new NextResponse('Forbidden path', { status: 403 });
  }

  try {
    if (!fs.existsSync(file_path)) {
      return new NextResponse('Image not found', { status: 404 });
    }

    const imageBuffer = fs.readFileSync(file_path);
    let contentType = 'image/jpeg';
    if (file_path.toLowerCase().endsWith('.png')) contentType = 'image/png';
    if (file_path.toLowerCase().endsWith('.webp')) contentType = 'image/webp';
    if (file_path.toLowerCase().endsWith('.gif')) contentType = 'image/gif';

    return new NextResponse(imageBuffer, {
      status: 200,
      headers: {
        'Content-Type': contentType,
        'Cache-Control': 'public, max-age=86400'
      }
    });

  } catch (err) {
    console.error('Media fetching error:', err);
    return new NextResponse('Internal Server Error', { status: 500 });
  }
}
