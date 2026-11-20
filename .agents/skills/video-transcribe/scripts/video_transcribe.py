"""Download, extract or transcribe one media input."""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


def executable(name):
    path = shutil.which(f"{name}.exe" if os.name == "nt" else name)
    if path is None:
        raise RuntimeError(f"{name} is missing from PATH. See SKILL.md for installation.")
    return path


def download(url, directory, audio_only, yt_dlp):
    command = [
        yt_dlp, "--ignore-config", "--no-playlist", "--playlist-end", "1",
        "--js-runtimes", "node", "--no-overwrites", "--no-simulate",
        "--format", "bestaudio/best" if audio_only else "bestvideo*+bestaudio/best",
        "--output", str(directory / "%(title).100B [%(id)s].%(ext)s"),
        "--print", "after_move:filepath",
    ]
    if audio_only:
        command += ["--extract-audio", "--audio-format", "best"]
    result = subprocess.run(
        [*command, "--", url], check=True, stdout=subprocess.PIPE, encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    paths = [Path(line) for line in result.stdout.splitlines() if line]
    if len(paths) != 1 or not paths[0].is_file() or paths[0].parent.resolve() != directory:
        raise RuntimeError("yt-dlp did not report a single downloaded media file.")
    return paths[0]


def extract(source, destination, ffmpeg):
    subprocess.run(
        [ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin", "-n",
         "-i", str(source), "-map", "0:a:0", "-ac", "1", "-ar", "16000",
         "-c:a", "pcm_s16le", str(destination)],
        check=True,
    )


def transcribe(source, directory, args, whisper):
    command = [
        whisper, str(source), "--model", args.model, "--task", "transcribe",
        "--output_dir", str(directory), "--output_format", "all", "--verbose", "False",
    ]
    if args.language:
        command += ["--language", args.language]
    if args.device:
        command += ["--device", args.device]
    if args.device == "cpu":
        command += ["--fp16", "False"]
    subprocess.run(command, check=True, env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    artifacts = [directory / f"{source.stem}.{ext}" for ext in ("txt", "srt")]
    if not all(path.is_file() for path in artifacts):
        raise RuntimeError("Whisper did not produce both TXT and SRT outputs.")
    return artifacts


def run(args):
    is_url = args.source.lower().startswith(("https://", "http://"))
    if args.action == "download" and not is_url:
        raise ValueError("download requires an HTTP or HTTPS URL.")
    if args.action == "extract" and is_url:
        raise ValueError("extract requires a local media file.")
    if not is_url:
        source = Path(args.source).expanduser().resolve()
        if not source.is_file():
            raise ValueError(f"Media file does not exist: {source}")

    ffmpeg = executable("ffmpeg")
    if is_url:
        executable("ffprobe")
        yt_dlp = executable("yt-dlp")
    if args.action == "transcribe":
        whisper = executable("whisper")

    output = Path(args.output_dir).expanduser().absolute()
    if output.exists():
        raise ValueError(f"Choose a new output directory: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".video-transcribe-", dir=output.parent) as temporary:
        stage = Path(temporary).resolve()
        if is_url:
            audio_only = args.action == "transcribe" or args.audio_only
            source = download(args.source, stage, audio_only, yt_dlp)
        if args.action == "download":
            artifacts = [(source, source.name)]
        elif args.action == "extract":
            wave = stage / "audio.wav"
            extract(source, wave, ffmpeg)
            artifacts = [(wave, wave.name)]
        else:
            artifacts = [
                (path, f"transcript{path.suffix}")
                for path in transcribe(source, stage, args, whisper)
            ]

        output.mkdir()
        for path, filename in artifacts:
            path.replace(output / filename)
            print(output / filename)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest="action", required=True)
    fetch = actions.add_parser("download", help="download a URL")
    fetch.add_argument("--audio-only", action="store_true", help="keep only audio")
    audio = actions.add_parser("extract", help="extract 16 kHz mono WAV from a local file")
    speech = actions.add_parser("transcribe", help="write TXT and SRT from a file or URL")
    speech.add_argument("--model", default="base", help="Whisper model (default: base)")
    speech.add_argument("--language", help="source language code, such as zh or en")
    speech.add_argument("--device", help="PyTorch device, such as cpu or cuda")
    for action in (fetch, audio, speech):
        action.add_argument("source", help="input media file or URL")
        action.add_argument("-o", "--output-dir", required=True, help="new directory for results")
    args = parser.parse_args()
    try:
        run(args)
    except (OSError, RuntimeError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"video-transcribe: {error}\n")


if __name__ == "__main__":
    main()
