import type { ReactNode } from "react";

type Kind = "info" | "warn" | "error";

export function Banner({ kind = "info", title, children }: { kind?: Kind; title?: string; children?: ReactNode }) {
  return (
    <div className={`banner ${kind}`} role={kind === "error" ? "alert" : "status"}>
      {title ? <h3>{title}</h3> : null}
      {children ? <div className="small muted">{children}</div> : null}
    </div>
  );
}
