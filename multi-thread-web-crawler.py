import requests
from bs4 import BeautifulSoup
import re
import numpy as np
import csv
import time
import threading
import queue
import matplotlib.pyplot as plt


def gen_url(page):
    print("生成子页URL：".center(page // 2, '-'))
    url_que = queue.Queue()
    offset = 0
    t = time.clock()
    for i in range(page+1):
        a = '*' * i
        b = '.' * (page - i)
        c = (i / page) * 100
        url = 'https://book.douban.com/tag/%E7%BC%96%E7%A8%8B?start={}&type=T'
        url_que.put(url.format(offset))
        offset += 20
        t -= time.clock()
        print("\r{:^3.0f}%[{}->{}]{:.2f}ms".format(c, a, b, -t), end='')
        time.sleep(0.05)
    return url_que


# 定义正则化函数
def normalize(arr):
    arr = (arr - np.min(arr)) / (np.max(arr) - np.min(arr))
    return arr


# 绘制柱状图
def plot_bar(l, arr, tag, c):
    labels = np.array(
        ["C", "C++", "Python", "Java", "JavaScript", "Android", "Algorithm", "Linux", "SQL", "C#", "Game"])
    plt.figure(figsize=(10, 8))
    plt.bar(range(l), arr, tick_label=labels, label=tag, fc=c, zorder=3)
    plt.legend()
    plt.grid(ls='--')
    plt.show()


def count(arr):
    nl = np.array(["c语言", "c++", "python", "java", "javascript", "android", "算法", "linux", "sql", "c#", "游戏"])
    l = len(nl)
    cnt = np.zeros(l)
    star = np.zeros(l)
    com = np.zeros(l)
    smean = np.zeros(l)
    cmean = np.zeros(l)
    kbi = np.zeros(l)
    (x, y) = arr.shape
    for n in range(x):
        for i in range(l):
            if arr[n, 0].lower().find(nl[i]) != -1:
                cnt[i] += 1
                com[i] += int(arr[n, 1])
                star[i] += float(arr[n, 2])
    # 得出真正Java类书籍的数据
    cnt[3] = cnt[3] - cnt[4]
    com[3] = com[3] - com[4]
    star[3] = star[3] - star[4]

    for i in range(l):
        if cnt[i] != 0:
            cmean[i] = com[i] / cnt[i]
            smean[i] = star[i] / cnt[i]

    cnorm = normalize(cmean)
    snorm = normalize(smean)
    for i in range(l):
        if cnt[i] != 0:
            kbi[i] = cnorm[i] * snorm[i]  # 定义口碑指数为评论数均值*评分均值
    print("各类书籍统计总书：", cnt)
    print("评论数均值：", cmean)
    print("评分均值：", smean)
    print("相对评分：", snorm)
    kbi = normalize(kbi)    # 归一化人气指数
    print("人气指数：", kbi)
    # 绘制柱状图
    plot_bar(l, cnt, "No.Book", 'g')
    plot_bar(l, cmean, "Average Comment", 'r')
    plot_bar(l, smean, "Average Score", 'b')
    plot_bar(l, snorm, "Relative Score", 'b')
    plot_bar(l, kbi, "Pop Index", 'y')


# 数据分析
def handle(result):
    array = np.array(result)
    sort_arr = array[np.lexsort(array.T)]   # 按照评分排序
    count(sort_arr)
    reverse_arr = sort_arr[::-1]
    sort_list = np.matrix.tolist(reverse_arr)
    return sort_list


# 将数据导出到csv
def save(data):
    file = open('douban.csv', 'w+', newline='')
    writer = csv.writer(file)
    header = ['书名', '评论数', '评分']
    writer.writerow(header)
    for book in data:
        try:
            writer.writerow(book)
        except:
            continue
    file.close()


# 请求url，下载html
def download():
    while True:
        try:
            url = url_task.get(block=False)
            resp = requests.get(url)
            html = resp.text
            task_html.put(html)
            time.sleep(1)
        except:
            break


# 解析html，获取评分
def extract():
    if task_html.qsize() > 10:
        while True:
            try:
                html = task_html.get(block=False)
                bs4 = BeautifulSoup(html, "lxml")
                book_list = bs4.find_all('li', class_='subject-item')
                if book_list is not None:
                    for book_info in book_list:
                        temp = []
                        try:
                            star = book_info.find('span', class_='rating_nums').get_text()
                            # if float(star) < 8.0:     # 控制分数门槛
                            #  continue
                            title = book_info.find('h2').get_text().replace(' ', '').replace('\n', '')
                            comment = book_info.find('span', class_='pl').get_text()
                            comment = re.sub("\D", "", comment)
                            if int(comment) > 30:     # 控制评论数
                                temp.append(title)
                                temp.append(comment)
                                temp.append(star)
                                info.append(temp)
                        except:
                            continue
            except:
                break


if __name__ == '__main__':
    url_task = gen_url(90)     # 生成子页URL队列
    print("\n生成URL完成")
    # 已下载的Html队列
    start = time.clock()
    task_html = queue.Queue()
    info = []
    threads = []
    for i in range(5):
        threads.append(threading.Thread(target=download))       # 下载Html线程
    for i in range(2):
        threads.append(threading.Thread(target=extract))    # 解析html线程
    print("创建线程完成")
    for i in threads:
        i.start()
        print("线程", i, "开始！")
        i.join()
    end = time.clock()
    print("爬取完成！用时共：", (end - start), "s.")

    save(handle(info))      # 主线程保存数据同时分析数据

