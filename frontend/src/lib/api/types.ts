import type { components } from "./schema";

/** Named aliases over the generated OpenAPI types. Never redeclare these by hand. */
type Schemas = components["schemas"];

export type TeamRef = Schemas["TeamRef"];
export type CompetitionRef = Schemas["CompetitionRef"];
export type MatchScore = Schemas["MatchScore"];
export type MatchSummary = Schemas["MatchSummary"];
export type MatchStatus = MatchSummary["status"];
export type FinishType = NonNullable<MatchSummary["finishType"]>;

export type TopMatches = Schemas["TopMatches"];
export type TopMatchItem = Schemas["TopMatchItem"];
export type TopMatchesState = TopMatches["state"];

export type FeedbackCreate = Schemas["FeedbackCreate"];
export type FeedbackType = NonNullable<FeedbackCreate["type"]>;
export type FeedbackReceipt = Schemas["FeedbackReceipt"];

export type ErrorResponse = Schemas["ErrorResponse"];
