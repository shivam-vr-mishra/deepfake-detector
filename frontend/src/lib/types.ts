export type ScanType = "image" | "video" | "audio" | "text" | "url";

export type ScanStatus =
  | "pending"
  | "scanning_virus"
  | "queued"
  | "processing"
  | "completed"
  | "failed"
  | "rejected";

export interface Scan {
  id: string;
  scan_type: ScanType;
  status: ScanStatus;
  original_filename: string | null;
  mime_type: string | null;
  file_size: number | null;
  source_url: string | null;
  score: number | null;
  label: string | null;
  confidence: string | null;
  explanation: string | null;
  result_payload: Record<string, unknown> | null;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  role: "user" | "admin";
  is_active: boolean;
  is_verified: boolean;
}

export interface Subscription {
  id: string;
  plan: "free" | "pro" | "enterprise";
  status: "active" | "cancelled" | "expired" | "pending";
  current_period_start: string | null;
  current_period_end: string | null;
  daily_limit: number;
  max_file_mb: number;
  used_today: number;
  credits_balance: number;
  credit_price_usd: number;
}

export interface Plan {
  plan: "free" | "pro" | "enterprise";
  daily_limit: number;
  max_file_mb: number;
  price_paise: number;
  price_inr: number;
}

export interface CreditWallet {
  balance: number;
  credit_price_usd: number;
  min_purchase: number;
  max_purchase: number;
}

export interface CreditOrderResponse {
  order_id: string;
  amount: number;
  currency: "USD";
  credits: number;
  razorpay_key_id: string;
}

export interface ScanCreatedResponse {
  scan_id: string;
  status: ScanStatus;
  message: string;
}
