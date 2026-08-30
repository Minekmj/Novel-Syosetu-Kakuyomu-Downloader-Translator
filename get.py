import urllib.parse
from bs4 import BeautifulSoup
import re
import json
from datetime import datetime, timedelta
import requests
http_session = requests.Session()

TAG_CATEGORIES = {
    "지위 · 신분 · 칭호": {
        "영주": "領主",
        "귀족": "貴族",
        "왕족": "王族",
        "왕자": "王子",
        "황녀/공주": "王女",
        "공녀": "公女",
        "영애": "令嬢",
        "악역영애": "悪役令嬢",
        "대공": "大公",
        "황제": "皇帝",
        "국왕": "国王",
        "마왕": "魔王",
        "용사": "勇者",
        "성녀": "聖女",
        "현자": "賢者",
        "교황": "教皇",
        "신": "神",
        "마신": "魔神",
        "단장": "団長",
        "기사": "騎士",
        "성기사": "聖騎士",
        "모험가": "冒険者",
        "노예": "奴隷",
        "집사": "執事",
        "메이드": "メイド",
        "소꿉친구": "幼馴染",
        "전생자": "転生者",
        "귀환자": "帰還者",
        "추방자": "追放者",
        "전학생": "転校生",
        "이방인": "異邦人",
        "후작": "侯爵",
        "백작": "伯爵",
        "자작": "子爵",
        "남작": "男爵",
        "공작": "公爵",
        "왕녀": "王女",
        "왕태자": "王太子",
        "황태자": "皇太子"
    },

    "직업 · 역할": {
        "상인": "商人",
        "가정교사": "家庭教師",
        "작가": "作家",
        "경찰": "警察",
        "형사": "刑事",
        "기자": "記者",
        "탐정": "探偵",
        "무사": "侍",
        "닌자": "忍者",
        "군인": "軍人",
        "마법사": "魔法使い",
        "연금술사": "錬金術師",
        "암살자": "暗殺者",
        "요리사": "料理人",
        "의사": "医者",
        "약사": "薬師",
        "연구원": "研究者",
        "교사": "教師",
        "학생": "学生",
        "점원": "店員",
        "아이돌": "アイドル",
        "배우": "俳優",
        "성우": "声優",
        "스트리머": "配信者",
        "버튜버": "VTuber",
        "인플루언서": "インフルエンサー",
        "야쿠자": "ヤクザ",
        "사무원": "会社員",
        "사축": "社畜",
        "경호원": "ボディーガード",
        "용병": "傭兵",
        "사냥꾼": "ハンター",
        "퇴마사": "退魔師",
        "음양사": "陰陽師",
        "무녀": "巫女",
        "신관": "神官",
        "대장장이": "鍛冶師",
        "농부": "農民",
        "목장주": "牧場",
        "게이머": "ゲーマー"
    },

    "캐릭터 · 속성": {
        "살인귀": "殺人鬼",
        "청부업자": "殺し屋",
        "해커": "ハッカー",
        "마법소녀": "魔法少女",
        "마녀": "魔女",
        "소악마": "小悪魔",
        "얀데레": "ヤンデレ",
        "츤데레": "ツンデレ",
        "쿨데레": "クーデレ",
        "데레데레": "デレデレ",
        "메스가키": "メスガキ",
        "오네에": "オネエ",
        "누님계": "お姉さん",
        "로리": "ロリ",
        "쇼타": "ショタ",
        "천연": "天然",
        "무표정": "無表情",
        "괴짜": "変人",
        "사이코패스": "サイコパス",
        "광인": "狂人",
        "광전사": "狂戦士",
        "중2병": "中二病",
        "불량": "不良",
        "문제아": "問題児",
        "천재": "天才",
        "평범한 주인공": "平凡",
        "최강": "最強",
        "치트": "チート",
        "무능": "無能",
        "숨은 강자": "実力者",
        "먼치킨": "無双",
        "복흑": "腹黒",
        "독설가": "毒舌",
        "음침": "陰キャ",
        "인싸": "陽キャ",
        "남장": "男装",
        "여장": "女装",
        "성별전환": "TS",
        "수인": "獣人",
        "엘프": "エルフ",
        "드래곤": "ドラゴン",
        "흡혈귀": "吸血鬼",
        "언데드": "アンデッド",
        "마족": "魔族",
        "천사": "天使",
        "악마": "悪魔",
        "인공지능": "AI",
        "로봇": "ロボット",
        "스마트폰": "スマートフォン"
    },

    "주인공 · 구성": {
        "남주인공": "男主人公",
        "여주인공": "女主人公",
        "남녀 더블 주인공": "男女主人公",
        "복수 주인공": "復讐主人公",
        "악역 주인공": "悪役主人公",
        "빌런 주인공": "主人公悪役",
        "비인간 주인공": "人外主人公",
        "몬스터 주인공": "モンスター主人公",
        "전생 주인공": "転生主人公",
        "아저씨 주인공": "おっさん主人公",
        "아저씨": "おっさん",
        "오네쇼타": "おねショタ",
        "쇼타 주인공": "ショタ主人公",
        "로리 주인공": "ロリ主人公",
        "다인 주인공": "群像劇",
        "군상극": "群像劇",
        "서브 주인공": "脇役",
        "악역영애 주인공": "悪役令嬢",
        "모브 주인공": "モブ",
        "약캐 주인공": "弱い主人公",
        "성장형 주인공": "成長する主人公"
    },

    "연애 · 관계": {
        "로맨스": "恋愛",
        "러브코미디": "ラブコメ",
        "BL": "BL",
        "백합": "百合",
        "하렘": "ハーレム",
        "역하렘": "逆ハーレム",
        "순애": "純愛",
        "익애": "溺愛",
        "메가데레": "溺愛",
        "집착": "執着",
        "집착남": "執着",
        "집착녀": "執着",
        "얀데레": "ヤンデレ",
        "첫사랑": "初恋",
        "짝사랑": "片思い",
        "양방향 짝사랑": "両片思い",
        "재회": "再会",
        "소꿉친구": "幼馴染",
        "여사친": "女友達",
        "남사친": "男友達",
        "전여친": "元カノ",
        "전남친": "元彼",
        "삼각관계": "三角関係",
        "사각관계": "四角関係",
        "수라장": "修羅場",
        "질투": "嫉妬",
        "밀당": "駆け引き",
        "엇갈림": "すれ違い",
        "나이차": "年の差",
        "연상": "年上",
        "연하": "年下",
        "동거": "同居",
        "부부": "夫婦",
        "결혼": "結婚",
        "신혼": "新婚",
        "약혼": "婚約",
        "정략결혼": "政略結婚",
        "계약결혼": "契約結婚",
        "이혼": "離婚",
        "파혼": "婚約破棄",
        "재혼": "再婚",
        "불륜": "不倫",
        "바람": "浮気",
        "NTR": "NTR",
        "네토리": "寝取り",
        "구원": "救済",
        "치유 관계": "癒し",
        "달달함": "甘々",
        "꽁냥꽁냥": "イチャイチャ",
        "오피스 러브": "オフィスラブ",
        "판타지 연애": "異世界恋愛"
    },

    "전생 · 시간 · 차원이동": {
        "이세계 전생": "異世界転生",
        "이세계 전이": "異世界転移",
        "현대 전이": "現代転移",
        "전생": "転生",
        "빙의": "憑依",
        "환생": "転生",
        "회귀": "回帰",
        "귀환": "帰還",
        "타임리프": "タイムリープ",
        "루프": "ループ",
        "회차물": "周回",
        "미래로 이동": "未来",
        "과거로 이동": "過去",
        "두 번째 인생": "二度目の人生",
        "인생 재시작": "人生やり直し",
        "빙의 빙의물": "憑依",
        "게임 세계 전이": "ゲーム世界",
        "소설 세계 전이": "小説世界"
    },

    "전개 · 클리셰": {
        "주인공 최강": "主人公最強",
        "무쌍": "無双",
        "치트": "チート",
        "하극상": "下剋上",
        "성장": "成長",
        "성장물": "成長",
        "성공": "成功",
        "벼락출세": "成り上がり",
        "복수": "復讐",
        "배신": "裏切り",
        "추방": "追放",
        "추방 후 성공": "追放",
        "후회물": "後悔",
        "이제 와서 늦었다": "もう遅い",
        "자업자득": "因果応報",
        "사이다": "ざまぁ",
        "참교육": "ざまぁ",
        "파혼": "婚約破棄",
        "약혼파기": "婚約破棄",
        "착각물": "勘違い",
        "착각계": "勘違い",
        "오해": "誤解",
        "숨은 실력": "実力",
        "정체 숨김": "正体隠し",
        "정체 발각": "正体バレ",
        "쌍방 착각": "勘違い",
        "복선 회수": "伏線回収",
        "반전": "どんでん返し",
        "게임 빙의": "ゲーム",
        "게이머": "ゲーム",
        "게임 시스템": "ステータス",
        "상태창": "ステータス",
        "레벨업": "レベルアップ",
        "스킬": "スキル",
        "가챠": "ガチャ",
        "던전": "ダンジョン",
        "레이드": "レイド",
        "영지 경영": "内政",
        "국가 경영": "国家運営",
        "개척": "開拓",
        "슬로우 라이프": "スローライフ",
        "농사": "農業",
        "상점 경영": "経営",
        "배달": "配達",
        "요리": "料理",
        "제작": "ものづくり",
        "크래프팅": "クラフト",
        "서바이벌": "サバイバル",
        "데스게임": "デスゲーム",
        "추리": "推理",
        "미스터리": "ミステリー",
        "전쟁": "戦争",
        "정치": "政治",
        "내정": "内政",
        "학원물": "学園",
        "동아리": "部活",
        "이능력": "異能力",
        "능력자 배틀": "能力バトル",
        "각성": "覚醒",
        "각성자": "覚醒者",
        "헌터물": "ハンター",
        "탑등반": "ダンジョン",
        "아포칼립스": "終末",
        "좀비": "ゾンビ",
        "괴수": "怪獣",
        "괴이": "怪異",
        "도시전설": "都市伝説"
    },

    "일본 웹소설 · 나로우 계열": {
        "ざまぁ": "ざまぁ",
        "사이다 전개": "ざまぁ",
        "후회물": "後悔",
        "이제 와서 늦었다": "もう遅い",
        "추방물": "追放",
        "치트": "チート",
        "무쌍": "無双",
        "실력 숨김": "実力隠し",
        "정체 숨김": "正体隠し",
        "정체 발각": "正体バレ",
        "먼치킨": "主人公最強",
        "모브": "モブ",
        "악역": "悪役",
        "악역영애": "悪役令嬢",
        "악역 전생": "悪役転生",
        "RTA": "RTA",
        "스피드런": "RTA",
        "게시판물": "掲示板",
        "댓글 반응": "掲示板",
        "라이브 방송": "配信",
        "인터넷 방송": "配信",
        "버튜버": "VTuber",
        "현대 던전": "現代ダンジョン",
        "현대 판타지": "現代ファンタジー",
        "상태창": "ステータス",
        "스킬제": "スキル",
        "레벨제": "レベル",
        "스테이터스": "ステータス",
        "현대 귀환": "帰還",
        "추방 후 무쌍": "追放",
        "느긋한 최강": "スローライフ",
        "알고 보니 최강": "実は最強",
        "너무 강함": "強すぎる",
        "무자각 최강": "無自覚",
        "주변이 착각": "勘違い",
        "전부 착각": "勘違い",
        "악역이지만 착함": "悪役",
        "운영물": "経営",
        "생산직": "生産職",
        "생산 치트": "生産",
        "마이너 직업": "不遇職",
        "하즈레 직업": "ハズレ職",
        "불우 직업": "不遇",
        "직업 체인지": "転職"
    },

    "배경 · 세계관": {
        "이세계": "異世界",
        "판타지": "ファンタジー",
        "하이 판타지": "ハイファンタジー",
        "로우 판타지": "ローファンタジー",
        "현대": "現代",
        "현대 판타지": "現代ファンタジー",
        "SF": "SF",
        "근미래": "近未来",
        "사이버펑크": "サイバーパンク",
        "스팀펑크": "スチームパンク",
        "우주": "宇宙",
        "우주선": "宇宙船",
        "아포칼립스": "終末",
        "포스트 아포칼립스": "ポストアポカリプス",
        "마왕성": "魔王城",
        "왕국": "王国",
        "제국": "帝国",
        "귀족 사회": "貴族",
        "학교": "学校",
        "학원": "学園",
        "대학": "大学",
        "회사": "会社",
        "오피스": "オフィス",
        "던전": "ダンジョン",
        "탑": "塔",
        "길드": "ギルド",
        "모험자 길드": "冒険者ギルド",
        "현대 던전": "現代ダンジョン",
        "VR 게임": "VR",
        "게임 세계": "ゲーム世界",
        "마법 세계": "魔法",
        "일본풍": "和風",
        "서양풍": "西洋",
        "중세": "中世",
        "전국시대": "戦国時代",
        "에도시대": "江戸時代"
    },

    "분위기 · 감정": {
        "시리어스": "シリアス",
        "코미디": "コメディ",
        "개그": "ギャグ",
        "러브코미디": "ラブコメ",
        "일상": "日常",
        "힐링": "癒し",
        "포근함": "ほのぼの",
        "청춘": "青春",
        "감동": "感動",
        "애절함": "切ない",
        "달달함": "甘々",
        "상쾌함": "スカッと",
        "사이다": "爽快",
        "서스펜스": "サスペンス",
        "스릴러": "スリラー",
        "미스터리": "ミステリー",
        "호러": "ホラー",
        "하드보일드": "ハードボイルド",
        "다크": "ダーク",
        "음울": "陰鬱",
        "퇴폐적": "退廃的",
        "잔혹": "残酷",
        "고어": "グロ",
        "피폐": "鬱",
        "피폐 전개": "鬱展開",
        "절망": "絶望",
        "불행": "不幸",
        "학대": "虐待",
        "정신적 고통": "精神的ダメージ",
        "흐림": "曇らせ",
        "캐릭터 피폐": "曇らせ",
        "답답함": "モヤモヤ",
        "고구마": "胸糞",
        "답답한 전개": "じれじれ",
        "애절한 관계": "切ない",
        "긴장감": "緊張感",
        "박진감": "迫力",
        "잔잔함": "ゆったり",
        "따뜻함": "温かい",
        "우울": "鬱",
        "희망": "希望",
        "희망과 절망": "希望と絶望"
    },

    "특수 · 서브컬쳐": {
        "데스게임": "デスゲーム",
        "괴이": "怪異",
        "괴담": "怪談",
        "도시전설": "都市伝説",
        "크툴루": "クトゥルフ",
        "마법소녀": "魔法少女",
        "변신 히어로": "変身ヒーロー",
        "특촬": "特撮",
        "이세계 개그": "異世界",
        "패러디": "パロディ",
        "2차 창작": "二次創作",
        "팬픽": "二次創作",
        "크로스오버": "クロスオーバー",
        "TS": "TS",
        "성별전환": "性転換",
        "빙의": "憑依",
        "몸 바꾸기": "入れ替わり",
        "인외": "人外",
        "몬스터": "モンスター",
        "좀비": "ゾンビ",
        "흡혈귀": "吸血鬼",
        "괴수": "怪獣",
        "아이돌물": "アイドル",
        "버튜버물": "VTuber",
        "방송물": "配信",
        "게시판물": "掲示板",
        "SNS": "SNS",
        "인터넷 문화": "ネット",
        "게임": "ゲーム",
        "VRMMO": "VRMMO",
        "MMORPG": "MMORPG",
        "RPG": "RPG",
        "로그라이크": "ローグライク"
    }
}

class KakuyomuSearch:
    BASE_URL = "https://kakuyomu.jp/search"

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "ja,ko-KR;q=0.9,ko;q=0.8,en-US;q=0.7,en;q=0.6",
    }

    GENRES = {
        "전체": "",
        "이세계 판타지": "fantasy",
        "현대 판타지": "action",
        "SF": "sf",
        "연애": "love_story",
        "러브코미디": "romance",
        "현대 드라마": "drama",
        "호러": "horror",
        "미스터리": "mystery",
        "에세이/논픽션": "nonfiction",
        "역사/시대": "history",
        "평론/창작론": "criticism",
        "시/기타": "others",
        "2차 창작": "fan_fiction",
    }

    SORT_ORDERS = {
        "인기순": "popular",
        "주간 랭킹순": "weekly_ranking",
        "최신 작성순": "published_at",
        "최신 갱신순": "last_episode_published_at",
        "글자수 많은 순": "total_character_count",
    }

    LAST_PUBLISHED_PERIODS = {
        "전체": "",
        "1일 이내": "1days",
        "7일 이내": "7days",
        "1개월 이내": "1months",
        "6개월 이내": "6months",
        "1년 이내": "1years",
    }

    SERIAL_STATUSES = {
        "전체": "",
        "연재 중": "running",
        "완결": "completed",
    }
    
    FLAG_INCLUSION_AND_EXLUSION = {
        "잔혹 묘사": "cruel",
        "폭력 묘사": "violent",
        "성 묘사": "sexual",
        "서적 미디어화": "has_publication"
    }

    @staticmethod
    def build_search_url(
        query: str = "",
        genre_name: str = "",
        exclude_words: list = None,
        min_chars: int = None,
        last_published: str = None,
        min_start: int = None,
        serial_status: str = None,
        order: str = "popular",
        inclusion_flag: list = None,
        exclusion_flag: list = None,
        page: int = 1,
    ) -> str:
        params = []
        if order:
            params.append(("order", order))
        if query:
            params.append(("q", query))
        if exclude_words:
            params.append(("ex_q", " ".join(exclude_words)))
        if genre_name:
            params.append(("genre_name", genre_name))
        if min_chars is not None and min_chars > 0:
            params.append(("total_character_count_range", f"{min_chars}-"))
        if last_published:
            params.append(("last_episode_published_date_range", last_published))
        if min_start:
            params.append(("total_review_point_range", f"{min_start}-"))
        if serial_status:
            params.append(("serial_status", serial_status))
        if inclusion_flag:
            params.append(("inclusion_conditions", ",".join(inclusion_flag)))
        if exclusion_flag:
            for i in exclusion_flag:
                params.append(("exclusion_flag_name", i))

        if page > 1:
            params.append(("page", str(page)))

        query_string = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
        return f"{KakuyomuSearch.BASE_URL}?{query_string}"

    @classmethod
    def parse_search_results(cls, html_content: str) -> dict:
        soup = BeautifulSoup(html_content, "html.parser")
        results = []

        empty_msg = soup.find("div", class_=lambda c: c and "EmptyMessage_body" in c)
        if empty_msg:
            return {"is_last_page": True, "items": []}

        card_boxes = soup.find_all(
            "div",
            class_=lambda c: c
            and "NewBox_box__45ont" in c
            and "NewBox_borderSize-bb-m" in c,
        )

        if not card_boxes:
            card_boxes = soup.find_all(
                "div",
                class_=lambda c: c
                and "LayoutItem_layoutItem__cl360" in c
                and "LayoutItem_flex-1__hhrWm" in c,
            )

        processed_work_ids = set()

        for card in card_boxes:
            title_tag = card.find("a", href=lambda h: h and h.startswith("/works/"))
            if not title_tag:
                continue

            href = title_tag.get("href", "")
            parts = [p for p in href.split("/") if p]
            if len(parts) < 2 or parts[0] != "works":
                continue

            work_id = parts[1]
            if work_id in processed_work_ids:
                continue

            title_text = title_tag.get_text(strip=True)
            if not title_text:
                continue

            stars = "0"
            status_episodes = ""
            updated_at = ""

            meta_items = card.find_all(
                "li", class_=lambda c: c and "Meta_metaItemWrapper" in c
            )
            for item in meta_items:
                item_text = item.get_text(strip=True)
                if "★" in item_text:
                    stars = item_text.replace("★", "").strip()
                elif "更新" in item_text or item.find("time"):
                    time_tag = item.find("time")
                    if time_tag:
                        updated_at = time_tag.get_text(strip=True)
                    else:
                        updated_at = item_text.replace("更新", "").strip()
                elif "話" in item_text or "連載" in item_text or "完結" in item_text:
                    status_episodes = item_text

            if status_episodes:
                status_episodes = status_episodes.replace("連載中", "연재중 ").replace("完結済", "완결 ")
                status_episodes = re.sub(r'(\d+)話', r'\1화', status_episodes)

            if updated_at:
                updated_at = updated_at.replace("年", "년 ").replace("月", "월 ").replace("日", "일")

            processed_work_ids.add(work_id)
            results.append(
                {
                    "work_id": work_id,
                    "title": title_text,
                    "url": f"https://kakuyomu.jp/works/{work_id}",
                    "stars": stars,
                    "status_episodes": status_episodes,
                    "updated_at": updated_at
                }
            )

        return {"is_last_page": len(results) == 0, "items": results}

    @classmethod
    def fetch_detail_description(cls, work_url: str) -> str:
        try:
           
            res = http_session.get(work_url, headers=cls.HEADERS, timeout=10)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, "html.parser")

               
                next_data = soup.find("script", id="__NEXT_DATA__")
                if next_data and next_data.string:
                    data = json.loads(next_data.string)

                   
                    def find_key(obj, target_key):
                        if isinstance(obj, dict):
                            if target_key in obj:
                                return obj[target_key]
                            for v in obj.values():
                                res = find_key(v, target_key)
                                if res:
                                    return res
                        elif isinstance(obj, list):
                            for item in obj:
                                res = find_key(item, target_key)
                                if res:
                                    return res
                        return None

                    intro_text = find_key(data, "introduction")
                    lal = ', '.join(find_key(data, "tagLabels"))
                    if intro_text:
                        return str(intro_text).strip() + "\n\n_____tags_____\n" + lal

                return "상세 줄거리를 찾을 수 없습니다."
            return f"페이지 로드 실패 (HTTP {res.status_code})"
        except Exception as e:
            return f"상세 정보 요청 오류: {e}"
        
class NaroSearch:
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    GENRES = {
        "전체": 0,
        "연애": 1,
        "이세계 연애": 101,
        "현실 연애": 102,
        "판타지": 2,
        "하이 판타지": 201,
        "로우 판타지": 202,
        "문예": 3,
        "순문학": 301,
        "휴먼 드라마": 302,
        "역사": 303,
        "추리": 304,
        "공포": 305,
        "액션": 306,
        "코미디": 307,
        "SF": 4,
        "VR 게임": 401,
        "우주": 402,
        "공산 과학": 403,
        "공황": 404,
        "기타": 99,
        "논픽션": 98
    }

    SORT_ORDERS = {
        "포인트순": "hyoka",
        "주간 포인트순": "weeklypoint",
        "월간 포인트순": "monthlypoint",
        "분기 포인트순": "quarterpoint",
        "연간 포인트순": "yearlypoint",
        "신작순": "new",
        "최신 갱신순": "weekly",
        "글자수순": "length"
    }

    SERIAL_STATUSES = {
        "전체": "",
        "단편": "t",
        "연재": "re",
        "연재중": "r",
        "완결": "er"
    }

    LAST_PUBLISHED_PERIODS = {
        "전체": None,
        "1일 이내": 1,
        "1주일 이내": 7,
        "1개월 이내": 30,
        "3개월 이내": 90,
        "반년 이내": 180,
        "1년 이내": 365
    }
    
    FLAG_INCLUSION_AND_EXLUSION = {
        "AI 사용": "ai",
        "R15": "r15",
        "잔인한 묘사": "zankoku",
        "BL": "bl",
        "GL": "gl",
        "이세계 환생": "tensei",
        "이세계 전이": "tenni",
        "장기 연재 중단": "stop"
    }
    
    FIND_AREA = {
        "작품 제목": "title",
        "줄거리": "ex",
        "키워드": "keyword",
        "저자 이름": "wname"
    }

    @staticmethod
    def fetch_search_results(params):

        api_url = "https://api.syosetu.com/novelapi/api/"

        page = max(1, int(params.get("page", 1)))

        payload = {
            "out": "json",
            "lim": 20,
            "st": (page - 1) * 20 + 1,
            "word": params.get("query", ""),
            "order": params.get("order", "hyoka")
        }

       
       
       

        exclude_words = params.get("exclude_words", [])

        if exclude_words:
            payload["notword"] = " ".join(
                str(word).strip()
                for word in exclude_words
                if str(word).strip()
            )

       
       
       

        genre_val = params.get("genre_val")

        if genre_val and int(genre_val) != 0:
            payload["genre"] = int(genre_val)

       
       
       

        min_chars = params.get("min_chars", 0)

        if min_chars and int(min_chars) > 0:
            payload["minlen"] = int(min_chars)
          
       
       
       
        min_pt = params.get("min_pt", 0)
        
        if min_pt and int(min_pt) > 0:
            payload["min_globalpoint"] = int(min_pt)

       
       
       

        serial_status = params.get("serial_status")

        if serial_status:
            payload["type"] = serial_status

       
       
       

        period_key = params.get("last_published")

        days = NaroSearch.LAST_PUBLISHED_PERIODS.get(
            period_key,
            period_key if isinstance(period_key, int) else None
        )

        if days:
            today = datetime.now()
            start_date = today - timedelta(days=days)

            payload["minlastup"] = start_date.strftime("%Y/%m/%d")
            payload["maxlastup"] = today.strftime("%Y/%m/%d")
        
       
       
       
        
        inclusion_flags = params.get("inclusion_flags", [])
        
        if inclusion_flags:
            for i in inclusion_flags:
                payload["is" + i] = 1
                
        exlusion_flags = params.get("exlusion_flags", [])
                
        if exlusion_flags:
            for i in exlusion_flags:
                payload["not" + i if i != "stop" else "stop"] = 1
                
       
       
       
        
        find_areas = params.get("find_areas", [])
          
        if find_areas:
            for i in exlusion_flags:
                payload[i] = 1

        try:
           
            res = http_session.get(
                api_url,
                params=payload,
                headers=NaroSearch.HEADERS,
                timeout=10
            )

            res.raise_for_status()

            data = res.json()

            if not data:
                return {
                    "is_last_page": True,
                    "items": []
                }

            all_count = data[0].get("allcount", 0)

            items = []

            for item in data[1:]:

                ncode = item.get("ncode", "").lower()

                keywords_str = item.get("keyword", "")

                keywords_list = [
                    keyword.strip()
                    for keyword in keywords_str.split()
                    if keyword.strip()
                ]

                end_value = item.get("end", 1)

                if end_value == 1:
                    status = "연재중"
                else:
                    status = "완결"

                items.append({
                    "title": item.get("title", ""),

                    "url": f"https://ncode.syosetu.com/{ncode}/",

                    "stars": item.get("global_point", 0),

                    "status_episodes":
                        f"총 {item.get('general_all_no', 0)}화 "
                        f"({status})",

                    "updated_at":
                        item.get("general_lastup", "")[:10],

                    "ncode": ncode,
                    
                    "story": item.get("story", "") + '_____tags_____' + ', '.join(keywords_list),

                    "keywords": keywords_list
                })

            is_last_page = page * 20 >= all_count

            return {
                "is_last_page": is_last_page,
                "items": items
            }

        except Exception as e:

            print(f"나로우 API 요청 에러: {e}")

            return {
                "is_last_page": True,
                "items": []
            }
    
    @staticmethod
    def fetch_detail_description(work_url):
        return work_url