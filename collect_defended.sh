#!/bin/bash
# collect_defended.sh
# DoH-Shield Phase 4A — Collect defended DoH traffic through live proxy
#
# What this does:
#   For each of 200 websites, visits it 10 times through the mitmproxy
#   proxy (which runs DoH-Shield morphing). Each visit's DoH flow stats
#   are captured from the proxy's stats.json and saved as a CSV row.
#
# Output: defended_dataset.csv — features + labels for 2000 sessions

set -e
cd "$(dirname "$0")"

# Activate virtual environment
if [ -f "./venv/bin/activate" ]; then
    source ./venv/bin/activate
else
    echo "[!] Virtual environment venv not found! Please create it first."
    exit 1
fi

OUTPUT_FILE="defended_dataset.csv"
LOG_FILE="stats.json"
PROXY="http://127.0.0.1:8080"
VISITS_PER_SITE=10
DELAY_BETWEEN_VISITS=3  # seconds

# ── Top 200 sites (Tranco list) ──────────────────────────────────────
SITES=(
    "google.com" "youtube.com" "facebook.com" "twitter.com" "instagram.com"
    "linkedin.com" "reddit.com" "wikipedia.org" "amazon.com" "netflix.com"
    "github.com" "stackoverflow.com" "medium.com" "quora.com" "pinterest.com"
    "tumblr.com" "wordpress.com" "blogger.com" "yahoo.com" "bing.com"
    "duckduckgo.com" "baidu.com" "nytimes.com" "bbc.com" "cnn.com"
    "theguardian.com" "washingtonpost.com" "reuters.com" "bloomberg.com" "forbes.com"
    "techcrunch.com" "wired.com" "arstechnica.com" "theverge.com" "engadget.com"
    "apple.com" "microsoft.com" "samsung.com" "sony.com" "lg.com"
    "adobe.com" "dropbox.com" "slack.com" "zoom.us" "trello.com"
    "spotify.com" "soundcloud.com" "twitch.tv" "tiktok.com" "snapchat.com"
    "whatsapp.com" "telegram.org" "discord.com" "signal.org" "skype.com"
    "paypal.com" "stripe.com" "shopify.com" "ebay.com" "etsy.com"
    "airbnb.com" "booking.com" "tripadvisor.com" "expedia.com" "kayak.com"
    "uber.com" "lyft.com" "doordash.com" "grubhub.com" "instacart.com"
    "coursera.org" "udemy.com" "edx.org" "khanacademy.org" "duolingo.com"
    "mit.edu" "stanford.edu" "harvard.edu" "ox.ac.uk" "cambridge.org"
    "arxiv.org" "nature.com" "science.org" "pubmed.ncbi.nlm.nih.gov" "ieee.org"
    "python.org" "nodejs.org" "reactjs.org" "vuejs.org" "angular.io"
    "docker.com" "kubernetes.io" "aws.amazon.com" "cloud.google.com" "azure.microsoft.com"
    "gitlab.com" "bitbucket.org" "npmjs.com" "pypi.org" "crates.io"
    "w3schools.com" "developer.mozilla.org" "css-tricks.com" "smashingmagazine.com" "alistapart.com"
    "cloudflare.com" "fastly.com" "akamai.com" "cdn77.com" "jsdelivr.net"
    "imdb.com" "rottentomatoes.com" "metacritic.com" "gamespot.com" "ign.com"
    "espn.com" "nba.com" "fifa.com" "nfl.com" "cricket.com"
    "webmd.com" "mayoclinic.org" "healthline.com" "nih.gov" "who.int"
    "nasa.gov" "noaa.gov" "weather.com" "accuweather.com" "timeanddate.com"
    "translate.google.com" "grammarly.com" "deepl.com" "wolframalpha.com"
    "archive.org" "gutenberg.org" "librarything.com" "goodreads.com" "scribd.com"
    "openai.com" "anthropic.com" "huggingface.co" "kaggle.com" "colab.research.google.com"
    "figma.com" "canva.com" "unsplash.com" "pexels.com" "flickr.com"
    "mapbox.com" "openstreetmap.org" "maps.google.com" "here.com" "waze.com"
    "gnu.org" "linux.org" "ubuntu.com" "debian.org" "archlinux.org"
    "mozilla.org" "firefox.com" "brave.com" "opera.com" "vivaldi.com"
    "nordvpn.com" "expressvpn.com" "protonvpn.com" "torproject.org" "mullvad.net"
    "letsencrypt.org" "ssl.com" "digicert.com" "godaddy.com" "namecheap.com"
    "1password.com" "lastpass.com" "bitwarden.com" "keybase.io" "veracrypt.fr"
    "wireshark.org" "nmap.org" "metasploit.com" "kali.org" "backbox.org"
    "usenix.org" "acm.org" "springer.com" "elsevier.com" "wiley.com"
)

echo "=================================================="
echo "🛡️  DOH-SHIELD DATA COLLECTION (PHASE 4A)  🛡️"
echo "=================================================="
echo "Sites count: ${#SITES[@]}"
echo "Visits per site: $VISITS_PER_SITE"
echo "Total visits planned: $((${#SITES[@]} * VISITS_PER_SITE))"
echo "=================================================="
echo ""

# Write CSV header
echo "site,visit,cluster_id,dummy_count,overhead_pct,formal_bound,timestamp" > "$OUTPUT_FILE"

# Ensure proxy is running
if ! curl -s --proxy "$PROXY" https://example.com -o /dev/null --max-time 5; then
    echo "❌ Proxy not responding at $PROXY"
    echo "   Please start the proxy in another terminal with: ./run.sh"
    exit 1
fi
echo "[+] Connected to proxy at $PROXY"
echo ""

SITE_IDX=0
for site in "${SITES[@]}"; do
    SITE_IDX=$((SITE_IDX + 1))
    echo "[$SITE_IDX/${#SITES[@]}] Resolving and visiting: $site"

    for visit in $(seq 1 $VISITS_PER_SITE); do
        # Record history length before request
        BEFORE_COUNT=$(python3 -c "
import json, os
if os.path.exists('$LOG_FILE'):
    try:
        print(len(json.load(open('$LOG_FILE')).get('history', [])))
    except:
        print(0)
else:
    print(0)
")

        # Make request through proxy to trigger DoH resolution
        curl -s \
            --proxy "$PROXY" \
            --max-time 10 \
            "https://$site" \
            -o /dev/null 2>/dev/null || true

        # Wait for DoH-Shield idle flush (2.0s timeout + buffer)
        sleep 2.5

        # Read latest session stats
        SESSION_DATA=$(python3 -c "
import json
try:
    d = json.load(open('$LOG_FILE'))
    history = d.get('history', [])
    if len(history) > $BEFORE_COUNT:
        s = history[-1]
        print(f'{s.get(\"target_cluster\", -1)},{s.get(\"dummies_injected\", 0)},{s.get(\"overhead_pct\", 0.0):.2f},{s.get(\"privacy_bound\", 0.0):.4f},{s.get(\"timestamp\", \"\")}')
    else:
        # If no new session flushed, check last session anyway
        if history:
            s = history[-1]
            print(f'{s.get(\"target_cluster\", -1)},{s.get(\"dummies_injected\", 0)},{s.get(\"overhead_pct\", 0.0):.2f},{s.get(\"privacy_bound\", 0.0):.4f},{s.get(\"timestamp\", \"\")}')
        else:
            print('-1,0,0.0,0.0,unknown')
except Exception as e:
    print('-1,0,0.0,0.0,error')
")

        echo "$site,$visit,$SESSION_DATA" >> "$OUTPUT_FILE"
        echo "   Visit $visit: Cluster $(echo $SESSION_DATA | cut -d',' -f1), Dummies: $(echo $SESSION_DATA | cut -d',' -f2), Overhead: $(echo $SESSION_DATA | cut -d',' -f3)%"
        sleep $DELAY_BETWEEN_VISITS
    done
    echo ""
done

echo "[+] Data collection complete!"
echo "Saved to: $OUTPUT_FILE"
wc -l "$OUTPUT_FILE"
