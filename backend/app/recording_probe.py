"""Bounded media validation; no transcription or invented media metadata."""

import json
import math
import subprocess
import wave


def inspect_recording(path, mime):
    if mime == "audio/wav":
        try:
            with wave.open(str(path), "rb") as recording:
                duration = recording.getnframes() / recording.getframerate()
                if duration <= 0:
                    raise ValueError("Empty recording")
                expected_bytes = (
                    recording.getnframes() * recording.getnchannels() * recording.getsampwidth()
                )
                if expected_bytes > path.stat().st_size or len(
                    recording.readframes(recording.getnframes())
                ) != expected_bytes:
                    raise ValueError("Truncated WAV recording")
                return {"duration_seconds": duration, "probe": "wave", "codec": "pcm"}
        except (wave.Error, EOFError, ZeroDivisionError):
            raise ValueError("Unsupported WAV recording") from None
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-protocol_whitelist",
                "file",
                "-show_entries",
                "format=duration,format_name:stream=codec_name,codec_type,width,height,channels,sample_rate",
                "-of",
                "json",
                str(path),
            ],
            capture_output=True,
            check=True,
            timeout=15,
        )
        report = json.loads(result.stdout)
        duration = float(report["format"]["duration"])
        streams = report["streams"]
        formats = report["format"]["format_name"].split(",")
        if (mime == "audio/mpeg" and "mp3" not in formats) or (
            mime == "video/mp4" and "mp4" not in formats
        ):
            raise ValueError("Recording container does not match declared format")
        expected = "video" if mime == "video/mp4" else "audio"
        if (
            not math.isfinite(duration)
            or duration <= 0
            or not any(s["codec_type"] == expected for s in streams)
        ):
            raise ValueError("Missing expected media stream")
        allowed = {"mp3"} if mime == "audio/mpeg" else {"h264", "aac"}
        if any(s["codec_name"] not in allowed for s in streams):
            raise ValueError("Use MP3 or H.264/AAC MP4 for browser playback")
        return {"duration_seconds": duration, "probe": "ffprobe", "streams": streams}
    except (OSError, subprocess.SubprocessError, KeyError, json.JSONDecodeError):
        raise ValueError("Media validation failed; check format and ffprobe availability") from None
