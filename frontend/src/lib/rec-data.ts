export type IdeaStatus = "backlog" | "ideation" | "analysis" | "prototype";

export interface Idea {
  id: string;
  title: string;
  impact: number;
  effort: number;
  value: number;
  status: IdeaStatus;
  contributors: number;
  sources: string[];
  /** Set when loaded from the recommendation API */
  score?: number;
  writeup?: string | null;
}

export const ideas: Idea[] = [
  {
    id: "1",
    title: "AI Content Discovery Engine",
    impact: 92,
    effort: 65,
    value: 88,
    status: "prototype",
    contributors: 14,
    sources: ["12 interviews", "47 community votes", "8 market signals"],
  },
  {
    id: "2",
    title: "Adaptive Challenge Generator",
    impact: 88,
    effort: 78,
    value: 82,
    status: "ideation",
    contributors: 9,
    sources: ["8 interviews", "31 community votes", "5 market signals"],
  },
  {
    id: "3",
    title: "Cross-Team Innovation Spaces",
    impact: 80,
    effort: 55,
    value: 85,
    status: "analysis",
    contributors: 11,
    sources: ["10 interviews", "28 community votes", "4 market signals"],
  },
  {
    id: "4",
    title: "Personalized Learning Pathways",
    impact: 85,
    effort: 70,
    value: 79,
    status: "ideation",
    contributors: 7,
    sources: ["6 interviews", "22 community votes", "6 market signals"],
  },
  {
    id: "5",
    title: "Low-Code ML Pipeline Builder",
    impact: 75,
    effort: 82,
    value: 72,
    status: "backlog",
    contributors: 5,
    sources: ["4 interviews", "15 community votes", "3 market signals"],
  },
  {
    id: "6",
    title: "Trend Intelligence Feed",
    impact: 68,
    effort: 45,
    value: 76,
    status: "backlog",
    contributors: 4,
    sources: ["3 interviews", "11 community votes", "9 market signals"],
  },
];

export const compositeScore = (i: Pick<Idea, "impact" | "effort" | "value">) =>
  i.impact * 0.4 + i.value * 0.35 + (100 - i.effort) * 0.25;

/** Kanban column order (left → right). */
export const statusColumnOrder: IdeaStatus[] = ["ideation", "backlog", "analysis", "prototype"];

export const statusMeta: Record<IdeaStatus, { label: string; dot: string; text: string }> = {
  backlog: { label: "Backlog", dot: "bg-brand-gray", text: "text-brand-gray" },
  ideation: { label: "Ideation", dot: "bg-brand-purple", text: "text-brand-purple" },
  analysis: { label: "Analysis", dot: "bg-brand-blue", text: "text-brand-blue" },
  prototype: { label: "Prototype", dot: "bg-brand-green", text: "text-brand-green" },
};

export type SignalSource = "interviews" | "community" | "market" | "events";

export const signalMeta: Record<SignalSource, { label: string; color: string; count: number }> = {
  interviews: { label: "Interviews", color: "bg-brand-blue", count: 6 },
  community: { label: "Community", color: "bg-brand-amber", count: 5 },
  market: { label: "Market", color: "bg-brand-green", count: 4 },
  events: { label: "Event Outcomes", color: "bg-brand-purple", count: 5 },
};

export const signals: Record<SignalSource, Array<{ text: string; trend?: "up" | "down"; votes?: number; relevance?: number }>> = {
  interviews: [
    { text: "Users want smarter content recommendations across teams", trend: "up", votes: 18 },
    { text: "Need faster onboarding for new innovation challenges", trend: "up", votes: 14 },
    { text: "Cross-functional collaboration is a recurring blocker", trend: "up", votes: 12 },
    { text: "Personalized learning would boost participation", trend: "up", votes: 9 },
    { text: "Difficulty discovering past prototypes", trend: "down", votes: 7 },
    { text: "Wish for clearer scoring on submitted ideas", trend: "up", votes: 5 },
  ],
  community: [
    { text: "Idea board needs voting weight by expertise", trend: "up", votes: 47 },
    { text: "Add tags for SAP product areas", trend: "up", votes: 31 },
    { text: "Show contributor reputation on each idea", trend: "up", votes: 28 },
    { text: "Comment threads for ideation phase", trend: "up", votes: 22 },
    { text: "Weekly digest of top-ranked ideas", trend: "down", votes: 15 },
  ],
  market: [
    { text: "Generative AI in enterprise content tools", relevance: 94 },
    { text: "Adaptive learning platforms for B2B", relevance: 81 },
    { text: "Low-code ML pipeline adoption rising", relevance: 72 },
    { text: "Trend intelligence dashboards in SaaS", relevance: 65 },
  ],
  events: [
    { text: "Spring Hackathon: 12 prototypes shipped, AI-assist track winner", trend: "up", votes: 42 },
    { text: "Innovation Day: cross-team pairing produced 8 new ideas", trend: "up", votes: 31 },
    { text: "Design Jam: personalization theme dominated submissions", trend: "up", votes: 24 },
    { text: "ML Workshop: low-code pipelines requested by 18 attendees", trend: "up", votes: 18 },
    { text: "Community Meetup: trend-feed concept validated by builders", trend: "down", votes: 11 },
  ],
};

export const insights = [
  {
    category: "Pattern",
    confidence: 91,
    description:
      "Personalization features have 2.3× higher engagement than generic content recommendations across the last 6 cohorts.",
  },
  {
    category: "Correlation",
    confidence: 84,
    description:
      "Interview themes and market trends are 78% aligned — strong signal that user pain points reflect broader industry direction.",
  },
  {
    category: "Quick Win",
    confidence: 88,
    description:
      "Trend Intelligence Feed has the best effort-to-value ratio in the current backlog. Recommend promoting to analysis.",
  },
  {
    category: "Loop Status",
    confidence: 95,
    description:
      "23 outcomes tracked since last retrain. Model accuracy improved from 72% → 87% over the most recent 4 cycles.",
  },
];