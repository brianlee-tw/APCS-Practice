import os
import re  # 👈 1. 統一搬到最頂端，乾淨又安全！

# --- 設定區：直觀定義結構與目標 ---
CONFIG = {
    "01_Basic_Syntax": {
        "total":                    11,
        "subs": {
            "01_IO_Optimization":   3,
            "02_Conditionals":      2,
            "03_Loops":             3,
            "04_Functions":         3,
        },
    },
    "02_Data_Structures": {
        "total":                    24,
        "subs": {"01_Array":        6, 
                 "02_Vector":       6, 
                 "03_String":       8, 
                 "04_Struct":       4
        },
    },
    "03_Basic_Algorithms": {
        "total":                    36,
        "subs": {
            "01_Sorting":           5,
            "02_Binary_Search":     6,
            "03_Greedy":            8,
            "04_Brute_Force":       5,
            "05_Two_Pointers":      7,
            "06_Math_Theory":       5,
        },
    },
    "04_Advanced_Topics": {
        "total":                    42,
        "subs": {
            "01_Recursion":         6,
            "02_Stack_Queue":       6,
            "03_DFS":               7,
            "04_BFS":               7,
            "05_DP":                10,
            "06_Graph_Tree":        6,
        },
    },
}

# --- 標籤設定 ---
ROOT_START, ROOT_END = "<!-- ROOT_START -->", "<!-- ROOT_END -->"
L1_START, L1_END = "<!-- L1_START -->", "<!-- L1_END -->"
L2_START, L2_END = "<!-- L2_START -->", "<!-- L2_END -->"


def update_l2_topic(path, sub_name):
    readme_path = os.path.join(path, "README.md")

    files = [f for f in os.listdir(path) if f.endswith((".cpp", ".py")) and "tempCodeRunner" not in f] if os.path.exists(path) else []

    data = {}
    for f in sorted(files):
        name = os.path.splitext(f)[0]
        ext = os.path.splitext(f)[1].lower()
        file_path = os.path.join(path, f)

        # 預設值
        prob_title, complexity, tag, difficulty, notion_url, head_content = name, "未標記", "`未標記`", "未標記", "請在此處貼上連結", ""

        try:
            with open(file_path, "r", encoding="utf-8") as file_obj:
                head_lines = [file_obj.readline() for _ in range(10)]
                head_content = "".join(head_lines)

                # 提取標籤
                title_match = re.search(r"(?://|#)\s*APCS Title:\s*(.*)", head_content)
                if title_match: prob_title = title_match.group(1).strip()
                
                comp_match = re.search(r"(?://|#)\s*APCS Complexity:\s*(.*)", head_content)
                if comp_match:
                    val = comp_match.group(1).strip()
                    if "sqrt" in val: val = re.sub(r"sqrt\((.*?)\)", r"\\sqrt{\1}", val)
                    if "log" in val: val = val.replace("log", "\\log ")
                    complexity = f"${val}$" if not val.startswith("$") else val

                tag_match = re.search(r"(?://|#)\s*APCS Tag:\s*(.*)", head_content)
                if tag_match:
                    raw_tag = tag_match.group(1).strip()
                    tags = [f"`{t.strip()}`" for t in raw_tag.split(",") if t.strip()]
                    tag = "<br>".join(tags) if tags else "`未標記`"

                diff_match = re.search(r"(?://|#)\s*APCS Difficulty:\s*(\d+)", head_content)
                if diff_match:
                    star_count = max(1, min(5, int(diff_match.group(1).strip())))
                    difficulty = " ".join(["★"] * star_count + ["☆"] * (5 - star_count))

                notion_match = re.search(r"(?://|#)\s*APCS Note:\s*(https?://[^\s]+)", head_content)
                if notion_match: notion_url = notion_match.group(1).strip()
        except Exception as e:
            print(f"無法讀取 {f} 的標籤資料: {e}")

        # 資料儲存
        if name not in data:
            data[name] = {"links": [], "title": prob_title, "complexity": complexity, "tag": tag, "difficulty": difficulty, "notion": notion_url, "head_content": head_content}
        
        data[name]["links"].append(f"[{'C++' if ext == '.cpp' else 'Py'}](./{f})")

    # 生成表格
    # === 替換這段：生成表格與寫回 README ===
    
    # 1. 精簡欄位標題，刪除「詳細筆記」，釋放橫向空間
    table = [
        "> 💡 **使用說明**：點擊 **「題目名稱」** 的藍色超連結，可直接跳轉至該題的 Notion 詳細筆記頁面。",
        "",
        "| 題目名稱 | 程式連結 | 時間複雜度 | 難度 | 核心觀念 | 狀態 |", 
        "| :--- | :---: | :--- | :--- | :--- | :---: |"  # 👈 將難度的 :---: 改為 :--- (靠左對齊)
    ]
    
    for name, info in data.items():
        header = info.get("head_content", "").lower()
        if not info["links"]: status_text = "⏳ 待挑戰"
        elif "# apcs status: in progress" in header: status_text = "🚧 進行中"
        elif info["notion"] == "請在此處貼上連結": status_text = "✍️ 補筆記"
        else: status_text = "✅ 已過關"
        
        # 2. 核心邏輯：判斷是否有筆記。如果有，將題目名稱做成 Notion 超連結；沒有則維持粗體
        if info["notion"] != "請在此處貼上連結":
            title_cell = f"[**{info['title']}**]({info['notion']})"
        else:
            title_cell = f"**{info['title']}**"
            
        # 3. 重新組合表格欄位（已拿掉原本的詳細筆記欄位）
        table.append(f"| {title_cell} | {' '.join(info['links'])} | {info['complexity']} | {info['difficulty']} | {info['tag']} | {status_text} |")

    # 寫回 README
    if os.path.exists(readme_path):
        with open(readme_path, "r", encoding="utf-8") as f: content = f.read()
        if L2_START and L2_END and L2_START in content and L2_END in content:
            pattern = f"{re.escape(L2_START)}.*?{re.escape(L2_END)}"
            old_block_match = re.search(pattern, content, flags=re.DOTALL)
            if old_block_match:
                new_content = content.replace(old_block_match.group(0), f"{L2_START}\n{'\n'.join(table)}\n{L2_END}")
                with open(readme_path, "w", encoding="utf-8") as f: f.write(new_content)

def update_l1_chapter(path, cat_name):
    readme_path = os.path.join(path, "README.md")
    if not os.path.exists(readme_path):
        return
    table = ["| 子主題 | 進度 | 完成率 | 狀態 |", "| :--- | :---: | :---: | :--- |"]
    for sub, target in CONFIG[cat_name]["subs"].items():
        sub_path = os.path.join(path, sub)
        
        # 🔒 題目去重機制：使用 set 抓取不含副檔名的題號/檔名
        if os.path.exists(sub_path):
            unique_problems = {
                os.path.splitext(f)[0] 
                for f in os.listdir(sub_path) 
                if f.endswith((".cpp", ".py")) and "tempCodeRunner" not in f
            }
            count = len(unique_problems)
        else:
            count = 0
            
        pct = int((count / target) * 100) if target > 0 else 0
        table.append(
            f"| [{sub}](./{sub}/) | {count}/{target} | {pct}% | {'✅' if count >= target else '🔥'} |"
        )

    table_content = "\n".join(table)
    with open(readme_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    # 👉 2. 加上防禦性判斷，確保 L1_START 不是空字串，且確實存在於內文中
    if L1_START and L1_END and L1_START in content and L1_END in content:
        parts = content.split(L1_START)
        new_content = f"{parts[0]}{L1_START}\n{table_content}\n{L1_END}{parts[1].split(L1_END)[1]}"
        if new_content != content:
            with open(readme_path, "w", encoding="utf-8") as f:
                f.write(new_content)
    else:
        print(f"⚠️ 警告：{readme_path} 找不到完整的 L1 標籤，已自動跳過。")


def update_l0_root():
    readme_path = "README.md"
    if not os.path.exists(readme_path):
        return
        
    table = ["| 階段大分類 | 完成度 | 完成率 |", "| :--- | :---: | :---: |"]
    for cat, info in CONFIG.items():
        
        # 🔒 根目錄大分類同樣導入去重機制
        count = 0
        for sub in info["subs"]:
            sub_path = os.path.join(cat, sub)
            if os.path.exists(sub_path):
                unique_problems = {
                    os.path.splitext(f)[0]
                    for f in os.listdir(sub_path)
                    if f.endswith((".cpp", ".py")) and "tempCodeRunner" not in f
                }
                count += len(unique_problems)
                
        pct = int((count / info["total"]) * 100) if info["total"] > 0 else 0
        table.append(f"| [{cat}](./{cat}/) | {count}/{info['total']} | {pct}% |")

    table_content = "\n".join(table)
    with open(readme_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    # 👉 確保 ROOT 標籤存在且不為空
    if ROOT_START and ROOT_END and ROOT_START in content and ROOT_END in content:
        parts = content.split(ROOT_START)
        new_content = f"{parts[0]}{ROOT_START}\n{table_content}\n{ROOT_END}{parts[1].split(ROOT_END)[1]}"
        if new_content != content:
            with open(readme_path, "w", encoding="utf-8") as f:
                f.write(new_content)
    else:
        print(f"⚠️ 警告：根目錄 {readme_path} 找不到完整的 ROOT 標籤，已自動跳過。")


if __name__ == "__main__":
    for cat, info in CONFIG.items():
        for sub in info["subs"]:
            update_l2_topic(os.path.join(cat, sub), sub)
        update_l1_chapter(cat, cat)
    update_l0_root()
    print("全站 README 同步完成！")