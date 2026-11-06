/**
 * Unified Password Management Module - Clinic with Agent Healthy
 * Standardizes password validation, policy enforcement, and client-side security checks.
 */

export interface PasswordValidationResult {
  isValid: boolean;
  errors: string[];
}

export const MIN_PASSWORD_LENGTH = 8;
export const MAX_PASSWORD_LENGTH = 128;

/**
 * Validates password against hospital ISO 27001 & Permenkes security requirements.
 */
export function validatePassword(password: string, confirmPassword?: string): PasswordValidationResult {
  const errors: string[] = [];

  if (!password || password.length < MIN_PASSWORD_LENGTH) {
    errors.push(`Kata sandi harus memiliki panjang minimal ${MIN_PASSWORD_LENGTH} karakter.`);
  }

  if (password && password.length > MAX_PASSWORD_LENGTH) {
    errors.push(`Kata sandi tidak boleh melebihi ${MAX_PASSWORD_LENGTH} karakter.`);
  }

  if (confirmPassword !== undefined && password !== confirmPassword) {
    errors.push("Konfirmasi kata sandi tidak cocok.");
  }

  return {
    isValid: errors.length === 0,
    errors,
  };
}

/**
 * Returns generic authentication failure message to prevent user enumeration attacks.
 */
export function getGenericAuthErrorMessage(): string {
  return "Email atau kata sandi salah.";
}
