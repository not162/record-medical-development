import os
from pathlib import Path

layout_file = Path("apps/web/src/app/admin/layout.tsx")
with open(layout_file, "r", encoding="utf-8") as f:
    code = f.read().replace("\r\n", "\n")

# 1. Update RBAC check
code = code.replace(
    '(!isAuthenticated || role !== "ADMIN")',
    '(!isAuthenticated || (role !== "ADMIN" && role !== "RESEARCHER"))'
)

# 2. Replace nav items with operational & research categories
old_nav_block = """  const adminNavItems = [
    { href: "/admin/dashboard", label: "Dashboard", icon: LayoutDashboard },
    { href: "/admin/datasets", label: "Dataset Management", icon: Database },
    { href: "/admin/datasets/imports", label: "Import Manifests", icon: FileText },
    { href: "/admin/annotations", label: "Annotation Studio", icon: CheckSquare },
    { href: "/admin/models", label: "Model Registry", icon: Cpu },
    { href: "/admin/training", label: "Model Training", icon: Activity },
    { href: "/admin/evaluation", label: "Evaluation & Metrics", icon: BarChart3 },
    { href: "/admin/knowledge-base", label: "Knowledge Index", icon: BookOpen },
    { href: "/admin/graph", label: "GraphRAG Visualizer", icon: GitFork },
    { href: "/admin/feedback", label: "Feedback Review", icon: ThumbsUp },
    { href: "/admin/audit-logs", label: "Audit Logs", icon: ShieldAlert },
    { href: "/admin/settings", label: "System Settings", icon: Settings },
  ];"""

new_nav_block = """  const operationalNavItems = [
    { href: "/admin/dashboard", label: "Dashboard Operasional", icon: LayoutDashboard },
    { href: "/admin/feedback", label: "Feedback Pasien", icon: ThumbsUp },
    { href: "/admin/audit-logs", label: "Log Audit Sistem", icon: ShieldAlert },
    { href: "/admin/settings", label: "Pengaturan Sistem", icon: Settings },
  ];

  const researchNavItems = [
    { href: "/admin/training", label: "Model Training & Simulasi", icon: Activity },
    { href: "/admin/models", label: "Model Registry", icon: Cpu },
    { href: "/admin/evaluation", label: "Evaluasi & Benchmark", icon: BarChart3 },
    { href: "/admin/datasets", label: "Manajemen Dataset", icon: Database },
    { href: "/admin/datasets/imports", label: "Import Manifests", icon: FileText },
    { href: "/admin/annotations", label: "Annotation Studio", icon: CheckSquare },
    { href: "/admin/knowledge-base", label: "Knowledge Index (RAG)", icon: BookOpen },
    { href: "/admin/graph", label: "GraphRAG Visualizer", icon: GitFork },
  ];"""

assert old_nav_block in code, "old_nav_block not found"
code = code.replace(old_nav_block, new_nav_block)

# 3. Replace nav rendering
old_nav_render = """          {/* Nav Items */}
          <nav className="p-3 space-y-1">
            {adminNavItems.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-medium transition ${
                    isActive
                      ? "bg-emerald-50 text-emerald-800 border border-emerald-200 shadow-sm font-semibold"
                      : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
                  }`}
                >
                  <Icon className={`w-4 h-4 ${isActive ? "text-emerald-700" : "text-slate-400"}`} />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </nav>"""

new_nav_render = """          {/* Nav Items Grouped by Role Category */}
          <nav className="p-3 space-y-4">
            {/* Kategori 1: Operasional Klinik */}
            <div>
              <div className="px-3 pb-1 text-[10px] font-bold text-slate-400 uppercase tracking-wider flex items-center justify-between">
                <span>Operasional Klinik</span>
                {role === "ADMIN" && (
                  <span className="text-[9px] px-1.5 py-0.2 bg-emerald-50 text-emerald-700 rounded border border-emerald-200">Aktif</span>
                )}
              </div>
              <div className="space-y-0.5">
                {operationalNavItems.map((item) => {
                  const Icon = item.icon;
                  const isActive = pathname === item.href;
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      className={`flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-medium transition ${
                        isActive
                          ? "bg-emerald-50 text-emerald-800 border border-emerald-200 shadow-xs font-semibold"
                          : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
                      }`}
                    >
                      <Icon className={`w-4 h-4 ${isActive ? "text-emerald-700" : "text-slate-400"}`} />
                      <span>{item.label}</span>
                    </Link>
                  );
                })}
              </div>
            </div>

            {/* Kategori 2: Workspace Riset & AI Engineering */}
            <div>
              <div className="px-3 pb-1 text-[10px] font-bold text-slate-400 uppercase tracking-wider flex items-center justify-between">
                <span>Workspace Riset AI</span>
                {role === "RESEARCHER" && (
                  <span className="text-[9px] px-1.5 py-0.2 bg-sky-50 text-sky-700 rounded border border-sky-200">Periset Aktif</span>
                )}
              </div>
              <div className="space-y-0.5">
                {researchNavItems.map((item) => {
                  const Icon = item.icon;
                  const isActive = pathname === item.href;
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      className={`flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-medium transition ${
                        isActive
                          ? "bg-sky-50 text-sky-800 border border-sky-200 shadow-xs font-semibold"
                          : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
                      }`}
                    >
                      <Icon className={`w-4 h-4 ${isActive ? "text-sky-700" : "text-slate-400"}`} />
                      <span>{item.label}</span>
                    </Link>
                  );
                })}
              </div>
            </div>
          </nav>"""

assert old_nav_render in code, "old_nav_render not found"
code = code.replace(old_nav_render, new_nav_render)

# 4. Replace footer role badge
old_footer_badge = """            <div className="truncate">
              <p className="text-xs font-semibold text-emerald-700 truncate">{user?.username}</p>
              <p className="text-[10px] text-slate-500 truncate">ROLE: ADMIN</p>
            </div>"""

new_footer_badge = """            <div className="truncate">
              <p className={`text-xs font-semibold truncate ${role === "RESEARCHER" ? "text-sky-700" : "text-emerald-700"}`}>
                {user?.username}
              </p>
              <span className={`inline-block px-1.5 py-0.5 rounded text-[9px] font-bold uppercase tracking-wider border ${
                role === "RESEARCHER"
                  ? "bg-sky-50 text-sky-700 border-sky-200"
                  : "bg-emerald-50 text-emerald-700 border-emerald-200"
              }`}>
                {role === "RESEARCHER" ? "ADMIN PERISET" : "ADMIN OPERASIONAL"}
              </span>
            </div>"""

assert old_footer_badge in code, "old_footer_badge not found"
code = code.replace(old_footer_badge, new_footer_badge)

with open(layout_file, "w", encoding="utf-8") as f:
    f.write(code)

print("[OK] Patched apps/web/src/app/admin/layout.tsx successfully.")

