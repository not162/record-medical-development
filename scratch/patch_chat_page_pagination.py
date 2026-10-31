import re

with open("apps/web/src/app/chat/page.tsx", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add states for message pagination
target_states = "  const [inputQuery, setInputQuery] = useState(\"\");"
new_states = """  const [inputQuery, setInputQuery] = useState("");
  const [hasMoreMessages, setHasMoreMessages] = useState(false);
  const [nextMessageCursor, setNextMessageCursor] = useState<string | null>(null);
  const [totalSessionMessages, setTotalSessionMessages] = useState<number>(0);
  const [loadingOlderMessages, setLoadingOlderMessages] = useState(false);"""

assert target_states in content, "target_states not found"
content = content.replace(target_states, new_states)

# 2. Update loadSession & add loadOlderMessages
old_load_session_block = """  const loadSession = useCallback(async (sessId: string) => {
    const token = localStorage.getItem("clinical_token");
    if (!token) return;
    try {
      const res = await fetch(`${API_BASE_URL}/chat/sessions/${sessId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setCurrentSessionId(data.id);
        if (data.messages && data.messages.length > 0) {
          const formatted: Message[] = data.messages.map((m: ApiSessionMessage) => ({
            id: m.id,
            sender: m.sender_role,
            content: m.content,
            department: m.triage_department || "Umum",
            safetyAlert: m.safety_alert,
            citations: m.citations || [],
            timestamp: new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            scanningDeteksiBahasa: m.scanning_deteksi_bahasa || null,
          }));
          setMessages(formatted);
        } else {
          setMessages([]);
        }
      }
    } catch {
      // offline fallback
    }
  }, []);"""

new_load_session_block = """  const loadSession = useCallback(async (sessId: string) => {
    const token = localStorage.getItem("clinical_token");
    if (!token) return;
    try {
      const res = await fetch(`${API_BASE_URL}/chat/sessions/${sessId}?limit=20`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setCurrentSessionId(data.id);
        setHasMoreMessages(Boolean(data.has_more));
        setNextMessageCursor(data.next_cursor || null);
        setTotalSessionMessages(Number(data.total_messages || (data.messages ? data.messages.length : 0)));

        if (data.messages && data.messages.length > 0) {
          const formatted: Message[] = data.messages.map((m: ApiSessionMessage) => ({
            id: m.id,
            sender: m.sender_role,
            content: m.content,
            department: m.triage_department || "Umum",
            safetyAlert: m.safety_alert,
            citations: m.citations || [],
            timestamp: new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            scanningDeteksiBahasa: null,
          }));
          setMessages(formatted);
        } else {
          setMessages([]);
        }
      }
    } catch {
      // offline fallback
    }
  }, []);

  const loadOlderMessages = async () => {
    if (!currentSessionId || !nextMessageCursor || loadingOlderMessages) return;
    const token = localStorage.getItem("clinical_token");
    if (!token) return;

    setLoadingOlderMessages(true);
    try {
      const res = await fetch(
        `${API_BASE_URL}/chat/sessions/${currentSessionId}?limit=20&before=${encodeURIComponent(nextMessageCursor)}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (res.ok) {
        const data = await res.json();
        setHasMoreMessages(Boolean(data.has_more));
        setNextMessageCursor(data.next_cursor || null);

        if (data.messages && data.messages.length > 0) {
          const formatted: Message[] = data.messages.map((m: ApiSessionMessage) => ({
            id: m.id,
            sender: m.sender_role,
            content: m.content,
            department: m.triage_department || "Umum",
            safetyAlert: m.safety_alert,
            citations: m.citations || [],
            timestamp: new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            scanningDeteksiBahasa: null,
          }));
          setMessages((prev) => [...formatted, ...prev]);
        }
      }
    } catch (err) {
      console.error("Failed to load older messages:", err);
    } finally {
      setLoadingOlderMessages(false);
    }
  };"""

assert old_load_session_block in content, "old_load_session_block not found"
content = content.replace(old_load_session_block, new_load_session_block)

# 3. Update fetchSessions to handle `{ items: [...] }`
old_fetch_sessions = """  // Load user sessions on mount
  const fetchSessions = useCallback(async () => {
    const token = localStorage.getItem("clinical_token");
    if (!token) return;
    try {
      const res = await fetch(`${API_BASE_URL}/chat/sessions`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setSessions(data);
        if (data.length > 0 && !currentSessionId) {
          loadSession(data[0].id);
        }
      }
    } catch {
      // offline fallback
    }
  }, [currentSessionId, loadSession]);"""

new_fetch_sessions = """  // Load user sessions on mount
  const fetchSessions = useCallback(async () => {
    const token = localStorage.getItem("clinical_token");
    if (!token) return;
    try {
      const res = await fetch(`${API_BASE_URL}/chat/sessions?limit=20`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        const items = Array.isArray(data) ? data : (data.items || []);
        setSessions(items);
        if (items.length > 0 && !currentSessionId) {
          loadSession(items[0].id);
        }
      }
    } catch {
      // offline fallback
    }
  }, [currentSessionId, loadSession]);"""

assert old_fetch_sessions in content, "old_fetch_sessions not found"
content = content.replace(old_fetch_sessions, new_fetch_sessions)

# 4. Update mount useEffect for sessions
old_mount_effect = """        if (res.ok && !ignore) {
          const data = await res.json();
          setSessions(data);
          if (data.length > 0) {
            loadSession(data[0].id);
          }
        }"""

new_mount_effect = """        if (res.ok && !ignore) {
          const data = await res.json();
          const items = Array.isArray(data) ? data : (data.items || []);
          setSessions(items);
          if (items.length > 0) {
            loadSession(items[0].id);
          }
        }"""

assert old_mount_effect in content, "old_mount_effect not found"
content = content.replace(old_mount_effect, new_mount_effect)

# 5. Insert pagination button above messages.map
target_map = "          {messages.map((msg) => ("
pagination_button = """          {/* Pagination: Muat pesan riwayat sebelumnya */}
          {hasMoreMessages && (
            <div className="flex justify-center my-2">
              <button
                type="button"
                onClick={loadOlderMessages}
                disabled={loadingOlderMessages}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 border border-slate-300 text-slate-700 text-xs font-semibold transition shadow-2xs disabled:opacity-50"
              >
                {loadingOlderMessages ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin text-cyan-600" />
                    <span>Memuat riwayat sebelumnya...</span>
                  </>
                ) : (
                  <>
                    <History className="w-3.5 h-3.5 text-cyan-700" />
                    <span>
                      Muat pesan sebelumnya ({Math.max(0, totalSessionMessages - messages.length)} pesan lagi)
                    </span>
                  </>
                )}
              </button>
            </div>
          )}

          {messages.map((msg) => ("""

assert target_map in content, "target_map not found"
content = content.replace(target_map, pagination_button)

with open("apps/web/src/app/chat/page.tsx", "w", encoding="utf-8") as f:
    f.write(content)

print("apps/web/src/app/chat/page.tsx successfully patched with pagination!")

