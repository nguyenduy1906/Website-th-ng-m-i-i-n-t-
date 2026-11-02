import json
from pathlib import Path
from app.db import connect, initialize

ROOT = Path(__file__).resolve().parent.parent


def main():
    initialize()
    entries = json.loads((ROOT / "docs/news-editorial.json").read_text(encoding="utf-8"))
    added = 0
    with connect() as db:
        for index, entry in enumerate(entries):
            if db.execute("SELECT 1 FROM articles WHERE title=?", (entry["title"],)).fetchone():
                continue
            db.execute("INSERT OR IGNORE INTO article_topics(name,active) VALUES(?,1)", (entry["topic"],))
            topic = db.execute("SELECT id FROM article_topics WHERE name=?", (entry["topic"],)).fetchone()["id"]
            images = db.execute("SELECT media FROM products WHERE active=1 AND deleted_at IS NULL AND category=? AND media!='' ORDER BY id", (entry["category"],)).fetchall()
            image = images[index % len(images)]["media"] if images else ""
            db.execute("INSERT INTO articles(title,summary,content,active,topic_id,image) VALUES(?,?,?,1,?,?)", (entry["title"],entry["summary"],entry["content"],topic,image))
            added += 1
    with connect() as db:
        for entry in json.loads((ROOT / "docs/news-baseline.json").read_text(encoding="utf-8")):
            db.execute("UPDATE articles SET content=? WHERE title=? AND length(content)<700", (entry['content'],entry['title']))
    print(f"Imported {added} new editorial articles; existing titles preserved.")


if __name__ == "__main__":
    main()
