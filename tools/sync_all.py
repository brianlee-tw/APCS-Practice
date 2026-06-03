import os
import re
import datetime
import subprocess

# --- 1. 規格化配置區：定義大分類與其預期的總目標題數 ---
CONFIG = {
    "01_Basic_Syntax_Optimization": {"title_zh": "語法特性與實作優化", "total": 11},
    "02_Data_Structures": {"title_zh": "線性與非線性資料結構", "total": 24},
    "03_Algorithmic_Paradigms": {"title_zh": "核心演算法典範", "total": 36},
    "04_Graph_Theory_and_Advanced_Topics": {"title_zh": "圖論與進階專題", "total": 42},
}

REVIEW_THRESHOLD_DAYS = 90

# --- 2. 標籤錨點設定 ---
ROOT_START, ROOT_END = "<!-- ROOT_START -->", "<!-- ROOT_END -->"
L1_START, L1_END = "<!-- L1_START -->", "<!-- L1_END -->"

def get_git_last_mod(file_path):
    """透過 Git Log 取得檔案最後提交日期"""
    try:
        # 執行 git log 指令取得該檔案最後一次變更的日期
        cmd = ["git", "log", "-1", "--format=%cd", "--date=short", file_path]
        result = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode('utf-8').strip()
        return result
    except:
        # 如果該檔案尚未被 Git 追蹤，回傳今日日期作為保底
        return datetime.datetime.now().strftime('%Y-%m-%d')

def parse_file_metadata(file_path, file_name):
    """解析檔案元數據，改用 Git 時間取代系統檔案時間"""
    name, ext = os.path.splitext(file_name)
    prob_id_match = re.match(r"([a-z]\d+)", file_name.lower())
    prob_id = prob_id_match.group(1) if prob_id_match else name.lower()

    # --- 修改點：這裡改為呼叫 Git 指令 ---
    last_mod = get_git_last_mod(file_path)

    metadata = {
        "prob_id": prob_id, "title": name, "complexity": "—",
        "tags": [], "difficulty": "★", "notion": None, 
        "status": "📝 Documenting", "ext": ext.lower(),
        "last_modified": last_mod
    }

    try:
        if os.path.getsize(file_path) == 0:
            metadata["status"] = "🆕 To-Do"
            return metadata

        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            head_content = "\n".join(content.splitlines()[:15])
        
        # 1. 提取題目名稱 (允許無 APCS Title 標頭，但若有則優先使用)
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
        
        # 判斷基礎狀態
        if status_match and "in progress" in status_match.group(1).lower():
            metadata["status"] = "🚧 In Progress"
        elif notion_match:
            metadata["status"] = "✅ Finished"
        else:
            metadata["status"] = "📝 Documenting"
            
        # 新增：複習提醒邏輯
        # 只有在狀態為 Finished 時才進行提醒
        if metadata["status"] == "✅ Finished":
            last_mod_date = datetime.datetime.strptime(metadata["last_modified"], '%Y-%m-%d')
            today = datetime.datetime.now()
            days_diff = (today - last_mod_date).days
            
            if days_diff >= REVIEW_THRESHOLD_DAYS:
                metadata["status"] = "🔔 Need Review" # 或者改為 "✅ Finished 🔔"
            
        if notion_match:
            metadata["notion"] = notion_match.group(1).strip()

    except Exception as e:
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
                "last_modified": meta["last_modified"] # <-- 記得加入這行
            }
        
        label = "C++" if meta["ext"] == ".cpp" else "Py"
        prob_summary[prob_id]["links"].append(f"[{label}](./{f})")

    # 1. 構建表格 Markdown
    # 1. 構建表格 Markdown (增加最後編輯欄位)
    markdown_lines = [
        "> 💡 **使用說明**：點擊 **「題目名稱」** 的藍色超連結，可直接跳轉至該題的 Notion 詳細筆記頁面。",
        "",
        "| 題目名稱 | 程式連結 | 時間複雜度 | 難度 | 核心觀念 | 狀態 | 最後編輯 |",
        "| :--- | :---: | :--- | :--- | :--- | :---: | :---: |"
    ]
    
    for prob_id, info in sorted(prob_summary.items()):
        title_cell = f"[**{info['title']}**]({info['notion']})" if info["notion"] != "請在此處貼上連結" else f"**{info['title']}**"
        formatted_tags = " ".join([f"`{t}`" for t in info["tags"]])
        prog_links = " ".join(sorted(info["links"], reverse=True))
        
        # 這裡加入 info['last_modified']
        markdown_lines.append(
            f"| {title_cell} | {prog_links} | {info['complexity']} | {info['difficulty']} | {formatted_tags} | {info['status']} | {info['last_modified']} |"
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
    """更新全專案根目錄的 README，包含統計數據、進度條與複習清單"""
    readme_path = "README.md"
    if not os.path.exists(readme_path): return

    # 1. 蒐集全域數據
    category_rows = []
    total_done, total_all = 0, 0
    need_review_list = []  # 用來存放待複習題目

    for cat, info in CONFIG.items():
        if not os.path.exists(cat): continue
        
        # 讀取該分類下的題目
        files = [f for f in os.listdir(cat) if f.endswith((".cpp", ".py")) and "tempCodeRunner" not in f]
        unique_probs = set()
        
        for f in files:
            file_path = os.path.join(cat, f)
            meta = parse_file_metadata(file_path, f)
            unique_probs.add(meta["prob_id"])
            
            # 檢查是否需要複習
            if "Need Review" in meta["status"]:
                need_review_list.append(f"[{meta['prob_id']}](./{cat}/{f})")
        
        count = len(unique_probs)
        pct = int((count / info["total"]) * 100) if info["total"] > 0 else 0
        html_progress = f'<progress value="{count}" max="{info["total"]}"></progress> {pct}%'
        
        category_rows.append(f"| [{cat}](./{cat}/) | {count}/{info['total']} | {html_progress} |")
        
        total_done += count
        total_all += info["total"]

    # 2. 處理複習清單字串
    review_display = ", ".join(need_review_list) if need_review_list else "目前無待複習題目"
    review_count = len(need_review_list)
    overall_pct = int((total_done / total_all) * 100) if total_all > 0 else 0

    # 3. 生成儀表板與進度表內容
    # 修改這裡，刪除 f""" 之後的所有縮排
    dashboard_content = f"""## 📈 全域學習儀表板
| 總覽指標 | 數據統計 |
| :--- | :--- |
| **總題目數** | `{total_done} / {total_all}` |
| **目前進度** | <progress value="{total_done}" max="{total_all}"></progress> {overall_pct}% |
| **待複習 (超過{REVIEW_THRESHOLD_DAYS}天)** | `{review_count} 題` |
| **複習清單** | {review_display} |

<br>

<br>

## 📊 題庫整體進度
| 階段大分類 | 完成度 | 完成率 |
| :--- | :---: | :---: |
{chr(10).join(category_rows)}"""

    # 4. 讀取並防呆寫入
    with open(readme_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    if ROOT_START not in content or ROOT_END not in content:
        content += f"\n\n{ROOT_START}\n{ROOT_END}\n"

    # 用字串切片相加，精準繞過 re.sub 的 Bug
    parts_start = content.split(ROOT_START)
    parts_end = parts_start[1].split(ROOT_END)
    new_content = f"{parts_start[0]}{ROOT_START}\n{dashboard_content}\n{ROOT_END}{parts_end[1]}"
    
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print("✅ 已成功更新全專案根目錄 README (含儀表板與複習清單)！")


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