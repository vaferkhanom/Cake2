import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { api, type MeOut } from "../lib/api";
import { haptic, backButton } from "../lib/telegram";
import CountUp from "../components/CountUp";
import { BackIcon, FlameIcon, HeartIcon, SparkleIcon, SunIcon, MoonIcon } from "../components/icons";
import { gentleSpring, durations } from "../motion/presets";
import { useTheme } from "../lib/useTheme.tsx";

export default function Profile() {
  const [me, setMe] = useState<MeOut | null>(null);
  const [error, setError] = useState("");
  const { resolvedTheme, toggleTheme } = useTheme();

  useEffect(() => backButton(() => history.back()), []);
  useEffect(() => {
    api.me().then(setMe).catch((e) => setError(e.message));
  }, []);

  if (error) {
    return (
      <div className="pt-20 text-center text-sm text-ink-soft dark:text-ink-darkSoft">
        <p className="mb-2">نتونستم پروفایل رو لود کنم 😔</p>
        <p className="text-xs text-ink-faint dark:text-ink-darkFaint">{error}</p>
      </div>
    );
  }

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
      <header className="flex items-center justify-between gap-3">
        <Link
          to="/"
          onClick={() => haptic("light")}
          className="flex h-10 w-10 items-center justify-center rounded-2xl bg-card text-ink dark:bg-card-dark dark:text-ink-dark shadow-card dark:shadow-cardDark"
        >
          <BackIcon size={20} />
        </Link>
        <h1 className="text-xl font-extrabold flex-1 text-center">پروفایل</h1>
        <button
          onClick={() => { haptic("light"); toggleTheme(); }}
          className="flex h-10 w-10 items-center justify-center rounded-2xl bg-card text-ink dark:bg-card-dark dark:text-ink-dark shadow-card dark:shadow-cardDark"
          aria-label={resolvedTheme === "dark" ? "حالت روشن" : "حالت تاریک"}
        >
          {resolvedTheme === "dark" ? <SunIcon size={22} /> : <MoonIcon size={22} />}
        </button>
      </header>

      {/* User card */}
      <motion.section
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={gentleSpring}
        className="rounded-card bg-gradient-to-br from-accent-soft to-card p-6 shadow-card dark:from-accent-deep/30 dark:to-card-dark dark:shadow-cardDark"
      >
        <div className="flex items-center gap-4">
          <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-full bg-accent text-2xl font-extrabold text-white overflow-hidden">
            {me.user.photo_url ? (
              <img
                src={me.user.photo_url}
                alt={me.user.display_name}
                className="h-full w-full object-cover"
                onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
              />
            ) : null}
            {(!me.user.photo_url) && me.user.display_name.slice(0, 1).toUpperCase()}
          </div>
          <div className="flex-1">
            <p className="text-lg font-extrabold text-ink dark:text-ink-dark">{me.user.display_name}</p>
            <p className="text-xs text-ink-soft dark:text-ink-darkSoft">
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
        <div className="rounded-card bg-card p-5 text-center shadow-card dark:bg-card-dark dark:shadow-cardDark">
          <p className="text-xs text-ink-soft dark:text-ink-darkSoft">امتیاز اعتبار</p>
          <p className="mt-1 text-3xl font-extrabold text-accent-deep">
            <CountUp value={me.user.score} />
          </p>
        </div>
        <div className="rounded-card bg-card p-5 text-center shadow-card dark:bg-card-dark dark:shadow-cardDark">
          <p className="flex items-center justify-center gap-1 text-xs text-ink-soft dark:text-ink-darkSoft">
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
        className="rounded-card bg-card p-5 shadow-card dark:bg-card-dark dark:shadow-cardDark"
      >
        <p className="mb-4 text-sm font-bold text-ink dark:text-ink-dark">عملکرد</p>
        <div className="mb-2 flex h-3 overflow-hidden rounded-full bg-bg-soft dark:bg-bg-dark">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${rate}%` }}
            transition={gentleSpring}
            className="bg-status-done"
          />
        </div>
        <div className="flex items-center justify-between text-xs text-ink-soft dark:text-ink-darkSoft">
          <span className="flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded-full bg-status-done" />
            {done} انجام‌شده
          </span>
          <span className="flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded-full bg-status-broken" />
            {broken} شکسته
          </span>
        </div>
        <div className="mt-4 flex items-center justify-center gap-2 rounded-2xl bg-bg-soft py-3 text-sm text-ink-soft dark:bg-bg-dark dark:text-ink-darkSoft">
          <SparkleIcon size={16} className="text-accent" />
          نرخ موفقیت: {rate}٪
        </div>
      </motion.section>

      {/* About */}
      <motion.section
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: durations.fast / 1000, ease: "easeOut", delay: 0.24 }}
        className="flex items-center justify-center gap-2 rounded-card bg-card py-4 text-xs text-ink-faint dark:text-ink-darkFaint shadow-card dark:bg-card-dark dark:shadow-cardDark"
      >
        <HeartIcon size={14} />
        ساخته‌شده با عشق برای قولیار
      </motion.section>
    </div>
  );
}
