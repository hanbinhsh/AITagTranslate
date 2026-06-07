import csv
from pathlib import Path


INPUT_FILE = "autocomplete.txt"

OUTPUT_TAG_FILE = "danbooru_custom.csv"
OUTPUT_TRANSLATION_FILE = "danbooru_custom_zh.csv"


def strip_leading_tag(tag: str, display: str) -> str:
    """
    把：
        1girl 人物-一个女孩
    转成：
        人物-一个女孩
    """
    display = display.strip()

    prefix = tag + " "
    if display.startswith(prefix):
        return display[len(prefix):].strip()

    return display


def main():
    input_path = Path(INPUT_FILE)

    if not input_path.exists():
        raise FileNotFoundError(f"找不到输入文件：{input_path.resolve()}")

    with open(INPUT_FILE, "r", encoding="utf-8-sig", newline="") as f_in, \
         open(OUTPUT_TAG_FILE, "w", encoding="utf-8", newline="") as f_tag, \
         open(OUTPUT_TRANSLATION_FILE, "w", encoding="utf-8", newline="") as f_zh:

        reader = csv.reader(f_in)
        tag_writer = csv.writer(f_tag)
        zh_writer = csv.writer(f_zh)

        count = 0

        for row in reader:
            if len(row) < 3:
                continue

            tag = row[0].strip()
            display = row[1].strip()
            post_count = row[2].strip()

            if not tag:
                continue

            zh = strip_leading_tag(tag, display)

            # A1111 TagComplete 主词表格式：
            # <name>,<type>,<postCount>,"<aliases>"
            #
            # 这里 type 统一写 0，表示 general tag。
            # 如果你后续有更精细分类，也可以改成 Danbooru 的类型编号。
            tag_writer.writerow([tag, 0, post_count, ""])

            # A1111 TagComplete 翻译文件格式：
            # <English tag/alias>,<Translation>
            if zh:
                zh_writer.writerow([tag, zh])

            count += 1

    print(f"完成：{OUTPUT_TAG_FILE}")
    print(f"完成：{OUTPUT_TRANSLATION_FILE}")
    print(f"共转换 {count} 条")


if __name__ == "__main__":
    main()