"""Station alias resolver — TRTC 121 stations, KRTC 39 stations, KLRT 38 stations."""

from __future__ import annotations

# 捷運系統站點對應表
# station_name: TDX API 實際回傳名稱（無「站」後綴，TRTC 例外如「台北車站」是專有名詞）
# station_id:   跨線換乘站以 / 分隔（如 BL12/R10）

STATION_ALIAS_MAP = {
    "TRTC": {
        # ── 跨線換乘站 ──
        "台北車站": {"station_name": "台北車站", "station_id": "BL12/R10"},
        "北車":     {"station_name": "台北車站", "station_id": "BL12/R10"},
        "南港展覽館": {"station_name": "南港展覽館", "station_id": "BL23/BR24"},
        "忠孝復興": {"station_name": "忠孝復興", "station_id": "BL15/BR10"},
        "忠孝新生": {"station_name": "忠孝新生", "station_id": "BL14/O07"},
        "西門":     {"station_name": "西門",     "station_id": "BL11/G12"},
        "南京復興": {"station_name": "南京復興", "station_id": "BR11/G16"},
        "松江南京": {"station_name": "松江南京", "station_id": "G15/O08"},
        "古亭":     {"station_name": "古亭",     "station_id": "G09/O05"},
        "中正紀念堂": {"station_name": "中正紀念堂", "station_id": "G10/R08"},
        "東門":     {"station_name": "東門",     "station_id": "O06/R07"},
        "中山":     {"station_name": "中山",     "station_id": "G14/R11"},
        "民權西路": {"station_name": "民權西路", "station_id": "O11/R13"},

        # ── 板南線 BL（單線）──
        "頂埔":     {"station_name": "頂埔",     "station_id": "BL01"},
        "永寧":     {"station_name": "永寧",     "station_id": "BL02"},
        "土城":     {"station_name": "土城",     "station_id": "BL03"},
        "海山":     {"station_name": "海山",     "station_id": "BL04"},
        "亞東醫院": {"station_name": "亞東醫院", "station_id": "BL05"},
        "府中":     {"station_name": "府中",     "station_id": "BL06"},
        "板橋":     {"station_name": "板橋",     "station_id": "BL07"},
        "新埔":     {"station_name": "新埔",     "station_id": "BL08"},
        "江子翠":   {"station_name": "江子翠",   "station_id": "BL09"},
        "龍山寺":   {"station_name": "龍山寺",   "station_id": "BL10"},
        "善導寺":   {"station_name": "善導寺",   "station_id": "BL13"},
        "忠孝敦化": {"station_name": "忠孝敦化", "station_id": "BL16"},
        "國父紀念館": {"station_name": "國父紀念館", "station_id": "BL17"},
        "市政府":   {"station_name": "市政府",   "station_id": "BL18"},
        "永春":     {"station_name": "永春",     "station_id": "BL19"},
        "後山埤":   {"station_name": "後山埤",   "station_id": "BL20"},
        "昆陽":     {"station_name": "昆陽",     "station_id": "BL21"},
        "南港":     {"station_name": "南港",     "station_id": "BL22"},

        # ── 文湖線 BR（單線）──
        "動物園":   {"station_name": "動物園",   "station_id": "BR01"},
        "木柵":     {"station_name": "木柵",     "station_id": "BR02"},
        "萬芳社區": {"station_name": "萬芳社區", "station_id": "BR03"},
        "萬芳醫院": {"station_name": "萬芳醫院", "station_id": "BR04"},
        "辛亥":     {"station_name": "辛亥",     "station_id": "BR05"},
        "麟光":     {"station_name": "麟光",     "station_id": "BR06"},
        "六張犁":   {"station_name": "六張犁",   "station_id": "BR07"},
        "科技大樓": {"station_name": "科技大樓", "station_id": "BR08"},
        "中山國中": {"station_name": "中山國中", "station_id": "BR12"},
        "松山機場": {"station_name": "松山機場", "station_id": "BR13"},
        "大直":     {"station_name": "大直",     "station_id": "BR14"},
        "劍南路":   {"station_name": "劍南路",   "station_id": "BR15"},
        "西湖":     {"station_name": "西湖",     "station_id": "BR16"},
        "港墘":     {"station_name": "港墘",     "station_id": "BR17"},
        "文德":     {"station_name": "文德",     "station_id": "BR18"},
        "內湖":     {"station_name": "內湖",     "station_id": "BR19"},
        "大湖公園": {"station_name": "大湖公園", "station_id": "BR20"},
        "葫洲":     {"station_name": "葫洲",     "station_id": "BR21"},
        "東湖":     {"station_name": "東湖",     "station_id": "BR22"},
        "南港軟體園區": {"station_name": "南港軟體園區", "station_id": "BR23"},

        # ── 松山新店線 G（單線）──
        "新店":     {"station_name": "新店",     "station_id": "G01"},
        "新店區公所": {"station_name": "新店區公所", "station_id": "G02"},
        "七張":     {"station_name": "七張",     "station_id": "G03"},
        "小碧潭":   {"station_name": "小碧潭",   "station_id": "G03A"},
        "大坪林":   {"station_name": "大坪林",   "station_id": "G04"},
        "景美":     {"station_name": "景美",     "station_id": "G05"},
        "萬隆":     {"station_name": "萬隆",     "station_id": "G06"},
        "公館":     {"station_name": "公館",     "station_id": "G07"},
        "台電大樓": {"station_name": "台電大樓", "station_id": "G08"},
        "小南門":   {"station_name": "小南門",   "station_id": "G11"},
        "北門":     {"station_name": "北門",     "station_id": "G13"},
        "台北小巨蛋": {"station_name": "台北小巨蛋", "station_id": "G17"},
        "小巨蛋":   {"station_name": "台北小巨蛋", "station_id": "G17"},
        "南京三民": {"station_name": "南京三民", "station_id": "G18"},
        "松山":     {"station_name": "松山",     "station_id": "G19"},

        # ── 中和新蘆線 O（單線）──
        "南勢角":   {"station_name": "南勢角",   "station_id": "O01"},
        "景安":     {"station_name": "景安",     "station_id": "O02"},
        "永安市場": {"station_name": "永安市場", "station_id": "O03"},
        "頂溪":     {"station_name": "頂溪",     "station_id": "O04"},
        "行天宮":   {"station_name": "行天宮",   "station_id": "O09"},
        "中山國小": {"station_name": "中山國小", "station_id": "O10"},
        "大橋頭":   {"station_name": "大橋頭",   "station_id": "O12"},
        "台北橋":   {"station_name": "台北橋",   "station_id": "O13"},
        "菜寮":     {"station_name": "菜寮",     "station_id": "O14"},
        "三重":     {"station_name": "三重",     "station_id": "O15"},
        "先嗇宮":   {"station_name": "先嗇宮",   "station_id": "O16"},
        "頭前庄":   {"station_name": "頭前庄",   "station_id": "O17"},
        "新莊":     {"station_name": "新莊",     "station_id": "O18"},
        "輔大":     {"station_name": "輔大",     "station_id": "O19"},
        "丹鳳":     {"station_name": "丹鳳",     "station_id": "O20"},
        "迴龍":     {"station_name": "迴龍",     "station_id": "O21"},
        "三重國小": {"station_name": "三重國小", "station_id": "O50"},
        "三和國中": {"station_name": "三和國中", "station_id": "O51"},
        "徐匯中學": {"station_name": "徐匯中學", "station_id": "O52"},
        "三民高中": {"station_name": "三民高中", "station_id": "O53"},
        "蘆洲":     {"station_name": "蘆洲",     "station_id": "O54"},

        # ── 淡水信義線 R（單線）──
        "象山":     {"station_name": "象山",     "station_id": "R02"},
        "台北101/世貿": {"station_name": "台北101/世貿", "station_id": "R03"},
        "101":      {"station_name": "台北101/世貿", "station_id": "R03"},
        "世貿":     {"station_name": "台北101/世貿", "station_id": "R03"},
        "信義安和": {"station_name": "信義安和", "station_id": "R04"},
        "大安森林公園": {"station_name": "大安森林公園", "station_id": "R06"},
        "台大醫院": {"station_name": "台大醫院", "station_id": "R09"},
        "雙連":     {"station_name": "雙連",     "station_id": "R12"},
        "圓山":     {"station_name": "圓山",     "station_id": "R14"},
        "劍潭":     {"station_name": "劍潭",     "station_id": "R15"},
        "士林":     {"station_name": "士林",     "station_id": "R16"},
        "芝山":     {"station_name": "芝山",     "station_id": "R17"},
        "明德":     {"station_name": "明德",     "station_id": "R18"},
        "石牌":     {"station_name": "石牌",     "station_id": "R19"},
        "唭哩岸":   {"station_name": "唭哩岸",   "station_id": "R20"},
        "奇岩":     {"station_name": "奇岩",     "station_id": "R21"},
        "北投":     {"station_name": "北投",     "station_id": "R22"},
        "新北投":   {"station_name": "新北投",   "station_id": "R22A"},
        "復興崗":   {"station_name": "復興崗",   "station_id": "R23"},
        "忠義":     {"station_name": "忠義",     "station_id": "R24"},
        "關渡":     {"station_name": "關渡",     "station_id": "R25"},
        "竹圍":     {"station_name": "竹圍",     "station_id": "R26"},
        "紅樹林":   {"station_name": "紅樹林",   "station_id": "R27"},
        "淡水":     {"station_name": "淡水",     "station_id": "R28"},
    },

    "KRTC": {
        # ── 跨線換乘站 ──
        "美麗島": {"station_name": "美麗島", "station_id": "O5/R10"},

        # ── 橘線 O（單線）──
        "哈瑪星":     {"station_name": "哈瑪星",     "station_id": "O1"},
        "鹽埕埔":     {"station_name": "鹽埕埔",     "station_id": "O2"},
        "前金":       {"station_name": "前金",       "station_id": "O4"},
        "信義國小":   {"station_name": "信義國小",   "station_id": "O6"},
        "文化中心":   {"station_name": "文化中心",   "station_id": "O7"},
        "五塊厝":     {"station_name": "五塊厝",     "station_id": "O8"},
        "苓雅運動園區": {"station_name": "苓雅運動園區", "station_id": "O9"},
        "衛武營":     {"station_name": "衛武營",     "station_id": "O10"},
        "鳳山西站":   {"station_name": "鳳山西站",   "station_id": "O11"},
        "鳳山":       {"station_name": "鳳山",       "station_id": "O12"},
        "大東":       {"station_name": "大東",       "station_id": "O13"},
        "鳳山國中":   {"station_name": "鳳山國中",   "station_id": "O14"},
        "大寮":       {"station_name": "大寮",       "station_id": "OT1"},

        # ── 紅線 R（單線）──
        "小港":       {"station_name": "小港",       "station_id": "R3"},
        "高雄國際機場": {"station_name": "高雄國際機場", "station_id": "R4"},
        "高雄機場":   {"station_name": "高雄國際機場", "station_id": "R4"},
        "草衙":       {"station_name": "草衙",       "station_id": "R4A"},
        "前鎮高中":   {"station_name": "前鎮高中",   "station_id": "R5"},
        "凱旋":       {"station_name": "凱旋",       "station_id": "R6"},
        "獅甲":       {"station_name": "獅甲",       "station_id": "R7"},
        "三多商圈":   {"station_name": "三多商圈",   "station_id": "R8"},
        "中央公園":   {"station_name": "中央公園",   "station_id": "R9"},
        "高雄車站":   {"station_name": "高雄車站",   "station_id": "R11"},
        "高雄":       {"station_name": "高雄車站",   "station_id": "R11"},
        "後驛":       {"station_name": "後驛",       "station_id": "R12"},
        "凹子底":     {"station_name": "凹子底",     "station_id": "R13"},
        "巨蛋":       {"station_name": "巨蛋",       "station_id": "R14"},
        "生態園區":   {"station_name": "生態園區",   "station_id": "R15"},
        "左營":       {"station_name": "左營",       "station_id": "R16"},
        "世運":       {"station_name": "世運",       "station_id": "R17"},
        "油廠國小":   {"station_name": "油廠國小",   "station_id": "R18"},
        "楠梓科技園區": {"station_name": "楠梓科技園區", "station_id": "R19"},
        "後勁":       {"station_name": "後勁",       "station_id": "R20"},
        "都會公園":   {"station_name": "都會公園",   "station_id": "R21"},
        "青埔":       {"station_name": "青埔",       "station_id": "R22"},
        "橋頭糖廠":   {"station_name": "橋頭糖廠",   "station_id": "R22A"},
        "橋頭火車站": {"station_name": "橋頭火車站", "station_id": "R23"},
        "岡山高醫":   {"station_name": "岡山高醫",   "station_id": "R24"},
        "岡山車站":   {"station_name": "岡山車站",   "station_id": "RK1"},
        "岡山":       {"station_name": "岡山車站",   "station_id": "RK1"},
    },

    "KLRT": {
        # 無此站（KLRT 無美麗島站）
        "美麗島": {"station_name": None, "station_id": None},
        # 以下站名與 station_id 均來自 TDX API（2026-05-21 驗證）
        "籬仔內": {"station_name": "籬仔內", "station_id": "C1"},
        "凱旋瑞田": {"station_name": "凱旋瑞田", "station_id": "C2"},
        "前鎮之星": {"station_name": "前鎮之星", "station_id": "C3"},
        "凱旋中華": {"station_name": "凱旋中華", "station_id": "C4"},
        "夢時代": {"station_name": "夢時代", "station_id": "C5"},
        "經貿園區": {"station_name": "經貿園區", "station_id": "C6"},
        "軟體園區": {"station_name": "軟體園區", "station_id": "C7"},
        "高雄展覽館": {"station_name": "高雄展覽館", "station_id": "C8"},
        "旅運中心": {"station_name": "旅運中心", "station_id": "C9"},
        "光榮碼頭": {"station_name": "光榮碼頭", "station_id": "C10"},
        "真愛碼頭": {"station_name": "真愛碼頭", "station_id": "C11"},
        "駁二大義": {"station_name": "駁二大義", "station_id": "C12"},
        "駁二蓬萊": {"station_name": "駁二蓬萊", "station_id": "C13"},
        "哈瑪星": {"station_name": "哈瑪星", "station_id": "C14"},
        "壽山公園站": {"station_name": "壽山公園站", "station_id": "C15"},
        "壽山公園": {"station_name": "壽山公園站", "station_id": "C15"},
        "文武聖殿站": {"station_name": "文武聖殿站", "station_id": "C16"},
        "文武聖殿": {"station_name": "文武聖殿站", "station_id": "C16"},
        "鼓山區公所站": {"station_name": "鼓山區公所站", "station_id": "C17"},
        "鼓山區公所": {"station_name": "鼓山區公所站", "station_id": "C17"},
        "鼓山": {"station_name": "鼓山", "station_id": "C18"},
        "馬卡道": {"station_name": "馬卡道", "station_id": "C19"},
        "臺鐵美術館": {"station_name": "臺鐵美術館", "station_id": "C20"},
        "台鐵美術館": {"station_name": "臺鐵美術館", "station_id": "C20"},
        "美術館": {"station_name": "美術館", "station_id": "C21"},
        "內惟藝術中心": {"station_name": "內惟藝術中心", "station_id": "C21A"},
        "聯合醫院": {"station_name": "聯合醫院", "station_id": "C22"},
        "龍華國小": {"station_name": "龍華國小", "station_id": "C23"},
        "愛河之心": {"station_name": "愛河之心", "station_id": "C24"},
        "新上國小": {"station_name": "新上國小", "station_id": "C25"},
        "大順民族": {"station_name": "大順民族", "station_id": "C26"},
        "灣仔內(大順鼎山)": {"station_name": "灣仔內(大順鼎山)", "station_id": "C27"},
        "灣仔內": {"station_name": "灣仔內(大順鼎山)", "station_id": "C27"},
        "大順鼎山": {"station_name": "灣仔內(大順鼎山)", "station_id": "C27"},
        "高雄高工": {"station_name": "高雄高工", "station_id": "C28"},
        "樹德家商": {"station_name": "樹德家商", "station_id": "C29"},
        "科工館": {"station_name": "科工館", "station_id": "C30"},
        "聖功醫院": {"station_name": "聖功醫院", "station_id": "C31"},
        "凱旋公園站": {"station_name": "凱旋公園站", "station_id": "C32"},
        "凱旋公園": {"station_name": "凱旋公園站", "station_id": "C32"},
        "衛生局站": {"station_name": "衛生局站", "station_id": "C33"},
        "衛生局": {"station_name": "衛生局站", "station_id": "C33"},
        "五權國小站": {"station_name": "五權國小站", "station_id": "C34"},
        "五權國小": {"station_name": "五權國小站", "station_id": "C34"},
        "凱旋武昌站": {"station_name": "凱旋武昌站", "station_id": "C35"},
        "凱旋武昌": {"station_name": "凱旋武昌站", "station_id": "C35"},
        "凱旋二聖站": {"station_name": "凱旋二聖站", "station_id": "C36"},
        "凱旋二聖": {"station_name": "凱旋二聖站", "station_id": "C36"},
        "輕軌機廠站": {"station_name": "輕軌機廠站", "station_id": "C37"},
        "輕軌機廠": {"station_name": "輕軌機廠站", "station_id": "C37"},
    },
}

# 需人工確認的歧義站名
AMBIGUOUS_ALIASES = {
    # 跨系統歧義
    "左營": ["高鐵左營站", "新左營站(台鐵)", "高雄捷運左營站(KRTC R16)"],
    # TRTC 同名不同線不同位置
    "大安": ["台北捷運文湖線大安站(BR09)", "台北捷運淡水信義線大安站(R05)"],
}


def resolve_station_alias(raw: str | None, rail_system: str | None = None) -> dict[str, object]:
    value = (raw or "").strip()
    if not value:
        return {
            "status": "invalid_input",
            "normalized_value": None,
            "needs_clarification": True,
            "candidates": [],
            "details": {"reason": "missing_station"},
        }

    if rail_system:
        mapping = STATION_ALIAS_MAP.get(rail_system, {})
        match = mapping.get(value)
        if match and match["station_name"]:
            return {
                "status": "ok",
                "normalized_value": match["station_name"],
                "needs_clarification": False,
                "candidates": [],
                "details": {
                    "station_id": match["station_id"],
                    "rail_system": rail_system,
                    "raw": value,
                },
            }

    if value in AMBIGUOUS_ALIASES:
        return {
            "status": "needs_clarification",
            "normalized_value": None,
            "needs_clarification": True,
            "candidates": AMBIGUOUS_ALIASES[value],
            "details": {"reason": "ambiguous_station_alias", "raw": value, "rail_system": rail_system},
        }

    return {
        "status": "needs_clarification",
        "normalized_value": None,
        "needs_clarification": True,
        "candidates": [],
        "details": {"reason": "unknown_station_alias", "raw": value, "rail_system": rail_system},
    }
