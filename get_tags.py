import csv
import time
import requests
from tqdm import tqdm


OUTPUT_FILE = "tags_input.csv"

# 想抓多少条。建议先 100000，够用了。
MAX_TAGS = 100000

# 每页数量。太大可能更容易被限流，200 比较稳。
PER_PAGE = 200

# 每页间隔，避免请求太快。
SLEEP_SECONDS = 0.5

# 是否跳过已废弃 tag
SKIP_DEPRECATED = True

# 只保留 post_count > 0 的 tag
MIN_POST_COUNT = 1


def fetch_page(page: int):
    url = "https://danbooru.donmai.us/tags.json"
    params = {
        "search[order]": "count",
        "limit": PER_PAGE,
        "page": page,
    }

    headers = {
        "User-Agent": "tag-list-fetcher/1.0"
    }

    resp = requests.get(url, params=params, headers=headers, timeout=30)

    if resp.status_code == 429:
        raise RuntimeError("请求过快，被限流 429。请增大 SLEEP_SECONDS。")

    resp.raise_for_status()
    return resp.json()


def main():
    written = 0
    page = 1

    with open(OUTPUT_FILE, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)

        with tqdm(total=MAX_TAGS) as pbar:
            while written < MAX_TAGS:
                try:
                    items = fetch_page(page)
                except Exception as e:
                    print(f"\n第 {page} 页失败：{e}")
                    print("等待 10 秒后重试。")
                    time.sleep(10)
                    continue

                if not items:
                    print("\n没有更多 tag 了。")
                    break

                for item in items:
                    name = item.get("name", "").strip()
                    post_count = int(item.get("post_count") or 0)
                    is_deprecated = bool(item.get("is_deprecated", False))

                    if not name:
                        continue

                    if SKIP_DEPRECATED and is_deprecated:
                        continue

                    if post_count < MIN_POST_COUNT:
                        continue

                    writer.writerow([name, post_count])
                    written += 1
                    pbar.update(1)

                    if written >= MAX_TAGS:
                        break

                page += 1
                time.sleep(SLEEP_SECONDS)

    print(f"完成：{OUTPUT_FILE}")
    print(f"共写入 {written} 条")


if __name__ == "__main__":
    main()