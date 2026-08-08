import { motion } from "framer-motion";
import type { PromiseOut } from "../lib/api";
import { BrokenHeartIcon, ClockIcon, CheckIcon, AlertIcon, SparkleIcon } from "./icons";

/** Status → pastel color + icon mapping (NO system emoji). */
export function statusTheme(status: string) {
 switch (status) {
 case "pending":
 return { color: "bg-status-pending", text: "text-status-pending", icon: ClockIcon };
 case "confirmed":
 return { color: "bg-status-confirmed", text: "text-status-confirmed", icon: SparkleIcon };
 case "done":
 return { color: "bg-status-done", text: "text-status-done", icon: CheckIcon };
 case "broken":
 return { color: "bg-status-broken", text: "text-status-broken", icon: BrokenHeartIcon };
 case "disputed":
 return { color: "bg-status-disputed", text: "text-status-disputed", icon: AlertIcon };
 default: // expired
 return { color: "bg-status-expired", text: "text-status-expired", icon: ClockIcon };
 }
}

export default function PromiseCard({
 promise,
 index = 0,
 onClick,
}: {
 promise: PromiseOut;
 index?: number;
 onClick: () => void;
}) {
 const t = statusTheme(promise.status);
 const Icon = t.icon;
 return (
 <motion.div
 layoutId={`promise-${promise.id}`}
 initial={{ opacity: 0, y: 12 }}
 animate={{ opacity: 1, y: 0 }}
 exit={{ opacity: 0, y: 8 }}
 transition={{ duration: 0.2, ease: "easeOut", delay: index * 0.05 }}
 whileTap={{ scale: 0.96 }}
 onClick={onClick}
 className="mb-3 cursor-pointer rounded-card bg-card p-4 shadow-card "
 >
 <div className="flex items-start gap-3">
 <div className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl ${t.color}`}>
 <Icon size={22} className="text-white" />
 </div>
 <div className="min-w-0 flex-1">
 <p className="mb-0.5 line-clamp-2 text-sm font-medium leading-6 text-ink ">
 {promise.content}
 </p>
 <p className="text-xs text-ink-soft ">
 {promise.status_text}
 {promise.jalali_deadline ? ` · مهلت: ${promise.jalali_deadline}` : ""}
 </p>
 {promise.target_type === "friend" && (
 <div className="mt-1 flex items-center gap-1.5 text-[11px] text-ink-faint ">
 {(() => {
 const photoUrl = promise.is_giver ? promise.receiver_photo_url : promise.giver_photo_url;
 const name = promise.is_giver ? promise.receiver_name : promise.giver_name;
 const label = promise.is_giver ? "به" : "از";
 return (
 <>
 {photoUrl ? (
 <img src={photoUrl} alt={name} className="h-4 w-4 rounded-full object-cover" />
 ) : null}
 <span>{label} {name}</span>
 </>
 );
 })()}
 </div>
 )}
 </div>
 </div>
 </motion.div>
 );
}
