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
    """嚴格模式：解析檔案元數據，解析失敗會將錯誤寫入 status"""
    name, ext = os.path.splitext(file_name)
    prob_id_match = re.match(r"([a-z]\d+)", file_name.lower())
    prob_id = prob_id_match.group(1) if prob_id_match else name.lower()

    # 預設結構：狀態預設為 AC (假設正確)
    metadata = {
        "prob_id": prob_id, "title": name, "complexity": "—",
        "tags": [], "difficulty": "★", "notion": None, 
        "status": "✅ Accepted", "ext": ext.lower()
    }

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            head_content = "".join([f.readline() for _ in range(15)])
        
        # --- 嚴格解析區 ---
        # 檢查是否有基本標頭，若無則拋出異常
        if "APCS Title:" not in head_content:
            raise ValueError("Missing APCS Title Header")

        # 1. 提取題目名稱
        title_match = re.search(r"(?://|#)\s*APCS Title:\s*(.*)", head_content)
        metadata["title"] = title_match.group(1).strip()
        
        # 2. 複雜度 (保持 LaTeX 格式)
        comp_match = re.search(r"(?://|#)\s*APCS Complexity:\s*(.*)", head_content)
        if comp_match: metadata["complexity"] = f"${comp_match.group(1).strip()}$"

        # 3. 難度 (僅顯示實心星星)
        diff_match = re.search(r"(?://|#)\s*APCS Difficulty:\s*(\d+)", head_content)
        if diff_match:
            metadata["difficulty"] = "★" * int(diff_match.group(1).strip())

        # 4. 標籤 (移除頓號，改用 Markdown code block 獨立標籤)
        tag_match = re.search(r"(?://|#)\s*APCS Tag:\s*(.*)", head_content)
        if tag_match:
            metadata["tags"] = [t.strip() for t in tag_match.group(1).split(",") if t.strip()]

        # 5. Notion 連結
        notion_match = re.search(r"(?://|#)\s*APCS Note:\s*(https?://[^\s]+)", head_content)
        if notion_match: 
            metadata["notion"] = notion_match.group(1).strip()
        else:
            metadata["status"] = "✍️ Documenting" # 無連結則視為文件化中

    except Exception as e:
        # 將錯誤資訊寫入 metadata，這樣 README 表格就會顯示出來
        metadata["status"] = f"❌ Error: {str(e)}"
        
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
        formatted_tags = " ".join([f"`{t}`" for t in info["tags"]])
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
        
    if L1_START not in content or L1_END not in content:
        content += f"\n\n{L1_START}\n{L1_END}\n"

    # 用字串切片相加，精準繞過 re.sub 的 Bug
    parts_start = content.split(L1_START)
    parts_end = parts_start[1].split(L1_END)
    new_content = f"{parts_start[0]}{L1_START}\n{progress_header}\n\n{table_content}\n{L1_END}{parts_end[1]}"
    
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
    # 獲取當前腳本所在的目錄
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # 獲取專案根目錄 (假設 tools 在根目錄下)
    root_dir = os.path.dirname(script_dir)
    
    # 切換工作目錄到根目錄
    os.chdir(root_dir)
    
    print(f"🚀 開始進行全新規格化平鋪架構 README 同步 (工作目錄: {root_dir})...")
    for cat in CONFIG.keys():
        update_l1_readme(cat)
    update_l0_root()
    print("✨ 資料庫驅動兩層式 README 索引重構完成！")