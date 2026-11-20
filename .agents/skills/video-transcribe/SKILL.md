---
name: video-transcribe
description: 使用 yt-dlp、FFmpeg 和本地 OpenAI Whisper 下载单个视频或音频、从本地媒体提取音轨，或把视频链接与本地音视频转成纯文本和 SRT 字幕。适用于视频下载、音频提取、逐字稿和字幕制作。
---

# 视频下载与转写

使用 [scripts/video_transcribe.py](scripts/video_transcribe.py) 处理用户提供的单个链接或本地文件。以下命令从 Skill 目录执行。为每次任务指定一个新输出目录，避免覆盖已有结果。

| 任务 | 命令 |
| --- | --- |
| 下载视频 | `python scripts/video_transcribe.py download "https://example.com/video" -o ./download` |
| 从链接下载音轨 | `python scripts/video_transcribe.py download "https://example.com/video" --audio-only -o ./download-audio` |
| 从本地媒体提取音频 | `python scripts/video_transcribe.py extract "./input.mp4" -o ./audio` |
| 转写本地音视频 | `python scripts/video_transcribe.py transcribe "./input.mp4" --language zh -o ./transcript` |
| 转写在线视频 | `python scripts/video_transcribe.py transcribe "https://example.com/video" -o ./transcript` |

- 下载时优先选择带音频的视频，必要时由 FFmpeg 合并音视频。音轨下载保留源音频格式。链接指向播放列表时最多处理一项。
- 提取音频输出 16 kHz 单声道 PCM WAV。转写默认使用多语言 `base` 模型，输出 `transcript.txt` 和 `transcript.srt`。省略 `--language` 时自动检测语言。可用 `--model small` 指定模型，或用 `--device cpu` 指定 CPU。
- 链接转写先下载音轨到临时目录，由 Whisper 调用 FFmpeg 解码。首次使用某个模型时会下载权重，转写在本机执行。
- 运行完成后检查输出路径及字幕时间轴。纯文本为空时检查音轨是否有人声、语言是否正确，再决定是否重试。用户仅需官方字幕时，可先用 `yt-dlp --list-subs URL` 查看可用字幕。

## 安装依赖

先检查 `yt-dlp --version`、`ffmpeg -version`、`ffprobe -version` 和 `whisper --help`，按需补装。新环境可使用 Python 3.11，并将三个工具的命令目录加入 PATH。

```sh
python -m pip install -U "yt-dlp[default]" openai-whisper
```

- FFmpeg 在 Windows 可用 `winget install --id Gyan.FFmpeg -e`，macOS 可用 `brew install ffmpeg`，Debian / Ubuntu 可用 `sudo apt install ffmpeg`。安装后重新打开终端。
- YouTube 下载还需要受支持的 JavaScript 运行时。yt-dlp 默认启用 Deno，本脚本也启用 PATH 上的 Node.js。
- 上游文档：[yt-dlp](https://github.com/yt-dlp/yt-dlp#dependencies)、[YouTube JavaScript 依赖](https://github.com/yt-dlp/yt-dlp/wiki/EJS)、[FFmpeg](https://ffmpeg.org/download.html)、[OpenAI Whisper](https://github.com/openai/whisper#setup)。
