import type { SearchMode } from "../api/search";

export type DemoStep = {
  title: string;
  actionLabel: string;
  detail: string;
  narration: string;
  mode: Exclude<SearchMode, "compare">;
  profileId: string;
  promotionId: string | null;
  prefixMatching?: boolean;
};

export type DemoPath = {
  id: string;
  label: string;
  summary: string;
  query: string;
  steps: DemoStep[];
};

export type RetailerTheme = {
  accent: string;
  accentBorder: string;
  accentStrong: string;
  accentSoft: string;
  bodyMuted: string;
  canvas: string;
  codeSurface: string;
  heading: string;
  ink: string;
  muted: string;
  panel: string;
  border: string;
  borderSoft: string;
  focus: string;
  successInk: string;
  successSoft: string;
  subtle: string;
};

export type RetailerExperience = {
  id: string;
  theme: RetailerTheme;
  demoPaths: DemoPath[];
};
