// 图片工具：上传前 canvas 压缩（手机原图常 10MB+）
interface CompressOpts {
  maxW?: number;
  maxH?: number;
  quality?: number;
}

export function compressImage(file: File, opts: CompressOpts = {}): Promise<Blob> {
  const { maxW = 1200, maxH = 1600, quality = 0.82 } = opts;
  return new Promise((resolve, reject) => {
    const img = new Image();
    const url = URL.createObjectURL(file);
    img.onload = () => {
      try {
        const ratio = Math.min(1, maxW / img.width, maxH / img.height);
        const w = Math.max(1, Math.round(img.width * ratio));
        const h = Math.max(1, Math.round(img.height * ratio));
        const canvas = document.createElement('canvas');
        canvas.width = w;
        canvas.height = h;
        const ctx = canvas.getContext('2d');
        if (!ctx) throw new Error('canvas 不可用');
        ctx.drawImage(img, 0, 0, w, h);
        canvas.toBlob(
          (blob) => {
            URL.revokeObjectURL(url);
            if (blob) {
              return resolve(blob);
            }
            reject(new Error('图片处理失败'));
          },
          'image/jpeg',
          quality,
        );
      } catch (e) {
        URL.revokeObjectURL(url);
        reject(e as Error);
      }
    };
    img.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error('图片读取失败'));
    };
    img.src = url;
  });
}