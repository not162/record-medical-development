path = r"apps/web/src/app/page.tsx"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

# 1. Add audit comment at top of file
if "// TODO: VERIFY ALL PERFORMANCE, PRIVACY AND CERTIFICATION CLAIMS WITH RSUKT" not in text:
    text = "// TODO: VERIFY ALL PERFORMANCE, PRIVACY AND CERTIFICATION CLAIMS WITH RSUKT\n" + text

# 2. Add icons Volume2, VolumeX, Maximize2, Minimize2, Subtitles
if "Volume2" not in text:
    text = text.replace(
        "Play, Pause, RotateCcw, XCircle, AlertOctagon,",
        "Play, Pause, RotateCcw, XCircle, AlertOctagon, Volume2, VolumeX, Maximize2, Minimize2, Subtitles,"
    )

# 3. Add video controls state
state_code = """  const [isMuted, setIsMuted] = useState<boolean>(false);
  const [volume, setVolume] = useState<number>(80);
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);
  const [showCaptions, setShowCaptions] = useState<boolean>(true);
  const videoContainerRef = React.useRef<HTMLDivElement>(null);
"""
if "const [isMuted, setIsMuted]" not in text:
    text = text.replace(
        "const [userRating, setUserRating] = useState<\"LIKE\" | \"DISLIKE\" | null>(null);",
        "const [userRating, setUserRating] = useState<\"LIKE\" | \"DISLIKE\" | null>(null);\n" + state_code
    )

# 4. Add keyboard listener for video player (Space, M, F, Arrows)
keyboard_handler = """  // 3.4 Keyboard accessible video controls
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't trigger if user is typing in an input or textarea
      if (['INPUT', 'TEXTAREA'].includes((e.target as HTMLElement)?.tagName)) return;

      if (e.code === 'Space') {
        e.preventDefault();
        setIsPlaying(prev => !prev);
      } else if (e.code === 'KeyM') {
        e.preventDefault();
        setIsMuted(prev => !prev);
      } else if (e.code === 'KeyF') {
        e.preventDefault();
        if (!document.fullscreenElement && videoContainerRef.current) {
          videoContainerRef.current.requestFullscreen?.().catch(() => {});
          setIsFullscreen(true);
        } else if (document.fullscreenElement) {
          document.exitFullscreen?.().catch(() => {});
          setIsFullscreen(false);
        }
      } else if (e.code === 'KeyC') {
        e.preventDefault();
        setShowCaptions(prev => !prev);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);
"""
if "// 3.4 Keyboard accessible video controls" not in text:
    text = text.replace(
        "const activeScenario = DEMO_SCENARIOS.find(s => s.id === selectedScenarioId) || DEMO_SCENARIOS[0];",
        "const activeScenario = DEMO_SCENARIOS.find(s => s.id === selectedScenarioId) || DEMO_SCENARIOS[0];\n" + keyboard_handler
    )

# 5. Add ref and aspect ratio to player container
text = text.replace(
    '<div className="rounded-3xl border-2 border-slate-800 bg-slate-950 text-slate-100 shadow-2xl overflow-hidden">',
    '<div ref={videoContainerRef} role="region" aria-label="Pemutar Simulasi Video Demo Chatbot RSUKT" className="rounded-3xl border-2 border-slate-800 bg-slate-950 text-slate-100 shadow-2xl overflow-hidden aspect-video min-h-[420px] flex flex-col justify-between relative">'
)

# 6. Add controls: Volume, Mute, Fullscreen, Captions into Bottom Controls
old_controls_btn = """                    <span className="text-[11px] font-mono text-slate-500 hidden sm:inline">
                      {playbackProgress === 100 ? "00:24 / 00:24" : "00:11 / 00:24"}
                    </span>
                  </div>"""

new_controls_btn = """                    <span className="text-[11px] font-mono text-slate-500 hidden sm:inline">
                      {playbackProgress === 100 ? "00:24 / 00:24" : "00:11 / 00:24"}
                    </span>

                    {/* Mute / Volume Control */}
                    <div className="flex items-center gap-1.5 ml-2">
                      <button
                        type="button"
                        onClick={() => setIsMuted(!isMuted)}
                        aria-label={isMuted ? "Aktifkan suara video (M)" : "Bisukan suara video (M)"}
                        className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition"
                        title="Bisukan / Aktifkan Suara (Tekan M)"
                      >
                        {isMuted ? <VolumeX className="w-3.5 h-3.5 text-rose-400" /> : <Volume2 className="w-3.5 h-3.5 text-cyan-400" />}
                      </button>
                      <input
                        type="range"
                        min="0"
                        max="100"
                        value={isMuted ? 0 : volume}
                        onChange={(e) => {
                          setVolume(Number(e.target.value));
                          if (isMuted) setIsMuted(false);
                        }}
                        aria-label="Pengatur volume video demo"
                        className="w-16 h-1 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-cyan-500 hidden sm:inline-block"
                      />
                    </div>

                    {/* Captions Toggle */}
                    <button
                      type="button"
                      onClick={() => setShowCaptions(!showCaptions)}
                      aria-label="Tampilkan atau sembunyikan teks terjemahan/takarir (C)"
                      className={`p-1.5 rounded-lg transition ${showCaptions ? "bg-cyan-950 text-cyan-400 border border-cyan-800" : "bg-slate-800 text-slate-400"}`}
                      title="Takarir / Subtitel (Tekan C)"
                    >
                      <Subtitles className="w-3.5 h-3.5" />
                    </button>

                    {/* Fullscreen Toggle */}
                    <button
                      type="button"
                      onClick={() => {
                        if (!document.fullscreenElement && videoContainerRef.current) {
                          videoContainerRef.current.requestFullscreen?.().catch(() => {});
                          setIsFullscreen(true);
                        } else if (document.fullscreenElement) {
                          document.exitFullscreen?.().catch(() => {});
                          setIsFullscreen(false);
                        }
                      }}
                      aria-label="Layar penuh (F)"
                      className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition hidden sm:inline-block"
                      title="Layar Penuh (Tekan F)"
                    >
                      {isFullscreen ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
                    </button>
                  </div>"""

text = text.replace(old_controls_btn, new_controls_btn)

# 7. Add WebVTT subtitles overlay if showCaptions is true
captions_overlay = """              {/* 3.4 WebVTT Accessible Captions Overlay */}
              {showCaptions && (
                <div aria-live="polite" className="w-full text-center px-4 py-1.5 bg-slate-950/80 backdrop-blur-xs border-t border-slate-800 text-[11px] text-cyan-200 font-medium">
                  [Takarir Demo Medis] {activeScenario.category} ({activeScenario.mode}): "{displayedText || activeScenario.query}"
                </div>
              )}
"""
text = text.replace(
    '{/* Video Player Bottom Controls */}',
    captions_overlay + '\n              {/* Video Player Bottom Controls */}'
)

# 8. Add footer links for privacy and terms
footer_links = """              <Link href="/privacy" className="hover:text-white transition">Kebijakan Privasi</Link>
              <Link href="/terms" className="hover:text-white transition">Syarat & Ketentuan</Link>"""

text = text.replace(
    '<Link href="/chat" className="hover:text-white transition">Chatbot Medis</Link>',
    '<Link href="/chat" className="hover:text-white transition">Chatbot Medis</Link>\n              ' + footer_links
)

with open(path, "w", encoding="utf-8") as f:
    f.write(text)

print("page.tsx updated with accessible video controls, audit comment, and legal links!")
