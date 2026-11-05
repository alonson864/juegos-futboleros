/** Cancha completa dibujada con líneas de cal. Se usa de fondo, en perspectiva. */
export function Cancha({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 1050 680" className={className} aria-hidden="true" preserveAspectRatio="xMidYMid slice">
      <g fill="none" stroke="var(--cal)" strokeWidth="3">
        <rect x="25" y="25" width="1000" height="630" />
        <line x1="525" y1="25" x2="525" y2="655" />
        <circle cx="525" cy="340" r="91.5" />
        <circle cx="525" cy="340" r="4" fill="var(--cal)" />
        {/* Áreas grandes y chicas */}
        <rect x="25" y="138.5" width="165" height="403" />
        <rect x="860" y="138.5" width="165" height="403" />
        <rect x="25" y="248.5" width="55" height="183" />
        <rect x="970" y="248.5" width="55" height="183" />
        {/* Puntos penales y medialunas */}
        <circle cx="135" cy="340" r="4" fill="var(--cal)" />
        <circle cx="915" cy="340" r="4" fill="var(--cal)" />
        <path d="M190 287 A91.5 91.5 0 0 1 190 393" />
        <path d="M860 287 A91.5 91.5 0 0 0 860 393" />
        {/* Esquinas */}
        <path d="M25 35 A10 10 0 0 0 35 25" />
        <path d="M1015 25 A10 10 0 0 0 1025 35" />
        <path d="M25 645 A10 10 0 0 1 35 655" />
        <path d="M1015 655 A10 10 0 0 1 1025 645" />
      </g>
    </svg>
  );
}

/** Logo: pelota simple. */
export function Pelota({ className = "h-7 w-7" }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true">
      <circle cx="12" cy="12" r="10.5" fill="currentColor" />
      <path d="M12 7.2l3.6 2.6-1.4 4.2H9.8L8.4 9.8z" fill="var(--cancha)" />
      <path
        d="M12 1.5v5.7M15.6 9.8l5.6-1.8M14.2 14l3.4 4.6M9.8 14l-3.4 4.6M8.4 9.8L2.8 8"
        stroke="var(--cancha)"
        strokeWidth="1.4"
        fill="none"
      />
    </svg>
  );
}
