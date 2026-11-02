"use client";

import React from "react";

/**
 * Avatar orang beranimasi (menggantikan ikon robot).
 * Kepala bergerak halus seperti bernapas dan mata berkedip. Animasi dimatikan
 * otomatis jika pengguna memilih "kurangi gerakan" di perangkatnya.
 */
export default function PersonAvatar({
  className = "w-5 h-5",
  talking = false,
}: {
  className?: string;
  talking?: boolean;
}) {
  return (
    <svg
      viewBox="0 0 48 48"
      className={className}
      role="img"
      aria-label="Asisten kesehatan"
      fill="none"
    >
      <g className="person-body">
        <path d="M8 46c0-9 7-15 16-15s16 6 16 15" fill="currentColor" opacity="0.9" />
        <g className="person-head">
          <circle cx="24" cy="19" r="9" fill="#fde7d3" />
          <path d="M14.5 17c0-6 4.2-9.5 9.5-9.5s9.5 3.5 9.5 9.5c-3-2-5.5-3.2-9.5-3.2S17.5 15 14.5 17z" fill="#3b2f2a" />
          <g className="person-eyes" fill="#3b2f2a">
            <ellipse cx="20.5" cy="19.5" rx="1.2" ry="1.5" />
            <ellipse cx="27.5" cy="19.5" rx="1.2" ry="1.5" />
          </g>
          {talking ? (
            <ellipse className="person-mouth" cx="24" cy="24.5" rx="2" ry="1.4" fill="#b4533c" />
          ) : (
            <path d="M21.5 24c1.4 1.4 3.6 1.4 5 0" stroke="#b4533c" strokeWidth="1.2" strokeLinecap="round" />
          )}
        </g>
      </g>
    </svg>
  );
}
