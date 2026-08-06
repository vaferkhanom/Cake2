import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { api, type PromiseOut } from "../lib/api";
import { haptic, backButton } from "../lib/telegram";
import { statusTheme } from "../components/PromiseCard";
import Confetti from "../components/Confetti";
import { BackIcon, CheckIcon, BrokenHeartIcon, AlertIcon, ClockIcon, SparkleIcon } from "../components/icons";
import { donePop, durations } from "../motion/presets";

export default function PromiseDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [promise, setPromise] = useState<PromiseOut | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [celebrate, setCelebrate] = useState(false);

  useEffect(() => backButton(() => navigate(-1)), [navigate]);

  const load = useCallback(() => {
    api
      .getPromise(Number(id))
      .then(setPromise)
      .catch((e) => setError(e.message));
  }, [id]);

  useEffect(load, [load]);

  if (error) {
    return (
      <div className="pt-20 text-center">
        <p className="mb-2 text-ink-soft dark:text-ink-darkSoft">{error}</p>
        <Link to="/" className="text-accent-deep text-sm font-bold">بازگشت</Link>
      </div>
    );
  }
  if (!promise) {
    return (
      <div className="flex flex-col gap-3 pt-4">
        <div className="skeleton h-44" />
        <div className="skeleton h-16" />
      </div>
    );
  }

  const t = statusTheme(promise.status);
  const Icon = t.icon;

  const run = async (fn: () => Promise<unknown>) => {
    setBusy(true);
    try {
      await fn();
      await load();
    } catch (e: any) {
      haptic("medium", "error");
      setError(e?.message || "خطا");
    } finally {
      setBusy(false);
    }
  };

  const doClaim = () =>
    run(async () => {
      await api.claimDone(promise!.id);
      haptic("medium", "success");
    });

  const doBroken = () =>
    run(async () => {
      await api.broken(promise!.id);
      haptic("medium", "warning");
    });

  const doConfirm = () =>
    run(async () => {
      await api.confirmDone(promise!.id);
      setCelebrate(true);
      haptic("medium", "success");
      setTimeout(() => setCelebrate(false), 1200);
    });

  const doDispute = () =>
    run(async () => {
      await api.dispute(promise!.id);
      haptic("medium", "warning");
    });

  const doResolve = () =>
    run(async () => {
      await api.resolveDispute(promise!.id);
      setCelebrate(true);
      haptic("medium", "success");
      setTimeout(() => setCelebrate(false), 1200);
    });

  const isDone = promise.status === "done";

  return (
    <div className="relative flex flex-col gap-4">
      {/* Header */}
      <header className="flex items-center gap-3">
        <Link
          to={`/promises/${promise.is_giver ? "given" : "received"}`}
          onClick={() => haptic("light")}
          className="flex h-10 w-10 items-center justify-center rounded-2xl bg-card text-ink dark:bg-card-dark dark:text-ink-dark shadow-card dark:shadow-cardDark"
        >
          <BackIcon size={20} />
        </Link>
        <h1 className="text-xl font-extrabold text-ink dark:text-ink-dark">جزئیات قول</h1>
      </header>

      {/* Hero card */}
      <motion.div
        key={promise.status + (isDone ? "-done" : "")}
        layoutId={`promise-${promise.id}`}
        initial={{ opacity: 0, scale: 0.96 }}
        animate={isDone ? { scale: [0, 1.15, 1] } : { opacity: 1, scale: 1 }}
        transition={isDone ? donePop.transition : { duration: 0.25, ease: "easeOut" }}
        className={`relative overflow-hidden rounded-card bg-card p-6 shadow-card dark:bg-card-dark dark:shadow-cardDark ${
          isDone ? "ring-4 ring-status-done/40" : ""
        }`}
      >
        <Confetti active={celebrate} />
        <div className="mb-4 flex items-center gap-3">
          <motion.div
            animate={
              promise.status === "broken" || promise.status === "disputed"
                ? { x: [0, -4, 4, -4, 0] }
                : {}
            }
            className={`flex h-12 w-12 items-center justify-center rounded-2xl ${t.color}`}
          >
            <Icon size={24} className="text-white" />
          </motion.div>
          <div>
            <p className={`text-sm font-bold ${t.text}`}>{promise.status_text}</p>
            <p className="text-[11px] text-ink-soft dark:text-ink-darkSoft">{promise.jalali_created_at}</p>
          </div>
        </div>
        <p className="text-lg font-bold leading-8 text-ink dark:text-ink-dark">{promise.content}</p>
        {promise.jalali_deadline && (
          <p className="mt-3 flex items-center gap-1.5 text-sm text-ink-soft dark:text-ink-darkSoft">
            <ClockIcon size={16} /> مهلت: {promise.jalali_deadline}
          </p>
        )}
        {promise.target_type === "friend" && (
          <p className="mt-2 text-sm text-ink-soft dark:text-ink-darkSoft">
            {promise.is_giver ? `گیرنده: ${promise.receiver_name}` : `قول‌دهنده: ${promise.giver_name}`}
          </p>
        )}
      </motion.div>

      {/* Context-aware actions */}
      <AnimatePresence mode="wait">
        <motion.div
          key={promise.status}
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 8 }}
          transition={{ duration: durations.fast / 1000, ease: "easeOut" }}
          className="flex flex-col gap-3"
        >
          {/* giver: CONFIRMED → claim done / admit broken */}
          {promise.is_giver && promise.status === "confirmed" && (
            <>
              <ActionButton variant="primary" disabled={busy} onClick={doClaim} icon={CheckIcon}>
                انجامش دادم
              </ActionButton>
              <ActionButton variant="danger" disabled={busy} onClick={doBroken} icon={BrokenHeartIcon}>
                نشد، بشکنم
              </ActionButton>
            </>
          )}

          {/* receiver: CLAIMED_DONE → confirm / dispute */}
          {promise.is_receiver && promise.status === "claimed_done" && (
            <>
              <ActionButton variant="primary" disabled={busy} onClick={doConfirm} icon={CheckIcon}>
                تایید می‌کنم، انجام شده
              </ActionButton>
              <ActionButton variant="danger" disabled={busy} onClick={doDispute} icon={AlertIcon}>
                قبول ندارم، ردش می‌کنم
              </ActionButton>
            </>
          )}

          {/* receiver: DISPUTED → resolve */}
          {promise.is_receiver && promise.status === "disputed" && (
            <ActionButton variant="primary" disabled={busy} onClick={doResolve} icon={SparkleIcon}>
              باشه، تایید می‌کنم
            </ActionButton>
          )}

          {/* no actions */}
          {(promise.status === "done" || promise.status === "broken" || promise.status === "expired") && (
            <p className="pt-2 text-center text-sm text-ink-soft dark:text-ink-darkSoft">
              {promise.status === "done"
                ? "آفرین! این قول به سرانجام رسید 🎉"
                : promise.status === "broken"
                ? "دفعه بعد حتماً انجامش می‌دی 💪"
                : "مهلت این قول گذشته."}
            </p>
          )}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}

function ActionButton({
  variant,
  icon: Icon,
  children,
  ...rest
}: {
  variant: "primary" | "danger";
  icon: React.ComponentType<{ size?: number; className?: string }>;
  children: React.ReactNode;
  disabled?: boolean;
  onClick?: () => void;
}) {
  const colors =
    variant === "primary" ? "bg-accent text-white" : "bg-status-broken/30 text-status-broken";
  return (
    <motion.button
      whileTap={{ scale: 0.96 }}
      transition={{ duration: 0.1 }}
      {...rest}
      className={`flex w-full items-center justify-center gap-2 rounded-2xl py-3.5 text-sm font-bold disabled:opacity-50 ${colors}`}
    >
      <Icon size={18} />
      {children}
    </motion.button>
  );
}
