import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import time
import random
import json
import os
import re
from urllib.parse import urlparse, urljoin

# Rotating set of user agents to appear more like different browsers
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.2 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/109.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 16_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.2 Mobile/15E148 Safari/604.1'
]

def get_headers():
    """Generate random headers to make requests look more like a browser"""
    return {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0',
        'Referer': 'https://www.google.com/'
    }

def create_session():
    """Create a session with cookies enabled for better site compatibility"""
    session = requests.Session()
    # Add cookie consent for European sites
    session.cookies.set('cookieconsent_status', 'dismiss', domain='.yahoo.com')
    session.cookies.set('cookieconsent_status', 'dismiss', domain='.bloomberg.com')
    session.cookies.set('cookieconsent_status', 'dismiss', domain='.marketwatch.com')
    session.cookies.set('cookieconsent_status', 'dismiss', domain='.cnbc.com')
    return session

def fetch_page(url, max_retries=3):
    """Fetch a page with retries and better error handling"""
    session = create_session()
    
    for attempt in range(max_retries):
        try:
            # Add a longer delay between attempts
            if attempt > 0:
                time.sleep(random.uniform(3, 7))
            
            print(f"Attempt {attempt+1} to fetch: {url}")
            headers = get_headers()  # Get new headers for each attempt
            
            response = session.get(url, headers=headers, timeout=20)
            
            # Print status code for debugging
            print(f"Status code: {response.status_code}")
            
            if response.status_code == 200:
                return response
            elif response.status_code in [403, 401, 429]:
                print(f"Access denied with status {response.status_code}. The site may be blocking web scraping.")
                time.sleep(random.uniform(5, 10))  # Longer wait for rate limiting
            else:
                print(f"Failed with status code {response.status_code}, retrying...")
                
        except requests.exceptions.RequestException as e:
            print(f"Request error: {e}")
            
    return None

def scrape_yahoo_finance():
    """Scrape tech stock news from Yahoo Finance"""
    # Yahoo Finance tech stocks page
    url = "https://finance.yahoo.com/topic/tech/"
    print(f"Scraping: {url}")
    
    response = fetch_page(url)
    if not response:
        # Try an alternative Yahoo Finance URL
        url = "https://finance.yahoo.com/news/"
        print(f"Trying alternative: {url}")
        response = fetch_page(url)
        if not response:
            return []
    
    soup = BeautifulSoup(response.text, 'html.parser')
    articles = []
    
    # Save debug HTML
    os.makedirs("debug", exist_ok=True)
    with open("debug/yahoo_finance.html", "w", encoding="utf-8") as f:
        f.write(soup.prettify())
    
    # Yahoo Finance has a few different article layouts
    # Try multiple selectors to find article containers
    
    # First approach - stream items
    stream_items = soup.find_all('div', {'class': 'Ov(h)'})
    
    # Second approach - common article containers
    if not stream_items:
        stream_items = soup.find_all('li', {'class': 'js-stream-content'})
    
    # Third approach - fallback to any div with a headline
    if not stream_items:
        stream_items = soup.find_all('h3')
        if stream_items:
            # Convert h3 elements to their parent containers
            stream_items = [h3.parent.parent for h3 in stream_items if h3.parent and h3.parent.parent]
    
    print(f"Found {len(stream_items)} potential Yahoo Finance articles")
    
    for item in stream_items:
        try:
            # Extract headline - look for h3 or h2
            headline_element = item.find('h3') or item.find('h2')
            if not headline_element:
                continue
                
            headline = headline_element.text.strip()
            
            # Skip non-news items
            if any(skip in headline.lower() for skip in ['advertisement', 'sponsor', 'promoted']):
                continue
                
            # Extract link
            link_element = headline_element.find('a')
            if not link_element and hasattr(headline_element, 'parent'):
                link_element = headline_element.parent if headline_element.parent.name == 'a' else None
                
            if link_element and 'href' in link_element.attrs:
                link = link_element['href']
                # Fix relative URLs
                if link.startswith('/'):
                    link = 'https://finance.yahoo.com' + link
            else:
                continue  # Skip if no link found
                
            # Extract summary
            summary_element = item.find('p')
            summary = summary_element.text.strip() if summary_element else ""
            
            # Extract date/source
            meta_element = item.find('span', {'class': 'C(#959595)'}) or item.find('div', {'class': 'C(#959595)'})
            if meta_element:
                meta_text = meta_element.text.strip()
                # Yahoo often formats as "Source · Time"
                if '·' in meta_text:
                    source, published_date = meta_text.split('·', 1)
                else:
                    source = "Yahoo Finance"
                    published_date = meta_text
            else:
                source = "Yahoo Finance"
                published_date = "Unknown"
            
            articles.append({
                'headline': headline,
                'summary': summary,
                'link': link,
                'published_date': published_date.strip(),
                'source': source.strip(),
                'scraped_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'category': 'tech stocks'
            })
            
        except Exception as e:
            print(f"Error extracting Yahoo Finance article: {e}")
    
    return articles

def scrape_cnbc_finance():
    """Scrape tech stock news from CNBC Finance section"""
    url = "https://www.cnbc.com/technology/"
    print(f"Scraping: {url}")
    
    response = fetch_page(url)
    if not response:
        # Try alternative CNBC URL
        url = "https://www.cnbc.com/investing/"
        print(f"Trying alternative: {url}")
        response = fetch_page(url)
        if not response:
            return []
    
    soup = BeautifulSoup(response.text, 'html.parser')
    articles = []
    
    # Save debug HTML
    os.makedirs("debug", exist_ok=True)
    with open("debug/cnbc_finance.html", "w", encoding="utf-8") as f:
        f.write(soup.prettify())
    
    # CNBC uses various card layouts
    card_containers = []
    
    # Try multiple selectors to find article cards
    selectors = [
        ('div', {'class': 'Card-titleContainer'}),
        ('div', {'class': 'Card-standardBreakerCard'}),
        ('div', {'class': 'Card-mediaCard'}),
        ('div', {'data-test': 'Card'})
    ]
    
    for tag, attrs in selectors:
        cards = soup.find_all(tag, attrs)
        if cards:
            card_containers.extend(cards)
    
    print(f"Found {len(card_containers)} potential CNBC articles")
    
    for item in card_containers:
        try:
            # Extract headline - multiple possible locations
            headline_element = (
                item.find('a', {'class': 'Card-title'}) or 
                item.find('span', {'class': 'Card-title'}) or
                item.find('h3', {'class': 'Card-title'})
            )
            
            if not headline_element:
                continue
                
            headline = headline_element.text.strip()
            
            # Skip non-news items
            if any(skip in headline.lower() for skip in ['advertisement', 'sponsored', 'promoted', 'paid program']):
                continue
                
            # Extract link - either from the headline or a parent/child
            if headline_element.name == 'a' and 'href' in headline_element.attrs:
                link = headline_element['href']
            else:
                link_element = item.find('a')
                link = link_element['href'] if link_element and 'href' in link_element.attrs else ""
                
            # Extract timestamp/date
            time_element = (
                item.find('span', {'class': 'Card-time'}) or 
                item.find('time') or
                item.find('span', {'data-test': 'Card-time'})
            )
            published_date = time_element.text.strip() if time_element else "Unknown"
            
            articles.append({
                'headline': headline,
                'summary': "",  # CNBC doesn't always have easily accessible summaries
                'link': link,
                'published_date': published_date,
                'source': "CNBC",
                'scraped_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'category': 'tech stocks'
            })
            
        except Exception as e:
            print(f"Error extracting CNBC article: {e}")
    
    return articles

def scrape_bloomberg_tech():
    """Scrape tech stock news from Bloomberg"""
    url = "https://www.bloomberg.com/technology"
    print(f"Scraping: {url}")
    
    response = fetch_page(url)
    if not response:
        # Try alternative Bloomberg URL
        url = "https://www.bloomberg.com/markets"
        print(f"Trying alternative: {url}")
        response = fetch_page(url)
        if not response:
            return []
    
    soup = BeautifulSoup(response.text, 'html.parser')
    articles = []
    
    # Save debug HTML
    os.makedirs("debug", exist_ok=True)
    with open("debug/bloomberg.html", "w", encoding="utf-8") as f:
        f.write(soup.prettify())
    
    # Bloomberg uses various article layouts
    # Try to find story packages
    story_packages = soup.find_all('div', {'class': 'story-package'})
    story_list = []
    
    if story_packages:
        for package in story_packages:
            stories = package.find_all('article') or package.find_all('div', {'class': 'story-list-story'})
            story_list.extend(stories)
    
    # If no stories found, try more generic article selectors
    if not story_list:
        story_list = soup.find_all('article') or soup.find_all('div', {'class': ['story-list-story', 'storyItem']})
    
    print(f"Found {len(story_list)} potential Bloomberg articles")
    
    for item in story_list:
        try:
            # Extract headline - multiple possible locations
            headline_element = (
                item.find('h3') or 
                item.find('h2') or
                item.find('h1')
            )
            
            if not headline_element:
                continue
                
            headline = headline_element.text.strip()
            
            # Skip non-news items
            if any(skip in headline.lower() for skip in ['advertisement', 'sponsored', 'promoted']):
                continue
                
            # Extract link - try multiple approaches
            link_element = headline_element.find('a')
            if not link_element and hasattr(headline_element, 'parent'):
                link_element = headline_element.parent if headline_element.parent.name == 'a' else None
                
            if link_element and 'href' in link_element.attrs:
                link = link_element['href']
                # Fix relative URLs
                if link.startswith('/'):
                    link = 'https://www.bloomberg.com' + link
            else:
                continue  # Skip if no link
                
            # Extract summary if available
            summary_element = item.find('p')
            summary = summary_element.text.strip() if summary_element else ""
            
            # Extract date if available
            time_element = item.find('time')
            published_date = time_element.text.strip() if time_element else "Unknown"
            
            articles.append({
                'headline': headline,
                'summary': summary,
                'link': link,
                'published_date': published_date,
                'source': "Bloomberg",
                'scraped_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'category': 'tech stocks'
            })
            
        except Exception as e:
            print(f"Error extracting Bloomberg article: {e}")
    
    return articles

def scrape_marketwatch_tech():
    """Scrape tech stock news from MarketWatch"""
    url = "https://www.marketwatch.com/investing/technology"
    print(f"Scraping: {url}")
    
    response = fetch_page(url)
    if not response:
        # Try alternative URL
        url = "https://www.marketwatch.com/latest-news"
        print(f"Trying alternative: {url}")
        response = fetch_page(url)
        if not response:
            return []
    
    soup = BeautifulSoup(response.text, 'html.parser')
    articles = []
    
    # Save debug HTML
    os.makedirs("debug", exist_ok=True)
    with open("debug/marketwatch.html", "w", encoding="utf-8") as f:
        f.write(soup.prettify())
    
    # MarketWatch article containers
    story_containers = soup.find_all('div', {'class': 'article__content'})
    
    if not story_containers:
        # Try alternative selectors
        story_containers = soup.find_all('div', {'class': ['story', 'story__body']})
    
    print(f"Found {len(story_containers)} potential MarketWatch articles")
    
    for item in story_containers:
        try:
            # Extract headline
            headline_element = (
                item.find('h3', {'class': 'article__headline'}) or 
                item.find('h2') or 
                item.find('h3')
            )
            
            if not headline_element:
                continue
                
            headline = headline_element.text.strip()
            
            # Skip non-news items
            if any(skip in headline.lower() for skip in ['advertisement', 'sponsored content', 'press release']):
                continue
                
            # Extract link
            link_element = headline_element.find('a')
            if not link_element and hasattr(headline_element, 'parent'):
                link_element = headline_element.parent if headline_element.parent.name == 'a' else None
                
            if link_element and 'href' in link_element.attrs:
                link = link_element['href']
                # Fix relative URLs
                if not link.startswith('http'):
                    link = 'https://www.marketwatch.com' + link
            else:
                continue  # Skip if no link
                
            # Extract summary
            summary_element = item.find('p', {'class': 'article__summary'}) or item.find('p')
            summary = summary_element.text.strip() if summary_element else ""
            
            # Extract date and source
            meta_element = item.find('div', {'class': 'article__details'})
            if meta_element:
                published_date = meta_element.text.strip()
                source = "MarketWatch"
            else:
                published_date = "Unknown"
                source = "MarketWatch"
            
            articles.append({
                'headline': headline,
                'summary': summary,
                'link': link,
                'published_date': published_date,
                'source': source,
                'scraped_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'category': 'tech stocks'
            })
            
        except Exception as e:
            print(f"Error extracting MarketWatch article: {e}")
    
    return articles

def scrape_investing_com():
    """Scrape tech stock news from Investing.com"""
    url = "https://www.investing.com/news/technology"
    print(f"Scraping: {url}")
    
    response = fetch_page(url)
    if not response:
        # Try alternative URL
        url = "https://www.investing.com/news/stock-market-news"
        print(f"Trying alternative: {url}")
        response = fetch_page(url)
        if not response:
            return []
    
    soup = BeautifulSoup(response.text, 'html.parser')
    articles = []
    
    # Save debug HTML
    os.makedirs("debug", exist_ok=True)
    with open("debug/investing_com.html", "w", encoding="utf-8") as f:
        f.write(soup.prettify())
    
    # Investing.com article containers
    news_items = soup.find_all('div', {'class': 'largeTitle'})
    
    if not news_items:
        # Try alternative selectors
        news_items = soup.find_all('article', {'class': 'js-article-item'})
    
    print(f"Found {len(news_items)} potential Investing.com articles")
    
    for item in news_items:
        try:
            # Extract headline
            headline_element = item.find('a', {'class': 'title'}) or item.find('a')
            
            if not headline_element or not headline_element.text:
                continue
                
            headline = headline_element.text.strip()
            
            # Skip non-news items
            if any(skip in headline.lower() for skip in ['advertisement', 'sponsored']):
                continue
                
            # Extract link
            if 'href' in headline_element.attrs:
                link = headline_element['href']
                # Fix relative URLs
                if link.startswith('/'):
                    link = 'https://www.investing.com' + link
            else:
                continue  # Skip if no link
                
            # Extract date
            date_element = item.find('span', {'class': 'date'}) or item.find('time')
            published_date = date_element.text.strip() if date_element else "Unknown"
            
            articles.append({
                'headline': headline,
                'summary': "",  # Investing.com doesn't typically show summaries in list view
                'link': link,
                'published_date': published_date,
                'source': "Investing.com",
                'scraped_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'category': 'tech stocks'
            })
            
        except Exception as e:
            print(f"Error extracting Investing.com article: {e}")
    
    return articles

def filter_tech_stock_articles(articles):
    """Filter articles to focus on tech stocks"""
    tech_terms = [
        'tech', 'technology', 'apple', 'microsoft', 'google', 'alphabet', 'amazon', 
        'tesla', 'nvidia', 'semiconductor', 'ai', 'artificial intelligence', 'meta', 
        'facebook', 'netflix', 'cloud', 'cybersecurity', 'software', 'hardware',
        'chips', 'intel', 'amd', 'tsmc', 'broadcom', 'oracle', 'salesforce',
        'aapl', 'msft', 'googl', 'goog', 'amzn', 'tsla', 'nvda', 'meta', 'nflx'
    ]
    
    tech_stock_articles = []
    
    for article in articles:
        headline = article['headline'].lower()
        summary = article.get('summary', '').lower()
        
        # Check if any tech terms appear in headline or summary
        if any(term in headline or term in summary for term in tech_terms):
            tech_stock_articles.append(article)
    
    print(f"Filtered {len(tech_stock_articles)} tech stock articles from {len(articles)} total articles")
    return tech_stock_articles

def scrape_tech_stock_news():
    """Scrape tech stock news from multiple reputable financial sources"""
    all_articles = []
    target_source_count = 50  # Target number of articles to collect
    
    # Try multiple news sources
    sources = [
        {"name": "Yahoo Finance", "function": scrape_yahoo_finance},
        {"name": "MarketWatch", "function": scrape_marketwatch_tech},
        {"name": "CNBC", "function": scrape_cnbc_finance},
        {"name": "Bloomberg", "function": scrape_bloomberg_tech},
        {"name": "Investing.com", "function": scrape_investing_com}
    ]
    
    # Shuffle sources for randomness
    random.shuffle(sources)
    
    for source in sources:
        try:
            print(f"\nAttempting to scrape {source['name']}...")
            articles = source['function']()
            
            # Add source-specific articles
            if articles:
                all_articles.extend(articles)
                print(f"Scraped {len(articles)} articles from {source['name']}")
                
                # If we have enough articles, we can stop
                if len(all_articles) >= target_source_count:
                    print(f"Reached target of {target_source_count} articles")
                    break
            
            # Sleep to avoid overloading servers and getting blocked
            delay = random.uniform(5, 10)
            print(f"Waiting {delay:.1f} seconds before next source...")
            time.sleep(delay)
                
        except Exception as e:
            print(f"Error scraping {source['name']}: {e}")
    
    # Filter to focus on tech stock related articles
    tech_stock_articles = filter_tech_stock_articles(all_articles)
    
    # Convert to DataFrame for easier analysis
    df = pd.DataFrame(tech_stock_articles)
    
    # Remove duplicates based on headline
    if not df.empty:
        df.drop_duplicates(subset=['headline'], inplace=True)
        print(f"Removed duplicates, down to {len(df)} unique articles")
    
    # Save to CSV if we have articles
    if not df.empty:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"tech_stock_news_{timestamp}.csv"
        df.to_csv(filename, index=False, encoding='utf-8')
        print(f"Saved {len(df)} articles to {filename}")
        
        # Also save as JSON for easier inspection
        df.to_json(f"tech_stock_news_{timestamp}.json", orient="records", indent=4)
        print(f"Saved JSON version to tech_stock_news_{timestamp}.json")
    else:
        print("No articles were found from any source.")
    
    return df

def extract_article_content(url):
    """Extract the main text content from an article URL with site-specific handling"""
    if not url or not url.startswith('http'):
        return "No valid URL provided"
        
    print(f"\nExtracting content from: {url}")
    
    domain = urlparse(url).netloc.lower()
    
    # Create a debug directory if it doesn't exist
    os.makedirs("debug", exist_ok=True)
    
    # Use different extraction techniques based on domain
    if 'yahoo.com' in domain:
        return extract_yahoo_article(url)
    elif 'cnbc.com' in domain:
        return extract_cnbc_article(url)
    elif 'marketwatch.com' in domain:
        return extract_marketwatch_article(url)
    elif 'bloomberg.com' in domain:
        return extract_bloomberg_article(url)
    elif 'investing.com' in domain:
        return extract_investing_article(url)
    else:
        return extract_generic_article(url)

def extract_yahoo_article(url):
    """Extract article content from Yahoo Finance"""
    response = fetch_page(url)
    if not response:
        return "Failed to fetch Yahoo article"
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Save for debugging
    filename = f"debug/yahoo_article_{urlparse(url).path.split('/')[-1]}.html"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(soup.prettify())
    
    # Remove unwanted elements
    for element in soup.find_all(['script', 'style', 'nav', 'header', 'footer']):
        element.decompose()
    
    # Yahoo Finance article container
    article_container = soup.find('div', {'class': 'caas-body'})
    
    if not article_container:
        # Try alternative container
        article_container = soup.find('div', {'class': ['canvas-body', 'article-body']})
    
    if article_container:
        paragraphs = article_container.find_all('p')
        article_text = '\n\n'.join([p.get_text().strip() for p in paragraphs])
        
        # Clean up the text
        article_text = clean_article_text(article_text)
        print(f"Extracted {len(article_text)} characters from Yahoo article")
        return article_text
    else:
        return "Could not find article content on Yahoo Finance"

def extract_cnbc_article(url):
    """Extract article content from CNBC"""
    response = fetch_page(url)
    if not response:
        return "Failed to fetch CNBC article"
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Save for debugging
    filename = f"debug/cnbc_article_{urlparse(url).path.split('/')[-1]}.html"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(soup.prettify())
    
    # Remove unwanted elements
    for element in soup.find_all(['script', 'style', 'nav', 'header', 'footer', 'aside']):
        element.decompose()
    
    # CNBC article container
    article_container = soup.find('div', {'class': 'ArticleBody-articleBody'})
    
    if not article_container:
        # Try alternative containers
        article_container = soup.find('div', {'id': 'article_body'}) or soup.find('div', {'class': 'Article-articleBody'})
    
    if article_container:
        # Get article groups or paragraphs
        article_groups = article_container.find_all('div', {'class': 'group'})
        
        if article_groups:
            paragraphs = []
            for group in article_groups:
                group_paragraphs = group.find_all('p')
                paragraphs.extend(group_paragraphs)
        else:
            paragraphs = article_container.find_all('p')
        
        article_text = '\n\n'.join([p.get_text().strip() for p in paragraphs])
        
        # Clean up the text
        article_text = clean_article_text(article_text)
        print(f"Extracted {len(article_text)} characters from CNBC article")
        return article_text
    else:
        return "Could not find article content on CNBC"

def extract_bloomberg_article(url):
    """Extract article content from Bloomberg"""
    response = fetch_page(url)
    if not response:
        return "Failed to fetch Bloomberg article - may be paywalled"
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Save for debugging
    filename = f"debug/bloomberg_article_{urlparse(url).path.split('/')[-1]}.html"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(soup.prettify())
    
    # Bloomberg often has paywalls, check for that
    paywall = soup.find('div', {'class': ['paywall', 'fence-body']})
    if paywall:
        return "This Bloomberg article is behind a paywall"
    
    # Remove unwanted elements
    for element in soup.find_all(['script', 'style', 'nav', 'header', 'footer']):
        element.decompose()
    
    # Bloomberg article container
    article_container = soup.find('div', {'class': ['body-copy', 'body-copy-v2', 'body-content']})
    
    if not article_container:
        # Try alternative selectors
        article_container = soup.find('div', {'class': 'story-body-container'})
    
    if article_container:
        paragraphs = article_container.find_all('p')
        article_text = '\n\n'.join([p.get_text().strip() for p in paragraphs])
        
        # Clean up the text
        article_text = clean_article_text(article_text)
        print(f"Extracted {len(article_text)} characters from Bloomberg article")
        return article_text
    else:
        return "Could not find article content on Bloomberg"

def extract_marketwatch_article(url):
    """Extract article content from MarketWatch"""
    response = fetch_page(url)
    if not response:
        return "Failed to fetch MarketWatch article"
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Save for debugging
    filename = f"debug/marketwatch_article_{urlparse(url).path.split('/')[-1]}.html"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(soup.prettify())
    
    # Remove unwanted elements
    for element in soup.find_all(['script', 'style', '