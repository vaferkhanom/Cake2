import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { api } from "../lib/api";
import { haptic, mainButton, backButton } from "../lib/telegram";
import { BackIcon, CheckIcon, HeartIcon, ListIcon } from "../components/icons";
import { durations, easings, gentleSpring } from "../motion/presets";

type Step = 0 | 1 | 2 | 3;

export default function NewPromise() {
  const navigate = useNavigate();
  const [step, setStep] = useState<Step>(0);
  const [content, setContent] = useState("");
  const [target, setTarget] = useState<"self" | "friend">("self");
  const [receiver, setReceiver] = useState("");
  const [deadline, setDeadline] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  // Telegram BackButton support
  useEffect(() => backButton(prev), [step]);

  const next = () => {
    haptic("light");
    setStep((s) => (s < 3 ? ((s + 1) as Step) : s));
  };
  const prev = () => {
    haptic("light");
    if (step === 0) {
      navigate("/");
    } else {
      setStep((s) => (s - 1) as Step);
    }
  };

  const submit = async () => {
    setBusy(true);
    try {
      await api.createPromise({
        content,
        target_type: target,
        ...(target === "friend" ? { receiver_username: receiver } : {}),
        ...(deadline ? { deadline: new Date(deadline).toISOString() } : {}),
      });
      haptic("medium", "success");
      navigate("/");
    } catch (e: any) {
      haptic("medium", "error");
      setError(e?.message || "خطا در ثبت");
      setBusy(false);
    }
  };

  const canNext =
    step === 0 ? content.trim().length >= 3 : step === 2 ? target === "self" || receiver.trim().length > 0 : true;

  // Telegram MainButton with cleanup + validation guard
  useEffect(() => {
    return mainButton(step === 3 ? "ثبت قول" : "ادامه", () => {
      if (!canNext || busy) return;
      return step === 3 ? submit() : next();
    });
  }, [step, canNext, busy]);

  return (
    <div className="flex flex-col gap-4">
      <header className="flex items-center gap-3">
        <button
          onClick={prev}
          className="flex h-10 w-10 items-center justify-center rounded-2xl bg-card text-ink shadow-card"
        >
          <BackIcon size={20} />
        </button>
        <h1 className="text-xl font-extrabold">قول جدید</h1>
      </header>

      {/* Progress bar */}
      <div className="h-1.5 overflow-hidden rounded-full bg-bg-soft">
        <motion.div
          className="h-full rounded-full bg-accent"
          animate={{ width: `${((step + 1) / 4) * 100}%` }}
          transition={gentleSpring}
        />
      </div>

      <AnimatePresence mode="wait">
        {step === 0 && (
          <StepWrap key="s0">
            <label className="mb-2 block text-sm font-bold text-ink-soft">قولت چیه؟ ✍️</label>
            <textarea
              autoFocus
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="مثلاً: قول می‌دم هر روز ۲۰ دقیقه کتاب بخونم…"
              className="min-h-32 w-full resize-none rounded-card border-0 bg-card p-4 text-ink shadow-card outline-none placeholder:text-ink-faint"
            />
          </StepWrap>
        )}
        {step === 1 && (
          <StepWrap key="s1">
            <label className="mb-2 block text-sm font-bold text-ink-soft">برای کی؟</label>
            <div className="flex flex-col gap-3">
              <TargetOption
                active={target === "self"}
                onClick={() => { setTarget("self"); next(); }}
                icon={<HeartIcon size={22} />}
                title="برای خودم"
                subtitle="قول شخصی — فقط من و خودم"
              />
              <TargetOption
                active={target === "friend"}
                onClick={() => { setTarget("friend"); next(); }}
                icon={<ListIcon size={22} />}
                title="برای یک دوست"
                subtitle="قول دوطرفه — اون هم باید تایید کنه"
              />
            </div>
          </StepWrap>
        )}
        {step === 2 && (
          <StepWrap key="s2">
            {target === "friend" && (
              <>
                <label className="mb-2 block text-sm font-bold text-ink-soft">یوزرنیم دوستت</label>
                <input
                  autoFocus
                  value={receiver}
                  onChange={(e) => setReceiver(e.target.value.replace("@", ""))}
                  placeholder="username"
                  dir="ltr"
                  className="w-full rounded-card border-0 bg-card p-4 text-left text-ink shadow-card outline-none placeholder:text-ink-faint"
                />
              </>
            )}
            <label className="mb-2 mt-4 block text-sm font-bold text-ink-soft">
              مهلت (اختیاری)
            </label>
            <input
              type="date"
              value={deadline}
              onChange={(e) => setDeadline(e.target.value)}
              className="w-full rounded-card border-0 bg-card p-4 text-ink shadow-card outline-none"
            />
          </StepWrap>
        )}
        {step === 3 && (
          <StepWrap key="s3">
            <div className="rounded-card bg-card p-5 shadow-card">
              <p className="mb-3 text-xs text-ink-soft">خلاصه قول:</p>
              <p className="mb-4 text-base font-bold leading-7">{content}</p>
              <div className="flex items-center gap-2 text-sm text-ink-soft">
                {target === "self" ? <HeartIcon size={16} /> : <ListIcon size={16} />}
                {target === "self" ? "قول شخصی" : `برای @${receiver || "؟"}`}
                {deadline && <span className="text-ink-faint">· {deadline}</span>}
              </div>
            </div>
            {error && <p className="text-center text-sm text-status-broken">{error}</p>}
            {busy && <p className="text-center text-sm text-ink-soft">در حال ثبت…</p>}
          </StepWrap>
        )}
      </AnimatePresence>

      {/* In-app CTA (works outside Telegram too) */}
      <button
        disabled={!canNext || busy}
        onClick={() => (step === 3 ? submit() : next())}
        className="mt-2 flex w-full items-center justify-center gap-2 rounded-2xl bg-accent py-3.5 text-sm font-bold text-white disabled:opacity-40"
      >
        <CheckIcon size={18} />
        {step === 3 ? "ثبت قول" : "ادامه"}
      </button>
    </div>
  );
}

function StepWrap({ children }: { children: React.ReactNode }) {
  return (
    <motion.div
      initial={{ opacity: 0, x: -40 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 40 }}
      transition={{ duration: durations.normal / 1000, ease: easings.standard }}
    >
      {children}
    </motion.div>
  );
}

function TargetOption({
  active,
  onClick,
  icon,
  title,
  subtitle,
}: {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  title: string;
  subtitle: string;
}) {
  return (
    <motion.button
      whileTap={{ scale: 0.96 }}
      transition={{ duration: 0.1 }}
      onClick={onClick}
      className={`flex items-center gap-4 rounded-card p-4 text-right shadow-card transition-colors ${
        active ? "bg-accent-soft ring-2 ring-accent" : "bg-card"
      }`}
    >
      <div className={`flex h-12 w-12 items-center justify-center rounded-2xl ${active ? "bg-accent" : "bg-bg-soft"} ${active ? "text-white" : "text-ink-soft"}`}>
        {icon}
      </div>
      <div className="flex-1">
        <p className="font-bold">{title}</p>
        <p className="text-xs text-ink-soft">{subtitle}</p>
      </div>
    </motion.button>
  );
}
