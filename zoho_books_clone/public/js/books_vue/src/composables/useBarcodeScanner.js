import { ref, onMounted, onUnmounted } from "vue";

/**
 * useBarcodeScanner
 * ------------------
 * Handles two scanning input modes commonly used at a billing counter:
 *
 * 1. Hardware / USB barcode scanners — these act as a keyboard and "type"
 *    the barcode very fast, then send Enter. We listen globally and buffer
 *    keystrokes that arrive faster than a human can type; on Enter (or a
 *    short pause) we treat the buffer as a scanned code. This needs no
 *    camera permission and works with any cheap USB/Bluetooth scanner.
 *
 * 2. Phone/laptop camera — using the browser's native BarcodeDetector API
 *    (supported on Chrome/Edge/Android; not on Safari/Firefox). No extra
 *    npm dependency required. Falls back gracefully when unsupported.
 *
 * Usage:
 *   const { cameraSupported, cameraOpen, openCamera, closeCamera, videoRef }
 *     = useBarcodeScanner({ onScan: (code) => { ... } });
 */
export function useBarcodeScanner({ onScan, minLength = 3, maxKeystrokeGapMs = 40 } = {}) {
  // ── Hardware scanner (keyboard wedge) ──────────────────────────────────
  let buffer = "";
  let lastKeyTime = 0;
  let bufferTimer = null;

  function resetBuffer() {
    buffer = "";
    if (bufferTimer) { clearTimeout(bufferTimer); bufferTimer = null; }
  }

  function handleGlobalKeydown(e) {
    // Ignore while the user is typing normally in an input/textarea/select —
    // scanners fire fast enough that this still works if a dedicated
    // "scan" input is focused, but we don't want every keystroke in a
    // description box mistaken for a scan.
    const tag = (e.target?.tagName || "").toLowerCase();
    const isEditable = tag === "input" || tag === "textarea" || tag === "select" || e.target?.isContentEditable;
    const now = Date.now();
    const gap = now - lastKeyTime;
    lastKeyTime = now;

    if (e.key === "Enter") {
      if (buffer.length >= minLength) {
        const code = buffer;
        resetBuffer();
        onScan && onScan(code);
        if (isEditable) e.preventDefault();
      }
      return;
    }
    if (e.key.length !== 1) return; // ignore Shift/Tab/Arrow/etc.

    // Human typing has gaps well over ~40ms between keys; scanners fire
    // near-instantly. If we're not mid-scan and typing looks human
    // (i.e. focused in an editable field), don't start capturing.
    if (isEditable && buffer === "" && gap > maxKeystrokeGapMs) return;

    if (gap > 300) buffer = ""; // stale partial scan, start fresh
    buffer += e.key;
    if (bufferTimer) clearTimeout(bufferTimer);
    bufferTimer = setTimeout(resetBuffer, 300);
  }

  onMounted(() => window.addEventListener("keydown", handleGlobalKeydown, true));
  onUnmounted(() => { window.removeEventListener("keydown", handleGlobalKeydown, true); resetBuffer(); stopCameraStream(); });

  // ── Camera scanner ──────────────────────────────────────────────────────
  const cameraSupported = typeof window !== "undefined" && "BarcodeDetector" in window;
  const cameraOpen = ref(false);
  const cameraError = ref("");
  const videoRef = ref(null);
  let stream = null;
  let detectLoop = null;
  let detector = null;

  async function openCamera() {
    cameraError.value = "";
    if (!cameraSupported) {
      cameraError.value = "This browser doesn't support camera barcode scanning. Use a USB/Bluetooth barcode scanner instead — just scan while the item field is focused.";
      cameraOpen.value = true; // still open the modal so the message is visible
      return;
    }
    try {
      stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
      cameraOpen.value = true;
      await new Promise(r => setTimeout(r, 0)); // let v-if render the <video>
      if (videoRef.value) {
        videoRef.value.srcObject = stream;
        await videoRef.value.play();
      }
      detector = new window.BarcodeDetector({
        formats: ["ean_13", "ean_8", "upc_a", "upc_e", "code_128", "code_39", "qr_code"],
      });
      scanLoop();
    } catch (err) {
      cameraError.value = err?.message?.includes("Permission")
        ? "Camera permission denied. Allow camera access to scan, or use a USB barcode scanner."
        : "Couldn't access the camera: " + (err?.message || err);
      cameraOpen.value = true;
    }
  }

  async function scanLoop() {
    if (!cameraOpen.value || !videoRef.value || !detector) return;
    try {
      const codes = await detector.detect(videoRef.value);
      if (codes && codes.length) {
        const code = codes[0].rawValue;
        onScan && onScan(code);
        closeCamera();
        return;
      }
    } catch { /* transient decode errors are normal, keep looping */ }
    detectLoop = requestAnimationFrame(scanLoop);
  }

  function stopCameraStream() {
    if (detectLoop) cancelAnimationFrame(detectLoop);
    detectLoop = null;
    if (stream) { stream.getTracks().forEach(t => t.stop()); stream = null; }
    detector = null;
  }

  function closeCamera() {
    cameraOpen.value = false;
    stopCameraStream();
  }

  return { cameraSupported, cameraOpen, cameraError, videoRef, openCamera, closeCamera };
}
