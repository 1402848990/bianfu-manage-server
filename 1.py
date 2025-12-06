import requests
import time

def get_qq_group_wpa_info(group_id: int):
    url = "https://shang.qq.com/wpa/g_wpa_get"
    params = {
        "guin": group_id,
        "t": int(time.time()*1000)  # 秒级时间戳
    }
    headers = {
        # "Referer": "http://qun.qq.com/join.html",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    }

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()  # 检查 HTTP 错误
        print("Status Code:", response.status_code)
        print("Response Text:")
        print(response.text)
        return response.text
    except requests.exceptions.RequestException as e:
        print("请求失败:", e)
        return None

# 示例：查询 QQ 群 123456789
if __name__ == "__main__":
    group_id = 545402644  # 替换成你要查询的群号
    get_qq_group_wpa_info(group_id)