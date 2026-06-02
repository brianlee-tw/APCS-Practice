import os
import re

# --- 1. 規格化配置區：定義大分類與其預期的子主題目標題數 ---
CONFIG = {
    "01_Basic_Syntax": {
        "total": 11,
        "subs": {
            "I/O Optimization": 3,
            "Conditionals": 2,
            "Loops": 3,
            "Functions": 3,
        },
    },
    "02_Data_Structures": {
        "total": 24,
        "subs": {
            "Array": 6, 
            "Vector": 6, 
            "String": 8, 
            "Struct": 4
        },
    },
    "03_Basic_Algorithms": {
        "total": 36,
        "subs": {
            "Sorting": 5,
            "Binary Search": 6,
            "Greedy": 8,
            "Brute Force": 5,
            "Two Pointers": 7,
            "Math Theory": 5,
        },
    },
    "04_Performance_Optimization": {  # 👈 修正為專業命名
        "total": 42,
        "subs": {
            "Recursion": 6,
            "Stack & Queue": 6,
            "DFS": 7,
            "BFS": 7,
            "DP": 10,
            "Graph & Tree": 6,
        },
    },
}

# --- 2. 標籤錨點設定 ---
ROOT_START, ROOT_END = "<!-- ROOT_START -->", "<!-- ROOT_END -->"

L1_START, L1_END = "<!-- L1_START -->", "<!-- L1_END -->"

L2_START, L2_END = "<!-- L2_START -->", "<!-- L2_END -->"


def parse_file_metadata(file_path, file_name):
    """精準解析單一檔案的標頭元數據 (Metadata)"""
    name, ext = os.path.splitext(file_name)
    prob_id = re.match(r"([a-z]\d+)", file_name).group(1) if re.match(r"([a-z]\d+)", file_name) else name

    # 預設學術严谨值
    metadata = {
        "prob_id": prob_id,
        "title": name,
        "complexity": "—",
        "tags": ["Uncategorized"],
        "difficulty": "未標記",
        "notion": "請在此處貼上連結",
        "status": "⏳ Todo",
        "ext": ext.lower()
    }

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            head_content = "".join([f.readline() for _ in range(15)])
        
        header_lower = head_content.lower()

        # 提取題目名稱
        title_match = re.search(r"(?://|#)\s*APCS Title:\s*(.*)", head_content)
        if title_match: metadata["title"] = title_match.group(1).strip()
        
        # 提取並標準化時間複雜度 (強制 LaTeX 學術小寫格式)
        comp_match = re.search(r"(?://|#)\s*APCS Complexity:\s*(.*)", head_content)
        if comp_match:
            val = comp_match.group(1).strip()
            val = val.replace("N", "n").replace("M", "m")  # 大寫轉小寫 n, m
            if "sqrt" in val: val = re.sub(r"sqrt\((.*?)\)", r"\\sqrt{\1}", val)
            if "log" in val: val = val.replace("log", "\\log ")
            metadata["complexity"] = f"${val}$" if not val.startswith("$") else val

        # 提取 APCS Tag (支援一題多標籤)
        tag_match = re.search(r"(?://|#)\s*APCS Tag:\s*(.*)", head_content)
        if tag_match:
            raw_tags = [t.strip() for t in tag_match.group(1).split(",") if t.strip()]
            if raw_tags: metadata["tags"] = raw_tags

        # 提取難度星星
        diff_match = re.search(r"(?://|#)\s*APCS Difficulty:\s*(\d+)", head_content)
        if diff_match:
            star_count = max(1, min(5, int(diff_match.group(1).strip())))
            metadata["difficulty"] = "".join(["★"] * star_count + ["☆"] * (5 - star_count))

        # 提取 Notion 連結
        notion_match = re.search(r"(?://|#)\s*APCS Note:\s*(https?://[^\s]+)", head_content)
        if notion_match: metadata["notion"] = notion_match.group(1).strip()

        # 判斷狀態 (工程化術語)
        if "# apcs status: in progress" in header_lower:
            metadata["status"] = "🚧 In Progress"
        elif metadata["notion"] == "請在此處貼上連結":
            metadata["status"] = "✍️ Documenting"
        else:
            metadata["status"] = "✅ Accepted"

    except Exception as e:
        print(f"❌ 無法讀取 {file_name} 的標籤資料: {e}")
        
    return metadata


def generate_l2_tables(category_name):
    """方案 B 核心：掃描平鋪檔案，依標籤分類生成多個區塊表格"""
    cat_path = category_name
    readme_path = os.path.join(cat_path, "README.md")
    
    if not os.path.exists(cat_path):
        return

    # 讀取該目錄下所有平鋪的原始碼
    files = [f for f in os.listdir(cat_path) if f.endswith((".cpp", ".py")) and "tempCodeRunner" not in f]
    
    # 建立按標籤分類的資料結構
    # { "Sorting": { "a010": {...} } }
    tag_groups = {}
    
    for f in sorted(files):
        file_path = os.path.join(cat_path, f)
        meta = parse_file_metadata(file_path, f)
        
        for tag in meta["tags"]:
            if tag not in tag_groups:
                tag_groups[tag] = {}
                
            prob_id = meta["prob_id"]
            if prob_id not in tag_groups[tag]:
                tag_groups[tag][prob_id] = {
                    "title": meta["title"],
                    "complexity": meta["complexity"],
                    "difficulty": meta["difficulty"],
                    "notion": meta["notion"],
                    "status": meta["status"],
                    "all_tags": meta["tags"],
                    "links": []
                }
            
            # 建立跨語言的程式連結
            label = "C++" if meta["ext"] == ".cpp" else "Py"
            tag_groups[tag][prob_id]["links"].append(f"[{label}](./{f})")

    # 根據配置好的子主題順序動態生成多張表格
    markdown_lines = [
        "> 💡 **使用說明**：點擊 **「題目名稱」** 的藍色超連結，可直接跳轉至該題的 Notion 詳細筆記頁面。",
        ""
    ]
    
    # 優先依照 CONFIG 中定義的子主題順序輸出，其餘沒定義到的標籤放後面
    defined_subs = list(CONFIG[category_name]["subs"].keys())
    all_tags = defined_subs + [t for t in tag_groups.keys() if t not in defined_subs]

    for tag in all_tags:
        if tag not in tag_groups or not tag_groups[tag]:
            continue
            
        markdown_lines.append(f"## 📌 {tag}")
        markdown_lines.append("")
        markdown_lines.append("| 題目名稱 | 程式連結 | 時間複雜度 | 難度 | 核心觀念 | 狀態 |")
        markdown_lines.append("| :--- | :---: | :--- | :--- | :--- | :---: |")
        
        for prob_id, info in sorted(tag_groups[tag].items()):
            title_cell = f"[**{info['title']}**]({info['notion']})" if info["notion"] != "請在此處貼上連結" else f"**{info['title']}**"
            formatted_tags = "<br>".join([f"`{t}`" for t in info["all_tags"]])
            prog_links = " ".join(sorted(info["links"]))
            
            markdown_lines.append(
                f"| {title_cell} | {prog_links} | {info['complexity']} | {info['difficulty']} | {formatted_tags} | {info['status']} |"
            )
        markdown_lines.append("")

    # 安全地寫回該分類的 README.md
    if os.path.exists(readme_path):
        with open(readme_path, "r", encoding="utf-8") as f:
            content = f.read()
        if L2_START in content and L2_END in content:
            pattern = f"{re.escape(L2_START)}.*?{re.escape(L2_END)}"
            table_content = "\n".join(markdown_lines)
            new_content = re.sub(pattern, f"{L2_START}\n{table_content}\n{L2_END}", content, flags=re.DOTALL)
            with open(readme_path, "w", encoding="utf-8") as f:
                f.write(new_content)


def update_l1_chapter(category_name):
    """更新大分類 README 的子主題進度條（完全從平鋪的檔案標籤中計算人數）"""
    readme_path = os.path.join(category_name, "README.md")
    if not os.path.exists(readme_path):
        return
        
    files = [f for f in os.listdir(category_name) if f.endswith((".cpp", ".py")) and "tempCodeRunner" not in f]
    
    # 統計各標籤不重複的題號數量
    tag_counts = {}
    for f in files:
        meta = parse_file_metadata(os.path.join(category_name, f), f)
        for tag in meta["tags"]:
            if tag not in tag_counts:
                tag_counts[tag] = set()
            tag_counts[tag].add(meta["prob_id"])

    table = ["| 子主題 | 進度 | 完成率 | 狀態 |", "| :--- | :---: | :---: | :--- |"]
    
    for sub, target in CONFIG[category_name]["subs"].items():
        count = len(tag_counts.get(sub, set()))
        pct = int((count / target) * 100) if target > 0 else 0
        table.append(f"| {sub} | {count}/{target} | {pct}% | {'✅' if count >= target else '🔥'} |")

    table_content = "\n".join(table)
    with open(readme_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    if L1_START in content and L1_END in content:
        parts = content.split(L1_START)
        new_content = f"{parts[0]}{L1_START}\n{table_content}\n{L1_END}{parts[1].split(L1_END)[1]}"
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(new_content)


def update_l0_root():
    """更新全專案根目錄的總進度表"""
    readme_path = "README.md"
    if not os.path.exists(readme_path):
        return
        
    table = ["| 階段大分類 | 完成度 | 完成率 |", "| :--- | :---: | :---: |"]
    
    for cat, info in CONFIG.items():
        if not os.path.exists(cat):
            continue
        # 直接統計大分類資料夾下平鋪的不重複題號
        unique_problems = {
            os.path.splitext(f)[0].split("_")[0]
            for f in os.listdir(cat)
            if f.endswith((".cpp", ".py")) and "tempCodeRunner" not in f
        }
        count = len(unique_problems)
        pct = int((count / info["total"]) * 100) if info["total"] > 0 else 0
        table.append(f"| [{cat}](./{cat}/) | {count}/{info['total']} | {pct}% |")

    table_content = "\n".join(table)
    with open(readme_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    if ROOT_START in content and ROOT_END in content:
        parts = content.split(ROOT_START)
        new_content = f"{parts[0]}{ROOT_START}\n{table_content}\n{ROOT_END}{parts[1].split(ROOT_END)[1]}"
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(new_content)


if __name__ == "__main__":
    print("🚀 開始進行全新全平鋪架構 README 同步...")
    for cat in CONFIG.keys():
        generate_l2_tables(cat)
        update_l1_chapter(cat)
    update_l0_root()
    print("✨ 全站數據驅動 README 索引重構完成！")