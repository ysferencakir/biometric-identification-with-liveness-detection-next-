/**
 * Kamera yardımcı fonksiyonları.
 * CameraFeed bileşeni dışında doğrudan kullanılmamalı.
 */

export async function startCamera(
  videoEl: HTMLVideoElement,
  constraints: MediaStreamConstraints = { video: { width: 640, height: 480 } }
): Promise<MediaStream> {
  const stream = await navigator.mediaDevices.getUserMedia(constraints);
  videoEl.srcObject = stream;
  await videoEl.play();
  return stream;
}

export function stopCamera(stream: MediaStream | null): void {
  stream?.getTracks().forEach((t) => t.stop());
}

/** Video elementinden tek bir kare yakalar, base64 JPEG döner. */
export function captureFrame(
  videoEl: HTMLVideoElement,
  quality = 0.85
): string | null {
  if (videoEl.readyState < HTMLMediaElement.HAVE_CURRENT_DATA) return null;

  const canvas = document.createElement("canvas");
  canvas.width = videoEl.videoWidth;
  canvas.height = videoEl.videoHeight;
  canvas.getContext("2d")?.drawImage(videoEl, 0, 0);
  // data:image/jpeg;base64,... → sadece base64 kısmı
  return canvas.toDataURL("image/jpeg", quality).split(",")[1];
}

/** Birden fazla kare yakalar (kayıt için). */
export async function captureFrames(
  videoEl: HTMLVideoElement,
  count: number,
  intervalMs = 300
): Promise<string[]> {
  const frames: string[] = [];
  for (let i = 0; i < count; i++) {
    const frame = captureFrame(videoEl);
    if (frame) frames.push(frame);
    if (i < count - 1) await new Promise((r) => setTimeout(r, intervalMs));
  }
  return frames;
}
