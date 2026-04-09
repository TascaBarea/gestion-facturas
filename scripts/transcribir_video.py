"""Transcribe audio from a video file using faster-whisper."""
import sys
import time
from pathlib import Path
from faster_whisper import WhisperModel


def format_timestamp(seconds: float) -> str:
    """Convert seconds to HH:MM:SS format."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def transcribir(video_path: str, modelo: str = "medium", idioma: str = "es"):
    """Transcribe video audio and save as .txt next to the video."""
    video = Path(video_path)
    if not video.exists():
        print(f"ERROR: No se encuentra el archivo: {video}")
        sys.exit(1)

    output_txt = video.with_suffix(".txt")

    print(f"Cargando modelo '{modelo}' (primera vez descarga ~1.5GB)...")
    t0 = time.time()
    model = WhisperModel(modelo, device="cpu", compute_type="int8")
    print(f"Modelo cargado en {time.time() - t0:.1f}s")

    print(f"Transcribiendo: {video.name}")
    t0 = time.time()
    segments, info = model.transcribe(
        str(video),
        language=idioma,
        beam_size=5,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500),
    )

    lines = []
    full_text_parts = []
    for segment in segments:
        ts = f"[{format_timestamp(segment.start)} - {format_timestamp(segment.end)}]"
        line = f"{ts} {segment.text.strip()}"
        lines.append(line)
        full_text_parts.append(segment.text.strip())
        print(line)

    elapsed = time.time() - t0
    print(f"\nTranscripción completada en {elapsed:.1f}s")
    print(f"Idioma detectado: {info.language} (prob: {info.language_probability:.2f})")

    # Save timestamped version
    output_txt.write_text("\n".join(lines), encoding="utf-8")
    print(f"Guardado con timestamps: {output_txt}")

    # Save plain text version
    output_plain = video.with_name(video.stem + "_texto.txt")
    output_plain.write_text("\n\n".join(full_text_parts), encoding="utf-8")
    print(f"Guardado texto plano:    {output_plain}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python transcribir_video.py <ruta_video> [modelo] [idioma]")
        print("  modelo: tiny, base, small, medium (default), large-v3")
        print("  idioma: es (default), en, fr, etc.")
        sys.exit(1)

    video = sys.argv[1]
    modelo = sys.argv[2] if len(sys.argv) > 2 else "medium"
    idioma = sys.argv[3] if len(sys.argv) > 3 else "es"
    transcribir(video, modelo, idioma)
