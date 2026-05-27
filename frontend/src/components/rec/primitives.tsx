import { cn } from "@/lib/utils";

export function Card({
  className,
  children,
  ...props
}: React.HTMLAttributes<HTMLDivElement> & { draggable?: boolean }) {
  return (
    <div className={cn("rounded-lg border border-border bg-card", className)} {...props}>
      {children}
    </div>
  );
}

export function Label({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={cn("text-[10px] font-medium uppercase tracking-wider text-text-tertiary", className)}>
      {children}
    </div>
  );
}

export function Bar({
  value,
  color = "bg-foreground",
  width = 64,
  full = false,
}: {
  value: number;
  color?: string;
  width?: number;
  full?: boolean;
}) {
  return (
    <div
      className={cn(
        "relative h-1 overflow-hidden rounded-full bg-border align-middle",
        full ? "block w-full" : "inline-block",
      )}
      style={full ? undefined : { width }}
    >
      <div
        className={cn("h-full rounded-full animate-bar-grow", color)}
        style={{ ["--bar-w" as string]: `${value}%` }}
      />
    </div>
  );
}

export function Dot({ className }: { className?: string }) {
  return <span className={cn("inline-block h-1.5 w-1.5 rounded-full", className)} />;
}

export function Square({ className }: { className?: string }) {
  return <span className={cn("inline-block h-2.5 w-2.5 rounded-[2px]", className)} />;
}