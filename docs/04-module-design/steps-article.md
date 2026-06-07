# 文章 / 播客分析步骤

网页文章、公众号文章、播客/音频的入库步骤链。相比视频无需截图与 OCR，链路更短。

## article pipeline（网页 / 公众号文章）

```
00_download → 16_parse_article → 17_article_sections → 18_smart_article → 19_review
```

| 步骤 | 池 | 说明 |
|------|----|------|
| 00_download | io | 抓取原始 HTML（http_article 源） |
| 16_parse_article | cpu | trafilatura 抽正文纯文本 + 元数据（title/author/date） |
| 17_article_sections | cpu | 纯文本按标题切分为章节树 |
| 18_smart_article | ai | 生成结构化笔记 |
| 19_review | ai | 质量评审 + 缺漏概念回收 |

## audio pipeline（单集播客 / 上传音频）

```
00_download → 00b_whisper → 20_transcript_parse → 21_smart_podcast → 22_review
```

| 步骤 | 池 | 说明 |
|------|----|------|
| 00_download | io | 下载音频 URL 或接收上传，桥接为 source.mp4 |
| 00b_whisper | gpu | 复用 video 的 whisper 转写（GPU 满回退 CPU base/int8） |
| 20_transcript_parse | cpu | SRT → 时间分段 |
| 21_smart_podcast | ai | 口语转写转结构化笔记 |
| 22_review | ai | 质量评审 |

## 与其它内容类型的复用

- 共用 StepBase、调度器、Worker 框架与资源池
- 共用 00_download（按源类型分支：http_article / podcast）
- audio 直接复用 video 的 00b_whisper
- smart / review 步复用 Prompt 模板结构
