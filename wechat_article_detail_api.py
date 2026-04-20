#!/usr/bin/env python3
"""
微信公众号文章获取 API 服务

提供HTTP接口获取微信公众号文章内容

用法:
  python3 wechat_article_detail_api.py          # 启动服务 (默认端口 8080)
  python3 wechat_article_detail_api.py --port 8888  # 指定端口

API 端点:
  POST /api/fetch
  请求体: {"link": "https://mp.weixin.qq.com/s/xxxxx", "format": "content"}
  返回: {"code": 200, "data": {"title": "...", "author": "...", "content": "..."}, "message": "成功"}

  GET /api/fetch?link=https://mp.weixin.qq.com/s/xxxxx&format=content
"""

import sys
import json
import urllib.request
import urllib.error
import urllib.parse
import re
import argparse
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs


class WeChatArticleExtractor:
    """微信公众号文章提取器"""

    @staticmethod
    def fetch_url(url, headers=None):
        """抓取URL内容"""
        if headers is None:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Linux; Android 10; SM-G981B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.162 Mobile Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9',
            }

        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as response:
                return response.read().decode('utf-8', errors='ignore'), None
        except Exception as e:
            return None, str(e)

    @staticmethod
    def extract_article_content(html):
        """提取单篇文章内容"""
        result = {
            'title': '',
            'author': '',
            'publish_time': '',
            'content': '',
            'read_count': '',
            'like_count': '',
            'cover_image': ''
        }

        # 提取标题
        patterns = [
            r'var msg_title = [\'"](.+?)[\'"];',
            r'<h1[^>]*class="rich_media_title[^"]*"[^>]*>(.*?)</h1>',
            r'<h2[^>]*class="rich_media_title[^"]*"[^>]*>(.*?)</h2>',
        ]
        for pattern in patterns:
            match = re.search(pattern, html, re.DOTALL)
            if match:
                title = match.group(1)
                title = title.replace('\\x26', '&').replace('\\x0a', '').replace('\\x20', ' ').replace('\\x2c', ',')
                result['title'] = re.sub(r'<[^>]+>', '', title).strip()
                break

        # 清理标题中的JavaScript代码
        if result['title'] and "'.html" in result['title']:
            result['title'] = result['title'].split("'.html")[0]

        # 提取作者
        author_patterns = [
            r'var nickname = [\'"](.+?)[\'"];',
            r'<a[^>]*id="js_name"[^>]*>(.*?)</a>',
            r'<span[^>]*class="profile_nickname"[^>]*>(.*?)</span>',
            r'<a[^>]*class="profile_nickname"[^>]*>(.*?)</a>',
        ]
        for pattern in author_patterns:
            match = re.search(pattern, html, re.DOTALL)
            if match:
                result['author'] = re.sub(r'<[^>]+>', '', match.group(1)).strip()
                break

        # 提取发布时间
        time_patterns = [
            r'<em[^>]*id="publish_time"[^>]*>(.*?)</em>',
            r'var publish_time = [\'"](.+?)[\'"];',
            r'<span[^>]*class="publish_time"[^>]*>(.*?)</span>',
        ]
        for pattern in time_patterns:
            match = re.search(pattern, html, re.DOTALL)
            if match:
                result['publish_time'] = re.sub(r'<[^>]+>', '', match.group(1)).strip()
                break

        # 提取封面图
        cover_patterns = [
            r'var msg_cdn_url = [\'"](https?://[^\'"]+)[\'"];',
            r'<img[^>]*data-src="(https?://mmbiz\.qpic\.cn[^"]+)"[^>]*class="rich_media_thumb',
        ]
        for pattern in cover_patterns:
            match = re.search(pattern, html, re.DOTALL)
            if match:
                result['cover_image'] = match.group(1)
                break

        # 提取正文
        content_match = re.search(r'<div[^>]*id="js_content"[^>]*>(.*?)</div>\s*(?:<script|</div>|<!--)', html, re.DOTALL)
        if content_match:
            content_html = content_match.group(1)
            # 处理图片
            content_html = re.sub(r'<img[^>]*data-src="([^"]+)"[^>]*>', r'\n[图片: \1]\n', content_html)
            # 保留段落和换行
            content_html = content_html.replace('</p>', '\n\n').replace('</div>', '\n').replace('</section>', '\n').replace('<br>', '\n').replace('<br/>', '\n')
            content = re.sub(r'<[^>]+>', '', content_html)
            content = content.replace('&nbsp;', ' ').replace('&quot;', '"').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
            content = re.sub(r'\n\s*\n', '\n\n', content)
            content = re.sub(r'\n{3,}', '\n\n', content)
            result['content'] = content.strip()

        return result

    @classmethod
    def fetch_article(cls, url):
        """获取文章完整信息"""
        html, error = cls.fetch_url(url)
        if html is None:
            return None, error

        article = cls.extract_article_content(html)
        article['url'] = url

        if not article['title']:
            return None, "无法提取文章标题，文章可能需要登录或已被删除"

        return article, None


class APIHandler(BaseHTTPRequestHandler):
    """API请求处理器"""

    def log_message(self, format, *args):
        """自定义日志输出"""
        print(f"[{self.log_date_time_string()}] {args[0]}")

    def _send_json_response(self, status_code, data):
        """发送JSON响应"""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8'))

    def _send_success(self, data, message="成功"):
        """发送成功响应 - 兼容你的Java DTO"""
        self._send_json_response(200, {
            "success": True,
            "data": data,
            "error": None
        })

    def _send_error(self, status_code, message):
        """发送错误响应 - 兼容你的Java DTO"""
        self._send_json_response(status_code, {
            "success": False,
            "data": None,
            "error": message
        })

    def do_OPTIONS(self):
        """处理CORS预检请求"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        """处理GET请求"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        query_params = parse_qs(parsed_path.query)

        # 健康检查
        if path == '/health':
            self._send_json_response(200, {'status': 'ok', 'service': 'wechat-article-api'})
            return

        # 获取文章 - 支持 link 或 url 参数
        if path == '/api/fetch':
            url = query_params.get('link', [''])[0] or query_params.get('url', [''])[0]
            format_type = query_params.get('format', ['content'])[0]
            self._handle_fetch(url, format_type)
            return

        # 404
        self._send_error(404, 'Not Found')

    def do_POST(self):
        """处理POST请求 —— 已修复，完美支持 JSON"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        try:
            # 1. 读取请求体长度
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length <= 0:
                self._send_error(400, 'Missing required parameter: link or url')
                return

            # 2. 读取原始 body
            body = self.rfile.read(content_length).decode('utf-8').strip()

            # 3. 解析 JSON
            data = json.loads(body)

            # 4. 从 JSON 中获取 link / url
            url = data.get('link') or data.get('url', '')
            format_type = data.get('format', 'content')

            # 5. 执行业务
            self._handle_fetch(url, format_type)

        except json.JSONDecodeError:
            self._send_error(400, 'Invalid JSON format')
        except Exception as e:
            self._send_error(400, f'Error: {str(e)}')

    def _handle_fetch(self, url, format_type):
        """处理获取文章请求"""
        # 验证URL
        if not url:
            self._send_error(400, 'Missing required parameter: link or url')
            return

        if not url.startswith('https://mp.weixin.qq.com/'):
            self._send_error(400, 'Invalid URL. Only mp.weixin.qq.com URLs are supported')
            return

        print(f"Fetching article: {url}")

        # 获取文章
        article, error = WeChatArticleExtractor.fetch_article(url)

        if article is None:
            self._send_error(500, f'Failed to fetch article: {error}')
            return

        # 统一返回格式: {success, data, error}
        result = {
            'title': article['title'],
            'author': article['author'],
            'content': article['content']
        }
        self._send_success(result, "成功")

    def _format_as_text(self, article):
        """格式化为纯文本"""
        lines = [
            '=' * 60,
            f"标题：{article['title']}",
            f"作者：{article['author']}",
            f"发布时间：{article['publish_time']}",
            f"原文链接：{article['url']}",
            '=' * 60,
            '',
            article['content'],
            '',
            '=' * 60,
            ]
        return '\n'.join(lines)

    def _format_as_markdown(self, article):
        """格式化为Markdown"""
        lines = [
            f"# {article['title']}",
            '',
            f"**作者：** {article['author']}",
            '',
            f"**发布时间：** {article['publish_time']}",
            '',
            f"**原文链接：** [{article['url']}]({article['url']})",
            '',
            '---',
            '',
            article['content'],
        ]
        return '\n'.join(lines)


def run_server(port=8080):
    """启动API服务器"""
    server_address = ('0.0.0.0', port)
    httpd = HTTPServer(server_address, APIHandler)
    print(f"=" * 60)
    print(f"微信公众号文章获取 API 服务")
    print(f"=" * 60)
    print(f"服务地址: http://0.0.0.0:{port}")
    print(f"")
    print(f"API 端点:")
    print(f"  GET  /health          - 健康检查")
    print(f"  GET  /api/fetch?link=<URL>")
    print(f"  POST /api/fetch       - 获取文章内容")
    print(f"")
    print(f"请求参数:")
    print(f"  link: 微信公众号文章链接 (必填)")
    print(f"")
    print(f"返回格式:")
    print(f"  {{")
    print(f"    'success': true,")
    print(f"    'data': {{")
    print(f"      'title': '文章标题',")
    print(f"      'author': '公众号名称',")
    print(f"      'content': '文章正文内容'")
    print(f"    }},")
    print(f"    'error': null")
    print(f"  }}")
    print(f"")
    print(f"示例:")
    print(f'  curl -X POST "http://localhost:{port}/api/fetch" \\')
    print(f'    -H "Content-Type: application/json" \\')
    print(f'    -d \'{"link": "https://mp.weixin.qq.com/s/xxxxx"}\'')
    print(f"=" * 60)
    print(f"按 Ctrl+C 停止服务")
    print(f"")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n服务已停止")
        httpd.server_close()


def main():
    parser = argparse.ArgumentParser(
        description='微信公众号文章获取 API 服务',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 启动服务 (默认端口 8080)
  python3 wechat_article_detail_api.py

  # 指定端口
  python3 wechat_article_detail_api.py --port 8888

  # 测试 API
  curl -X POST "http://localhost:8080/api/fetch" \\
    -H "Content-Type: application/json" \\
    -d '{"link": "https://mp.weixin.qq.com/s/xxxxx"}'
        """
    )
    parser.add_argument('--port', type=int, default=8080, help='服务端口 (默认: 8080)')

    args = parser.parse_args()
    run_server(args.port)


if __name__ == '__main__':
    main()