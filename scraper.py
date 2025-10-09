import requests
from bs4 import BeautifulSoup
import os
import time
import re
from datetime import datetime, date
import hashlib
import json

# 目标网址
URLS = [
    "https://zhaosf.aitingshuchang.com/",
    "https://zhaosf.aitingshuchang.com/index2.html",
    "https://jjj.com"
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
    
    # 如果URL不包含有效的协议，则不采集
    if 'http' not in server_url:
        return None
    
    # 去除URL中的参数（问号及后面的内容）
    if '?' in server_url:
        server_url = server_url.split('?')[0]
    
    # 进一步清理URL，确保去除可能的锚点
    if '#' in server_url:
        server_url = server_url.split('#')[0]
    
    server_type_link = cells[1].find('a')
    server_type = server_type_link.get_text(strip=True) if server_type_link else ''
    
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
    
    # 检查是否为表头数据
    if is_header_data(server_name, server_type, server_url, low_consumption, description, features):
        return None
    
    # 创建唯一标识用于去重 (根据URL和时间戳)
    unique_id = f"{server_url}_{timestamp}"
    
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

def is_header_data(server_name, server_type, server_url, low_consumption, description, features):
    """
    判断是否为表头数据
    """
    # 检查是否为典型的表头格式
    if (server_name == '服务器名称' and 
        '链接' in server_url and 
        server_type == '服务器类型' and 
        low_consumption == '最低消费' and 
        description == '描述' and 
        features == '特色'):
        return True
    
    # 定义表头关键词
    header_keywords = ['链接', '服务器', '名称', '时间', '消费', '描述', '特色', '最低', '类型']
    
    # 检查各个字段是否包含表头关键词
    fields_to_check = [server_name, server_type, server_url, low_consumption, description, features]
    
    # 如果超过3个字段包含表头关键词，则认为是表头数据
    header_keyword_count = 0
    for field in fields_to_check:
        if any(keyword in field for keyword in header_keywords):
            header_keyword_count += 1
    
    if header_keyword_count >= 3:
        return True
    
    # 特殊检查：如果服务器名称和URL看起来像表头
    if '服务器' in server_name and '链接' in server_url:
        return True
    
    return False

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
        
        # 为jjj.com网站使用专门的处理函数
        if 'jjj.com' in url:
            return scrape_jjj_data(soup)
        
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

def scrape_api_data(api_url):
    """
    采集API数据
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        }
        
        response = requests.get(api_url, headers=headers, timeout=15)  # 增加超时时间
        response.raise_for_status()  # 检查HTTP错误
        
        # 解析JSON数据
        data = response.json()
        
        # 检查API响应结构 (根据实际返回的数据结构调整)
        if 'data' in data and 'list' in data['data']:
            records = data['data']['list']
        elif 'list' in data:
            records = data['list']
        else:
            records = data if isinstance(data, list) else []
        
        server_data = []
        for record in records:
            # 提取服务器信息
            server_info = extract_api_server_info(record)
            if server_info:
                server_data.append(server_info)
        
        return server_data
    except requests.exceptions.RequestException as e:
        print(f"网络请求错误: {e}")
        return []
    except json.JSONDecodeError as e:
        print(f"JSON解析错误: {e}")
        return []
    except Exception as e:
        print(f"采集API {api_url} 时出错: {e}")
        return []

def extract_api_server_info(record):
    """
    从API记录中提取服务器信息
    """
    try:
        # 根据API返回的数据结构提取信息 (根据实际返回的数据结构调整)
        server_name = record.get('serverName', '')
        server_url = record.get('webUrl', '')
        server_type = record.get('serverType', '')
        server_ip = record.get('serverIp', '')  # 获取serverIp字段
        low_consumption = record.get('serviceQq', '')
        description = record.get('gameIntro', '')
        
        # 将serverIp字段的值添加到features字段中
        features = server_ip
        
        # 处理时间字段
        time_str = record.get('startServerTime', '')
        timestamp = parse_api_time(time_str)
        
        # 如果没有URL链接，则不采集这条数据
        if not server_url:
            return None
        
        # 如果URL不包含有效的协议，则添加http://前缀
        if 'http' not in server_url:
            server_url = 'http://' + server_url
        
        # 去除URL中的参数（问号及后面的内容）
        if '?' in server_url:
            server_url = server_url.split('?')[0]
        
        # 进一步清理URL，确保去除可能的锚点
        if '#' in server_url:
            server_url = server_url.split('#')[0]
        
        # 如果时间戳不是整数（即解析失败），则不采集
        if not isinstance(timestamp, int):
            return None
        
        # 如果时间戳为0或负数，则不采集
        if timestamp <= 0:
            return None
        
        # 创建唯一标识用于去重 (根据URL和时间戳)
        unique_id = f"{server_url}_{timestamp}"
        
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
    except Exception as e:
        print(f"解析API记录时出错: {e}")
        return None

def scrape_jjj_data(soup):
    """
    专门用于采集jjj.com网站数据的函数
    数据格式为JavaScript函数调用: o4("服务器名称","URL","类型","时间","最低消费","描述","特色");
    """
    server_data = []
    try:
        # 获取页面的所有文本内容
        page_text = str(soup)
        
        # 使用正则表达式匹配o4函数调用
        import re
        from bs4 import BeautifulSoup
        pattern = r'o4\s*\(\s*"([^"]*)"\s*,\s*"([^"]*)"\s*,\s*"([^"]*)"\s*,\s*"([^"]*)"\s*,\s*"([^"]*)"\s*,\s*"([^"]*)"\s*,\s*"([^"]*)"\s*\)'
        matches = re.findall(pattern, page_text)
        
        for match in matches:
            # 提取各个字段
            server_name = match[0].strip()
            server_url = match[1].strip()
            server_type = match[2].strip()
            time_text = match[3].strip()
            low_consumption = match[4].strip()
            description = match[5].strip()
            features = match[6].strip()
            
            # 解析时间
            time_element = BeautifulSoup(f'<td class="time">{time_text}</td>', 'lxml').td
            timestamp = parse_time_to_timestamp(time_element)
            
            # 数据验证
            if not server_url or 'http' not in server_url:
                continue
            
            if not isinstance(timestamp, int) or timestamp <= 0:
                continue
            
            # 去除URL参数
            if '?' in server_url:
                server_url = server_url.split('?')[0]
            if '#' in server_url:
                server_url = server_url.split('#')[0]
            
            # 检查是否为表头数据
            if is_header_data(server_name, server_type, server_url, low_consumption, description, features):
                continue
            
            # 创建唯一标识用于去重
            unique_id = f"{server_url}_{timestamp}"
            
            server_data.append({
                'unique_id': unique_id,
                'server_name': server_name,
                'server_url': server_url,
                'server_type': server_type,
                'timestamp': timestamp,
                'low_consumption': low_consumption,
                'description': description,
                'features': features
            })
        
        return server_data
    except Exception as e:
        print(f"采集jjj.com数据时出错: {e}")
        return []

def parse_api_time(time_str):
    """
    解析API时间字符串
    """
    if not time_str:
        return int(datetime.now().timestamp())
    
    try:
        # 尝试多种时间格式
        if isinstance(time_str, str):
            # 尝试解析时间戳字符串
            if time_str.isdigit():
                return int(time_str)
            
            # 尝试解析常见的时间格式
            time_formats = [
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d %H:%M',
                '%Y-%m-%d',
                '%m月%d日/%H:%M',
                '%m-%d %H:%M'
            ]
            
            for fmt in time_formats:
                try:
                    if '%Y' not in fmt:
                        # 如果没有年份，假设是当前年份
                        current_year = datetime.now().year
                        time_obj = datetime.strptime(time_str, fmt).replace(year=current_year)
                    else:
                        time_obj = datetime.strptime(time_str, fmt)
                    return int(time_obj.timestamp())
                except ValueError:
                    continue
        
        # 如果是数字类型，直接返回
        if isinstance(time_str, (int, float)):
            return int(time_str)
        
        # 默认返回当前时间戳
        return int(datetime.now().timestamp())
    except Exception:
        return int(datetime.now().timestamp())

def deduplicate_data(data):
    """
    去除重复数据
    根据时间和URL来判断重复数据，同一时间段的相同URL视为重复
    """
    unique_data = {}
    for item in data:
        # 使用URL和时间戳组合作为唯一标识
        unique_key = f"{item['server_url']}_{item['timestamp']}"
        if unique_key not in unique_data:
            unique_data[unique_key] = item
    return list(unique_data.values())

def save_to_markdown(data, filename):
    """
    将数据保存为Markdown格式
    """
    filepath = os.path.join(DATA_DIR, filename)
    
    # 先清空文件内容
    with open(filepath, 'w', encoding='utf-8') as f:
        pass  # 清空文件内容
    
    # 写入数据
    with open(filepath, 'a', encoding='utf-8') as f:
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
    
    # 先清空文件内容
    with open(filepath, 'w', encoding='utf-8') as f:
        pass  # 清空文件内容
    
    # 写入数据
    with open(filepath, 'a', encoding='utf-8') as f:
        # 根据项目规范，不写入表头，只输出数据行
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
    
    # 采集API数据
    api_url = "https://k-4-5.fhjkwerv.com:9001/api/gameAd/getList"
    print(f"正在采集API: {api_url}")
    api_data = scrape_api_data(api_url)
    print(f"从API采集到 {len(api_data)} 条数据")
    
    # 将API数据添加到总数据中
    all_data.extend(api_data)
    
    # 去重
    unique_data = deduplicate_data(all_data)
    print(f"去重后共有 {len(unique_data)} 条数据")
    
    # 保存到Markdown文件
    save_to_markdown(unique_data, "9pk.md")
    
    # 保存为每行一条记录的格式
    save_as_lines(unique_data, "9pk_lines.txt")
    
    # 保存API数据到30ok.txt
    if api_data:
        # API数据已经包含在all_data中并经过了统一去重处理
        # 这里筛选出所有API来源的数据
        api_filtered_data = [item for item in unique_data if item['unique_id'] in [api_item['unique_id'] for api_item in api_data]]
        save_as_lines(api_filtered_data, "30ok.txt")
        print(f"API数据已保存到 30ok.txt，共 {len(api_filtered_data)} 条数据")
    
    # 保存jjj.com数据到jjj.txt
    # 筛选出所有来自jjj.com的数据
    jjj_data = [item for item in unique_data if "jjj.com" in item['server_url']]
    if jjj_data:
        save_as_lines(jjj_data, "jjj.txt")
        print(f"jjj.com数据已保存到 jjj.txt，共 {len(jjj_data)} 条数据")
    
    print("采集完成!")

if __name__ == "__main__":
    main()