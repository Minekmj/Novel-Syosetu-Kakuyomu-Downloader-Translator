import os
import re

class EpisodeStorage:
    @staticmethod
    def read_backup(title_path, current_idx, trs_path, act_massage, total_count, progress_state, label_callback, printcall):
        backup_file = None
        prefix = f"[{current_idx}] "
        if os.path.exists(title_path):
            for fname in os.listdir(title_path):
                if fname.startswith(prefix) and fname.endswith(".txt"):
                    backup_file = os.path.join(title_path, fname)
                    break

        if backup_file and os.path.exists(backup_file):
            try:
                with open(backup_file, "r", encoding="utf-8") as f:
                    content = f.read()

                parts = content.split("=" * 30)
                if len(parts) >= 3:
                    subtitle = parts[1].strip()
                    body = ("=" * 30).join(parts[2:]).lstrip("\r\n")
                else:
                    subtitle = os.path.splitext(os.path.basename(backup_file))[0].replace(prefix, "", 1)
                    body = content.strip()

                safe_title = re.sub(r'[\\/:*?"<>|]', "_", subtitle)
                trs_file_path = os.path.join(trs_path, f"{current_idx}번_{safe_title}.txt")

                if act_massage != "":
                    a = body.find(act_massage)
                    if a > 0:
                        body = body[0:a]

                with open(trs_file_path, "w", encoding="utf-8") as f:
                    f.write(subtitle + "\n\n" + body + "\n\n")

                EpisodeStorage.update_progress(progress_state, total_count, label_callback)
                return True
            except Exception as e:
                printcall(f"에피소드 {current_idx}화 기존 백업 읽기 실패 ({e}). 웹에서 새로 다운로드합니다.")
        return False

    @staticmethod
    def save_episode(title_path, trs_path, current_idx, subtitle, body, body_raw, act_massage=""):
        safe_title = re.sub(r'[\\/:*?"<>|]', "_", subtitle)
        file_path = os.path.join(trs_path, f"{current_idx}번_{safe_title}.txt")

        if act_massage != "":
            a = body.find(act_massage)
            if a > 0:
                body = body[0:a]

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(subtitle + "\n\n" + body + "\n\n")

        with open(
            os.path.join(title_path, f"[{current_idx}] {safe_title}.txt"),
            "w",
            encoding="utf-8"
        ) as f:
            f.write('=' * 30 + "\n" + subtitle + "\n" + '=' * 30 + "\n\n\n\n" + body_raw)

    @staticmethod
    def update_progress(progress_state, total_count, label_callback):
        # 진행률
        with progress_state["lock"]:
            progress_state["done"] += 1
            done = progress_state["done"]

        progress_percent = round((100 / total_count) * done, 1)
        label_callback(f"{progress_percent}%")