#!/usr/bin/env python3
import re
import json
import argparse


def extract_chrcomponents(html: str) -> dict:
    pattern = r"window\.chrComponents\s*=\s*(\{.*?\});"
    match = re.search(pattern, html, re.DOTALL)
    if not match:
        raise ValueError("在 HTML 中未找到 window.chrComponents 定义。")
    json_text = match.group(1)
    return json.loads(json_text)


def main():
    parser = argparse.ArgumentParser(
        description="从 HTML 文件中提取 window.chrComponents 并输出 JSON"
    )
    parser.add_argument(
        "html_file",
        help="待读取的 HTML 文件路径"
    )
    parser.add_argument(
        "json_file",
        help="输出的 JSON 文件路径"
    )
    args = parser.parse_args()

    with open(args.html_file, 'r', encoding='utf-8') as f:
        html = f.read()

    data = extract_chrcomponents(html)

    with open(args.json_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"已将 window.chrComponents 输出到 {args.json_file}")


if __name__ == "__main__":
    main()