import time
import hashlib
import requests
import random
import string
import os
import sys
from collections import Counter
from requests.packages.urllib3.exceptions import InsecureRequestWarning

# 禁用不安全请求警告
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# ===================== 空颜色函数（兼容逻辑） =====================
def get_color(verdict):
    return ""

def generate_random_str(length=6):
    """生成6位随机数字串"""
    return ''.join(random.choices(string.digits, k=length))

def generate_cf_api_url(handle, api_key, secret):
    """生成带签名的Codeforces API请求URL"""
    method = "user.status"
    rand_str = generate_random_str()
    now = int(time.time())
    params = f"apiKey={api_key}&handle={handle}&time={now}"
    sign_str = f"{rand_str}/{method}?{params}#{secret}"
    sha512 = hashlib.sha512(sign_str.encode()).hexdigest()
    api_sig = rand_str + sha512
    return f"https://codeforces.com/api/{method}?{params}&apiSig={api_sig}"

def get_user_submissions(handle, api_key, secret):
    """获取单个用户的所有提交记录"""
    url = generate_cf_api_url(handle, api_key, secret)
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"}
    try:
        response = requests.get(url, timeout=15, verify=False, headers=headers)
        response.raise_for_status()
        data = response.json()
        if data["status"] != "OK":
            return []
        return data["result"]
    except requests.exceptions.RequestException:
        return []

def filter_and_enrich(handle, submissions, target_problems, days=1):
    """过滤目标题目提交，补充时间/用户等信息"""
    one_day_ago = int(time.time()) - days * 86400
    enriched = []
    problem_set = {f"{cid}{idx}" for cid, idx in target_problems}
    for sub in submissions:
        try:
            t = sub["creationTimeSeconds"]
            cid = sub["problem"]["contestId"]
            idx = sub["problem"]["index"]
            v = sub["verdict"]
            p = f"{cid}{idx}"
        except KeyError:
            continue
        if t >= one_day_ago and p in problem_set:
            enriched.append({
                "user": handle,
                "problem": p,
                "verdict": v,
                "ts": t,
                "time_str": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t)),
                "is_first_blood": False
            })
    return enriched

def mark_first_blood(all_subs):
    """标记每道题的首杀（第一个Accepted的提交）"""
    sorted_subs = sorted(all_subs, key=lambda x: x["ts"])
    first_blood = {}
    for sub in sorted_subs:
        p = sub["problem"]
        if p not in first_blood and sub["verdict"] == "OK":
            sub["is_first_blood"] = True
            first_blood[p] = sub
    return sorted_subs, first_blood

def read_inputs_from_file(file_path="inputs.txt"):
    """从inputs.txt读取配置参数"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]

        if len(lines) < 3:
            return None, None, None

        # 解析用户名
        handles = [h.strip() for h in lines[0].split(",") if h.strip()]
        if not handles:
            return None, None, None

        # 解析查询天数
        try:
            days = int(lines[1])
        except ValueError:
            return None, None, None

        # 解析题目列表
        problems = []
        for line in lines[2:]:
            if len(problems) >= 6:
                break
            try:
                cid, idx = line.split()
                problems.append((int(cid), idx))
            except:
                continue

        if not problems:
            return None, None, None

        return handles, problems, days

    except FileNotFoundError:
        return None, None, None
    except Exception:
        return None, None, None

# ===================== 主程序 =====================
if __name__ == "__main__":
    # 配置你的Codeforces API密钥（替换为自己的！）
    CF_API_KEY = "86d64560e423acfcfd6ee77a87d698c07a6604bf"
    CF_SECRET = "9284945298c8d3e931d794252d7f09d036614539"

    if not CF_API_KEY or not CF_SECRET:
        exit(1)

    # 1. 从文件读取输入信息
    handles, problems, days = read_inputs_from_file("inputs.txt")
    if not handles or not problems or not days:
        exit(1)

    # 2. 输出到static/status.txt（前端可访问）
    sys.stdout = open("static/status.txt", "w", encoding="utf-8")

    try:
        # 3. 获取并过滤提交记录
        all_subs = []
        for h in handles:
            subs = get_user_submissions(h, CF_API_KEY, CF_SECRET)
            if not subs:
                continue
            all_subs.extend(filter_and_enrich(h, subs, problems, days))

        # 4. 排序+标记首杀
        sorted_subs, first_blood = mark_first_blood(all_subs)

        # 5. 输出提交记录（无多余空格）
        for sub in sorted_subs:
            verdict_full_name = {
                "OK": "Accepted",
                "WRONG_ANSWER": "Wrong Answer",
                "CHALLENGED": "Hacked",
                "RUNTIME_ERROR": "Runtime Error",
                "COMPILATION_ERROR": "Compilation Error",
                "TIME_LIMIT_EXCEEDED": "Time Limit Exceeded",
                "MEMORY_LIMIT_EXCEEDED": "Memory Limit Exceeded",
                "OUTPUT_LIMIT_EXCEEDED": "Output Limit Exceeded",
                "TESTING": "Running",
                "SKIPPED": "Skipped",
                "FAILED": "Judgement Failed",
                "PARTIALLY_ACCEPTED": "Partially Accepted",
                "PRESENTATION_ERROR": "Presentation Error",
                "IDLENESS_LIMIT_EXCEEDED": "Idleness Limit Exceeded",
                "SECURITY_VIOLATED": "Security Violated",
                "CRASHED": "Denial of Judgement",
                "INPUT_PREPARATION_CRASH": "Input Preparation Failed",
                "REJECTED": "Rejected"
            }
            full_status = verdict_full_name.get(sub["verdict"], "UKE")
            fb_tag = "+" if sub["is_first_blood"] else "-"
            # 调整宽度，去掉多余空格
            print(f"{sub['time_str']} | {sub['user']:20} | {sub['problem']:6} | {full_status:<19}{fb_tag}")

        # 6. 首杀汇总
        print()  # 空行分隔
        for cid, idx in problems:
            p = f"{cid}{idx}"
            if p in first_blood:
                fb = first_blood[p]
                print(f"{p}: {fb['user']} {fb['time_str']}")

    finally:
        # 关闭文件
        sys.stdout.close()
        # 恢复stdout
        sys.stdout = sys.__stdout__
