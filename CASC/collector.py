"""
中国航天人才网 2027 届校招职位采集

招聘单位取 parentDeptName，二级部门取 deptName。
先请求 deptTree 拿顶层院，再逐院请求 listHtPositions，按 positionId 去重。

用法:
    python collector.py
    python collector.py --debug
"""

import csv
import json
import os
import re
import sys
import time
from datetime import datetime

from DrissionPage import ChromiumPage

from config import (
    API_URL, DEPT_TREE_URL, DEPT_TREE_PAYLOAD, PAGE_URL,
    REQUEST_METHOD, HEADERS, BASE_PAYLOAD,
    FIELD_MAP, OUTPUT_FIELDS, CITY_FROM_TITLE_PATTERN,
    APPLY_URL_TEMPLATE, ROOT_DEPT_IDS,
    PAGE_SIZE, REQUEST_INTERVAL, MAX_RETRIES, RETRY_BACKOFF,
    OUTPUT_DIR, CSV_FILE, JSON_FILE,
)


def log(msg):
    """带时间戳的日志输出"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def pick(item, candidates, default=""):
    """按候选字段名列表取值，返回第一个非空命中，都没有就返回默认值"""
    for key in candidates:
        if key in item and item[key] not in (None, "", []):
            return item[key]
    return default


def extract_city(title):
    """从岗位名里拆城市，如 '体系仿真设计(北京)' -> '北京'"""
    m = re.search(CITY_FROM_TITLE_PATTERN, title or "")
    return m.group(1).strip() if m else ""


def merge_majors(item):
    """需求学科由三个字段拼成，用 ' / ' 连接"""
    parts = []
    for key in ["mainMajorName", "otherMajor1Name", "otherMajor2Name"]:
        v = item.get(key)
        if v:
            parts.append(str(v).strip())
    return " / ".join(parts)


def fmt_digital(val):
    """数智博士字段是布尔值，转成中文"""
    if val is True:
        return "是"
    if val is False:
        return "否"
    return ""


class OutputWriter:
    """CSV + JSON 双写，每写一条立即落盘，保证中断不丢数据"""

    def __init__(self, output_dir):
        os.makedirs(output_dir, exist_ok=True)
        self.csv_path = os.path.join(output_dir, CSV_FILE)
        self.json_path = os.path.join(output_dir, JSON_FILE)
        self.records = []
        self.f = open(self.csv_path, "w", newline="", encoding="utf-8-sig")
        self.w = csv.DictWriter(self.f, fieldnames=OUTPUT_FIELDS)
        self.w.writeheader()
        self.f.flush()

    def write(self, row):
        """写一条记录，同时刷新 CSV 和 JSON"""
        self.w.writerow(row)
        self.records.append(row)
        self.f.flush()
        with open(self.json_path, "w", encoding="utf-8") as f:
            json.dump(self.records, f, ensure_ascii=False, indent=2)

    def close(self):
        self.f.close()

    def total(self):
        return len(self.records)


def send_request(page, url, payload):
    """
    在浏览器内发 fetch 请求。
    站点有瑞数动态防护，直接 session 请求会被 403，必须走浏览器上下文。
    失败时按退避策略重试。
    """
    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            js = f'''
                return fetch("{url}", {{
                    method: "{REQUEST_METHOD}",
                    headers: {json.dumps(HEADERS)},
                    body: JSON.stringify({json.dumps(payload)})
                }}).then(r => r.text());
            '''
            text = page.run_js(js)
            if not text:
                raise RuntimeError("返回空")
            data = json.loads(text)
            if isinstance(data, dict) and data.get("code") not in (None, 0):
                raise RuntimeError(data.get("message"))
            return data
        except Exception as e:
            last_err = e
            wait = REQUEST_INTERVAL * (RETRY_BACKOFF ** (attempt - 1))
            log(f"    重试 {attempt}/{MAX_RETRIES} ({e})，{wait:.1f}s")
            time.sleep(wait)
    raise RuntimeError(f"最终失败: {last_err}")


def fetch_top_depts(page):
    """
    请求 deptTree，返回顶层院列表。
    接口返回的是嵌套结构，递归展开，只保留 parentId 为空的节点。
    顺便用 seen 集合去重，防止同一 deptId 重复出现。
    """
    data = send_request(page, DEPT_TREE_URL, DEPT_TREE_PAYLOAD)
    tops, seen = [], set()

    def walk(node):
        if isinstance(node, list):
            for it in node:
                walk(it)
            return
        if not isinstance(node, dict):
            return
        did, dname, pid = node.get("deptId"), node.get("deptName"), node.get("parentId")
        if did is not None and dname and did not in seen:
            seen.add(did)
            if pid in ROOT_DEPT_IDS:
                tops.append({"deptId": did, "deptName": dname})
        # 子节点可能在多个不同的 key 里
        for key in ("children", "childList", "list", "result", "data", "items"):
            if node.get(key):
                walk(node[key])

    walk(data)
    return tops


def main():
    debug = "--debug" in sys.argv

    page = ChromiumPage()
    page.get(PAGE_URL)
    time.sleep(3)

    log("抓取顶层院...")
    try:
        tops = fetch_top_depts(page)
    except Exception as e:
        log(f"deptTree 失败: {e}")
        page.quit()
        return

    log(f"共 {len(tops)} 个顶层院")
    for d in tops:
        log(f"  {d['deptId']}  {d['deptName']}")

    if not tops:
        log("未识别到顶层院，检查 config.py 里的 ROOT_DEPT_IDS")
        page.quit()
        return

    writer = OutputWriter(OUTPUT_DIR)
    seen_pids = set()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 逐个顶层院请求，拿到它下面所有岗位
    for i, top in enumerate(tops, 1):
        dept_id = top["deptId"]
        dept_name = top["deptName"]
        payload = dict(BASE_PAYLOAD, deptId=dept_id,
                       pageNum=1, pageSize=PAGE_SIZE)

        try:
            res = send_request(page, API_URL, payload)
        except Exception as e:
            log(f"[{i}/{len(tops)}] {dept_name} 失败: {e}")
            continue

        items = (res.get("result") or {}).get("list") or []

        if debug and items and i == 1:
            log("第一条记录字段: " + str(list(items[0].keys())))

        added = 0
        for it in items:
            # 不同院之间可能有共享岗位，用 positionId 去重
            pid = it.get("positionId")
            if pid is None or pid in seen_pids:
                continue
            seen_pids.add(pid)

            title = pick(it, FIELD_MAP["岗位名称"])

            writer.write({
                "招聘单位": it.get("parentDeptName") or "",
                "二级部门": it.get("deptName") or "",
                "岗位名称": title,
                "需求学科": merge_majors(it),
                "学历要求": pick(it, FIELD_MAP["学历要求"]),
                "需求人数": pick(it, FIELD_MAP["需求人数"]),
                "工作城市": pick(it, FIELD_MAP["工作城市"]) or extract_city(title),
                "数智博士": fmt_digital(it.get("shuZhiBoShi")),
                "发布日期": pick(it, FIELD_MAP["发布日期"]),
                "申请链接": APPLY_URL_TEMPLATE.format(dept_id=dept_id, position_id=pid),
                "抓取时间": now_str,
            })
            added += 1

        log(f"[{i}/{len(tops)}] {dept_name}: 新增 {added}，累计 {writer.total()}")
        time.sleep(REQUEST_INTERVAL)

    writer.close()
    log(f"完成，共 {writer.total()} 条 -> {writer.csv_path}")
    page.quit()


if __name__ == "__main__":
    main()