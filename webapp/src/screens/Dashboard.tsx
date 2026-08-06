import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import { api, type MeOut } from "../lib/api";
import { haptic } from "../lib/telegram";
import CountUp, { Card } from "../components/CountUp";
import { FlameIcon, PlusIcon, HeartIcon, ListIcon, UserIcon } from "../components/icons";
import { gentleSpring, durations } from "../motion/presets";

export default function Dashboard() {
  const [me, setMe] = useState<MeOut | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .me()
      .then(setMe)
      .catch((e) => setError(e.message));
  }, []);

  if (error) {
    return (
      <div className="pt-20 text-center text-sm text-ink-soft">
        <p className="mb-2">نتونستم وصل بشم 😔</p>
        <p className="text-xs text-ink-faint">{error}</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-5">
      {/* Header */}
      <motion.header
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: durations.fast / 1000, ease: "easeOut" }}
        className="flex items-center justify-between"
      >
        <div>
          <h1 className="text-2xl font-extrabold">قولیار</h1>
          <p className="text-sm text-ink-soft">
            سلام {me?.user.display_name || "دوست"}! امروز چی قول می‌دی؟
          </p>
        </div>
        <Link
          to="/profile"
          onClick={() => haptic("light")}
          className="flex h-11 w-11 items-center justify-center rounded-2xl bg-card text-accent shadow-card"
        >
          <UserIcon size={22} />
        </Link>
      </motion.header>

      {/* Score hero */}
      <motion.section
        initial={{ opacity: 0, scale: 0.96 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={gentleSpring}
        className="rounded-card bg-gradient-to-br from-accent-soft to-card p-6 shadow-card"
      >
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs text-ink-soft">امتیاز اعتبار</p>
            <p className="mt-1 text-4xl font-extrabold text-accent-deep">
              {me ? <CountUp value={me.user.score} /> : "—"}
            </p>
          </div>
          <div className="flex flex-col items-center gap-1 rounded-2xl bg-card/70 px-4 py-3">
            <FlameIcon size={26} className="text-status-pending" />
            <p className="text-sm font-bold">{me ? me.user.current_streak : "—"}</p>
            <p className="text-[10px] text-ink-soft">روز متوالی</p>
          </div>
        </div>
      </motion.section>

      {/* Quick stats */}
      <motion.section
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: durations.fast / 1000, ease: "easeOut", delay: 0.1 }}
        className="grid grid-cols-3 gap-3"
      >
        <Card className="!p-3 text-center">
          <p className="text-lg font-extrabold text-status-done">{me?.stats.done ?? "—"}</p>
          <p className="mt-0.5 text-[11px] text-ink-soft">قول انجام‌شده</p>
        </Card>
        <Card className="!p-3 text-center">
          <p className="text-lg font-extrabold text-status-broken">{me?.stats.broken ?? "—"}</p>
          <p className="mt-0.5 text-[11px] text-ink-soft">قول شکسته</p>
        </Card>
        <Card className="!p-3 text-center">
          <p className="text-lg font-extrabold text-status-pending">{me?.stats.total_given ?? "—"}</p>
          <p className="mt-0.5 text-[11px] text-ink-soft">کل قول‌ها</p>
        </Card>
      </motion.section>

      {/* Lists */}
      <motion.section
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: durations.fast / 1000, ease: "easeOut", delay: 0.2 }}
        className="flex flex-col gap-3"
      >
        <Link to="/promises/self" onClick={() => haptic("light")}>
          <Card className="flex items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-status-pending">
              <HeartIcon size={22} className="text-white" />
            </div>
            <div className="flex-1">
              <p className="font-bold">قول‌های شخصی</p>
              <p className="text-xs text-ink-soft">قول‌هایی که به خودت دادی</p>
            </div>
            <span className="text-ink-faint">‹</span>
          </Card>
        </Link>
        <Link to="/promises/given" onClick={() => haptic("light")}>
          <Card className="flex items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-status-confirmed">
              <ListIcon size={22} className="text-white" />
            </div>
            <div className="flex-1">
              <p className="font-bold">قول‌های داده‌شده</p>
              <p className="text-xs text-ink-soft">قول‌هایی که به دوستان دادی</p>
            </div>
            <span className="text-ink-faint">‹</span>
          </Card>
        </Link>
        <Link to="/promises/received" onClick={() => haptic("light")}>
          <Card className="flex items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-status-done">
              <HeartIcon size={22} className="text-white" />
            </div>
            <div className="flex-1">
              <p className="font-bold">قول‌های گرفته‌شده</p>
              <p className="text-xs text-ink-soft">قول‌هایی که دوستان به تو دادند</p>
            </div>
            <span className="text-ink-faint">‹</span>
          </Card>
        </Link>
      </motion.section>

      {/* Floating + CTA */}
      <Link
        to="/new"
        onClick={() => haptic("medium")}
        className="fixed bottom-6 left-1/2 z-20 flex h-14 w-14 -translate-x-1/2 items-center justify-center rounded-full bg-accent text-white shadow-float"
        style={{ right: "auto" }}
      >
        <PlusIcon size={28} />
      </Link>
    </div>
  );
}
