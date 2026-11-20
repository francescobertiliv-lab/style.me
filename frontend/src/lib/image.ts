// Prepara la foto sul telefono: la rimpicciolisce e la scontorna nel browser.
// Lo scontorno usa un modello che gira in locale (scaricato la prima volta, poi in cache):
// la foto non va da nessuna parte prima di arrivare al tuo server.

export async function resize(file: Blob, maxSide = 1600, type = "image/jpeg"): Promise<Blob> {
  const bitmap = await createImageBitmap(file);
  const scale = Math.min(1, maxSide / Math.max(bitmap.width, bitmap.height));
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(bitmap.width * scale);
  canvas.height = Math.round(bitmap.height * scale);
  canvas.getContext("2d")!.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
  return new Promise((ok) => canvas.toBlob((b) => ok(b!), type, 0.88));
}

export async function cutout(photo: Blob, onProgress?: (msg: string) => void): Promise<Blob | null> {
  try {
    onProgress?.("Scontorno il capo…");
    const { removeBackground } = await import("@imgly/background-removal");
    const small = await resize(photo, 1024, "image/png");
    return await removeBackground(small, { output: { format: "image/png" } });
  } catch {
    return null; // il server toglierà almeno lo sfondo bianco
  }
}
