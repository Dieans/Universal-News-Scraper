# 🌍 Universal News Scraper v4.0

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![RSS](https://img.shields.io/badge/Powered%20by-Bing%20RSS-orange.svg)](https://www.bing.com/news)

A powerful, terminal-based news aggregator that supports **RSS feeds**, **Web Scraping**, and **Topic Auto-Discovery** via Bing News RSS.

![Demo Screenshot](sreenshot.png)

---

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| 🕵️ **Auto-Discovery** | Find news on ANY topic (Crypto, Sports, Politics, AI) without knowing the URL |
| 📂 **Preset Categories** | 6 built-in categories with 30+ international news sources |
| 🛡️ **Anti-Blocking** | Random User-Agent rotation to bypass restrictions |
| 💾 **Dual Export** | Save results as CSV, JSON, or both |
| 🎨 **Modern UI** | Beautiful terminal interface powered by the `Rich` library |
| 📅 **Date Filtering** | Only get articles from a specific date onwards |
| 🔑 **Keyword Filtering** | Filter articles by multiple keywords |
| 🔄 **Settings Memory** | Remembers your last configuration for quick re-runs |

---

## 📂 Preset Categories

| Category | Sources |
|----------|---------|
| 📰 **International News** | BBC, CNN, Reuters, Al Jazeera, The Guardian, NPR |
| ⚽ **Sports** | ESPN, BBC Sport, Sky Sports, Bleacher Report |
| 💻 **Tech & Science** | TechCrunch, The Verge, Wired, Ars Technica, Space.com |
| 🔒 **Cybersecurity** | The Hacker News, BleepingComputer, Krebs, Dark Reading |
| 💰 **Business & Finance** | Bloomberg, CNBC, Financial Times, CoinDesk, CoinTelegraph |
| 🎬 **Entertainment** | Variety, Hollywood Reporter, IGN, Kotaku |

---

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/Universal-News-Scraper.git
cd Universal-News-Scraper
```

### 2. Create Virtual Environment (Recommended)

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the Scraper

```bash
python scraper.py
```

---

## 📖 Usage Guide

### Main Menu

```
╭─────────────────────────────────────────╮
│  🌍 UNIVERSAL NEWS SCRAPER v4.0         │
│  Powered by Python & Bing RSS           │
╰─────────────────────────────────────────╯

┌──────────────── Main Menu ─────────────────┐
│ [1] 🔄 Use previous settings               │
│ [2] 📝 Enter new settings manually         │
│ [3] 🕵️ Auto-Discover & Scrape by Topic     │  ← Recommended!
│ [4] 📋 Choose from preset sources          │
│ [5] ❌ Exit                                │
└────────────────────────────────────────────┘
```

### Option 3: Auto-Discover by Topic (Recommended)

1. Enter any topic (e.g., `Bitcoin`, `AI`, `Elections`, `Sports`)
2. The scraper generates a Bing News RSS feed automatically
3. Optionally add keyword filters
4. Set date filter (optional)
5. Choose export format (CSV/JSON/Both)
6. Results are saved automatically!

### Option 4: Preset Sources

1. Select a category (International, Sports, Tech, etc.)
2. Choose specific sources or select ALL
3. Add keyword filters (optional)
4. Export results

---

## 📤 Output Formats

### CSV Output (`results.csv`)

```csv
title,url,date,description,source,matched_keywords
"AI Revolution in 2026...",https://...,2026-01-20,"Artificial intelligence...",Techcrunch,"AI, technology"
```

### JSON Output (`results.json`)

```json
[
  {
    "title": "AI Revolution in 2026...",
    "url": "https://...",
    "date": "2026-01-20",
    "description": "Artificial intelligence...",
    "source": "Techcrunch",
    "matched_keywords": "AI, technology"
  }
]
```

---

## 🛠️ Requirements

```
requests>=2.31.0
beautifulsoup4>=4.12.0
feedparser>=6.0.0
fake-useragent>=1.4.0
htmldate>=1.6.0
rich>=13.7.0
lxml>=4.9.0
```

---

## 📁 Project Structure

```
Universal-News-Scraper/
├── scraper.py           # Main application
├── sources.json         # Preset RSS sources (editable)
├── requirements.txt     # Python dependencies
├── .scraper_config.json # Auto-saved settings
└── README.md            # This file
```

---

## ⚙️ Configuration

The scraper automatically saves your settings to `.scraper_config.json`:

```json
{
  "urls": ["https://techcrunch.com/feed/"],
  "keywords": ["AI", "startup"],
  "start_date": "2026-01-01",
  "output_file": "tech_news",
  "export_format": "both",
  "last_run": "2026-01-20 10:30:00"
}
```

---

## 📌 Examples

### Example 1: Find Bitcoin News

```
Select option: 3
Enter topic: Bitcoin
Keywords: (empty for all)
Export format: Both
→ Saves bitcoin_news.csv and bitcoin_news.json
```

### Example 2: Scrape All Cybersecurity Sources

```
Select option: 4
Select category: 4 (Cybersecurity)
Select sources: A (ALL)
Keywords: ransomware, CVE
→ Filters articles containing "ransomware" or "CVE"
```

### Example 3: Quick Re-run

```
Select option: 1
→ Uses your previous settings instantly
```

---

## ⚠️ Disclaimer

This tool is intended for **educational and research purposes only**. 

- Always respect websites' Terms of Service
- Don't overwhelm servers with excessive requests
- Use responsibly for legitimate research and news aggregation

---

## 📄 License

MIT License - Feel free to use and modify!

---

## 🔄 Changelog

### v4.0 (Current)
- 🎨 Complete UI rebrand - "Universal News Scraper"
- 🌐 Switched from Google Search to **Bing News RSS** (no rate limits!)
- 📂 6 international preset categories with 30+ sources
- 🗑️ Removed deprecated dependencies
- 📖 Updated documentation

### v3.0
- Added Topic Discovery via Google Search
- Cybersecurity-focused preset sources

### v2.0
- Initial release with RSS/HTML scraping
- Keyword and date filtering

---

**Happy Scraping! 🌍📰**
