import csv
from pathlib import Path


# 原先已有的翻译表，可以是 old_translation.csv 或 old_autocomplete.txt
OLD_FILE = "jin-10w-zh_cn-2.csv"

# 当前重新抽取的英文 tag 表
NEW_FILE = "tags_input.csv"

# 原翻译表中存在，但当前新表中不存在的 tag
OUTPUT_MISSING_FILE = "missing_from_new.csv"

# 当前新表中存在，但原翻译表中不存在的 tag，可选
OUTPUT_NEW_ONLY_FILE = "new_only_tags.csv"


def read_csv_by_first_column(path: str):
    """
    读取 CSV 文件，以第一列作为 tag。
    返回：
        tag_set: 所有 tag 的集合
        rows_by_tag: tag -> 原始行
    """
    tag_set = set()
    rows_by_tag = {}

    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)

        for row in reader:
            if not row:
                continue

            tag = row[0].strip()

            if not tag:
                continue

            # 只跳过真正的表头，例如 tag,count 或 tag,translation
            if tag.lower() in {"tag", "name"}:
                if len(row) >= 2 and row[1].strip().lower() in {
                    "count", "post_count", "postcount", "translation", "zh", "中文"
                }:
                    continue

            tag_set.add(tag)

            # 如果同一个 tag 出现多次，保留第一次
            if tag not in rows_by_tag:
                rows_by_tag[tag] = row

    return tag_set, rows_by_tag


def write_rows(path: str, tags, rows_by_tag):
    """
    按排序后的 tag 写出原始行。
    """
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)

        for tag in sorted(tags):
            writer.writerow(rows_by_tag[tag])


def main():
    old_path = Path(OLD_FILE)
    new_path = Path(NEW_FILE)

    if not old_path.exists():
        raise FileNotFoundError(f"找不到原翻译表：{old_path.resolve()}")

    if not new_path.exists():
        raise FileNotFoundError(f"找不到当前抽取表：{new_path.resolve()}")

    old_tags, old_rows = read_csv_by_first_column(OLD_FILE)
    new_tags, new_rows = read_csv_by_first_column(NEW_FILE)

    missing_from_new = old_tags - new_tags
    new_only = new_tags - old_tags

    write_rows(OUTPUT_MISSING_FILE, missing_from_new, old_rows)
    write_rows(OUTPUT_NEW_ONLY_FILE, new_only, new_rows)

    print(f"原翻译表 tag 数：{len(old_tags)}")
    print(f"当前抽取表 tag 数：{len(new_tags)}")
    print(f"原表有但新表没有：{len(missing_from_new)} 条")
    print(f"新表有但原表没有：{len(new_only)} 条")
    print(f"已输出：{OUTPUT_MISSING_FILE}")
    print(f"已输出：{OUTPUT_NEW_ONLY_FILE}")


if __name__ == "__main__":
    main()