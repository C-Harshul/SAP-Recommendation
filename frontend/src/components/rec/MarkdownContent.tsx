import ReactMarkdown from "react-markdown";
import { cn } from "@/lib/utils";

interface MarkdownContentProps {
  content: string;
  className?: string;
}

/** Renders mission writeups and other engine markdown (## headings, lists, etc.). */
export function MarkdownContent({ content, className }: MarkdownContentProps) {
  return (
    <div
      className={cn(
        "prose prose-sm max-w-none dark:prose-invert",
        "prose-headings:font-semibold prose-headings:text-foreground",
        "prose-p:text-text-secondary prose-p:leading-relaxed",
        "prose-li:text-text-secondary prose-strong:text-foreground",
        "prose-a:text-sap-amber prose-a:no-underline hover:prose-a:underline",
        className,
      )}
    >
      <ReactMarkdown>{content}</ReactMarkdown>
    </div>
  );
}
