import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { motion } from "framer-motion";
import { api, type PromiseOut, type PromiseType } from "../lib/api";
import { haptic, backButton } from "../lib/telegram";
import PromiseCard from "../components/PromiseCard";
import { BackIcon } from "../components/icons";
import { durations } from "../motion/presets";

const TABS: { key: PromiseType; label: string }[] = [
  { key: "self", label: "شخصی" },
  { key: "given", label: "داده‌شده" },
  { key: "received", label: "گرفته‌شده" },
];

export default function PromiseList() {
  const { type = "self" } = useParams();
  const active: PromiseType = TABS.some((t) => t.key === type) ? (type as PromiseType) : "self";

  const [items, setItems] = useState<PromiseOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => backButton(() => history.back()), []);

  const load = useCallback(() => {
    setLoading(true);
    api
      .listPromises(active)
      .then((res) => {
        setItems(res.items);
        setError("");
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [active]);

  useEffect(load, [load]);

  return (
    <div className="flex flex-col gap-4">
      {/* Header */}
      <header className="flex items-center gap-3">
        <Link
          to="/"
          onClick={() => haptic("light")}
          className="flex h-10 w-10 items-center justify-center rounded-2xl bg-card text-ink dark:bg-card-dark dark:text-ink-dark shadow-card dark:shadow-cardDark"
        >
          <BackIcon size={20} />
        </Link>
        <h1 className="text-xl font-extrabold text-ink dark:text-ink-dark">قول‌های من</h1>
      </header>

      {/* Tabs */}
      <div className="flex rounded-2xl bg-card p-1 shadow-card dark:bg-card-dark dark:shadow-cardDark">
        {TABS.map((t) => (
          <Link
            key={t.key}
            to={`/promises/${t.key}`}
            onClick={() => haptic("light")}
            className={`relative flex-1 rounded-xl py-2 text-center text-sm font-medium transition-colors ${
              active === t.key ? "text-white" : "text-ink-soft dark:text-ink-darkSoft"
            }`}
          >
            {active === t.key && (
              <motion.div
                layoutId="tab-pill"
                className="absolute inset-0 rounded-xl bg-accent"
                transition={{ type: "spring", stiffness: 400, damping: 32 }}
              />
            )}
            <span className="relative z-10">{t.label}</span>
          </Link>
        ))}
      </div>

      {/* List */}
      <div className="flex flex-col">
        {loading ? (
          <div className="flex flex-col gap-3">
            {[0, 1, 2].map((i) => (
              <div key={i} className="skeleton h-20" />
            ))}
          </div>
        ) : error ? (
          <p className="pt-10 text-center text-sm text-ink-soft dark:text-ink-darkSoft">{error}</p>
        ) : items.length === 0 ? (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: durations.fast / 1000, ease: "easeOut" }}
            className="pt-14 text-center"
          >
            <p className="mb-1 text-4xl">📭</p>
            <p className="font-bold text-ink-soft dark:text-ink-darkSoft">هنوز قولی ثبت نکردی</p>
            <Link
              to="/new"
              className="mt-4 inline-block rounded-2xl bg-accent px-6 py-2.5 text-sm font-bold text-white"
            >
              ثبت اولین قول
            </Link>
          </motion.div>
        ) : (
          items.map((p, i) => (
            <PromiseCard
              key={p.id}
              promise={p}
              index={i}
              onClick={() => {
                haptic("light");
                window.location.href = `/promise/${p.id}`;
              }}
            />
          ))
        )}
      </div>
    </div>
  );
}
