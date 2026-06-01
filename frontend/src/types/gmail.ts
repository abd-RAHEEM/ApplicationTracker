export interface OAuthUrlResponse {
  auth_url: string;
}

export interface InitialImportConfigRequest {
  import_range: string; // E.g., '1_month', '6_months'
  import_from: string;  // ISO 8601 Date string
}

export interface GmailConnectionRead {
  gmail_email: string;
  is_active: boolean;
  connected_at: string;
  last_successful_sync_at: string | null;
  initial_import_done: boolean;
  initial_import_from: string | null;
}
