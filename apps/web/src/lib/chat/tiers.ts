export type ChatTier = "GUEST" | "AUTHENTICATED";

export interface ChatTierConfig {
  tier: ChatTier;
  label: string;
  maxChars: number;
  rateLimitPerHour: number;
  allowedModes: ("fast" | "thinking")[];
  defaultMode: "fast" | "thinking";
  isEphemeral: boolean;
  canSaveHistory: boolean;
  canExportRme: boolean;
  consentRequired: boolean;
}

export const GUEST_TIER_CONFIG: ChatTierConfig = {
  tier: "GUEST",
  label: "Mode Tamu (Anonim)",
  maxChars: 500,
  rateLimitPerHour: 10,
  allowedModes: ["fast"],
  defaultMode: "fast",
  isEphemeral: true,
  canSaveHistory: false,
  canExportRme: false,
  consentRequired: true,
};

export const AUTHENTICATED_TIER_CONFIG: ChatTierConfig = {
  tier: "AUTHENTICATED",
  label: "Pasien Terdaftar RSUKT",
  maxChars: 2000,
  rateLimitPerHour: 60,
  allowedModes: ["fast", "thinking"],
  defaultMode: "thinking",
  isEphemeral: false,
  canSaveHistory: true,
  canExportRme: true,
  consentRequired: false,
};

export function getChatTier(user: { id: string; role?: string } | null): ChatTierConfig {
  if (user && user.id) {
    return AUTHENTICATED_TIER_CONFIG;
  }
  return GUEST_TIER_CONFIG;
}
