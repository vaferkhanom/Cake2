import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { api, type MeOut } from "../lib/api";
import { haptic, backButton } from "../lib/telegram";
import CountUp from "../components/CountUp";
import { BackIcon, FlameIcon, HeartIcon, SparkleIcon } from "../components/icons";
import { gentleSpring, durations } from "../motion/presets";

export default function Profile() {
  const [me, setMe] = useState<MeOut | null>(null);

  useEffect(() => backButton(() => history.back()), []);
  useEffect(() => {
    api.me().then(setMe).catch(() => {});
  }, []);

  if (!me) {
    return (
      <div className="flex flex-col gap-3 pt-4">
        <div className="skeleton h-36" />
        <div className="skeleton h-24" />
      </div>
    );
  }

  const done = me.stats.done;
  const broken = me.stats.broken;
  const total = me.stats.total_given;
  const rate = total > 0 ? Math.round((done / total) * 100) : 0;

  return (
    <div className="flex flex-col gap-4">
      <header className="flex items-center gap-3">
        <Link
          to="/"
          onClick={() => haptic("light")}
          className="flex h-10 w-10 items-center justify-center rounded-2xl bg-card text-ink shadow-card"
        >
          <BackIcon size={20} />
        </Link>
        <h1 className="text-xl font-extrabold">پروفایل</h1>
      </header>

      {/* User card */}
      <motion.section
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={gentleSpring}
        className="rounded-card bg-gradient-to-br from-accent-soft to-card p-6 shadow-card"
      >
        <div className="flex items-center gap-4">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-accent text-2xl font-extrabold text-white">
            {me.user.display_name.slice(0, 1).toUpperCase()}
          </div>
          <div className="flex-1">
            <p className="text-lg font-extrabold">{me.user.display_name}</p>
            <p className="text-xs text-ink-soft">
              {me.user.username ? `@${me.user.username}` : "کاربر قولیار"}
            </p>
          </div>
        </div>
      </motion.section>

      {/* Score row */}
      <motion.section
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: durations.fast / 1000, ease: "easeOut", delay: 0.08 }}
        className="grid grid-cols-2 gap-3"
      >
        <div className="rounded-card bg-card p-5 text-center shadow-card">
          <p className="text-xs text-ink-soft">امتیاز اعتبار</p>
          <p className="mt-1 text-3xl font-extrabold text-accent-deep">
            <CountUp value={me.user.score} />
          </p>
        </div>
        <div className="rounded-card bg-card p-5 text-center shadow-card">
          <p className="flex items-center justify-center gap-1 text-xs text-ink-soft">
            <FlameIcon size={13} className="text-status-pending" /> استریک
          </p>
          <p className="mt-1 text-3xl font-extrabold text-status-pending">
            <CountUp value={me.user.current_streak} />
          </p>
        </div>
      </motion.section>

      {/* Trend viz */}
      <motion.section
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: durations.fast / 1000, ease: "easeOut", delay: 0.16 }}
        className="rounded-card bg-card p-5 shadow-card"
      >
        <p className="mb-4 text-sm font-bold">عملکرد</p>
        <div className="mb-2 flex h-3 overflow-hidden rounded-full bg-bg-soft">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${rate}%` }}
            transition={gentleSpring}
            className="bg-status-done"
          />
        </div>
        <div className="flex items-center justify-between text-xs text-ink-soft">
          <span className="flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded-full bg-status-done" />
            {done} انجام‌شده
          </span>
          <span className="flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded-full bg-status-broken" />
            {broken} شکسته
          </span>
        </div>
        <div className="mt-4 flex items-center justify-center gap-2 rounded-2xl bg-bg-soft py-3 text-sm text-ink-soft">
          <SparkleIcon size={16} className="text-accent" />
          نرخ موفقیت: {rate}٪
        </div>
      </motion.section>

      {/* About */}
      <motion.section
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: durations.fast / 1000, ease: "easeOut", delay: 0.24 }}
        className="flex items-center justify-center gap-2 rounded-card bg-card py-4 text-xs text-ink-faint shadow-card"
      >
        <HeartIcon size={14} />
        ساخته‌شده با عشق برای قولیار
      </motion.section>
    </div>
  );
}
