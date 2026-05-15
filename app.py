import re
import json
import os
import streamlit as st
from datetime import datetime, date

st.title("📩 Mail ToDo Sorter")
st.write("メール本文からカテゴリ・重要度・締切・ToDoを生成し、ToDo一覧として管理するツール")

TODO_FILE = "todos.json"
COMPANY_FILE = "companies.json"
TODO_OPTION_FILE = "todo_options.json"
SUBJECT_FILE = "subjects.json"


def load_json(filename, default_value):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    return default_value


def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def extract_deadline(text):
    patterns = [
        r"\d{1,2}月\d{1,2}日(?:\s?\d{1,2}:\d{2})?",
        r"\d{1,2}/\d{1,2}(?:\s?\d{1,2}:\d{2})?",
        r"\d{4}/\d{1,2}/\d{1,2}(?:\s?\d{1,2}:\d{2})?",
        r"\d{4}年\d{1,2}月\d{1,2}日(?:\s?\d{1,2}:\d{2})?",
        r"本日中",
        r"明日",
        r"今週中",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group()

    return "未検出"


def parse_deadline(deadline):
    if deadline == "未検出":
        return datetime.max

    match = re.match(r"(\d{1,2})月(\d{1,2})日(?:\s?(\d{1,2}):(\d{2}))?", deadline)
    if match:
        year = datetime.now().year
        month = int(match.group(1))
        day = int(match.group(2))
        hour = int(match.group(3)) if match.group(3) else 23
        minute = int(match.group(4)) if match.group(4) else 59
        return datetime(year, month, day, hour, minute)

    return datetime.max


def classify_email(text):
    text_lower = text.lower()

    job_keywords = ["面接", "選考", "説明会", "エントリー", "内定", "採用", "履歴書", "es", "適性検査", "webテスト"]
    university_keywords = ["授業", "講義", "課題", "レポート", "研究室", "奨学金", "学務", "教務", "学生課", "情報センター", "保健室"]
    delivery_keywords = ["配送", "配達", "発送", "荷物", "お届け", "ヤマト", "佐川", "日本郵便", "追跡", "不在"]
    reservation_keywords = ["予約", "チケット", "受付番号", "整理番号", "入場", "購入完了", "決済完了", "公演", "イベント"]

    if any(keyword in text_lower for keyword in job_keywords):
        return "就活"
    elif any(keyword in text for keyword in university_keywords):
        return "大学"
    elif any(keyword in text for keyword in delivery_keywords):
        return "宅配"
    elif any(keyword in text for keyword in reservation_keywords):
        return "予約・チケット"
    else:
        return "その他"


def judge_importance(text):
    high_keywords = ["至急", "重要", "期限", "締切", "本日中", "明日", "面接", "選考", "提出", "受験", "返信", "確認"]
    medium_keywords = ["ご案内", "お知らせ", "説明会", "予約", "発送", "配達"]

    if any(keyword in text for keyword in high_keywords):
        return "高"
    elif any(keyword in text for keyword in medium_keywords):
        return "中"
    else:
        return "低"


def generate_todo(category, text):
    text_lower = text.lower()

    if category == "就活":
        if "面接" in text:
            return "面接日程・参加方法を確認する"
        elif "適性検査" in text or "webテスト" in text_lower:
            return "適性検査・Webテストを受験する"
        elif "提出" in text or "履歴書" in text or "es" in text_lower:
            return "提出物を確認して対応する"
        elif "返信" in text:
            return "企業へ返信する"
        else:
            return "就活関連の内容を確認する"

    elif category == "大学":
        if "課題" in text or "レポート" in text:
            return "課題・レポートの内容と締切を確認する"
        elif "授業" in text or "講義" in text:
            return "授業・講義の連絡内容を確認する"
        elif "奨学金" in text:
            return "奨学金関連の案内を確認する"
        else:
            return "大学からの連絡内容を確認する"

    elif category == "宅配":
        return "配送状況・受け取り日時を確認する"

    elif category == "予約・チケット":
        return "予約内容・日時・チケット情報を確認する"

    else:
        return "内容を確認し、必要があれば対応する"


def detect_company(text, companies):
    for company in companies:
        if company in text:
            return company
    return "未分類"

def get_todo_options(category, custom_todo_options):
    default_options = {
        "就活": [
            "面接日程・参加方法を確認する",
            "企業へ返信する",
            "提出物を確認して対応する",
            "適性検査・Webテストを受験する",
            "選考結果を確認する",
        ],
        "大学": [
            "授業・講義の連絡内容を確認する",
            "課題・レポートの内容と締切を確認する",
            "研究室関連の連絡を確認する",
            "奨学金関連の案内を確認する",
        ],
        "宅配": [
            "配送状況・受け取り日時を確認する",
            "再配達を依頼する",
        ],
        "予約・チケット": [
            "予約内容・日時・チケット情報を確認する",
            "支払い状況を確認する",
            "当日の持ち物・集合時間を確認する",
        ],
        "その他": [
            "内容を確認し、必要があれば対応する",
        ],
    }

    options = default_options.get(category, default_options["その他"])

    if category in custom_todo_options:
        options += custom_todo_options[category]

    return list(dict.fromkeys(options))
    
def related_name_input(category, current_value, companies, subjects, key_prefix):
    if category == "就活":
        options = ["未分類"] + companies + ["新しく追加する"]
        default_index = options.index(current_value) if current_value in options else 0

        selected = st.selectbox(
            "企業名",
            options,
            index=default_index,
            key=f"{key_prefix}_company_select"
        )

        if selected == "新しく追加する":
            return st.text_input(
                "新しい企業名",
                value="" if current_value == "未分類" else current_value,
                key=f"{key_prefix}_new_company"
            )
        return selected

    elif category == "大学":
        options = ["未分類"] + subjects + ["新しく追加する"]
        default_index = options.index(current_value) if current_value in options else 0

        selected = st.selectbox(
            "教科名・大学関連名",
            options,
            index=default_index,
            key=f"{key_prefix}_subject_select"
        )

        if selected == "新しく追加する":
            return st.text_input(
                "新しい教科名・大学関連名",
                value="" if current_value == "未分類" else current_value,
                key=f"{key_prefix}_new_subject"
            )
        return selected

    elif category == "予約・チケット":
        options = ["交通", "宿泊", "遊び", "その他"]
        default_index = options.index(current_value) if current_value in options else 3

        return st.selectbox(
            "予約・チケットの種類",
            options,
            index=default_index,
            key=f"{key_prefix}_reservation_type"
        )

    elif category == "宅配":
        return ""

    else:
        return st.text_input(
            "関連先",
            value=current_value,
            key=f"{key_prefix}_related_name"
        )

def todo_input(category, current_todo, custom_todo_options, key_prefix):
    todo_options = get_todo_options(category, custom_todo_options)

    todo_options = todo_options + ["新しく追加する"]

    selected_todo = st.selectbox(
        "ToDo内容",
        todo_options,
        key=f"{key_prefix}_todo_select"
    )

    if selected_todo == "新しく追加する":
        return st.text_input(
            "新しいToDo内容",
            value="",
            key=f"{key_prefix}_new_todo"
        )

    return selected_todo

def parse_deadline_to_date(deadline):
    if not deadline or deadline == "未検出":
        return date.today()

    match = re.match(r"(\d{1,2})月(\d{1,2})日", deadline)
    if match:
        year = datetime.now().year
        month = int(match.group(1))
        day = int(match.group(2))
        return date(year, month, day)

    match = re.match(r"(\d{4})年(\d{1,2})月(\d{1,2})日", deadline)
    if match:
        year = int(match.group(1))
        month = int(match.group(2))
        day = int(match.group(3))
        return date(year, month, day)

    return date.today()

def parse_deadline_to_time(deadline):
    if not deadline or deadline == "未検出":
        return datetime.strptime("23:59", "%H:%M").time()

    match = re.search(r"(\d{1,2}):(\d{2})", deadline)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2))
        return datetime.strptime(f"{hour:02d}:{minute:02d}", "%H:%M").time()

    return datetime.strptime("23:59", "%H:%M").time()

todos = load_json(TODO_FILE, [])
companies = load_json(COMPANY_FILE, [])
subjects = load_json(SUBJECT_FILE, [])
custom_todo_options = load_json(TODO_OPTION_FILE, {})

st.subheader("📩 メール解析")

if "email_box_key" not in st.session_state:
    st.session_state.email_box_key = 0

email_text = st.text_area(
    "メール本文を貼り付けてください",
    height=250,
    key=f"email_text_{st.session_state.email_box_key}"
)

if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None

if "show_add_form" not in st.session_state:
    st.session_state.show_add_form = False

if "edit_mode" not in st.session_state:
    st.session_state.edit_mode = False

if st.button("解析する"):
    if email_text.strip():
        category = classify_email(email_text)
        importance = judge_importance(email_text)
        deadline = extract_deadline(email_text)
        todo_text = generate_todo(category, email_text)
        detected_company = detect_company(email_text, companies)

        st.session_state.analysis_result = {
            "category": category,
            "importance": importance,
            "deadline": deadline,
            "todo": todo_text,
            "related_name": detected_company,
        }

        st.session_state.show_add_form = True
    else:
        st.warning("メール本文を入力してください。")


result = st.session_state.analysis_result

if result and st.session_state.show_add_form:
    st.subheader("📋 解析結果")
    st.write(f"**カテゴリ:** {result['category']}")
    st.write(f"**重要度:** {result['importance']}")
    st.write(f"**締切:** {result['deadline']}")
    st.write(f"**ToDo:** {result['todo']}")

    st.write("### ✏️ ToDo追加前の編集")

    edited_category = st.selectbox(
        "カテゴリ",
        ["就活", "大学", "宅配", "予約・チケット", "その他"],
        index=["就活", "大学", "宅配", "予約・チケット", "その他"].index(result["category"]),
        key="add_category"
    )

    edited_related_name = related_name_input(
        edited_category,
        result.get("related_name", result.get("company", "未分類")),
        companies,
        subjects,
        "add"
    )

    edited_importance = st.selectbox(
        "重要度",
        ["高", "中", "低"],
        index=["高", "中", "低"].index(result["importance"]),
        key="add_importance"
    )

    edited_deadline_date = st.date_input(
        "締切日",
        value=parse_deadline_to_date(result["deadline"]),
        key="add_deadline_date"
    )

    edited_deadline_time = st.time_input(
        "締切時刻",
        value=parse_deadline_to_time(result["deadline"]),
        key="add_deadline_time"
    )

    edited_deadline = (
        f"{edited_deadline_date.month}月"
        f"{edited_deadline_date.day}日 "
        f"{edited_deadline_time.strftime('%H:%M')}"
    )

    edited_todo = todo_input(
        edited_category,
        result["todo"],
        custom_todo_options,
        "add"
    )

    col_add, col_cancel = st.columns(2)

    with col_add:

        if st.button("➕ ToDoに追加"):
            if edited_category == "就活" and edited_related_name not in ["", "未分類"] and edited_related_name not in companies:
                companies.append(edited_related_name)
                save_json(COMPANY_FILE, companies)

            if edited_category == "大学" and edited_related_name not in ["", "未分類"] and edited_related_name not in subjects:
                subjects.append(edited_related_name)
                save_json(SUBJECT_FILE, subjects)

            if edited_todo and edited_todo not in get_todo_options(edited_category, custom_todo_options):
                if edited_category not in custom_todo_options:
                    custom_todo_options[edited_category] = []
                custom_todo_options[edited_category].append(edited_todo)
                save_json(TODO_OPTION_FILE, custom_todo_options)

            todos.append({
                "category": edited_category,
                "related_name": edited_related_name,
                "importance": edited_importance,
                "deadline": edited_deadline,
                "todo": edited_todo,
                "completed": False
            })

            save_json(TODO_FILE, todos)
            st.session_state.email_box_key += 1
            st.session_state.analysis_result = None
            st.session_state.show_add_form = False
            st.success("ToDoを追加しました！")
            st.rerun()

    with col_cancel:
        if st.button("追加せず閉じる"):
            st.session_state.email_box_key += 1
            st.session_state.analysis_result = None
            st.session_state.show_add_form = False
            st.rerun()

if "filter_date_key" not in st.session_state:
    st.session_state.filter_date_key = 0

col_date, col_today = st.columns([3, 1])

with col_date:
    selected_filter_date = st.date_input(
        "表示する締切日",
        value=date.today(),
        key=f"todo_filter_date_{st.session_state.filter_date_key}"
    )

with col_today:
    st.write("")
    st.write("")
    if st.button("今日"):
        st.session_state.filter_date_key += 1
        st.rerun()
show_all = st.checkbox(
    "すべてのToDoを表示する",
    value=False
)

st.subheader("📅 ToDo一覧（締切順）")

if "edit_mode" not in st.session_state:
    st.session_state.edit_mode = False

sorted_todos = sorted(
    enumerate(todos),
    key=lambda x: parse_deadline(x[1]["deadline"])
)

filtered_todos = [
    (index, item)
    for index, item in sorted_todos
    if parse_deadline_to_date(item["deadline"]) == selected_filter_date
]

if show_all:
    display_todos = sorted_todos
else:
    display_todos = filtered_todos

if sorted_todos:
    checked_indexes = []

    for original_index, item in display_todos:
        category_colors = {
            "就活": "#E3F2FD",          # 薄い青
            "大学": "#E8F5E9",          # 薄い緑
            "宅配": "#FFF3E0",          # 薄いオレンジ
            "予約・チケット": "#F3E5F5", # 薄い紫
            "その他": "#F5F5F5",        # 薄いグレー
        }

        bg_color = category_colors.get(item["category"], "#F5F5F5")

        importance_badges = {
            "高": "🔴 高",
            "中": "🟠 中",
            "低": "⚪ 低",
        }

        importance_badge = importance_badges.get(item["importance"], "⚪ 低")

        label = (
            f"{item['deadline']} | "
            f"{importance_badge} | "
            f"{item['category']} | "
            f"{item.get('related_name', '')} | "
            f"{item['todo']}"
        )

        st.markdown(
            f"""
            <div style="
                background-color: {bg_color};
                padding: 8px 12px;
                border-radius: 8px;
                margin-bottom: 4px;
                color: black;
            ">
                {label}
            </div>
            """,
            unsafe_allow_html=True
        )

        checked = st.checkbox(
            "完了",
            value=item["completed"],
            key=f"todo_check_{original_index}"
        )

        todos[original_index]["completed"] = checked

        if checked:
            checked_indexes.append(original_index)

    save_json(TODO_FILE, todos)

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🗑️ チェック済みToDoを削除"):
            todos = [
                item for index, item in enumerate(todos)
                if index not in checked_indexes
            ]
            save_json(TODO_FILE, todos)
            st.success("チェック済みのToDoを削除しました！")
            st.session_state.edit_mode = False
            st.rerun()

    with col2:
        if st.button("✏️ ToDoを編集"):
            st.session_state.edit_mode = True

    if st.session_state.edit_mode:
        st.subheader("✏️ 編集するToDoを選択")

        todo_labels = []
        index_map = {}

        for original_index, item in sorted_todos:
            label = (
                f"{item['deadline']} | "
                f"{item['category']} | "
                f"{item.get('related_name', '')} | "
                f"{item['todo']}"
            )
            todo_labels.append(label)
            index_map[label] = original_index

        selected_label = st.radio(
            "編集したいToDoを選択してください",
            todo_labels
        )

        selected_index = index_map[selected_label]
        selected_item = todos[selected_index]

        st.subheader("🛠️ ToDo編集画面")

        edited_category = st.selectbox(
            "カテゴリ",
            ["就活", "大学", "宅配", "予約・チケット", "その他"],
            index=["就活", "大学", "宅配", "予約・チケット", "その他"].index(selected_item["category"]),
            key=f"edit_category_{selected_index}"
        )

        edited_related_name = related_name_input(
            edited_category,
            selected_item.get("related_name", "未分類"),
            companies,
            subjects,
            f"edit_{selected_index}"
        )

        edited_deadline_date = st.date_input(
            "締切日",
            value=parse_deadline_to_date(selected_item["deadline"]),
            key=f"edit_deadline_date_{selected_index}"
        )

        edited_deadline_time = st.time_input(
            "締切時刻",
            value=parse_deadline_to_time(selected_item["deadline"]),
            key=f"edit_deadline_time_{selected_index}"
        )

        edited_deadline = (
            f"{edited_deadline_date.month}月"
            f"{edited_deadline_date.day}日 "
            f"{edited_deadline_time.strftime('%H:%M')}"
        )

        edited_todo = todo_input(
            edited_category,
            selected_item["todo"],
            custom_todo_options,
            f"edit_{selected_index}"
        )

        edited_importance = st.selectbox(
            "重要度",
            ["高", "中", "低"],
            index=["高", "中", "低"].index(selected_item["importance"]),
            key=f"edit_importance_{selected_index}"
        )

        col_save, col_delete, col_cancel = st.columns(3)

        with col_save:
            if st.button("💾 編集内容を保存"):
                if edited_todo and edited_todo not in get_todo_options(edited_category, custom_todo_options):
                    if edited_category not in custom_todo_options:
                        custom_todo_options[edited_category] = []
                    custom_todo_options[edited_category].append(edited_todo)
                    save_json(TODO_OPTION_FILE, custom_todo_options)
                todos[selected_index] = {
                    "category": edited_category,
                    "related_name": edited_related_name,
                    "importance": edited_importance,
                    "deadline": edited_deadline,
                    "todo": edited_todo,
                    "completed": selected_item["completed"]
                }
                save_json(TODO_FILE, todos)
                st.success("ToDoを更新しました！")
                st.session_state.edit_mode = False
                st.rerun()

        with col_delete:
            if st.button("🗑️ このToDoを削除"):
                todos.pop(selected_index)
                save_json(TODO_FILE, todos)
                st.success("ToDoを削除しました！")
                st.session_state.edit_mode = False
                st.rerun()

        with col_cancel:
            if st.button("キャンセル"):
                st.session_state.edit_mode = False
                st.rerun()

else:
    st.info("まだToDoは登録されていません。")