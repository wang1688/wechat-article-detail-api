# 背景
    我有一个对公众号改写的服务已经上线，上线后发现获取文章详情经常被微信风控，一天甚至会出现两次无法获取微信公众号文章的情况，于是我就想办法优化，openclaw装了一个多月了，终于该他上场实战了

# 过程
    直接对话告诉openclaw，获取微信公众号“https://mp.weixin.qq.com/s/xxx”文本内容,欻欻，几秒就搞定了，于是我发现这家伙这次靠谱，于是我就接着告诉他，“将这个功能做成一个api吧，就是发给你文章链接，你返回公众号文本内容”，全部是json格式
    请求入参示例：
    {"link":"https://mp.weixin.qq.com/s/qP7DRV86j0Z1U4_kHXj8wA"}
    返回结果示例：
    {
        "code": 200,
        "data": {
                "title": "标题",
                "author": "作者",
                "content": "正文内容"
        },
        "message": "成功"
    }
# 结果
    大约1分钟就生成好了，实测也正常可用，还告诉了我怎么使用，怎么部署服务
    使用：
    curl -X POST "http://<服务器IP>:8080/api/fetch" \
    -H "Content-Type: application/json" \
    -d '{"link": "https://mp.weixin.qq.com/s/qP7DRV86j0Z1U4_kHXj8wA", "format": "content"}'


# 部署文档


    1. 安装依赖
          Copy
          pip3 install urllib3
    2. 启动服务
      Copy
      python3 wechat_article_detail_api.py --port 8080


    