/** Price alert types (F106) */

export interface AlertResponse {
  id: number;
  card_id: number;
  card_name: string | null;
  target_price: number;
  direction: "below" | "above";
  is_active: boolean;
  triggered_at: string | null;
  created_at: string;
}

export interface AlertNotificationResponse {
  id: number;
  alert_id: number;
  card_name: string;
  old_price: number | null;
  new_price: number;
  is_read: boolean;
  notified_at: string;
}

export interface NotificationsListResponse {
  notifications: AlertNotificationResponse[];
  unread_count: number;
}

export interface CreateAlertRequest {
  card_id: number;
  target_price: number;
  direction: "below" | "above";
}
