import { useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { useModal } from '../modal/ModalContext';
import { useToast } from '../toast';
import { useTemplates } from '../api/hooks';
import { generationApi } from '../api/generation';
import type { User } from '../types';
import Uploader from '../components/Uploader';
import TemplatePicker from '../components/TemplatePicker';
import PromptInput from '../components/PromptInput';
import QuantitySelector from '../components/QuantitySelector';

export default function WorkspacePage() {
  const { user } = useAuth();
  const { showLogin, showPay } = useModal();
  const toast = useToast();
  const navigate = useNavigate();
  const templates = useTemplates();

  const userRef = useRef<User | null>(null);
  userRef.current = user;

  const [selfie, setSelfie] = useState<{ key: string; url: string | null } | null>(null);
  const [reference, setReference] = useState<{ key: string; url: string | null } | null>(null);
  const [templateId, setTemplateId] = useState<number | null>(null);
  const [prompt, setPrompt] = useState('');
  const [quantity, setQuantity] = useState(1);
  const [submitting, setSubmitting] = useState(false);

  const template = templates.data?.items.find((t) => t.id === templateId);
  const ready = !!selfie && (!!templateId || prompt.trim().length > 0);

  const submit = async () => {
    const u = userRef.current;
    if (!u) {
      showLogin();
      return;
    }
    if (!selfie) {
      toast('先上传一张自拍', 'error');
      return;
    }
    const isTrial = !u.trial_used;
    if (!isTrial && !u.unlocked) {
      showPay({ orderType: 'unlock', onPaid: () => void submit() });
      return;
    }
    if (!isTrial && u.credits < quantity) {
      showPay({ orderType: 'recharge', amount: 5000, onPaid: () => void submit() });
      return;
    }

    setSubmitting(true);
    try {
      const data = await generationApi.create(
        {
          selfie_key: selfie.key,
          reference_key: reference?.key ?? null,
          template_id: templateId,
          prompt: prompt.trim() || null,
          quantity,
        },
        crypto.randomUUID(),
      );
      navigate(`/result/${data.generation_id}`);
    } catch (e) {
      toast((e as Error).message || '生成失败', 'error');
    }
    setSubmitting(false);
  };

  const pickTemplate = (id: number) => {
    setTemplateId((prev) => (prev === id ? null : id));
    const t = templates.data?.items.find((x) => x.id === id);
    if (t) setPrompt(t.prompt_template);
  };

  return (
    <div className="workspace">
      <section className="block">
        <div className="section-title">
          1. 上传自拍
          <span className="muted">正面清晰、五官可见</span>
        </div>
        <div className="upload-row">
          <Uploader
            kind="selfie"
            label="自拍原图"
            hint="点此上传 / 拍照"
            value={selfie?.key ?? null}
            previewUrl={selfie?.url ?? null}
            onChange={(key) => setSelfie({ key, url: null })}
          />
          <Uploader
            kind="reference"
            label="风格参考（选填）"
            hint="喜欢的穿搭/场景照"
            value={reference?.key ?? null}
            previewUrl={reference?.url ?? null}
            onChange={(key) => setReference({ key, url: null })}
          />
        </div>
        <p className="note">AI 只优化穿搭、光线、环境，不改变五官。</p>
      </section>

      <TemplatePicker value={templateId} onPick={pickTemplate} />

      {template?.prompt_tips && <p className="note">{template.prompt_tips}</p>}

      <PromptInput value={prompt} onChange={setPrompt} />

      <QuantitySelector value={quantity} onChange={setQuantity} />

      <div className="generate-bar">
        <button className="btn btn--gold btn--lg btn--block" disabled={!ready || submitting} onClick={() => void submit()}>
          {submitting ? '提交中…' : user ? (user.trial_available ? '免费生成这张' : `生成（将扣 ${quantity} 次）`) : '登录后免费生成'}
        </button>
        {user && (
          <p className="muted center">
            剩余 <b>{user.credits}</b> 次 · {user.trial_available ? '本次免费体验' : user.unlocked ? '已解锁' : '未解锁'}
          </p>
        )}
      </div>
    </div>
  );
}