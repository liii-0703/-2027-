"""
配置文件
采集策略：
  - deptTree 拿所有部门，只保留顶层院（parentId 为空/0/1 的节点）
  - 逐顶层院请求 listHtPositions
  - 每条岗位：招聘单位 = 当前顶层院名，二级部门 = 岗位自己的 deptName
"""

# 接口契约

API_URL = "https://www.spacetalent.com.cn/htrc/public/mobile/web/htPosition/listHtPositions"
DEPT_TREE_URL = "https://www.spacetalent.com.cn/htrc/public/mobile/web/sysDept/deptTree"
PAGE_URL = "https://www.spacetalent.com.cn/zhiweicx.html"

REQUEST_METHOD = "POST"

HEADERS = {
    "Content-Type": "application/json",
    "Referer": PAGE_URL,
    "Origin": "https://www.spacetalent.com.cn",
}

DEPT_TREE_PAYLOAD = {"parentDeptId": 1}

BASE_PAYLOAD = {
    "pageNum": 1,
    "pageSize": 100,
    "deptId": None,
}

APPLY_URL_TEMPLATE = (
    "https://www.spacetalent.com.cn/jituan_xxx.html"
    "?id={dept_id}&positionId={position_id}"
)

# 顶层院的 parentId 取值集合
ROOT_DEPT_IDS = {None, 0, 1}


# 字段映射

FIELD_MAP = {
    "岗位名称": ["positionName"],
    "需求学科": ["mainMajorName", "otherMajor1Name", "otherMajor2Name"],
    "学历要求": ["educationText"],
    "需求人数": ["peopleNum"],
    "工作城市": ["workPlaceName"],
    "数智博士": ["shuZhiBoShi"],
    "发布日期": ["releaseDate"],
    "申请链接": ["applyUrl", "detailUrl", "positionUrl"],
}

OUTPUT_FIELDS = [
    "招聘单位", "二级部门", "岗位名称", "需求学科", "学历要求",
    "需求人数", "工作城市", "数智博士", "发布日期", "申请链接", "抓取时间",
]

CITY_FROM_TITLE_PATTERN = r"[\(（]([^\)）]+)[\)）]"


# 采集策略

PAGE_SIZE = 100
REQUEST_INTERVAL = 0.8
MAX_RETRIES = 3
RETRY_BACKOFF = 2.0

OUTPUT_DIR = "output"
CSV_FILE = "spacetalent_jobs.csv"
JSON_FILE = "spacetalent_jobs.json"