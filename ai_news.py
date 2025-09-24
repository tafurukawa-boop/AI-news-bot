import feedparser
import openai
from slack_sdk.webhook import WebhookClient
import os

# --- APIキーはGitHub Secretsから取得 ---
openai.api_key = os.getenv("OPENAI_API_KEY")
slack_webhook_url = os.getenv("SLACK_WEBHOOK_URL")

# --- ニュース収集（RSSから取得） ---
def fetch_rss(feed_url, max_items=2):
    feed = feedparser.parse(feed_url)
    articles = []
    for entry in feed.entries[:max_items]:
        articles.append({
            "title": entry.title,
            "link": entry.link,
            "summary": entry.get("summary", "") or entry.get("description", "")
        })
    return articles

# --- GPTによる仕分け＆要約 ---
def classify_and_summarize(articles):
    articles_text = "\n".join([f"- {a['title']} ({a['link']}) {a['summary']}" for a in articles])
    prompt = f"""
以下のニュース記事を「注目ニュース」と「その他ニュース」に分類し、指定フォーマットで要約してください。

### 注目ニュース（優先度の高い条件）
- 日本国内の出来事
- 人材業界や採用に関係する出来事
- 海外発でも、日本市場やIndeedの役割に影響が出る可能性が高いもの

#### 出力フォーマット
⚡ 刺激フレーズ（読んでいる人がハッとする短い言葉）
📰 タイトル
✅ 世の中はどう変わるか？
👉 日本国内での採用・人材業界への影響
🟢 CS視点での示唆（既存フローがどう変わるか、先読みして準備すべきこと）
💡 他代理店・他部署との差別化ポイント（自分たちが武器にできること）
🔮 近未来予測（3年以内に起こりそうな変化）

### その他ニュース（それ以外）
📌 タイトル
→ 一言コメント（なぜ重要 or 参考になるかを簡単に）
🔗 URL

記事一覧：
{articles_text}
"""
    res = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )
    return res.choices[0].message.content

# --- Slack投稿 ---
def post_to_slack(message):
    webhook = WebhookClient(slack_webhook_url)
    webhook.send(text=message)

# --- メイン処理 ---
if __name__ == "__main__":
    rss_urls = [
        # 🌍 海外
        "https://techcrunch.com/tag/artificial-intelligence/feed/",
        "https://venturebeat.com/category/ai/feed/",
        "https://www.technologyreview.com/feed/",
        "https://www.theverge.com/artificial-intelligence/rss/index.xml",
        "http://feeds.bbci.co.uk/news/technology/rss.xml",

        # 🇯🇵 国内
        "https://www.nikkei.com/rss/technology.rdf",
        "https://rss.itmedia.co.jp/rss/2.0/news_bursts.xml",
        "https://www.hrpro.co.jp/rss/",
        "https://jinjibu.jp/rss/news.xml",
        "https://ai-scholar.tech/feed"
    ]

    all_articles = []
    for url in rss_urls:
        all_articles.extend(fetch_rss(url, max_items=1))  # 1記事だけ取るよう調整

    print(f"収集記事数: {len(all_articles)}")

    summary = classify_and_summarize(all_articles)
    post_to_slack(summary)
    print("Slackに送信しました ✅")
