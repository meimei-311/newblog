# from flask import Flask, render_template
from urllib.parse import urljoin, urlunparse, urlparse, urlsplit
from posixpath import normpath
import requests
import re
import time
import os
from treelib import Node, Tree
from lxml import etree


save_dir = './downloads/abc'

html_pages = set()
already_save_pages = []
already_save_elements = []
root_dir = save_dir




class SavePath(object): 
    def __init__(self, path): 
        self.path = path


def url_join_path(url, relative_path):
    arr = urlparse(urljoin(url, relative_path))
    return urlunparse((arr.scheme, 
                        arr.netloc, 
                        normpath(arr[2]), 
                        arr.params, 
                        arr.query, 
                        arr.fragment))


def save(relative_path, content):
    """
    relative_path :存储的相对路径

    """
    # 去掉/开头
    rela_path = relative_path.replace('/', '', 1) if relative_path.startswith('/') else relative_path
    save_path = os.path.join(root_dir, rela_path)

    if not os.path.exists(save_path):
        save_dir = os.path.dirname(save_path)
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        with open(save_path, 'w') as f:
            f.write(content)
        print('save!!\t', save_path)


def save_css(relative_path, url):
    """
    relative_path :存储的相对路径

    """
    # 去掉/开头
    rela_path = relative_path.replace('/', '', 1) if relative_path.startswith('/') else relative_path
    save_path = os.path.join(root_dir, rela_path)

    content = Spider().run(url)
    if content:
        if not os.path.exists(save_path):
            save_dir = os.path.dirname(save_path)
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)
            with open(save_path, 'w') as f:
                f.write(content)
            print('save!!css\t', save_path)
        inner_img_css(relative_path, url, content)
        return True
    else:
        return False


def inner_img_css(save_path, css_url, css_text):
    """
        下载css中的img
    """
    inner_img_regex = r'background: url\((.*?)\)'
    images = re.findall(inner_img_regex, css_text)
    print('css==\t', css_url, '\nimg==\t', images)
    for one in images:
        save_img_path = url_join_path(save_path, one)
        img_url = url_join_path(css_url, one)
        save_images(save_img_path, img_url)



def save_js(relative_path, url):
    """
    relative_path :存储的相对路径

    """
    # 去掉/开头
    rela_path = relative_path.replace('/', '', 1) if relative_path.startswith('/') else relative_path
    save_path = os.path.join(root_dir, rela_path)

    content = Spider().run(url)
    if content:
        if not os.path.exists(save_path):
            save_dir = os.path.dirname(save_path)
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)
            with open(save_path, 'w') as f:
                f.write(content)
            print('save!!js\t', save_path, '\t', url)
        return True
    else:
        return False


def save_images(relative_path, url):
    """
    """
    content = Spider().content(url)
    save_path = os.path.join(root_dir, relative_path)
    if content:
        dirname = os.path.dirname(save_path)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        with open(save_path, 'wb') as f:
            f.write(content)
        print('save!!image\t', save_path, '\t', url)
        return True
    else:
        return False


# url的域
def domain_url(url):
    return urlsplit(url)[1].split(':')[0]


# url的path, file
def parse_url_relative(url):
    if url.endswith('/'):
        return urlparse(url).path, None
    else:
        url_part = urlparse(url).path.split('/')
        return ('/'.join(url_part[:-1]), url_part[-1])

# html页面保存的path, file
def page_relative(url, root_path):
    """
        root_path同级或子级的页面才保存，其他返回None
    """
    url_path = urlparse(url).path
    url_dir = os.path.dirname(url_path)
    url_file = os.path.basename(url_path)
    if url_dir == root_path:    #同级页面
        return url_file
    elif url_dir in root_path:    #子级页面
        return url_path.replace(root_path, '')
    else:
        print('不是同一级或子级')
        return None



# 获取url的源码，text
class Spider(object):
    def run(self, url):
        html = requests.get(url, timeout=20)
        html.encoding = 'utf-8'
        if html.status_code != requests.codes.ok:
            return None
        return html.text
    
    def content(self, url):
        html = requests.get(url, timeout=20)
        if html.status_code != requests.codes.ok:
            return None
        return html.content



def save_element(etree_html, xpath_pattern, default_path, inner_img=0):
    """
        从html源码中提取 css,js,img等，保存
    """
    results = etree_html.xpath(xpath_pattern)

    # content中的css href替换,(源href, 现href)
    replace = []

    for link in results:
        real_path = link.split('?')[0]
        if real_path.startswith('http') or real_path.startswith("//"):
            _, file_name = parse_url_relative(real_path)
            save_path = os.path.join(default_path, file_name)
            download_url = real_path
        else:
            # 域内css文件按原路径保存
            download_url = url_join_path(root, real_path)
            save_path = real_path.replace('/', '', 1) if real_path.startswith('/') else real_path
           
        if save_path in already_save_elements:
            continue

        ret = False
        if default_path == 'images':
            ret = save_images(save_path, download_url)
        elif default_path == 'js':
            ret = save_js(save_path, download_url)
        elif default_path == 'css':
            ret = save_css(save_path, download_url)
        
        if not ret:
            continue
        already_save_elements.append(save_path)

        if real_path != save_path:
            replace.append((real_path, save_path))
            
    return replace


def element(content, parent_page):
    html = etree.HTML(content)
    ret_content = content
    element = [('//link[@rel="stylesheet"]/@href', 'css', 1),
                ('//script/@src', 'js', 0),
                ('//img/@src', 'images', 0)]
    replaces = []

    for ele in element:
        replaces += save_element(html, ele[0], ele[1], ele[2])

    # 替换content中的css href
    for rp in replaces:
        print('replaces:----', rp)
        ret_content = ret_content.replace(rp[0], rp[1])

    return ret_content

def subpages(content, parent_page):
    """
        从content中找到同域 同级页面或子页面 返回
    """
    etree_html = etree.HTML(content)
    # etree_html = etree.tostring(content, encoding='utf-8')
    pages_in = etree_html.xpath('//a/@href')
    print('pages in:\t', set(pages_in))
    new_pages = []
    p = filter(lambda x : x not in ['/','#'] and (not x.startswith('#')) and len(x.strip())>0, pages_in)
    for one in set(p):
        subpage = url_join_path(parent_page, one)
        if domain_url(subpage) == domain \
                    and subpage not in new_pages \
                    and subpage not in already_save_pages:
            # fetch subpage or brother
            if one.startswith('http') or one.startswith('//'):
                page_path, _ = parse_url_relative(one)
                # new_pages.append(one)
            else:
                new_pages.append(subpage)

            if not tree.contains(subpage):
                tree.create_node(subpage, subpage, parent=parent_page, data=SavePath(''))

    return new_pages

def run(pages, level=3):

    global domain
    global tree
    global already_save_pages
    global root
    global root_path

    new_pages = []
    for page in pages:
        if page in already_save_pages or domain_url(page) != domain:
            continue

        already_save_pages.append(page)

        ori_html = Spider().run(page)
        if not ori_html:
            continue

        html = element(ori_html, page)
        relative_path = page_relative(page, root_path)

        save(relative_path, html)
        node = tree.get_node(page)
        if node:
            node.data = SavePath(relative_path)

        subpage = subpages(html, page)
        print("subpage-----", subpage)
        new_pages += subpage  

    if new_pages and tree.level(root) < level:
        run(new_pages, level)






if __name__ == '__main__':
    
    # url = ['http://view.jqueryfuns.com/2019/4/3/25c12c43a656b98f5c33788c0ff8100b/index.html']
    # url = ['https://www.w3cschool.cn/flask/flask_templates.html']
    # spider = SpiderHtmlElement(url, './downloads/yqq')

    # root = 'http://view.jqueryfuns.com/2019/4/3/25c12c43a656b98f5c33788c0ff8100b/index.html'
    # root = 'https://www.cnblogs.com/adamans/articles/9093711.html'
    root = 'http://demo.cssmoban.com/cssthemes6/cpts_1873_cyq/index.html'
    # root = "http://www.spiderpy.cn/blog/index/"
    domain = urlsplit(root)[1].split(':')[0]

    # root = 'https://i.cnblogs.com/EditPosts.aspx?opt=1'
    # url_part = urlparse(root)
    # url_root = '/'.join(url_part.path.split('/')[:-1])
    root_path, root_file = parse_url_relative(root)
    print('url_root:', root_path, root_file)


    tree = Tree()
    tree.create_node(root, root)  # root node
    level = 2
    run([root], level)
    

    # tree.show(idhidden=False)
    tree.show(idhidden=False, data_property="path")



    # print(page_relative('http://demo.cssmoban.com/cssthemes6/cpts_1873_cyq/about.html',
    #      '/cssthemes6/cpts_1873_cyq'))







