path = r"apps/web/src/app/chat/page.tsx"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

# 1. Add getChatTier import
if 'import { getChatTier } from "@/lib/chat/tiers";' not in text:
    text = text.replace(
        'import { API_BASE_URL } from "@/lib/api";',
        'import { API_BASE_URL } from "@/lib/api";\nimport { getChatTier } from "@/lib/chat/tiers";'
    )

# 2. Add tier resolving inside ChatPage
tier_code = """  const { user } = useAuth();
  const currentTier = getChatTier(user);
  const [guestConsentDismissed, setGuestConsentDismissed] = useState(false);
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);
  const [isUpgrading, setIsUpgrading] = useState(false);
"""

if "const currentTier = getChatTier" not in text:
    text = text.replace("const { role: userRole } = useAuth();", "const { role: userRole } = useAuth();\n" + tier_code)

# 3. Update handleSendMessage to support guest and tier limits
old_send = """    let activeSessId = currentSessionId;
    const token = localStorage.getItem("clinical_token");

    // If no active session, create one first
    if (!activeSessId && token) {
      try {
        const sRes = await fetch(`${API_BASE_URL}/chat/sessions`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`
          },
          body: JSON.stringify({ title: query.slice(0, 40) })
        });
        if (sRes.ok) {
          const sData = await sRes.json();
          activeSessId = sData.id;
          setCurrentSessionId(activeSessId);
        }
      } catch {
        // continue
      }
    }"""

new_send = """    let activeSessId = currentSessionId;
    const token = typeof window !== "undefined" ? localStorage.getItem("clinical_token") : null;

    if (!activeSessId && token) {
      try {
        const sRes = await fetch(`${API_BASE_URL}/chat/sessions`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`
          },
          body: JSON.stringify({ title: query.slice(0, 40) })
        });
        if (sRes.ok) {
          const sData = await sRes.json();
          activeSessId = sData.id;
          setCurrentSessionId(activeSessId);
        }
      } catch {
        // continue
      }
    }

    // Guest fallback session id
    if (!activeSessId) {
      activeSessId = `guest-session-${Date.now()}`;
    }"""

text = text.replace(old_send, new_send)

# 4. Update the fetch stream/sync block to support guest (without requiring token)
old_fetch_branch = """      if (token && activeSessId) {
        // Respons Percakapan Real-Time (Server-Sent Events)
        const res = await fetch(`${API_BASE_URL}/chat/messages/stream`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`
          },
          body: JSON.stringify({
            session_id: activeSessId,
            content: query,
            reasoning_mode: reasoningMode,
            model_size: modelSize
          })
        });"""

new_fetch_branch = """      if (activeSessId) {
        const headers: Record<string, string> = {
          "Content-Type": "application/json",
        };
        if (token) {
          headers["Authorization"] = `Bearer ${token}`;
        }

        const effectiveMode = token ? reasoningMode : "fast";

        // Respons Percakapan Real-Time (Server-Sent Events)
        const res = await fetch(`${API_BASE_URL}/chat/messages/stream`, {
          method: "POST",
          headers,
          credentials: "include",
          body: JSON.stringify({
            session_id: activeSessId,
            content: query,
            reasoning_mode: effectiveMode,
            model_size: effectiveMode === "thinking" ? "70b" : "8b"
          })
        });"""

text = text.replace(old_fetch_branch, new_fetch_branch)

# 5. Update sync fallback block
old_sync_branch = """          const syncRes = await fetch(`${API_BASE_URL}/chat/messages`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${token}`
            },
            body: JSON.stringify({
              session_id: activeSessId,
              content: query,
              reasoning_mode: reasoningMode
            })
          });"""

new_sync_branch = """          const syncRes = await fetch(`${API_BASE_URL}/chat/messages`, {
            method: "POST",
            headers,
            credentials: "include",
            body: JSON.stringify({
              session_id: activeSessId,
              content: query,
              reasoning_mode: effectiveMode
            })
          });"""

text = text.replace(old_sync_branch, new_sync_branch)

# 6. Update fetchSessions invocation to only run when token is present
text = text.replace("fetchSessions();\n                }", "if (token) fetchSessions();\n                }")
text = text.replace("fetchSessions();\n          } else {", "if (token) fetchSessions();\n          } else {")

with open(path, "w", encoding="utf-8") as f:
    f.write(text)

print("apps/web/src/app/chat/page.tsx upgraded with Phase 2 guest flow!")
