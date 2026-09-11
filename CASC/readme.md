# 中国航天人才网 校招职位采集

采集 https://www.spacetalent.com.cn/zhiweicx.html 的 2027 届校园招聘职位列表，
输出统一的 CSV 和 JSON。

## 数据规模

- 官网声明总数：约 2900~3000 条（会随官网更新浮动）
- 覆盖 26 个顶层院（航天一院至十一院、卫通、乐凯、长城工业等）
- 每条记录 11 个字段

## 输出字段

| 字段 | 来源 | 说明 |
|---|---|---|
| 招聘单位 | `parentDeptName` | 院/公司级，如"航天十一院" |
| 二级部门 | `deptName` | 部门级，如"战术部"；扁平结构的院该字段等于院名 |
| 岗位名称 | `positionName` | |
| 需求学科 | `mainMajorName` + `otherMajor1Name` + `otherMajor2Name` | 多学科用 ` / ` 拼接 |
| 学历要求 | `educationText` | 中文，如"硕士及以上" |
| 需求人数 | `peopleNum` | |
| 工作城市 | `workPlaceName` | 接口直接给，缺失时从岗位名括号里拆 |
| 数智博士 | `shuZhiBoShi` | 布尔值转中文，空值留空 |
| 发布日期 | `releaseDate` | |
| 申请链接 | 拼接 | `jituan_xxx.html?id={deptId}&positionId={positionId}` |
| 抓取时间 | 本地生成 | |

## 环境要求

- Python 3.9+
- 本机已安装 Chrome 或 Edge（DrissionPage 需要）
- 能访问 https://www.spacetalent.com.cn

## 安装

```bash
pip install -r requirements.txt