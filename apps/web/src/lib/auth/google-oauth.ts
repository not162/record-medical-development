/**
 * Login Google (OAuth 2.0 Authorization Code + PKCE).
 * state & code_verifier disimpan di sessionStorage tab ini dan dihapus setelah callback.
 */
const STORE_KEY = "google_oauth_pending";
const AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth";
export const GOOGLE_CALLBACK_PATH = "/login/google/callback";

function b64url(bytes: Uint8Array): string {
  let s = "";
  bytes.forEach((b) => (s += String.fromCharCode(b)));
  return btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function randomString(len = 32): string {
  return b64url(crypto.getRandomValues(new Uint8Array(len)));
}

export function googleRedirectUri(): string {
  return `${window.location.origin}${GOOGLE_CALLBACK_PATH}`;
}

/** Arahkan browser ke halaman persetujuan Google. */
export async function startGoogleLogin(clientId: string, remember = true): Promise<void> {
  const state = randomString(24);
  const verifier = randomString(48); // 64 karakter
  const challenge = b64url(new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(verifier))));
  sessionStorage.setItem(STORE_KEY, JSON.stringify({ state, verifier, remember }));
  const params = new URLSearchParams({
    client_id: clientId,
    redirect_uri: googleRedirectUri(),
    response_type: "code",
    scope: "openid email profile",
    state,
    code_challenge: challenge,
    code_challenge_method: "S256",
    prompt: "select_account",
  });
  window.location.assign(`${AUTH_URL}?${params.toString()}`);
}

/** Ambil & hapus data PKCE bila `state` cocok (mencegah CSRF login). */
export function consumeGooglePending(state: string | null): { verifier: string; remember: boolean } | null {
  try {
    const raw = sessionStorage.getItem(STORE_KEY);
    sessionStorage.removeItem(STORE_KEY);
    if (!raw || !state) return null;
    const p = JSON.parse(raw) as { state: string; verifier: string; remember: boolean };
    return p.state === state ? { verifier: p.verifier, remember: p.remember } : null;
  } catch {
    return null;
  }
}
