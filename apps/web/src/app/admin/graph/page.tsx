"use client";

import React, { useEffect, useRef, useState } from "react";
import { GitFork, Search, RefreshCw, ZoomIn, ZoomOut, Maximize2, Activity, Sparkles, CheckCircle2, X } from "lucide-react";
import { API_BASE_URL, getToken } from "@/lib/api";
import type { Core as CytoscapeCore } from "cytoscape";

interface GraphNode {
  id: string;
  name: string;
  category: "DISEASE" | "SYMPTOM" | "DRUG" | "DEPARTMENT" | "GUIDELINE";
  properties?: Record<string, string | number | boolean | null | undefined>;
}

interface GraphEdge {
  source: string;
  target: string;
  relation: "CONTRAINDICATES" | "HAS_SYMPTOM" | "RECOMMENDS" | "TREATED_IN" | "GOVERNED_BY";
  properties?: Record<string, string | number | boolean | null | undefined>;
}

interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

interface Optimize15Result {
  status: string;
  method: string;
  nodes_count: number;
  original_edges_count: number;
  pruned_noise_edges_15pct: number;
  retained_edges_count: number;
  indexed_top_15pct_hubs: Array<{
    name: string;
    degree: number;
    category: string;
  }>;
  candidate_margin_pct: number;
  timestamp: string;
}

export default function AdminGraphPage() {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<CytoscapeCore | null>(null);
  const [loading, setLoading] = useState(true);
  const [graphData, setGraphData] = useState<GraphData>({ nodes: [], edges: [] });
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [connectedEdges, setConnectedEdges] = useState<GraphEdge[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [filterCategory, setFilterCategory] = useState<string>("ALL");
  const [error, setError] = useState<string | null>(null);
  const [optimizeLoading, setOptimizeLoading] = useState(false);
  const [optimizeResult, setOptimizeResult] = useState<Optimize15Result | null>(null);

  const handleRunOptimize15 = async () => {
    setOptimizeLoading(true);
    setError(null);
    try {
      const token = getToken();
      const res = await fetch(`${API_BASE_URL}/admin/graph/optimize-15pct`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` }
      });
      if (!res.ok) throw new Error("Gagal menjalankan optimalisasi 15% Code of Product.");
      const data: Optimize15Result = await res.json();
      setOptimizeResult(data);
      await fetchGraphData();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Gagal menjalankan optimalisasi 15%.");
    } finally {
      setOptimizeLoading(false);
    }
  };

  const fetchGraphData = async (entity?: string) => {
    setLoading(true);
    setError(null);
    try {
      const token = getToken();
      const endpoint = entity && entity.trim().length > 1
        ? `${API_BASE_URL}/admin/graph/subgraph?entity=${encodeURIComponent(entity.trim())}`
        : `${API_BASE_URL}/admin/graph/all`;

      const res = await fetch(endpoint, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Gagal mengambil data graf pengetahuan klinis.");
      const data: GraphData = await res.json();
      setGraphData(data);
      initCytoscape(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Terjadi kesalahan graf.");
    } finally {
      setLoading(false);
    }
  };

  const initCytoscape = async (data: GraphData) => {
    if (!containerRef.current) return;
    const cytoscape = (await import("cytoscape")).default;

    if (cyRef.current) {
      cyRef.current.destroy();
    }

    const elements = [
      ...data.nodes.map(n => ({
        data: {
          id: n.id,
          label: n.name,
          category: n.category,
          properties: n.properties,
        },
      })),
      ...data.edges.map((e, idx) => ({
        data: {
          id: `edge-${idx}-${e.source}-${e.target}`,
          source: e.source,
          target: e.target,
          label: e.relation,
          relation: e.relation,
          properties: e.properties,
        },
      })),
    ];

    const cy = cytoscape({
      container: containerRef.current,
      elements,
      style: [
        {
          selector: "node",
          style: {
            label: "data(label)",
            color: "#0f172a",
            "font-size": "11px",
            "font-family": "Inter, sans-serif",
            "font-weight": "bold",
            "text-valign": "center",
            "text-halign": "center",
            "text-outline-color": "#ffffff",
            "text-outline-width": 2,
            width: 44,
            height: 44,
            "border-width": 2,
            "transition-property": "background-color, line-color, target-arrow-color",
            "transition-duration": 0.2,
          },
        },
        {
          selector: 'node[category = "DISEASE"]',
          style: {
            shape: "ellipse",
            "background-color": "#f43f5e", // rose-500
            "border-color": "#fda4af",
            width: 52,
            height: 52,
          },
        },
        {
          selector: 'node[category = "DRUG"]',
          style: {
            shape: "round-rectangle",
            "background-color": "#0284c7", // sky-600
            "border-color": "#7dd3fc",
            width: 48,
            height: 40,
          },
        },
        {
          selector: 'node[category = "SYMPTOM"]',
          style: {
            shape: "diamond",
            "background-color": "#d97706", // amber-600
            "border-color": "#fde68a",
            width: 46,
            height: 46,
          },
        },
        {
          selector: 'node[category = "DEPARTMENT"]',
          style: {
            shape: "hexagon",
            "background-color": "#7c3aed", // violet-600
            "border-color": "#c4b5fd",
            width: 50,
            height: 50,
          },
        },
        {
          selector: 'node[category = "GUIDELINE"]',
          style: {
            shape: "round-tag",
            "background-color": "#059669", // emerald-600
            "border-color": "#6ee7b7",
            width: 46,
            height: 40,
          },
        },
        {
          selector: "edge",
          style: {
            width: 2,
            "line-color": "#94a3b8",
            "target-arrow-color": "#94a3b8",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            label: "data(label)",
            "font-size": "9px",
            color: "#475569",
            "text-background-opacity": 0.95,
            "text-background-color": "#ffffff",
            "text-background-padding": "2px",
            "text-background-shape": "roundrectangle",
          },
        },
        {
          selector: 'edge[relation = "CONTRAINDICATES"]',
          style: {
            width: 3,
            "line-color": "#ef4444",
            "target-arrow-color": "#ef4444",
            "line-style": "dashed",
            color: "#dc2626",
          },
        },
        {
          selector: 'edge[relation = "RECOMMENDS"]',
          style: {
            width: 2.5,
            "line-color": "#059669",
            "target-arrow-color": "#059669",
            color: "#047857",
          },
        },
        {
          selector: 'edge[relation = "HAS_SYMPTOM"]',
          style: {
            width: 2,
            "line-color": "#d97706",
            "target-arrow-color": "#d97706",
            color: "#b45309",
          },
        },
        {
          selector: ":selected",
          style: {
            "border-width": 4,
            "border-color": "#0284c7",
          },
        },
      ],
      layout: {
        name: "cose",
        animate: true,
        animationDuration: 600,
        nodeRepulsion: () => 650000,
        idealEdgeLength: () => 110,
        edgeElasticity: () => 100,
        gravity: 0.25,
      },
    });

    cy.on("tap", "node", (evt) => {
      const node = evt.target;
      const nodeData = node.data();
      const matchedNode = data.nodes.find(n => n.id === nodeData.id) || {
        id: nodeData.id,
        name: nodeData.label,
        category: nodeData.category,
        properties: nodeData.properties,
      };
      setSelectedNode(matchedNode);

      const connected = data.edges.filter(
        e => e.source === nodeData.id || e.target === nodeData.id
      );
      setConnectedEdges(connected);
    });

    cy.on("tap", (evt) => {
      if (evt.target === cy) {
        setSelectedNode(null);
        setConnectedEdges([]);
      }
    });

    cyRef.current = cy;
  };

  useEffect(() => {
    let ignore = false;
    async function load() {
      try {
        const token = getToken();
        const res = await fetch(`${API_BASE_URL}/admin/graph/all`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) throw new Error("Gagal mengambil data graf pengetahuan klinis.");
        const data: GraphData = await res.json();
        if (!ignore) {
          setGraphData(data);
          initCytoscape(data);
        }
      } catch (err: unknown) {
        if (!ignore) {
          setError(err instanceof Error ? err.message : "Terjadi kesalahan graf.");
        }
      } finally {
        if (!ignore) {
          setLoading(false);
        }
      }
    }
    load();
    return () => {
      ignore = true;
    };
  }, []);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    fetchGraphData(searchQuery);
  };

  const handleReset = () => {
    setSearchQuery("");
    fetchGraphData();
  };

  const filteredNodes = filterCategory === "ALL"
    ? graphData.nodes
    : graphData.nodes.filter(n => n.category === filterCategory);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between pb-4 border-b border-slate-200 gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 flex items-center gap-2">
            <GitFork className="w-6 h-6 text-emerald-600" />
            <span>GraphRAG | Graf Pengetahuan Medis Terstruktur</span>
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Penalaran relasional (Disease, Symptom, Drug, Guideline, Department) yang diinjeksikan secara real-time ke Qwen 3.8-27b untuk pencegahan kontraindikasi.
          </p>
        </div>

        {/* Search & Actions */}
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={handleRunOptimize15}
            disabled={optimizeLoading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 disabled:opacity-50 text-white font-semibold text-xs transition shadow-xs"
            title="Jalankan Optimalisasi 15% Code of Product (Prune Noise & Index Hubs)"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>{optimizeLoading ? "Mengoptimasi 15%..." : "Optimalisasi 15% (Code of Product)"}</span>
          </button>

          <form onSubmit={handleSearch} className="relative flex items-center">
            <Search className="w-3.5 h-3.5 absolute left-3 text-slate-400 pointer-events-none" />
            <input
              type="text"
              placeholder="Cari entitas (mis: Asma, STEMI)..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-8 pr-3 py-1.5 rounded-xl bg-white border border-slate-200 text-xs text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-emerald-500 w-56 shadow-sm"
            />
          </form>

          <button
            onClick={handleReset}
            className="p-2 rounded-xl bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 text-xs transition shadow-sm"
            title="Muat Ulang Seluruh Graf"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* 15% Code of Product Optimization Results Banner */}
      {optimizeResult && (
        <div className="p-4 rounded-2xl bg-gradient-to-r from-emerald-50 via-teal-50 to-cyan-50 border border-emerald-200 shadow-xs space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-emerald-200/60">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-700" />
              <span className="font-bold text-xs text-emerald-900">
                Optimalisasi Graf Berhasil: {optimizeResult.method}
              </span>
            </div>
            <button
              onClick={() => setOptimizeResult(null)}
              className="p-1 rounded-lg text-slate-400 hover:text-slate-700"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
            <div className="p-2.5 rounded-xl bg-white border border-emerald-100 shadow-2xs">
              <span className="text-[10px] text-slate-500 block">Relasi Awal</span>
              <span className="font-bold text-slate-800 text-sm">{optimizeResult.original_edges_count} relasi</span>
            </div>
            <div className="p-2.5 rounded-xl bg-white border border-emerald-100 shadow-2xs">
              <span className="text-[10px] text-emerald-700 font-semibold block">Pruned Noise (Bottom 15%)</span>
              <span className="font-bold text-rose-600 text-sm">-{optimizeResult.pruned_noise_edges_15pct} relasi</span>
            </div>
            <div className="p-2.5 rounded-xl bg-white border border-emerald-100 shadow-2xs">
              <span className="text-[10px] text-slate-500 block">Relasi Dipertahankan</span>
              <span className="font-bold text-emerald-700 text-sm">{optimizeResult.retained_edges_count} relasi</span>
            </div>
            <div className="p-2.5 rounded-xl bg-white border border-emerald-100 shadow-2xs">
              <span className="text-[10px] text-slate-500 block">Candidate Margin</span>
              <span className="font-bold text-cyan-700 text-sm">+{optimizeResult.candidate_margin_pct}% Fast Index</span>
            </div>
          </div>

          {optimizeResult.indexed_top_15pct_hubs.length > 0 && (
            <div className="text-xs">
              <span className="text-[11px] font-semibold text-slate-700 block mb-1.5">
                Top 15% Key Hub Entities (Fast-Retrieval Cache Index):
              </span>
              <div className="flex flex-wrap gap-1.5">
                {optimizeResult.indexed_top_15pct_hubs.map((hub, i) => (
                  <span
                    key={i}
                    className="px-2 py-0.5 rounded-lg bg-white border border-emerald-200 text-[10px] text-slate-800 font-medium shadow-2xs flex items-center gap-1"
                  >
                    <span className="font-bold text-emerald-700">{hub.name}</span>
                    <span className="text-[9px] text-slate-500">({hub.degree} derajat)</span>
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Category Pills & Graph Stats */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-1.5 text-xs">
          {[
            { label: "Semua", value: "ALL", count: graphData.nodes.length, color: "text-slate-700" },
            { label: "Penyakit", value: "DISEASE", count: graphData.nodes.filter(n => n.category === "DISEASE").length, color: "text-rose-600" },
            { label: "Obat", value: "DRUG", count: graphData.nodes.filter(n => n.category === "DRUG").length, color: "text-sky-600" },
            { label: "Gejala", value: "SYMPTOM", count: graphData.nodes.filter(n => n.category === "SYMPTOM").length, color: "text-amber-600" },
            { label: "Pedoman", value: "GUIDELINE", count: graphData.nodes.filter(n => n.category === "GUIDELINE").length, color: "text-emerald-600" },
            { label: "Departemen", value: "DEPARTMENT", count: graphData.nodes.filter(n => n.category === "DEPARTMENT").length, color: "text-violet-600" },
          ].map((cat) => (
            <button
              key={cat.value}
              onClick={() => setFilterCategory(cat.value)}
              className={`px-3 py-1 rounded-lg border text-[11px] font-medium transition ${
                filterCategory === cat.value
                  ? "bg-emerald-50 border-emerald-300 text-emerald-800 shadow-sm"
                  : "bg-white border-slate-200 text-slate-600 hover:bg-slate-50"
              }`}
            >
              <span className={cat.color}>{cat.label}</span>
              <span className="ml-1.5 text-[10px] text-slate-500">({cat.count})</span>
            </button>
          ))}
        </div>

        <div className="text-[11px] text-slate-500 flex items-center gap-3">
          <span>Relasi: <b className="text-slate-900">{graphData.edges.length} relasi</b></span>
          <span>Simpul: <b className="text-slate-900">{filteredNodes.length} / {graphData.nodes.length} entitas</b></span>
        </div>
      </div>

      {error && (
        <div className="p-3 rounded-xl bg-red-50 border border-red-200 text-xs text-red-800">
          {error}
        </div>
      )}

      {/* Main Canvas & Detail Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Cytoscape Canvas Container */}
        <div className="lg:col-span-3 bg-slate-50 rounded-2xl border border-slate-200 p-2 relative min-h-[550px] overflow-hidden shadow-sm flex flex-col">
          <div className="absolute top-4 left-4 z-10 flex items-center gap-2 bg-white/90 backdrop-blur-md px-3 py-1.5 rounded-xl border border-slate-200 text-[11px] text-slate-700 shadow-sm">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            <span>Cytoscape.js Interactive Graph Engine</span>
          </div>

          <div className="absolute top-4 right-4 z-10 flex items-center gap-1.5">
            <button
              onClick={() => cyRef.current?.zoom(cyRef.current.zoom() * 1.2)}
              className="p-1.5 rounded-lg bg-white/90 hover:bg-white border border-slate-200 text-slate-700 transition shadow-sm"
              title="Perbesar"
            >
              <ZoomIn className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => cyRef.current?.zoom(cyRef.current.zoom() * 0.8)}
              className="p-1.5 rounded-lg bg-white/90 hover:bg-white border border-slate-200 text-slate-700 transition shadow-sm"
              title="Perkecil"
            >
              <ZoomOut className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => cyRef.current?.fit()}
              className="p-1.5 rounded-lg bg-white/90 hover:bg-white border border-slate-200 text-slate-700 transition shadow-sm"
              title="Paskan ke Layar"
            >
              <Maximize2 className="w-3.5 h-3.5" />
            </button>
          </div>

          <div
            ref={containerRef}
            className="w-full h-full flex-1 rounded-xl"
            style={{ minHeight: "530px" }}
          />

          {loading && (
            <div className="absolute inset-0 bg-white/80 backdrop-blur-sm flex items-center justify-center z-20">
              <div className="flex flex-col items-center gap-2">
                <RefreshCw className="w-6 h-6 text-emerald-600 animate-spin" />
                <span className="text-xs text-slate-600">Menghitung topologi graf pengetahuan...</span>
              </div>
            </div>
          )}
        </div>

        {/* Node & Edge Inspector Sidebar */}
        <div className="lg:col-span-1 bg-white rounded-2xl border border-slate-200 p-5 space-y-4 shadow-sm">
          <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2 border-b border-slate-100 pb-3">
            <Activity className="w-4 h-4 text-emerald-600" />
            <span>Inspektor Entitas Medis</span>
          </h3>

          {selectedNode ? (
            <div className="space-y-4 text-xs">
              <div>
                <span className="text-[10px] text-slate-500 uppercase tracking-wider font-mono">
                  {selectedNode.category}
                </span>
                <h4 className="text-base font-bold text-slate-900 mt-0.5">
                  {selectedNode.name}
                </h4>
                <div className="text-[10px] text-slate-500 font-mono mt-0.5">
                  ID: {selectedNode.id}
                </div>
              </div>

              {selectedNode.properties && (
                <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 space-y-1">
                  <span className="text-[10px] text-slate-500 font-semibold uppercase">Atribut Medis</span>
                  {Object.entries(selectedNode.properties).map(([k, v]) => (
                    <div key={k} className="text-[11px] text-slate-700">
                      <span className="text-slate-500">{k}:</span> {String(v)}
                    </div>
                  ))}
                </div>
              )}

              {/* Connected Relations */}
              <div className="space-y-2">
                <span className="text-[10px] text-slate-500 font-semibold uppercase">
                  Relasi Terhubung ({connectedEdges.length})
                </span>
                <div className="space-y-1.5 max-h-60 overflow-y-auto pr-1">
                  {connectedEdges.map((edge, i) => {
                    const isSource = edge.source === selectedNode.id;
                    const counterpart = isSource ? edge.target : edge.source;
                    const isContra = edge.relation === "CONTRAINDICATES";

                    return (
                      <div
                        key={i}
                        className={`p-2.5 rounded-lg border text-[11px] ${
                          isContra
                            ? "bg-red-50 border-red-200 text-red-900"
                            : "bg-slate-50 border-slate-200 text-slate-700"
                        }`}
                      >
                        <div className="flex items-center justify-between font-mono text-[10px]">
                          <span className={isContra ? "text-red-600 font-bold" : "text-emerald-700"}>
                            {edge.relation}
                          </span>
                          <span className="text-slate-500">{isSource ? "Outbound ->" : "<- Inbound"}</span>
                        </div>
                        <div className="font-semibold text-slate-900 mt-1">
                          {counterpart}
                        </div>
                        {edge.properties?.notes && (
                          <div className="text-[10px] text-slate-500 mt-1 italic">
                            {edge.properties.notes}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center py-16 text-slate-500 text-xs space-y-2">
              <GitFork className="w-8 h-8 text-slate-400 mx-auto" />
              <p className="text-slate-500">Klik salah satu simpul (node) pada kanvas untuk menginspeksi rincian entitas dan relasi klinis.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
