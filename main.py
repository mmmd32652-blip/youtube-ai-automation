
import os
import uuid
import subprocess
from pathlib import Path

from flask import Flask, request, send_file, render_template_string
from gtts import gTTS
import imageio_ffmpeg

app = Flask(__name__)

WORK_DIR = Path("/tmp/story_videos")
WORK_DIR.mkdir(parents=True, exist_ok=True)

PAGE = """
<!doctype html>
<html lang="ur" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>اردو کہانی ویڈیو میکر</title>
<style>
body {background:#101827;color:white;font-family:sans-serif;
padding:20px;max-width:650px;margin:auto}
textarea,input,button {box-sizing:border-box;width:100%;padding:14px;
margin:10px 0;border-radius:8px;font-size:16px}
textarea {height:300px;line-height:2}
button {background:#16a34a;color:white;border:0;font-weight:bold}
.note {color:#cbd5e1;line-height:1.8}
</style>
</head>
<body>
<h2>🎬 اردو سبق آموز کہانی ویڈیو میکر</h2>
<p class="note">اپنی اردو کہانی نیچے لکھیں یا پیسٹ کریں۔
یہ ٹول اس کی اردو آواز اور ویڈیو تیار کرے گا۔</p>
<form method="post" action="/generate">
<textarea name="story" required minlength="100"
maxlength="7000" placeholder="یہاں اپنی کہانی لکھیں..."></textarea>
<button type="submit">ویڈیو بنائیں</button>
</form>
<p class="note">ویڈیو تیار ہونے پر ڈاؤن لوڈ کا لنک ملے گا۔
اس میں فی الحال سادہ پس منظر اور اردو آواز ہوگی۔</p>
</body>
</html>
"""

@app.get("/")
def home():
    return render_template_string(PAGE)

@app.post("/generate")
def generate():
    story = request.form.get("story", "").strip()

    if len(story) < 100:
        return "براہ کرم کم از کم 100 حروف کی کہانی لکھیں۔", 400

    if len(story) > 7000:
        return "کہانی بہت لمبی ہے۔ اسے مختصر کریں۔", 400

    job_id = uuid.uuid4().hex
    audio_path = WORK_DIR / f"{job_id}.mp3"
    video_path = WORK_DIR / f"{job_id}.mp4"

    try:
        # اردو آواز بنائیں
        gTTS(text=story, lang="ur", slow=False).save(str(audio_path))

        # آواز کے دورانیے کے مطابق عمودی ویڈیو بنائیں
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        command = [
            ffmpeg, "-y",
            "-f", "lavfi",
            "-i", "color=c=0x14213d:s=480x854:r=15",
            "-i", str(audio_path),
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "96k",
            "-shortest",
            "-movflags", "+faststart",
            str(video_path)
        ]

        subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=240
        )

        return f"""
        <!doctype html>
        <html lang="ur" dir="rtl">
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <body style="background:#101827;color:white;font-family:sans-serif;
        padding:25px;text-align:center">
        <h2>آپ کی ویڈیو تیار ہے!</h2>
        <p>نیچے والے لنک پر کلک کرکے MP4 ویڈیو حاصل کریں۔</p>
        <a style="color:#4ade80;font-size:20px"
        href="/download/{job_id}">ویڈیو ڈاؤن لوڈ کریں</a>
        <p>اب اسے خود YouTube پر اپلوڈ کر سکتے ہیں۔</p>
        <a style="color:white" href="/">واپس جائیں</a>
        </body></html>
        """

    except subprocess.TimeoutExpired:
        return "ویڈیو بنانے میں زیادہ وقت لگا۔ مختصر کہانی سے دوبارہ کوشش کریں۔", 500
    except Exception:
        app.logger.exception("Video generation failed")
        return "ویڈیو نہیں بن سکی۔ Render کے Logs میں خرابی دیکھیں۔", 500
    finally:
        if audio_path.exists():
            audio_path.unlink(missing_ok=True)

@app.get("/download/<job_id>")
def download(job_id):
    # صرف اس ایپ کے بنائے ہوئے شناختی نمبرز قبول کریں
    if len(job_id) != 32 or not all(
        c in "0123456789abcdef" for c in job_id
    ):
        return "غلط ویڈیو شناخت۔", 400

    video_path = WORK_DIR / f"{job_id}.mp4"

    if not video_path.exists():
        return "ویڈیو موجود نہیں۔ دوبارہ بنائیں۔", 404

    return send_file(
        video_path,
        as_attachment=True,
        download_name="urdu_story.mp4",
        mimetype="video/mp4"
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)
