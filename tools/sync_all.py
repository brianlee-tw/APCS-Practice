import os
import re
import datetime
import subprocess

# --- 1. 規格化配置區：定義大分類與其預期的總目標題數 ---
CONFIG = {
    "01_Basic_Syntax_Optimization": {"title_zh": "語法特性與實作優化", "total": 50},
    "02_Data_Structures": {"title_zh": "線性與非線性資料結構", "total": 50},
    "03_Algorithmic_Paradigms": {"title_zh": "核心演算法典範", "total": 50},
    "04_Graph_Theory_and_Advanced_Topics": {"title_zh": "圖論與進階專題", "total": 50},
}

REVIEW_THRESHOLD_DAYS = 90

# --- 2. 標籤錨點設定 ---
ROOT_START, ROOT_END = "<!-- ROOT_START -->", "<!-- ROOT_END -->"
L1_START, L1_END = "<!-- L1_START -->", "<!-- L1_END -->"

def get_file_last_mod_time(file_path):
    """結合 Git Log 與本機檔案系統，取得最精準的最後修改日期"""
    try:
        # 1. 取得本機檔案系統的最後修改時間
        mtime = os.path.getmtime(file_path)
        local_date = datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d')
        
        # 2. 嘗試取得 Git 的最後提交時間
        abs_path = os.path.abspath(file_path)
        file_dir = os.path.dirname(abs_path)
        file_name = os.path.basename(abs_path)
        
        cmd = ["git", "log", "-1", "--format=%cd", "--date=short", file_name]
        git_date = subprocess.check_output(
            cmd, 
            cwd=file_dir, 
            stderr=subprocess.PIPE
        ).decode('utf-8').strip()
        
        # 採取安全策略：如果檔案在本地被動過，以最新修改為準
        if git_date:
            return max(local_date, git_date)
            
        return local_date
        
    except Exception:
        try:
            return datetime.datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d')
        except:
            return datetime.datetime.now().strftime('%Y-%m-%d')

def parse_file_metadata(file_path, file_name):
    """解析檔案元數據，優化欄位長度與時間抓取"""
    name, ext = os.path.splitext(file_name)
    prob_id_match = re.match(r"([a-z]\d+)", file_name.lower())
    prob_id = prob_id_match.group(1) if prob_id_match else name.lower()

    last_mod = get_file_last_mod_time(file_path)

    metadata = {
        "prob_id": prob_id, "title": name, "complexity": "—",
        "tags": [], "difficulty": "★", "notion": None, 
        "status": "📝", 
        "ext": ext.lower(),
        "last_modified": last_mod
    }

    try:
        if os.path.getsize(file_path) == 0:
            metadata["status"] = "🆕"
            return metadata

        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            head_content = "\n".join(content.splitlines()[:15])
        
        # 1. 提取題目名稱
        title_match = re.search(r"(?://|#)\s*APCS Title:\s*(.*)", head_content)
        if title_match: metadata["title"] = title_match.group(1).strip()
        
        # 2. 複雜度
        comp_match = re.search(r"(?://|#)\s*APCS Complexity:\s*(.*)", head_content)
        if comp_match: metadata["complexity"] = f"${comp_match.group(1).strip()}$"

        # 3. 難度
        diff_match = re.search(r"(?://|#)\s*APCS Difficulty:\s*(\d+)", head_content)
        if diff_match: metadata["difficulty"] = "★" * int(diff_match.group(1).strip())

        # 4. 標籤
        tag_match = re.search(r"(?://|#)\s*APCS Tag:\s*(.*)", head_content)
        if tag_match:
            metadata["tags"] = [t.strip() for t in tag_match.group(1).split(",") if t.strip()]

        # 5. 狀態判定與 Notion 連結
        status_match = re.search(r"(?://|#)\s*APCS Status:\s*(.*)", head_content, re.IGNORECASE)
        notion_match = re.search(r"(?://|#)\s*APCS Note:\s*(https?://[^\s]+)", head_content)
        
        if status_match and "in progress" in status_match.group(1).lower():
            metadata["status"] = "🚧"
        elif notion_match:
            metadata["status"] = "✅"
        else:
            metadata["status"] = "📝"
            
        if metadata["status"] == "✅":
            last_mod_date = datetime.datetime.strptime(metadata["last_modified"], '%Y-%m-%d')
            today = datetime.datetime.now()
            days_diff = (today - last_mod_date).days
            
            if days_diff >= REVIEW_THRESHOLD_DAYS:
                metadata["status"] = "🔔"
            
        if notion_match:
            metadata["notion"] = notion_match.group(1).strip()

    except Exception:
        metadata["status"] = "❌"
        
    return metadata

def update_l1_readme(category_name):
    """更新或創建大分類 (L1) README 檔案"""
    cat_path = category_name
    readme_path = os.path.join(cat_path, "README.md")
    
    if not os.path.exists(cat_path):
        print(f"⚠️ 找不到資料夾 {cat_path}，跳過。")
        return

    if not os.path.exists(readme_path):
        initial_content = f"# {category_name}: {CONFIG[category_name]['title_zh']}\n\n{L1_START}\n{L1_END}\n"
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
                "links": [],
                "last_modified": meta["last_modified"]
            }
        
        label = "C++" if meta["ext"] == ".cpp" else "Py"
        prob_summary[prob_id]["links"].append(f"[{label}](./{f})")

    # --- 構建表格 Markdown ---
    markdown_lines = [
        "> 💡 **使用說明**：點擊 **「題目名稱」** 的藍色超連結，可直接跳轉至該題的 Notion 詳細筆記頁面。",
        "",
        "| 題目名稱 | 程式 | 複雜度 | 難度 | 核心觀念 | 狀態 | 最後編輯 |",
        "|:---|:---:|:---|:---|:---|:---:|:---:|"
    ]
    
    for prob_id, info in sorted(prob_summary.items()):
        title_cell = f"[**{info['title']}**]({info['notion']})" if info["notion"] else f"**{info['title']}**"
        
        # 1. 修正：程式連結改用 <br> 換行標示
        prog_links = "<br>".join(sorted(info["links"], reverse=True))
        
        # 2. 修正：核心觀念正確分隔，並使用 <small> 縮小字體
        tags_string = ", ".join([f"`{t}`" for t in info["tags"]])
        formatted_tags = f"<small>{tags_string}</small>" if tags_string else "—"
        
        # 3. 修正：最後編輯移除反引號，並使用 <small> 縮小字體
        date_cell = f"<small>{info['last_modified']}</small>"
        
        markdown_lines.append(
            f"| {title_cell} | {prog_links} | {info['complexity']} | {info['difficulty']} | {formatted_tags} | {info['status']} | {date_cell} |"
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

    parts_start = content.split(L1_START)
    parts_end = parts_start[1].split(L1_END)
    new_content = f"{parts_start[0]}{L1_START}\n{progress_header}\n\n{table_content}\n{L1_END}{parts_end[1]}"
    
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"✅ 已成功更新大分類總表: {readme_path}")


def update_l0_root():
    """更新全專案根目錄的 README，包含統計數據、進度條與複習清單"""
    readme_path = "README.md"
    if not os.path.exists(readme_path): return

    category_rows = []
    total_done, total_all = 0, 0
    need_review_list = []

    for cat, info in CONFIG.items():
        if not os.path.exists(cat): continue
        
        files = [f for f in os.listdir(cat) if f.endswith((".cpp", ".py")) and "tempCodeRunner" not in f]
        unique_probs = set()
        
        for f in files:
            file_path = os.path.join(cat, f)
            meta = parse_file_metadata(file_path, f)
            unique_probs.add(meta["prob_id"])
            
            if "🔔" in meta["status"]:
                need_review_list.append(f"[{meta['prob_id']}](./{cat}/{f})")
        
        count = len(unique_probs)
        pct = int((count / info["total"]) * 100) if info["total"] > 0 else 0
        html_progress = f'<progress value="{count}" max="{info["total"]}"></progress> {pct}%'
        
        category_rows.append(f"| [{cat}](./{cat}/) | {count}/{info['total']} | {html_progress} |")
        
        total_done += count
        total_all += info["total"]

    review_display = ", ".join(need_review_list) if need_review_list else "目前無待複習題目"
    review_count = len(need_review_list)
    overall_pct = int((total_done / total_all) * 100) if total_all > 0 else 0

    dashboard_content = f"""## 全域學習儀表板
| 總覽指標 | 數據統計 |
| :--- | :--- |
| **總題目數** | `{total_done} / {total_all}` |
| **目前進度** | <progress value="{total_done}" max="{total_all}"></progress> {overall_pct}% |
| **待複習 (超過{REVIEW_THRESHOLD_DAYS}天)** | `{review_count} 題` |
| **複習清單** | {review_display} |

<br>

## 題庫整體進度
| 階段大分類 | 完成度 | 完成率 |
| :--- | :---: | :---: |
{chr(10).join(category_rows)}"""

    with open(readme_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    if ROOT_START not in content or ROOT_END not in content:
        content += f"\n\n{ROOT_START}\n{ROOT_END}\n"

    parts_start = content.split(ROOT_START)
    parts_end = parts_start[1].split(ROOT_END)
    new_content = f"{parts_start[0]}{ROOT_START}\n{dashboard_content}\n{ROOT_END}{parts_end[1]}"
    
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print("✅ 已成功更新全專案根目錄 README (含儀表板與複習清單)！")


if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(script_dir)
    os.chdir(root_dir)
    
    print(f"🚀 開始進行全新規格化平鋪架構 README 同步 (工作目錄: {root_dir})...")
    for cat in CONFIG.keys():
        update_l1_readme(cat)
    update_l0_root()
    print("✨ 資料庫驅動兩層式 README 索引重構完成！")