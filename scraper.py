import requests
from bs4 import BeautifulSoup
import os
import time
import re
from datetime import datetime, date
import hashlib

# 目标网址
URLS = [
    "https://zhaosf.aitingshuchang.com/",
    "https://zhaosf.aitingshuchang.com/index2.html"
]

# 创建data目录
DATA_DIR = "data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

def parse_time_to_timestamp(time_element):
    """
    解析时间元素并转换为时间戳
    支持三种格式:
    1. <td class="time">10月10日/13:00</td>
    2. <td class="time color1">今日14:00</td>
    3. <td class='time'><span style='color:#008910'>★★精品全天推荐★★</span></td>
    """
    time_text = time_element.get_text(strip=True)
    
    # 格式3: 精品全天推荐，不更改
    if "精品全天推荐" in time_text:
        return time_text
    
    # 格式2: 今日时间
    if "今日" in time_text:
        today = date.today()
        time_part = time_text.replace("今日", "")
        time_obj = datetime.strptime(time_part, "%H:%M").time()
        dt = datetime.combine(today, time_obj)
        return int(dt.timestamp())
    
    # 格式1: 月日/时分
    match = re.match(r"(\d+)月(\d+)日/(\d+):(\d+)", time_text)
    if match:
        month, day, hour, minute = map(int, match.groups())
        # 假设是当前年份
        current_year = datetime.now().year
        try:
            dt = datetime(current_year, month, day, hour, minute)
            return int(dt.timestamp())
        except ValueError:
            # 如果日期无效，返回原始文本
            return time_text
    
    return time_text

def extract_server_info(row):
    """
    从表格行中提取服务器信息
    """
    cells = row.find_all('td')
    if len(cells) < 7:
        return None
    
    # 提取各字段信息
    server_name_link = cells[0].find('a')
    server_name = server_name_link.get_text(strip=True) if server_name_link else ''
    server_url = server_name_link.get('href', '') if server_name_link else ''
    
    # 如果没有URL链接，则不采集这条数据
    if not server_url:
        return None
    
    # 如果URL链接看起来像表头（包含中文字段名），则不采集
    header_keywords = ['链接', '服务器', '名称', '时间', '消费', '描述', '特色']
    if any(keyword in server_url for keyword in header_keywords):
        return None
    
    # 如果URL不包含有效的协议，则不采集
    if 'http' not in server_url:
        return None
    
    # 去除URL中的参数（问号及后面的内容）
    if '?' in server_url:
        server_url = server_url.split('?')[0]
    
    # 如果服务器名称看起来像表头，则不采集
    if any(keyword in server_name for keyword in header_keywords):
        return None
    
    server_type_link = cells[1].find('a')
    server_type = server_type_link.get_text(strip=True) if server_type_link else ''
    
    # 如果服务器类型看起来像表头，则不采集
    if any(keyword in server_type for keyword in header_keywords):
        return None
    
    time_element = cells[2]
    low_consumption = cells[3].get_text(strip=True)
    description = cells[4].get_text(strip=True)
    features = cells[5].get_text(strip=True)
    
    # 解析时间戳
    timestamp = parse_time_to_timestamp(time_element)
    
    # 如果时间戳不是整数（即解析失败），则不采集
    if not isinstance(timestamp, int):
        return None
    
    # 如果时间戳为0或负数，则不采集
    if timestamp <= 0:
        return None
    
    # 创建唯一标识用于去重
    unique_id = f"{server_name}_{server_type}_{timestamp}"
    
    return {
        'unique_id': unique_id,
        'server_name': server_name,
        'server_url': server_url,
        'server_type': server_type,
        'timestamp': timestamp,
        'low_consumption': low_consumption,
        'description': description,
        'features': features
    }

def scrape_url(url):
    """
    采集单个URL的数据
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'lxml')
        
        # 查找所有开区信息的tr元素
        rows = soup.find_all('tr', attrs={'onmouseover': True})
        
        server_data = []
        for row in rows:
            info = extract_server_info(row)
            if info:
                server_data.append(info)
        
        return server_data
    except Exception as e:
        print(f"采集 {url} 时出错: {e}")
        return []

def deduplicate_data(data):
    """
    去除重复数据
    """
    unique_data = {}
    for item in data:
        unique_id = item['unique_id']
        if unique_id not in unique_data:
            unique_data[unique_id] = item
    return list(unique_data.values())

def save_to_markdown(data, filename):
    """
    将数据保存为Markdown格式
    """
    filepath = os.path.join(DATA_DIR, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write("# 开区信息采集结果\n\n")
        f.write(f"采集时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("| 服务器名称 | 服务器链接 | 服务器类型 | 开区时间 | 最低消费 | 描述 | 特色 |\n")
        f.write("| --- | --- | --- | --- | --- | --- | --- |\n")
        
        for item in data:
            # 格式化时间显示
            if isinstance(item['timestamp'], int):
                time_display = datetime.fromtimestamp(item['timestamp']).strftime('%Y-%m-%d %H:%M')
            else:
                time_display = item['timestamp']
            
            f.write(f"| {item['server_name']} | {item['server_url']} | {item['server_type']} | {time_display} | {item['low_consumption']} | {item['description']} | {item['features']} |\n")
    
    print(f"数据已保存到 {filepath}")

def save_as_lines(data, filename):
    """
    将数据保存为每行一条记录的格式，使用制表符分隔
    """
    filepath = os.path.join(DATA_DIR, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        # 写入表头
        f.write("服务器名称\t服务器链接\t服务器类型\t开区时间\t最低消费\t描述\t特色\n")
        
        for item in data:
            # 格式化时间显示
            if isinstance(item['timestamp'], int):
                time_display = str(item['timestamp'])  # 保持时间戳格式
            else:
                time_display = item['timestamp']
            
            # 写入数据行，使用制表符分隔
            f.write(f"{item['server_name']}\t{item['server_url']}\t{item['server_type']}\t{time_display}\t{item['low_consumption']}\t{item['description']}\t{item['features']}\n")
    
    print(f"数据已保存到 {filepath} (每行一条记录格式)")

def main():
    """
    主函数
    """
    all_data = []
    
    # 采集所有URL的数据
    for url in URLS:
        print(f"正在采集: {url}")
        data = scrape_url(url)
        all_data.extend(data)
        print(f"从 {url} 采集到 {len(data)} 条数据")
    
    # 去重
    unique_data = deduplicate_data(all_data)
    print(f"去重后共有 {len(unique_data)} 条数据")
    
    # 保存到Markdown文件
    save_to_markdown(unique_data, "9pk.md")
    
    # 保存为每行一条记录的格式
    save_as_lines(unique_data, "9pk_lines.txt")
    
    print("采集完成!")

if __name__ == "__main__":
    main()