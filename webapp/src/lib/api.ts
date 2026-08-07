/**
 * API client for the Mini App backend.
 * Sends the raw initData in the Authorization header (tma scheme),
 * as the FastAPI side expects.
 */

import { getInitData } from "./telegram";

const BASE = "/api";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    Authorization: `tma ${getInitData()}`,
    ...(init?.body ? { "Content-Type": "application/json" } : {}),
    ...(init?.headers as Record<string, string> | undefined),
  };
  const res = await fetch(`${BASE}${path}`, { ...init, headers });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (body?.detail) detail = body.detail;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

export interface UserOut {
  telegram_id: number;
  username: string | null;
  full_name: string;
  photo_url: string | null;
  score: number;
  current_streak: number;
  display_name: string;
  created_at: string | null;
}

export interface MeOut {
  user: UserOut;
  stats: {
    total_given: number;
    done: number;
    broken: number;
    total_received: number;
    accepted: number;
  };
}

export interface PromiseOut {
  id: number;
  promise_id: number | null;
  content: string;
  giver_id: number;
  receiver_id: number | null;
  target_type: "self" | "friend";
  status: string;
  deadline: string | null;
  created_at: string;
  claimed_done_at: string | null;
  resolved_at: string | null;
  status_text: string;
  status_emoji: string;
  jalali_created_at: string;
  jalali_deadline: string | null;
  giver_name: string;
  giver_photo_url: string | null;
  receiver_name: string;
  receiver_photo_url: string | null;
  is_giver: boolean;
  is_receiver: boolean;
}

export interface PromiseListOut {
  type: string;
  page: number;
  total: number;
  total_pages: number;
  items: PromiseOut[];
}

export type PromiseType = "self" | "given" | "received";

export const api = {
  me: () => request<MeOut>("/me"),
  listPromises: (type: PromiseType, page = 0) =>
    request<PromiseListOut>(`/promises?type=${type}&page=${page}`),
  getPromise: (id: number) => request<PromiseOut>(`/promises/${id}`),
  createPromise: (body: {
    content: string;
    target_type: "self" | "friend";
    receiver_username?: string;
    deadline?: string;
  }) =>
    request<PromiseOut>("/promises", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  respond: (id: number, action: "accept" | "reject") =>
    request<{ ok: boolean; deleted?: boolean }>(`/promises/${id}/respond`, {
      method: "POST",
      body: JSON.stringify({ action }),
    }),
  claimDone: (id: number) =>
    request<{ ok: boolean; status: string }>(`/promises/${id}/claim-done`, {
      method: "POST",
    }),
  broken: (id: number) =>
    request<{ ok: boolean; status: string }>(`/promises/${id}/broken`, {
      method: "POST",
    }),
  confirmDone: (id: number) =>
    request<{ ok: boolean; status: string }>(`/promises/${id}/confirm-done`, {
      method: "POST",
    }),
  dispute: (id: number) =>
    request<{ ok: boolean; status: string }>(`/promises/${id}/dispute`, {
      method: "POST",
    }),
  resolveDispute: (id: number) =>
    request<{ ok: boolean; status: string }>(`/promises/${id}/resolve-dispute`, {
      method: "POST",
    }),
};
