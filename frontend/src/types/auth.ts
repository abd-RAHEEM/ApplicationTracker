/**
 * Shared TypeScript types mirroring backend Pydantic schemas.
 *
 * Keep in sync with:
 *   backend/app/schemas/auth.py
 *   backend/app/schemas/user.py
 */

// ── Auth ───────────────────────────────────────────────────────────────────────
export interface RegisterRequest {
  full_name: string;
  username: string;
  password: string;
  confirm_password: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface PasswordResetRequest {
  username: string;
}

export interface PasswordResetConfirm {
  token: string;
  new_password: string;
  confirm_password: string;
}

// ── User ───────────────────────────────────────────────────────────────────────
export interface UserRead {
  id: string;
  username: string;
  full_name: string;
  is_active: boolean;
  is_email_verified: boolean;
  is_onboarding_completed: boolean;
  created_at: string;
  updated_at: string;
  gmail_connected: boolean;
  gmail_email: string | null;
  initial_import_done: boolean;
}

export interface UserAuthResponse {
  id: string;
  username: string;
  full_name: string;
  gmail_connected: boolean;
  initial_import_done: boolean;
  is_onboarding_completed: boolean;
}

export interface LoginResponse {
  user: UserAuthResponse;
}

export interface RegisterResponse {
  id: string;
  username: string;
  full_name: string;
  created_at: string;
}

// ── API Envelope ───────────────────────────────────────────────────────────────
export interface ApiSuccessResponse<T> {
  success: true;
  message: string;
  data: T;
}

export interface ApiErrorResponse {
  success: false;
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  };
}
