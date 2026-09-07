import { useRef, useState } from 'react';
import { uploadApi, uploadRaw } from '../api/upload';
import { compressImage } from '../utils/image';
import { useToast } from '../toast';

interface Props {
  kind: 'selfie' | 'reference';
  label: string;
  hint?: string;
  value: string | null;
  previewUrl?: string | null;
  onChange: (key: string) => void;
}

export default function Uploader({ kind, label, hint, value, previewUrl, onChange }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const toast = useToast();
  const [localPreview, setLocalPreview] = useState<string | null>(null);

  const pick = async (file: File) => {
    setBusy(true);
    try {
      const blob = await compressImage(file, { maxW: 1200, maxH: 1700, quality: 0.82 });
      const target = await uploadApi.presign(kind, blob.type || 'image/jpeg', blob.size);
      await uploadRaw(target, blob);
      setLocalPreview(URL.createObjectURL(blob));
      onChange(target.object_key);
    } catch (e) {
      toast((e as Error).message || '上传失败', 'error');
    }
    setBusy(false);
  };

  const show = value ? (previewUrl ?? localPreview) : null;

  return (
    <div className={`uploader ${busy ? 'is-busy' : ''} ${show ? 'has-img' : ''}`} onClick={() => inputRef.current?.click()}>
      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp,image/heic"
        hidden
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) void pick(f);
          e.target.value = '';
        }}
      />
      {show ? (
        <img src={show} alt={label} />
      ) : (
        <div className="uploader-empty">
          <span className="plus">＋</span>
          <b>{label}</b>
          <i>{busy ? '上传中…' : hint ?? '点击选择/拍照'}</i>
        </div>
      )}
      {show && <span className="uploader-tag">{busy ? '上传中…' : '点击更换'}</span>}
    </div>
  );
}