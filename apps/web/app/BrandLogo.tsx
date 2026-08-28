export default function BrandLogo({className = ""}: {className?: string}) {
  return (
    <span className={`brand-logo${className ? ` ${className}` : ""}`} aria-hidden="true">
      <svg width="24" height="24" viewBox="0 0 32 32" fill="none" focusable="false">
        <path className="brand-logo-route" d="M7.5 21.5 13 16l4.2 3.2L24.5 10" stroke="currentColor" />
        <path className="brand-logo-arrow" d="M19.3 10h5.2v5.2" stroke="currentColor" />
        <circle cx="7.5" cy="21.5" r="2" fill="currentColor" />
        <circle cx="13" cy="16" r="2" fill="currentColor" />
        <circle cx="17.2" cy="19.2" r="2" fill="currentColor" />
      </svg>
    </span>
  );
}
