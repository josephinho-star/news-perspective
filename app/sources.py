TOPICS = [
    ("world", "World"),
    ("us-politics", "US Politics"),
    ("international-relations", "International Relations"),
    ("eu-politics", "EU Politics"),
    ("asia", "Asia"),
    ("turkey", "Turkey"),
    ("business", "Business"),
    ("finance", "Finance"),
    ("tech", "Tech"),
    ("science", "Science"),
    ("climate", "Climate"),
    ("sports", "Sports"),
]

# bias_label: left | lean-left | center | lean-right | right
# topics: comma-separated slugs from TOPICS above
SEED_SOURCES = [
    dict(name="PBS NewsHour", feed_url="https://www.pbs.org/newshour/feeds/rss/headlines", bias_label="center", topics="world,us-politics", paywalled=False),
    dict(name="Associated Press", feed_url="https://feedx.net/rss/ap.xml", bias_label="center", topics="world,us-politics", paywalled=False),
    dict(name="BBC News", feed_url="http://feeds.bbci.co.uk/news/world/rss.xml", bias_label="center", topics="world", paywalled=False),
    dict(name="NPR", feed_url="https://feeds.npr.org/1001/rss.xml", bias_label="lean-left", topics="world,us-politics", paywalled=False),
    dict(name="The Guardian", feed_url="https://www.theguardian.com/world/rss", bias_label="lean-left", topics="world", paywalled=False),
    dict(name="Al Jazeera English", feed_url="https://www.aljazeera.com/xml/rss/all.xml", bias_label="lean-left", topics="world", paywalled=False),
    dict(name="CNN", feed_url="http://rss.cnn.com/rss/cnn_topstories.rss", bias_label="lean-left", topics="world,us-politics", paywalled=False),
    dict(name="Fox News", feed_url="https://moxie.foxnews.com/google-publisher/latest.xml", bias_label="right", topics="us-politics,world", paywalled=False),
    dict(name="New York Post", feed_url="https://nypost.com/feed/", bias_label="lean-right", topics="us-politics", paywalled=False),
    dict(name="Breitbart", feed_url="https://feeds.feedburner.com/breitbart", bias_label="right", topics="us-politics", paywalled=False),
    dict(name="The Hill", feed_url="https://thehill.com/feed/", bias_label="center", topics="us-politics", paywalled=False),
    dict(name="Politico", feed_url="https://rss.politico.com/politics-news.xml", bias_label="center", topics="us-politics", paywalled=False),
    dict(name="Axios", feed_url="https://api.axios.com/feed/", bias_label="center", topics="us-politics,business", paywalled=False),
    dict(name="New York Times", feed_url="https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml", bias_label="lean-left", topics="world,us-politics", paywalled=True),
    dict(name="Washington Post", feed_url="http://feeds.washingtonpost.com/rss/national", bias_label="lean-left", topics="us-politics", paywalled=True),
    dict(name="Wall Street Journal", feed_url="https://feeds.a.dj.com/rss/RSSWorldNews.xml", bias_label="lean-right", topics="world,business,finance", paywalled=True),
    dict(name="The Economist", feed_url="https://www.economist.com/the-world-this-week/rss.xml", bias_label="center", topics="world,business,finance", paywalled=True),
    dict(name="Bloomberg", feed_url="https://feeds.bloomberg.com/markets/news.rss", bias_label="center", topics="business,finance", paywalled=True),
    dict(name="CNBC", feed_url="https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114", bias_label="center", topics="business,finance", paywalled=False),
    dict(name="MarketWatch", feed_url="https://www.marketwatch.com/rss/topstories", bias_label="center", topics="finance", paywalled=False),
    dict(name="Financial Times", feed_url="https://www.ft.com/rss/home", bias_label="center", topics="finance,world", paywalled=True),
    dict(name="Foreign Policy", feed_url="https://foreignpolicy.com/feed/", bias_label="center", topics="international-relations", paywalled=True),
    dict(name="The Diplomat", feed_url="https://thediplomat.com/feed/", bias_label="center", topics="international-relations,asia", paywalled=False),
    dict(name="POLITICO Europe", feed_url="https://www.politico.eu/feed/", bias_label="center", topics="eu-politics,international-relations", paywalled=False),
    dict(name="South China Morning Post", feed_url="https://www.scmp.com/rss/91/feed", bias_label="center", topics="asia", paywalled=False),
    dict(name="Nikkei Asia", feed_url="https://asia.nikkei.com/rss/feed/nar", bias_label="center", topics="asia,business", paywalled=True),
    dict(name="Daily Sabah", feed_url="https://www.dailysabah.com/rssFeed/home", bias_label="lean-right", topics="turkey", paywalled=False),
    dict(name="Hurriyet Daily News", feed_url="https://www.hurriyetdailynews.com/rss/news", bias_label="center", topics="turkey", paywalled=False),
    dict(name="Turkish Minute", feed_url="https://www.turkishminute.com/feed/", bias_label="lean-left", topics="turkey", paywalled=False),
    dict(name="The Verge", feed_url="https://www.theverge.com/rss/index.xml", bias_label="center", topics="tech", paywalled=False),
    dict(name="TechCrunch", feed_url="https://techcrunch.com/feed/", bias_label="center", topics="tech,business", paywalled=False),
    dict(name="Ars Technica", feed_url="https://feeds.arstechnica.com/arstechnica/index", bias_label="center", topics="tech,science", paywalled=False),
    dict(name="Nature News", feed_url="https://www.nature.com/nature.rss", bias_label="center", topics="science", paywalled=False),
    dict(name="Scientific American", feed_url="https://www.scientificamerican.com/platform/syndication/rss/", bias_label="center", topics="science,climate", paywalled=False),
    dict(name="ESPN", feed_url="https://www.espn.com/espn/rss/news", bias_label="center", topics="sports", paywalled=False),
]

BIAS_COLORS = {
    "left": "#4a6fa5",
    "lean-left": "#7c9cc4",
    "center": "#8a8a85",
    "lean-right": "#c17a6c",
    "right": "#a94436",
}

BIAS_SHORT = {
    "left": "L",
    "lean-left": "LL",
    "center": "C",
    "lean-right": "LR",
    "right": "R",
}

BIAS_ORDER = ["left", "lean-left", "center", "lean-right", "right"]
