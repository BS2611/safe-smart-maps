import Link from "next/link";
import type { ReactNode } from "react";

import { BackIcon, BrandMark } from "./Icons";

type Props = { title?: string; subtitle?: string; backHref?: string; right?: ReactNode };

export function AppHeader({ title, subtitle, backHref, right }: Props) {
  return (
    <header className="app-header row between">
      <div className="row grow">
        {backHref ? (
          <Link href={backHref} className="icon-btn" aria-label="Back">
            <BackIcon />
          </Link>
        ) : (
          <span className="brand-mark"><BrandMark /></span>
        )}
        <div className="grow">
          {title ? <h1 className="brand">{title}</h1> : <div className="brand">Safe Smart Maps</div>}
          {subtitle ? <div className="caption">{subtitle}</div> : null}
        </div>
      </div>
      {right}
    </header>
  );
}
