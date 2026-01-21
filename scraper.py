#!/usr/bin/env python3
"""
Universal News Scraper v4.0
Aggregate news from multiple sources + Topic Discovery
Powered by Python & Bing RSS
"""

import os
import sys
import csv
import json
import hashlib
import time
import re
from datetime import datetime
from urllib.parse import urlparse
from pathlib import Path

import requests
import feedparser
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from htmldate import find_date
from urllib.parse import quote_plus
from rich.console import Console
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.text import Text
from rich import box

# Initialize Rich console
console = Console()

# Configuration file paths
CONFIG_FILE = Path(__file__).parent / ".scraper_config.json"
SOURCES_FILE = Path(__file__).parent / "sources.json"


def load_sources() -> dict:
    """Load news sources from sources.json file."""
    if SOURCES_FILE.exists():
        try:
            with open(SOURCES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("categories", {})
        except Exception as e:
            console.print(f"[yellow]⚠️ Could not load sources.json: {e}[/yellow]")
    return {}


class NewsScraper:
    """Main scraper class for news aggregation."""
    
    def __init__(self):
        self.ua = UserAgent()
        self.session = requests.Session()
        self.results = []
        self.seen_urls = set()
        self.stats = {}
        
    def get_headers(self):
        """Generate random headers to avoid blocking."""
        return {
            "User-Agent": self.ua.random,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }
    
    def normalize_url(self, url: str) -> str:
        """Normalize URL by adding https:// if missing."""
        url = url.strip()
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        return url
    
    def get_source_name(self, url: str) -> str:
        """Extract a friendly source name from URL."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.replace("www.", "")
            # Remove common prefixes/suffixes
            name = domain.split(".")[0].title()
            return name
        except:
            return "Unknown"
    
    def is_rss_feed(self, url: str, response: requests.Response) -> bool:
        """Detect if URL is an RSS feed."""
        content_type = response.headers.get("Content-Type", "").lower()
        if any(ct in content_type for ct in ["xml", "rss", "atom"]):
            return True
        if any(ext in url.lower() for ext in ["/feed", "/rss", ".xml", "atom"]):
            return True
        # Check content for RSS markers
        content_start = response.text[:500].lower()
        if "<rss" in content_start or "<feed" in content_start or "<channel" in content_start:
            return True
        return False
    
    def parse_date(self, date_str: str) -> datetime | None:
        """Parse various date formats."""
        if not date_str:
            return None
        
        formats = [
            "%Y-%m-%d",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S%z",
            "%a, %d %b %Y %H:%M:%S %z",
            "%a, %d %b %Y %H:%M:%S %Z",
            "%d %b %Y",
            "%B %d, %Y",
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue
        
        # Try htmldate as fallback
        try:
            result = find_date(date_str)
            if result:
                return datetime.strptime(result, "%Y-%m-%d")
        except:
            pass
        
        return None
    
    def matches_keywords(self, text: str, keywords: list) -> list:
        """Check if text contains any of the keywords (case-insensitive)."""
        if not keywords or keywords == ['']:
            return ['*']  # No filter, matches all
        
        text_lower = text.lower()
        matched = []
        for keyword in keywords:
            if keyword.lower().strip() in text_lower:
                matched.append(keyword.strip())
        return matched
    
    def get_url_hash(self, url: str) -> str:
        """Generate a hash for URL deduplication."""
        return hashlib.md5(url.encode()).hexdigest()
    
    def scrape_rss(self, url: str, content: str, keywords: list, start_date: datetime) -> list:
        """Parse RSS feed and extract articles."""
        articles = []
        feed = feedparser.parse(content)
        
        for entry in feed.entries:
            try:
                title = entry.get("title", "No Title")
                link = entry.get("link", "")
                
                # Skip if already seen
                url_hash = self.get_url_hash(link)
                if url_hash in self.seen_urls:
                    continue
                
                # Get date
                pub_date = None
                for date_field in ["published", "updated", "created"]:
                    if hasattr(entry, date_field):
                        pub_date = self.parse_date(getattr(entry, date_field))
                        if pub_date:
                            break
                
                # Date filter
                if pub_date and start_date and pub_date.date() < start_date.date():
                    continue
                
                # Get description
                description = ""
                if hasattr(entry, "summary"):
                    soup = BeautifulSoup(entry.summary, "html.parser")
                    description = soup.get_text()[:300].strip()
                elif hasattr(entry, "description"):
                    soup = BeautifulSoup(entry.description, "html.parser")
                    description = soup.get_text()[:300].strip()
                
                # Keyword matching (in title, link, or description)
                search_text = f"{title} {link} {description}"
                matched_keywords = self.matches_keywords(search_text, keywords)
                
                if matched_keywords:
                    self.seen_urls.add(url_hash)
                    articles.append({
                        "title": title,
                        "url": link,
                        "date": pub_date.strftime("%Y-%m-%d") if pub_date else "Unknown",
                        "description": description,
                        "source": self.get_source_name(url),
                        "matched_keywords": ", ".join(matched_keywords)
                    })
            except Exception as e:
                continue
        
        return articles
    
    def scrape_html(self, url: str, content: str, keywords: list, start_date: datetime) -> list:
        """Parse HTML page and extract articles."""
        articles = []
        soup = BeautifulSoup(content, "lxml")
        
        # Common article selectors
        article_selectors = [
            "article",
            ".post",
            ".entry",
            ".article",
            ".news-item",
            ".story",
            "[class*='article']",
            "[class*='post']",
        ]
        
        found_articles = []
        for selector in article_selectors:
            found = soup.select(selector)
            if found:
                found_articles.extend(found)
                break
        
        # Fallback to finding links
        if not found_articles:
            found_articles = soup.find_all("a", href=True)
        
        for article in found_articles[:50]:  # Limit to prevent overwhelming
            try:
                # Get link and title
                if article.name == "a":
                    link = article.get("href", "")
                    title = article.get_text().strip()
                else:
                    link_tag = article.find("a", href=True)
                    if not link_tag:
                        continue
                    link = link_tag.get("href", "")
                    title = link_tag.get_text().strip() or article.get_text()[:100].strip()
                
                if not link or not title or len(title) < 10:
                    continue
                
                # Normalize link
                if link.startswith("/"):
                    parsed = urlparse(url)
                    link = f"{parsed.scheme}://{parsed.netloc}{link}"
                elif not link.startswith("http"):
                    continue
                
                # Skip if already seen
                url_hash = self.get_url_hash(link)
                if url_hash in self.seen_urls:
                    continue
                
                # Try to extract date from article page
                pub_date = None
                try:
                    date_str = find_date(str(article))
                    if date_str:
                        pub_date = datetime.strptime(date_str, "%Y-%m-%d")
                except:
                    pass
                
                # Date filter
                if pub_date and start_date and pub_date.date() < start_date.date():
                    continue
                
                # Get description
                description = ""
                desc_tags = article.find_all(["p", "span", "div"], class_=re.compile(r"(excerpt|summary|desc)", re.I))
                if desc_tags:
                    description = desc_tags[0].get_text()[:300].strip()
                
                # Keyword matching
                search_text = f"{title} {link} {description}"
                matched_keywords = self.matches_keywords(search_text, keywords)
                
                if matched_keywords:
                    self.seen_urls.add(url_hash)
                    articles.append({
                        "title": title[:150],
                        "url": link,
                        "date": pub_date.strftime("%Y-%m-%d") if pub_date else "Unknown",
                        "description": description,
                        "source": self.get_source_name(url),
                        "matched_keywords": ", ".join(matched_keywords)
                    })
            except Exception:
                continue
        
        return articles
    
    def scrape_url(self, url: str, keywords: list, start_date: datetime) -> list:
        """Scrape a single URL (auto-detect RSS or HTML)."""
        url = self.normalize_url(url)
        articles = []
        
        try:
            response = self.session.get(
                url,
                headers=self.get_headers(),
                timeout=15,
                allow_redirects=True
            )
            response.raise_for_status()
            
            if self.is_rss_feed(url, response):
                articles = self.scrape_rss(url, response.text, keywords, start_date)
            else:
                articles = self.scrape_html(url, response.text, keywords, start_date)
            
            self.stats[url] = {"status": "✅ Success", "count": len(articles)}
            
        except requests.exceptions.Timeout:
            self.stats[url] = {"status": "⏱️ Timeout", "count": 0}
            console.print(f"  [yellow]⚠️ Timeout for {url}[/yellow]")
        except requests.exceptions.RequestException as e:
            self.stats[url] = {"status": "❌ Error", "count": 0}
            console.print(f"  [red]❌ Failed to fetch {url}: {str(e)[:50]}[/red]")
        except Exception as e:
            self.stats[url] = {"status": "❌ Error", "count": 0}
            console.print(f"  [red]❌ Error processing {url}: {str(e)[:50]}[/red]")
        
        return articles
    
    def scrape_single_article(self, url: str, topic: str, start_date: datetime) -> dict | None:
        """Scrape a single article page (for Google Search results)."""
        url = self.normalize_url(url)
        
        # Skip if already seen
        url_hash = self.get_url_hash(url)
        if url_hash in self.seen_urls:
            return None
        
        try:
            response = self.session.get(
                url,
                headers=self.get_headers(),
                timeout=15,
                allow_redirects=True
            )
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "lxml")
            
            # Extract title
            title = ""
            title_tag = soup.find("h1") or soup.find("title")
            if title_tag:
                title = title_tag.get_text().strip()[:200]
            
            if not title or len(title) < 10:
                return None
            
            # Extract description from meta or first paragraphs
            description = ""
            meta_desc = soup.find("meta", attrs={"name": "description"})
            if meta_desc and meta_desc.get("content"):
                description = meta_desc.get("content")[:300].strip()
            else:
                # Get first meaningful paragraphs
                paragraphs = soup.find_all("p")
                for p in paragraphs[:5]:
                    text = p.get_text().strip()
                    if len(text) > 50:
                        description = text[:300]
                        break
            
            # Extract date using htmldate
            pub_date = None
            try:
                date_str = find_date(response.text)
                if date_str:
                    pub_date = datetime.strptime(date_str, "%Y-%m-%d")
            except:
                pass
            
            # Date filter
            if pub_date and start_date and pub_date.date() < start_date.date():
                return None
            
            self.seen_urls.add(url_hash)
            self.stats[url] = {"status": "✅ Success", "count": 1}
            
            return {
                "title": title,
                "url": url,
                "date": pub_date.strftime("%Y-%m-%d") if pub_date else "Unknown",
                "description": description,
                "source": self.get_source_name(url),
                "matched_keywords": topic
            }
            
        except requests.exceptions.Timeout:
            self.stats[url] = {"status": "⏱️ Timeout", "count": 0}
            return None
        except requests.exceptions.RequestException:
            self.stats[url] = {"status": "❌ Error", "count": 0}
            return None
        except Exception:
            self.stats[url] = {"status": "❌ Error", "count": 0}
            return None
    
    def run(self, urls: list, keywords: list, start_date: datetime):
        """Run the scraper on multiple URLs."""
        self.results = []
        self.stats = {}
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            for url in urls:
                url = url.strip()
                if not url:
                    continue
                
                task = progress.add_task(f"[cyan]🔍 Scanning {url[:50]}...[/cyan]", total=None)
                articles = self.scrape_url(url, keywords, start_date)
                self.results.extend(articles)
                progress.remove_task(task)
                
                # Rate limiting
                time.sleep(1)
        
        return self.results
    
    def run_discovery(self, urls: list, topic: str, start_date: datetime):
        """Run the scraper on discovered URLs (single article mode)."""
        self.results = []
        self.stats = {}
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            for url in urls:
                url = url.strip()
                if not url:
                    continue
                
                task = progress.add_task(f"[cyan]🔍 Fetching {url[:50]}...[/cyan]", total=None)
                article = self.scrape_single_article(url, topic, start_date)
                if article:
                    self.results.append(article)
                progress.remove_task(task)
                
                # Rate limiting
                time.sleep(1.5)
        
        return self.results


def load_config() -> dict:
    """Load saved configuration."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {}


def save_config(config: dict):
    """Save configuration for future use."""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
    except:
        pass


def export_results(results: list, filename: str, export_format: str):
    """Export results to CSV and/or JSON."""
    if not results:
        return
    
    base_name = Path(filename).stem
    
    if export_format in ["csv", "both"]:
        csv_file = f"{base_name}.csv"
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)
        console.print(f"  [green]📄 CSV saved: {csv_file}[/green]")
    
    if export_format in ["json", "both"]:
        json_file = f"{base_name}.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        console.print(f"  [green]📋 JSON saved: {json_file}[/green]")


def show_banner():
    """Display the application header."""
    console.print()
    console.print(Panel(
        "[bold white]🌍 UNIVERSAL NEWS SCRAPER[/bold white] [dim]v4.0[/dim]\n\n"
        "[dim]Aggregate news from any topic • RSS Feeds • Web Scraping[/dim]\n"
        "[dim cyan]Powered by Python & Bing RSS[/dim cyan]",
        style="blue",
        border_style="bold blue",
        padding=(1, 4)
    ))
    console.print()


def show_preset_menu() -> list:
    """Display preset sources menu with categories and return selected URLs."""
    categories = load_sources()
    
    if not categories:
        console.print("[yellow]⚠️ No sources.json found. Enter URLs manually.[/yellow]")
        custom = Prompt.ask("[bold cyan]Enter URLs (comma-separated)[/bold cyan]")
        return [u.strip() for u in custom.split(",")]
    
    # Display categories
    console.print("\n[bold yellow]📋 Select a Category:[/bold yellow]\n")
    
    category_list = list(categories.keys())
    for idx, cat_name in enumerate(category_list, 1):
        source_count = len(categories[cat_name])
        console.print(f"  [{idx}] {cat_name} [dim]({source_count} sources)[/dim]")
    
    console.print(f"\n  [0] ✏️  Enter custom URLs\n")
    
    cat_choice = Prompt.ask(
        "[bold cyan]Select category[/bold cyan]", 
        choices=[str(i) for i in range(len(category_list) + 1)], 
        default="1"
    )
    
    if cat_choice == "0":
        custom = Prompt.ask("[bold cyan]Enter URLs (comma-separated)[/bold cyan]")
        return [u.strip() for u in custom.split(",")]
    
    # Get selected category
    selected_cat = category_list[int(cat_choice) - 1]
    sources = categories[selected_cat]
    
    # Display sources in category
    console.print(f"\n[bold green]📰 {selected_cat}:[/bold green]\n")
    
    for idx, source in enumerate(sources, 1):
        console.print(f"  [{idx}] {source['name']}")
    
    console.print(f"\n  [A] 🌐 [bold]ALL in this category[/bold]")
    console.print(f"  [0] ↩️  Back to categories\n")
    
    src_choice = Prompt.ask(
        "[bold cyan]Select sources (comma-separated, e.g., 1,2,3 or A for all)[/bold cyan]", 
        default="A"
    )
    
    if src_choice.upper() == "A":
        return [s["url"] for s in sources]
    elif src_choice == "0":
        return show_preset_menu()  # Recursion to go back
    else:
        urls = []
        choices = [c.strip() for c in src_choice.split(",")]
        for c in choices:
            try:
                idx = int(c) - 1
                if 0 <= idx < len(sources):
                    urls.append(sources[idx]["url"])
            except ValueError:
                continue
        return urls


def validate_date(date_str: str) -> datetime | None:
    """Validate and parse date string."""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str.strip(), "%Y-%m-%d")
    except ValueError:
        return None


def generate_bing_news_rss(topic: str) -> str:
    """Generate Bing News RSS feed URL for a topic."""
    encoded_topic = quote_plus(topic)
    return f"https://www.bing.com/news/search?q={encoded_topic}&format=RSS"


def run_topic_discovery():
    """Handle the Topic Discovery flow using Bing News RSS."""
    console.print(Panel.fit(
        "[bold]🕵️ TOPIC DISCOVERY ENGINE[/bold]\n"
        "[dim]Powered by Bing News RSS - 100% Reliable[/dim]",
        border_style="magenta"
    ))
    
    # Get topic with examples
    console.print("[dim]Examples: Bitcoin, AI, Elections, Sports, Olympiacos, Technology[/dim]")
    topic = Prompt.ask("\n[cyan]🔍 Enter your topic[/cyan]", default="Technology")
    
    # Generate Bing News RSS URL
    bing_rss_url = generate_bing_news_rss(topic)
    
    console.print(f"\n[bold green]📡 Generated Bing News RSS:[/bold green]")
    console.print(f"[dim]{bing_rss_url}[/dim]\n")
    
    # Optional: Add keyword filter
    kw_input = Prompt.ask(
        "[cyan]🔑 Additional keyword filter (empty for all articles)[/cyan]",
        default=""
    )
    keywords = [k.strip() for k in kw_input.split(",")] if kw_input else []
    
    # Get date filter
    start_date = None
    while True:
        date_input = Prompt.ask(
            "[cyan]📅 Start date filter (YYYY-MM-DD, empty for no filter)[/cyan]",
            default=""
        )
        if not date_input:
            break
        start_date = validate_date(date_input)
        if start_date:
            break
        console.print("[red]❌ Invalid date format. Use YYYY-MM-DD[/red]")
    
    # Get output filename
    output_file = Prompt.ask(
        "[cyan]💾 Output filename (without extension)[/cyan]",
        default=f"{topic.lower().replace(' ', '_')}_news"
    )
    
    # Get export format
    console.print("\n[bold yellow]📤 Export Format:[/bold yellow]")
    console.print("  [1] CSV only")
    console.print("  [2] JSON only")
    console.print("  [3] Both CSV + JSON\n")
    
    fmt_choice = Prompt.ask("[cyan]Choose format[/cyan]", choices=["1", "2", "3"], default="3")
    export_format = {"1": "csv", "2": "json", "3": "both"}[fmt_choice]
    
    # Return RSS URL as list for compatibility with scraper.run()
    return [bing_rss_url], topic, keywords, start_date, output_file, export_format


def show_summary(scraper: NewsScraper, results: list):
    """Display summary table."""
    console.print("\n")
    
    # Create summary table
    table = Table(
        title="📊 SCRAPING SUMMARY",
        box=box.ROUNDED,
        header_style="bold magenta",
        title_style="bold white"
    )
    
    table.add_column("Source", style="cyan", no_wrap=True)
    table.add_column("Articles", justify="center", style="green")
    table.add_column("Status", justify="center")
    
    for url, stat in scraper.stats.items():
        source_name = scraper.get_source_name(url)
        table.add_row(
            source_name[:25],
            str(stat["count"]),
            stat["status"]
        )
    
    console.print(table)
    console.print(f"\n[bold green]✅ Total articles found: {len(results)}[/bold green]\n")


def main():
    """Main entry point."""
    os.system("cls" if os.name == "nt" else "clear")
    show_banner()
    
    config = load_config()
    
    # Main menu
    console.print(Panel.fit(
        "[1] � Use previous settings\n"
        "[2] 📝 Enter new settings manually\n"
        "[3] 🕵️ Auto-Discover & Scrape by Topic\n"
        "[4] 📋 Choose from preset sources\n"
        "[5] ❌ Exit",
        title="[bold]Main Menu[/bold]",
        border_style="cyan"
    ))
    
    if config:
        console.print(f"[dim]Last run: URLs={len(config.get('urls', []))}, Keywords={config.get('keywords', [])}[/dim]\n")
    
    choice = Prompt.ask("[bold cyan]Your choice[/bold cyan]", choices=["1", "2", "3", "4", "5"], default="3")
    
    if choice == "5":
        console.print("[yellow]� Goodbye![/yellow]")
        sys.exit(0)
    
    # Handle Topic Discovery mode
    if choice == "3":
        urls, topic, keywords, start_date, output_file, export_format = run_topic_discovery()
        
        if not urls:
            console.print("[yellow]👋 No URLs to scrape. Goodbye![/yellow]")
            sys.exit(0)
        
        # Run RSS scraper (Bing News RSS is an RSS feed, so use run() not run_discovery())
        console.print("\n[bold green]🚀 Starting Bing News RSS scraper...[/bold green]\n")
        
        scraper = NewsScraper()
        results = scraper.run(urls, keywords, start_date)
        
        # Show summary
        show_summary(scraper, results)
        
        # Export results
        if results:
            console.print("[bold yellow]💾 Exporting results...[/bold yellow]\n")
            export_results(results, output_file, export_format)
        else:
            console.print("[yellow]⚠️ No articles found matching your criteria.[/yellow]")
        
        console.print("\n[bold cyan]🎉 Done! Happy hunting![/bold cyan]\n")
        return
    
    # Standard scraping modes
    urls = []
    keywords = []
    start_date = None
    output_file = "results"
    export_format = "both"
    
    if choice == "1" and config:
        urls = config.get("urls", [])
        keywords = config.get("keywords", [])
        start_date_str = config.get("start_date", "")
        start_date = validate_date(start_date_str)
        output_file = config.get("output_file", "results")
        export_format = config.get("export_format", "both")
        console.print("[green]✅ Loaded previous settings[/green]")
    
    elif choice == "4":
        urls = show_preset_menu()
    
    if not urls:  # choice == "2" or no URLs from presets
        console.print("\n[bold yellow]� Enter Scraping Configuration:[/bold yellow]\n")
        
        url_input = Prompt.ask(
            "[cyan]🔗 Enter URLs (comma-separated)[/cyan]",
            default="https://feeds.feedburner.com/TheHackersNews"
        )
        urls = [u.strip() for u in url_input.split(",")]
    
    # Get keywords if not loaded
    if not keywords:
        kw_input = Prompt.ask(
            "[cyan]🔑 Enter keywords (comma-separated, empty for all)[/cyan]",
            default=""
        )
        keywords = [k.strip() for k in kw_input.split(",")] if kw_input else []
    
    # Get start date if not loaded
    if not start_date:
        while True:
            date_input = Prompt.ask(
                "[cyan]📅 Start date (YYYY-MM-DD, empty for no filter)[/cyan]",
                default=""
            )
            if not date_input:
                break
            start_date = validate_date(date_input)
            if start_date:
                break
            console.print("[red]❌ Invalid date format. Use YYYY-MM-DD[/red]")
    
    # Get output filename
    if choice != "1":
        output_file = Prompt.ask(
            "[cyan]� Output filename (without extension)[/cyan]",
            default="results"
        )
    
    # Get export format
    if choice != "1":
        console.print("\n[bold yellow]📤 Export Format:[/bold yellow]")
        console.print("  [1] CSV only")
        console.print("  [2] JSON only")
        console.print("  [3] Both CSV + JSON\n")
        
        fmt_choice = Prompt.ask("[cyan]Choose format[/cyan]", choices=["1", "2", "3"], default="3")
        export_format = {"1": "csv", "2": "json", "3": "both"}[fmt_choice]
    
    # Save configuration
    new_config = {
        "urls": urls,
        "keywords": keywords,
        "start_date": start_date.strftime("%Y-%m-%d") if start_date else "",
        "output_file": output_file,
        "export_format": export_format,
        "last_run": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    save_config(new_config)
    
    # Run scraper
    console.print("\n[bold green]🚀 Starting scraper...[/bold green]\n")
    
    scraper = NewsScraper()
    results = scraper.run(urls, keywords, start_date)
    
    # Show summary
    show_summary(scraper, results)
    
    # Export results
    if results:
        console.print("[bold yellow]💾 Exporting results...[/bold yellow]\n")
        export_results(results, output_file, export_format)
    else:
        console.print("[yellow]⚠️ No articles found matching your criteria.[/yellow]")
    
    console.print("\n[bold cyan]🎉 Done! Happy hunting![/bold cyan]\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]👋 Interrupted by user. Goodbye![/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[red]❌ Unexpected error: {e}[/red]")
        sys.exit(1)
