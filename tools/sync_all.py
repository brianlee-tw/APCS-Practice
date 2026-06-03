import os
import re

# --- 1. 規格化配置區：定義大分類與其預期的總目標題數 ---
CONFIG = {
    "01_Basic_Syntax_Optimization": {"title_zh": "語法特性與實作優化", "total": 11},
    "02_Data_Structures": {"title_zh": "線性與非線性資料結構", "total": 24},
    "03_Algorithmic_Paradigms": {"title_zh": "核心演算法典範", "total": 36},
    "04_Graph_Theory_and_Advanced_Topics": {"title_zh": "圖論與進階專題", "total": 42},
}

# --- 2. 標籤錨點設定 ---
ROOT_START, ROOT_END = "<!-- ROOT_START -->", "<!-- ROOT_END -->"
L1_START, L1_END = "<!-- L1_START -->", "<!-- L1_END -->"


def parse_file_metadata(file_path, file_name):
    """精準解析單一檔案的標頭元數據 (Metadata)"""
    name, ext = os.path.splitext(file_name)
    prob_id_match = re.match(r"([a-z]\d+)", file_name.lower())
    prob_id = prob_id_match.group(1) if prob_id_match else name.lower()

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

        # 1. 提取題目名稱
        title_match = re.search(r"(?://|#)\s*APCS Title:\s*(.*)", head_content)
        if title_match: metadata["title"] = title_match.group(1).strip()
        
        # 2. 提取並標準化時間複雜度
        comp_match = re.search(r"(?://|#)\s*APCS Complexity:\s*(.*)", head_content)
        if comp_match:
            val = comp_match.group(1).strip()
            val = val.replace("N", "n").replace("M", "m")  
            if "sqrt" in val: val = re.sub(r"sqrt\((.*?)\)", r"\\sqrt{\1}", val)
            if "log" in val: val = val.replace("log", "\\log ")
            metadata["complexity"] = f"${val}$" if not val.startswith("$") else val

        # 3. 提取 APCS Tag
        tag_match = re.search(r"(?://|#)\s*APCS Tag:\s*(.*)", head_content)
        if tag_match:
            raw_tags = [t.strip().replace("_", " ") for t in tag_match.group(1).split(",") if t.strip()]
            if raw_tags: metadata["tags"] = raw_tags

        # 4. 提取難度星星
        diff_match = re.search(r"(?://|#)\s*APCS Difficulty:\s*(\d+)", head_content)
        if diff_match:
            star_count = max(1, min(5, int(diff_match.group(1).strip())))
            metadata["difficulty"] = "".join(["★"] * star_count + ["☆"] * (5 - star_count))

        # 5. 提取 Notion 連結
        notion_match = re.search(r"(?://|#)\s*APCS Note:\s*(https?://[^\s]+)", head_content)
        if notion_match: metadata["notion"] = notion_match.group(1).strip()

        # 6. 判斷狀態
        if "# apcs status: in progress" in header_lower or "// apcs status: in progress" in header_lower:
            metadata["status"] = "🚧 In Progress"
        elif metadata["notion"] == "請在此處貼上連結":
            metadata["status"] = "✍️ Documenting"
        else:
            metadata["status"] = "✅ Accepted"

    except Exception as e:
        print(f"❌ 無法讀取 {file_name} 的標籤資料: {e}")
        
    return metadata


def update_l1_readme(category_name):
    """更新或創建大分類 (L1) README 檔案"""
    cat_path = category_name
    readme_path = os.path.join(cat_path, "README.md")
    
    if not os.path.exists(cat_path):
        print(f"⚠️ 找不到資料夾 {cat_path}，跳過。")
        return

    # 如果 README 不存在，自動初始化一個
    if not os.path.exists(readme_path):
        initial_content = f"# {category_name}: {CONFIG[category_name]['title_zh']}\n\n{L1_START_TXT}\n{L1_END_TXT}\n"
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(initial_content)
        print(f"ℹ️ 自動創建了缺失的 {readme_path}")

    files = [f for f in os.listdir(cat_path) if f.endswith((".cpp", ".py")) and "tempCodeRunner" not in f]
    
    prob_summary = {}
    for f in sorted(files):
        file_path = os.path.join(cat_path, f)
        meta = parse_file_metadata(file_path, f)
        prob_id = meta["prob_id"]
        
        if prob_id not in prob_summary:
            prob_summary[prob_id] = {
                "title": meta["title"],
                "complexity": meta["complexity"],
                "difficulty": meta["difficulty"],
                "notion": meta["notion"],
                "status": meta["status"],
                "tags": meta["tags"],
                "links": []
            }
        
        label = "C++" if meta["ext"] == ".cpp" else "Py"
        prob_summary[prob_id]["links"].append(f"[{label}](./{f})")

    # 1. 構建表格 Markdown
    markdown_lines = [
        "> 💡 **使用說明**：點擊 **「題目名稱」** 的藍色超連結，可直接跳轉至該題的 Notion 詳細筆記頁面。",
        "",
        "| 題目名稱 | 程式連結 | 時間複雜度 | 難度 | 核心觀念 | 狀態 |",
        "| :--- | :---: | :--- | :--- | :--- | :---: |"
    ]
    
    for prob_id, info in sorted(prob_summary.items()):
        title_cell = f"[**{info['title']}**]({info['notion']})" if info["notion"] != "請在此處貼上連結" else f"**{info['title']}**"
        formatted_tags = "、".join([f"`{t}`" for t in info["tags"]])
        prog_links = " ".join(sorted(info["links"], reverse=True))
        
        markdown_lines.append(
            f"| {title_cell} | {prog_links} | {info['complexity']} | {info['difficulty']} | {formatted_tags} | {info['status']} |"
        )
    
    table_content = "\n".join(markdown_lines)

    # 2. 計算總進度
    total_target = CONFIG[category_name]["total"]
    total_done = len(prob_summary)
    pct = int((total_done / total_target) * 100) if total_target > 0 else 0
    progress_header = f"### 📊 當前章節複習進度：`{total_done}/{total_target}` ({pct}%)"

    # 3. 讀取並防呆寫入
    with open(readme_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    if L1_START_TXT not in content or L1_END_TXT not in content:
        content += f"\n\n{L1_START_TXT}\n{L1_END_TXT}\n"

    # 用字串切片相加，精準繞過 re.sub 的 Bug
    parts_start = content.split(L1_START_TXT)
    parts_end = parts_start[1].split(L1_END_TXT)
    new_content = f"{parts_start[0]}{L1_START_TXT}\n{progress_header}\n\n{table_content}\n{L1_END_TXT}{parts_end[1]}"
    
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"✅ 已成功更新大分類總表: {readme_path}")


def update_l0_root():
    """更新全專案根目錄的總進度表"""
    readme_path = "README.md"
    if not os.path.exists(readme_path):
        return
        
    table = ["| 階段大分類 | 完成度 | 完成率 |", "| :--- | :---: | :---: |"]
    
    for cat, info in CONFIG.items():
        if not os.path.exists(cat):
            continue
        
        unique_problems = set()
        for f in os.listdir(cat):
            if f.endswith((".cpp", ".py")) and "tempCodeRunner" not in f:
                meta = parse_file_metadata(os.path.join(cat, f), f)
                unique_problems.add(meta["prob_id"])
                
        count = len(unique_problems)
        pct = int((count / info["total"]) * 100) if info["total"] > 0 else 0
        table.append(f"| [{cat}](./{cat}/) | {count}/{info['total']} | {pct}% |")

    table_content = "\n".join(table)
    with open(readme_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    if ROOT_START not in content or ROOT_END not in content:
        content += f"\n\n{ROOT_START}\n{ROOT_END}\n"

    parts = content.split(ROOT_START)
    new_content = f"{parts[0]}{ROOT_START}\n{table_content}\n{ROOT_END}{parts[1].split(ROOT_END)[1]}"
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print("✅ 已成功更新全專案根目錄 README！")


if __name__ == "__main__":
    # 用於內部解析的實際 HTML 註解字串（防止被系統渲染吃掉的防禦寫法）
    L1_START_TXT = "<!-- L1_START -->"
    L1_END_TXT = "<!-- L1_END -->"
    
    print("🚀 開始進行全新規格化平鋪架構 README 同步...")
    for cat in CONFIG.keys():
        update_l1_readme(cat)
    update_l0_root()
    print("✨ 資料庫驅動兩層式 README 索引重構完成！")