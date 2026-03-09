# Gecko Notes

一个由 Markdown 驱动的静态个人博客。

## 你以后只需要管这几个文件夹

- `content/software-hardware/`：软硬件、工具、设备、折腾记录
- `content/contract-trading/`：合约交易、策略、复盘、风控
- `content/project-lab/`：项目实验、工具开发、想法验证
- `content/weekly-notes/`：周记、随笔、观察记录

往这些文件夹里直接放 `.md` 文件就行。

## 生成站点

运行下面这条命令会自动把 Markdown 生成成首页、分类页和文章页：

```powershell
python scripts/build_blog.py
```

## Markdown 写法

最简单的写法就是直接从一级标题开始：

```md
# 文章标题

这里写正文。
```

脚本会自动从文件名和正文里提取标题、摘要和时间。

## 站点结构

- `blog_config.json`：站点标题、分区配置
- `scripts/build_blog.py`：Markdown 生成脚本
- `index.html`：自动生成的首页
- `categories/`：自动生成的板块页面
- `posts/`：自动生成的文章页面
- `assets/`：样式和脚本

## 发布方式

站点仍然部署在 GitHub Pages 上。以后你把 `.md` 放进内容目录后，我帮你执行生成并推送到 GitHub 就可以了。
