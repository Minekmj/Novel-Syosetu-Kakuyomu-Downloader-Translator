from src.system.data import load_data, save_data

def normalize_site_url(url):
    url = url.strip()
    if "syosetu.com" in url:
        if not url.endswith("/"):
            url += "/"
    elif "kakuyomu.jp" in url:
        if url.endswith("/"):
            url = url.rstrip("/")
    return url

def filter_and_sort_rows(rows, search_query, sort_mode, only_remaining, pinned_row):
    visible = []

    for row in rows:
        if search_query and search_query not in row.title_text.lower():
            row.hide()
            continue

        remaining = row.get_remaining_episodes()
        if only_remaining and remaining <= 0:
            row.hide()
            continue

        row.show()
        visible.append(row)

    is_pinned = pinned_row in visible
    if is_pinned:
        visible.remove(pinned_row)

    if sort_mode == 0:
        visible.sort(key=lambda x: x.title_text)
    elif sort_mode == 1:
        visible.sort(key=lambda x: x.title_text, reverse=True)
    elif sort_mode == 2:
        visible.sort(key=lambda x: x.get_remaining_episodes(), reverse=True)
    elif sort_mode == 3:
        visible.sort(key=lambda x: x.get_remaining_episodes())
    elif sort_mode == 4:
        visible.sort(key=lambda x: x.down_time, reverse=True)
    elif sort_mode == 5:
        visible.sort(key=lambda x: x.down_time)
    elif sort_mode == 6:
        visible.sort(key=lambda x: (x.time != "", x.time), reverse=True)
    elif sort_mode == 7:
        visible.sort(key=lambda x: (x.time == "", x.time))

    if is_pinned:
        visible.insert(0, pinned_row)

    return visible

def save_novel_entry(title, url):
    data = load_data()
    if "list" not in data:
        data["list"] = {}
    data["list"][title] = {
        "src": url,
        "down": "",
        "down_time": "0"
    }
    save_data(data)

def delete_novel_entry(title):
    data = load_data()
    if title in data.get("list", {}):
        del data["list"][title]
        save_data(data)