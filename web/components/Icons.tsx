// Small outline icons (inline SVG, decorative: hidden from screen readers).
import type { ReactNode } from "react";

function Svg({ children, size = 20 }: { children: ReactNode; size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">
      {children}
    </svg>
  );
}

export const RouteIcon = () => (<Svg><circle cx="6" cy="19" r="2" /><circle cx="18" cy="5" r="2" /><path d="M6 17V9a3 3 0 0 1 3-3h6" /></Svg>);
export const StoreIcon = () => (<Svg><path d="M4 9l1-5h14l1 5" /><path d="M5 9v10h14V9" /><path d="M10 19v-5h4v5" /></Svg>);
export const ClockIcon = () => (<Svg><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></Svg>);
export const InfoIcon = () => (<Svg><circle cx="12" cy="12" r="9" /><path d="M12 11v5M12 8h.01" /></Svg>);
export const BackIcon = () => (<Svg><path d="M15 5l-7 7 7 7" /></Svg>);
export const SwapIcon = () => (<Svg><path d="M7 4v14M7 18l-3-3M7 18l3-3M17 20V6M17 6l-3 3M17 6l3 3" /></Svg>);
export const SearchIcon = () => (<Svg><circle cx="11" cy="11" r="6" /><path d="M20 20l-4-4" /></Svg>);
export const LocationOffIcon = () => (<Svg><path d="M12 21s6-5.5 6-11a6 6 0 0 0-12 0c0 5.5 6 11 6 11z" /><path d="M4 4l16 16" /></Svg>);
export const CheckIcon = () => (<Svg><path d="M5 12l5 5 9-10" /></Svg>);
export const WalkIcon = () => (<Svg><circle cx="13" cy="4" r="1.5" /><path d="M10 21l2-6-2-3 1-4 3 2 2 2M8 11l3-3" /></Svg>);
export const SlidersIcon = () => (<Svg><path d="M4 7h10M18 7h2M4 17h2M10 17h10" /><circle cx="16" cy="7" r="2" /><circle cx="8" cy="17" r="2" /></Svg>);
export const CloseIcon = () => (<Svg><path d="M6 6l12 12M18 6L6 18" /></Svg>);
export const RefreshIcon = () => (<Svg><path d="M20 11a8 8 0 1 0-2 6" /><path d="M20 5v6h-6" /></Svg>);
export const HourglassIcon = () => (<Svg><path d="M6 3h12M6 21h12M7 3c0 5 5 5 5 9s-5 4-5 9M17 3c0 5-5 5-5 9s5 4 5 9" /></Svg>);

export function BrandMark() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#89d5bc" strokeWidth="2"
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">
      <circle cx="5" cy="19" r="2" /><circle cx="19" cy="5" r="2" /><path d="M7 19h6a4 4 0 0 0 4-4V9" />
    </svg>
  );
}
