use reqwest::{Client, cookie::Jar};
use rusqlite::{params, Connection};
use scraper::{Html, Selector};
use std::sync::Arc;
use std::sync::Mutex;
use std::process::Command;
use tokio::sync::Semaphore;
use tokio::time::{sleep, Duration};
use indicatif::{ProgressBar, ProgressStyle};
use regex::Regex;
use anyhow::{Result, anyhow};
use std::time::Instant;

const MAX_WORKERS: usize = 50;
const RETRY_DELAY: u64 = 1;
const DB_PATH: &str = r"C:\Users\seo\.local\bin\cricket_simulator\data\master_archive.sqlite";

struct VpnLock {
    is_toggling: bool,
}

fn toggle_vpn(lock: &mut VpnLock) -> Result<()> {
    if lock.is_toggling { return Ok(()); }
    lock.is_toggling = true;
    
    println!(">>> CLOUDFLARE BLOCK (403) DETECTED. COOLING DOWN FOR 30 SECONDS... <<<");
    std::thread::sleep(Duration::from_secs(30));
    println!(">>> COOLDOWN COMPLETE. RESUMING... <<<");
    
    lock.is_toggling = false;
    Ok(())
}

fn extract_cookies() -> Arc<Jar> {
    let jar = Arc::new(Jar::default());
    
    // We will call out to python to quickly get the cookies since browser_cookie3 
    // handles all the Firefox DB decryption which is hard to do natively in Rust
    let output = Command::new("python")
        .arg("-c")
        .arg("import browser_cookie3; cj = browser_cookie3.firefox(); print(','.join([f'{c.name}={c.value}' for c in cj if 'cricketarchive' in c.domain]))")
        .output()
        .expect("Failed to execute python cookie extractor");
        
    let cookie_str = String::from_utf8_lossy(&output.stdout);
    let url = "https://cricketarchive.com".parse::<reqwest::Url>().unwrap();
    
    for c in cookie_str.trim().split(',') {
        if !c.is_empty() {
            jar.add_cookie_str(c, &url);
        }
    }
    jar
}

fn ensure_tables(conn: &Connection) -> Result<()> {
    conn.execute_batch(
        "
        CREATE TABLE IF NOT EXISTS ScrapedMatches (
            match_id INTEGER PRIMARY KEY,
            title TEXT, series TEXT, venue TEXT, date_text TEXT,
            format TEXT, toss TEXT, result TEXT, balls_per_over TEXT
        );
        CREATE TABLE IF NOT EXISTS ScrapedInnings (
            id INTEGER PRIMARY KEY AUTOINCREMENT, match_id INTEGER,
            innings_number INTEGER, batting_team TEXT, total_runs INTEGER,
            total_wickets INTEGER, total_overs TEXT,
            FOREIGN KEY(match_id) REFERENCES ScrapedMatches(match_id)
        );
        CREATE TABLE IF NOT EXISTS ScrapedBatting (
            id INTEGER PRIMARY KEY AUTOINCREMENT, match_id INTEGER,
            innings_number INTEGER, player_name TEXT, dismissal TEXT,
            runs INTEGER, balls TEXT, mins TEXT, fours TEXT, sixes TEXT,
            FOREIGN KEY(match_id) REFERENCES ScrapedMatches(match_id)
        );
        CREATE TABLE IF NOT EXISTS ScrapedBowling (
            id INTEGER PRIMARY KEY AUTOINCREMENT, match_id INTEGER,
            innings_number INTEGER, player_name TEXT, overs TEXT,
            maidens TEXT, runs INTEGER, wickets INTEGER, wides TEXT, no_balls TEXT,
            FOREIGN KEY(match_id) REFERENCES ScrapedMatches(match_id)
        );
        CREATE TABLE IF NOT EXISTS ScrapeProgress (
            key TEXT PRIMARY KEY, value TEXT
        );
        "
    )?;
    Ok(())
}

// Minimal placeholder parser for speed demonstration
fn parse_and_save(html: &str, match_id: i64, conn: &Connection) -> bool {
    let document = Html::parse_document(html);
    let table_sel = Selector::parse("table").unwrap();
    let tr_sel = Selector::parse("tr").unwrap();
    let td_sel = Selector::parse("td, th").unwrap();
    
    let mut tables = document.select(&table_sel).peekable();
    if tables.peek().is_none() { return false; }
    
    let meta_table = tables.next().unwrap();
    let mut title = String::new();
    let mut venue = String::new();
    
    for row in meta_table.select(&tr_sel) {
        let cells: Vec<String> = row.select(&td_sel).map(|c| c.text().collect::<Vec<_>>().concat().trim().to_string()).collect();
        if cells.len() >= 2 {
            let label = cells[0].to_lowercase();
            if label.contains("venue") { venue = cells[1].clone(); }
            else if title.is_empty() { title = cells[1].clone(); }
        }
    }
    
    conn.execute(
        "INSERT OR REPLACE INTO ScrapedMatches (match_id, title, venue, series, date_text, format, toss, result, balls_per_over) VALUES (?1, ?2, ?3, '', '', '', '', '', '')",
        params![match_id, title, venue]
    ).unwrap_or(0);
    
    true
}

async fn fetch_worker(
    client: Client, 
    match_id: i64, 
    sem: Arc<Semaphore>, 
    vpn_lock: Arc<Mutex<VpnLock>>
) -> Result<bool> {
    let _permit = sem.acquire().await?;
    let url = format!("https://cricketarchive.com/Archive/Scorecards/{}/{}.html", match_id / 1000, match_id);
    
    loop {
        match client.get(&url).send().await {
            Ok(resp) => {
                let status = resp.status();
                if status.as_u16() == 403 {
                    {
                        let mut lock = vpn_lock.lock().unwrap();
                        let _ = toggle_vpn(&mut lock);
                    }
                    sleep(Duration::from_secs(RETRY_DELAY)).await;
                    continue;
                }
                if !status.is_success() { return Ok(false); }
                
                let text = resp.text().await?;
                if text.contains("Access Denied") {
                    {
                        let mut lock = vpn_lock.lock().unwrap();
                        let _ = toggle_vpn(&mut lock);
                    }
                    sleep(Duration::from_secs(RETRY_DELAY)).await;
                    continue;
                }
                
                let conn = Connection::open(DB_PATH)?;
                return Ok(parse_and_save(&text, match_id, &conn));
            },
            Err(_) => {
                sleep(Duration::from_secs(RETRY_DELAY)).await;
            }
        }
    }
}

#[tokio::main]
async fn main() -> Result<()> {
    let start_id = 1;
    let end_id = 900000;
    
    println!("Connecting to Database...");
    let conn = Connection::open(DB_PATH)?;
    ensure_tables(&conn)?;
    
    let mut last_id: i64 = 0;
    if let Ok(val) = conn.query_row("SELECT value FROM ScrapeProgress WHERE key='last_match_id'", [], |row| row.get::<_, String>(0)) {
        last_id = val.parse().unwrap_or(0);
    }
    
    let actual_start = if last_id > 0 { last_id + 1 } else { start_id };
    println!("Resuming from Match ID {}", actual_start);
    
    let jar = extract_cookies();
    let client = reqwest::Client::builder()
        .user_agent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        .cookie_provider(jar.clone())
        .timeout(std::time::Duration::from_secs(15))
        .build()?;
        
    let sem = Arc::new(Semaphore::new(MAX_WORKERS));
    let vpn_lock = Arc::new(Mutex::new(VpnLock { is_toggling: false }));
    
    let pb = ProgressBar::new((end_id - actual_start) as u64);
    pb.set_style(ProgressStyle::default_bar()
        .template("[{elapsed_precise}] [{bar:40.cyan/blue}] {pos}/{len} ({per_sec}) {msg}")?
        .progress_chars("#>-"));
        
    let start_time = Instant::now();
    let mut success_count = 0;
    
    const BATCH_SIZE: i64 = 5000;
    
    for batch_start in (actual_start..=end_id).step_by(BATCH_SIZE as usize) {
        let batch_end = std::cmp::min(batch_start + BATCH_SIZE - 1, end_id);
        let mut tasks = Vec::new();
        
        for match_id in batch_start..=batch_end {
            let c = client.clone();
            let s = sem.clone();
            let v = vpn_lock.clone();
            tasks.push(tokio::spawn(async move {
                fetch_worker(c, match_id, s, v).await
            }));
        }
        
        for task in tasks {
            if let Ok(Ok(true)) = task.await {
                success_count += 1;
            }
            pb.inc(1);
        }
        
        conn.execute("INSERT OR REPLACE INTO ScrapeProgress (key, value) VALUES ('last_match_id', ?1)", params![batch_end.to_string()])?;
    }
    
    pb.finish_with_message("Complete!");
    println!("Total successful scorecards parsed: {}", success_count);
    println!("Time taken: {:?}", start_time.elapsed());
    
    Ok(())
}
