import csv
import json
import os
import time
from pathlib import Path
from typing import Dict, List
from concurrent.futures import ThreadPoolExecutor, as_completed

from openai import OpenAI
from tqdm import tqdm


# ======================
# 基本配置
# ======================

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.environ["NVIDIA_API_KEY"],
)

MODEL = "qwen/qwen3.5-397b-a17b"

INPUT_FILE = "tags_input.csv"
OUTPUT_FILE = "autocomplete.txt"
CACHE_FILE = "translation_cache.jsonl"
FAILED_FILE = "failed_batches.jsonl"

BATCH_SIZE = 40

# 同时向 API 发送 3 个请求
MAX_WORKERS = 3

SLEEP_SECONDS = 0.05

CATEGORIES = [
    "人物", "发型", "五官", "表情", "姿势", "动作", "服装", "身体",
    "构图", "背景", "场景", "物品", "动物", "画风", "质量", "光影",
    "视线", "文本", "其他"
]


MANUAL_OVERRIDES = {
    "1girl": {"category": "人物", "zh": "一个女孩"},
    "1boy": {"category": "人物", "zh": "一个男孩"},
    "solo": {"category": "人物", "zh": "单人"},
    "highres": {"category": "质量", "zh": "高分辨率"},
    "long_hair": {"category": "发型", "zh": "长发"},
    "short_hair": {"category": "发型", "zh": "短发"},
    "commentary_request": {"category": "文本", "zh": "请求评论"},
    "breasts": {"category": "身体", "zh": "胸部"},
    "looking_at_viewer": {"category": "视线", "zh": "看向观众"},
    "blush": {"category": "表情", "zh": "脸红"},
    "smile": {"category": "表情", "zh": "微笑"},
    "open_mouth": {"category": "表情", "zh": "张嘴"},
    "head_tilt": {"category": "姿势", "zh": "歪头"},
    "looking_up": {"category": "视线", "zh": "向上看"},
    "black_hair": {"category": "发型", "zh": "黑发"},
    "blue_eyes": {"category": "五官", "zh": "蓝眼睛"},
    "school_uniform": {"category": "服装", "zh": "校服"},
    "white_background": {"category": "背景", "zh": "白色背景"},
    "masterpiece": {"category": "质量", "zh": "杰作"},
    "best_quality": {"category": "质量", "zh": "最佳质量"},
}


def read_tags(path: str) -> List[Dict]:
    """
    输入格式：
        1girl,4114588
        solo,3426446
        tag,1705

    第一列 tag 发给模型。
    第二列 count 不发给模型，但输出时保持原样。
    """
    rows = []

    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)

        for line_no, row in enumerate(reader, start=1):
            if not row:
                continue

            tag = row[0].strip()

            if not tag:
                continue

            count = ""
            if len(row) >= 2:
                count = row[1].strip()

            # 只在第一行确实像表头时跳过，例如：
            # tag,count
            # name,post_count
            if line_no == 1:
                first = tag.lower()
                second = count.lower()

                if first in {"tag", "name"} and second in {"count", "post_count", "postcount"}:
                    continue

            rows.append({
                "tag": tag,
                "count": count,
            })

    return rows


def load_cache(path: str) -> Dict[str, Dict]:
    cache = {}
    p = Path(path)

    if not p.exists():
        return cache

    with p.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if not line:
                continue

            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue

            tag = item.get("tag")
            category = item.get("category")
            zh = item.get("zh")

            if tag and category and zh:
                cache[tag] = {
                    "tag": tag,
                    "category": category,
                    "zh": zh,
                }

    return cache


def append_cache(path: str, items: List[Dict]):
    """
    只在主线程里调用，避免多线程同时写文件造成错乱。
    """
    with open(path, "a", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


def append_failed_batch(tags: List[str], error: str):
    with open(FAILED_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps({
            "tags": tags,
            "error": error,
        }, ensure_ascii=False) + "\n")


def extract_json_array(text: str):
    """
    处理 Qwen thinking mode 输出：
    1. 去掉 <think>...</think>
    2. 去掉 ```json ... ``` 包裹
    3. 截取最终 JSON 数组
    """
    text = text.strip()

    while "<think>" in text and "</think>" in text:
        start = text.find("<think>")
        end = text.find("</think>") + len("</think>")
        text = text[:start] + text[end:]
        text = text.strip()

    if text.startswith("```"):
        lines = text.splitlines()

        if lines and lines[0].startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]

        text = "\n".join(lines).strip()

    start = text.find("[")
    end = text.rfind("]")

    if start == -1 or end == -1 or end <= start:
        raise ValueError(f"没有找到合法 JSON 数组，模型原始输出前 500 字：\n{text[:500]}")

    json_text = text[start:end + 1]

    return json.loads(json_text)


def translate_batch(tags: List[str]) -> List[Dict]:
    """
    传给模型的只有 tag 列表，不包含 count。
    """
    prompt = f"""
你是 Stable Diffusion / Danbooru tag 中文词表整理助手。

你的任务：把输入的英文 tag 翻译成适合中文搜索的短中文，并给出分类。

你可以在内部思考，但最终答案必须只包含一个严格 JSON 数组。
不要输出 Markdown，不要解释，不要额外文字。

分类只能从下面这些词中选择：
{", ".join(CATEGORIES)}

要求：
1. tag 必须原样返回，不要把下划线改成空格。
2. zh 要自然、简短，适合提示词补全，不要机翻腔。
3. 不要解释 tag 的含义，只给最适合搜索的中文短词。
4. 人名、角色名、作品名如果无法确定，就保留英文或使用常见译名，不要乱翻。
5. 对明显不适合出图提示词的 tag，也照常翻译，不要丢弃。
6. 常见含义注意：
   - 1girl 是“一个女孩”
   - 1boy 是“一个男孩”
   - solo 是“单人”
   - highres 是“高分辨率”
   - commentary_request 是“请求评论”
   - looking_at_viewer 是“看向观众”
   - head_tilt 是“歪头”，不是“抬头”
   - looking_up 是“向上看”或“抬头”
   - breasts 是“胸部”
7. 最终输出格式必须严格如下：

[
  {{"tag": "1girl", "category": "人物", "zh": "一个女孩"}},
  {{"tag": "head_tilt", "category": "姿势", "zh": "歪头"}}
]

输入 tags：
{json.dumps(tags, ensure_ascii=False)}
""".strip()

    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": "你是严谨的词表翻译助手。最终答案必须是严格 JSON 数组。"
            },
            {
                "role": "user",
                "content": prompt
            },
        ],
        temperature=0.6,
        top_p=0.95,
        max_tokens=8192,
        extra_body={
            "top_k": 20,
            "min_p": 0
        },
    )

    text = resp.choices[0].message.content
    data = extract_json_array(text)

    results = []
    valid_tags = set(tags)

    for item in data:
        tag = str(item.get("tag", "")).strip()
        category = str(item.get("category", "其他")).strip()
        zh = str(item.get("zh", "")).strip()

        if tag not in valid_tags:
            continue

        if not zh:
            continue

        if category not in CATEGORIES:
            category = "其他"

        results.append({
            "tag": tag,
            "category": category,
            "zh": zh,
        })

    return results


def translate_batch_with_retry(tags: List[str], max_retries: int = 3) -> List[Dict]:
    """
    单个批次失败后自动重试。
    """
    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            result = translate_batch(tags)

            if not result:
                raise ValueError("模型返回结果为空")

            return result

        except Exception as e:
            last_error = e
            print(f"\n批次失败，第 {attempt}/{max_retries} 次：{tags[:8]}")
            print(f"错误：{e}")

            # 递增等待，防止限流或临时网络错误
            time.sleep(5 * attempt)

    append_failed_batch(tags, str(last_error))
    print(f"\n该批次多次失败，已写入 {FAILED_FILE}：{tags[:8]}")
    return []


def build_translation_cache(rows: List[Dict]) -> Dict[str, Dict]:
    cache = load_cache(CACHE_FILE)

    # 手动覆盖优先
    for tag, value in MANUAL_OVERRIDES.items():
        cache[tag] = {
            "tag": tag,
            "category": value["category"],
            "zh": value["zh"],
        }

    need_rows = [r for r in rows if r["tag"] not in cache]

    print(f"总计读取 {len(rows)} 条 tag")
    print(f"手动覆盖 {len(MANUAL_OVERRIDES)} 条")
    print(f"缓存已有 {len(cache)} 条")
    print(f"需要 API 翻译 {len(need_rows)} 条")
    print(f"并发请求数 {MAX_WORKERS}")
    print(f"每批 tag 数 {BATCH_SIZE}")

    if not need_rows:
        return cache

    batches = [
        need_rows[i:i + BATCH_SIZE]
        for i in range(0, len(need_rows), BATCH_SIZE)
    ]

    def submit_one(executor, batch_rows):
        tags = [r["tag"] for r in batch_rows]
        future = executor.submit(translate_batch_with_retry, tags, 3)
        return future, tags

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        pending = {}
        batch_index = 0
        total_batches = len(batches)

        # 先提交最多 MAX_WORKERS 个任务
        while batch_index < total_batches and len(pending) < MAX_WORKERS:
            future, tags = submit_one(executor, batches[batch_index])
            pending[future] = tags
            batch_index += 1
            time.sleep(SLEEP_SECONDS)

        try:
            with tqdm(total=total_batches) as pbar:
                while pending:
                    for future in as_completed(pending):
                        tags = pending.pop(future)

                        try:
                            translated = future.result()
                        except Exception as e:
                            print(f"\n线程异常：{tags[:8]}")
                            print(f"错误：{e}")
                            append_failed_batch(tags, str(e))
                            translated = []

                        if translated:
                            append_cache(CACHE_FILE, translated)

                            for item in translated:
                                cache[item["tag"]] = item

                        pbar.update(1)

                        # 完成一个，再提交一个，始终保持最多 3 个并发
                        if batch_index < total_batches:
                            new_future, new_tags = submit_one(executor, batches[batch_index])
                            pending[new_future] = new_tags
                            batch_index += 1
                            time.sleep(SLEEP_SECONDS)

                        # 重要：跳出 for，让 while 重新读取 pending
                        break

        except KeyboardInterrupt:
            print("\n检测到 Ctrl + C。")
            print("已经写入 translation_cache.jsonl 的内容会保留，下次运行会继续补未完成部分。")
            executor.shutdown(wait=False, cancel_futures=True)
            raise

    return cache


def write_autocomplete(rows: List[Dict], cache: Dict[str, Dict]):
    """
    输出格式：
        1girl,1girl 人物-一个女孩,4114588

    第 1 列：点击后真正插入的 tag
    第 2 列：用于搜索和显示的文本，包含英文 tag + 中文分类翻译
    第 3 列：保持 input 文件里的原始数字
    """
    written = 0
    missing = []

    with open(OUTPUT_FILE, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)

        for row in rows:
            tag = row["tag"]
            item = cache.get(tag)

            if not item:
                missing.append(tag)
                continue

            category = item.get("category", "其他").strip()
            zh = item.get("zh", "").strip()

            if not zh:
                missing.append(tag)
                continue

            display = f"{tag} {category}-{zh}"

            # 保持 input 里的数字
            priority = row.get("count", "")

            writer.writerow([tag, display, priority])
            written += 1

    print(f"已生成：{OUTPUT_FILE}")
    print(f"总计 {len(rows)} 条")
    print(f"共写入 {written} 条")
    print(f"仍缺失 {len(missing)} 条")

    if missing:
        with open("missing_tags.txt", "w", encoding="utf-8") as f:
            for tag in missing:
                f.write(tag + "\n")

        print("缺失 tag 已写入：missing_tags.txt")


def main():
    rows = read_tags(INPUT_FILE)

    try:
        cache = build_translation_cache(rows)
    except KeyboardInterrupt:
        print("\n已中断。下次重新运行会从缓存继续。")
        return

    write_autocomplete(rows, cache)


if __name__ == "__main__":
    main()