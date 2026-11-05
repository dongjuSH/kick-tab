import type { components, paths } from "./schema";

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
export type TopMatchesView = TopMatches["view"];
export type TopMatchesMeta = Schemas["TopMatchesMeta"];
export type TopMatchesVersion = Schemas["TopMatchesVersion"];

export type MatchInfo = Schemas["MatchInfo"];
export type UpdatedMeta = Schemas["UpdatedMeta"];
export type MatchRecords = Schemas["MatchRecords"];
export type BlockStatus = MatchRecords["events"]["status"];
export type MatchEvent = Schemas["MatchEvent"];
export type StatRow = Schemas["StatRow"];
export type TeamLineup = Schemas["TeamLineup"];
export type LineupPlayer = Schemas["LineupPlayer"];
export type PlayerRating = Schemas["PlayerRating"];
export type HeadToHead = Schemas["HeadToHead"];
export type PastMeeting = Schemas["PastMeeting"];
export type FormMatch = Schemas["FormMatch"];
export type FormBlock = Schemas["FormBlock"];
export type ReviewList = Schemas["ReviewList"];
export type ReviewItem = Schemas["ReviewItem"];
export type ReviewSort = NonNullable<
  NonNullable<NonNullable<paths["/api/v1/fixtures/{fixture_id}/reviews"]["get"]["parameters"]["query"]>["sort"]>
>;

export type CompetitionItem = Schemas["CompetitionItem"];
export type CompetitionGroup = CompetitionItem["group"];
export type SeasonItem = Schemas["SeasonItem"];
export type ResultsPage = Schemas["ResultsPage"];
export type ResultsMeta = Schemas["ResultsMeta"];
export type ScheduleMeta = Schemas["ScheduleMeta"];
export type FixtureAvailability = Schemas["FixtureAvailability"];
export type FavoriteSchedule = Schemas["FavoriteSchedule"];
export type TeamSchedule = Schemas["TeamSchedule"];
export type NewsItem = Schemas["NewsItem"];
export type NewsBadge = NonNullable<NewsItem["badge"]>;
export type NewsMeta = Schemas["NewsMeta"];
export type NewsLink = Schemas["NewsLink"];

export type FeedbackCreate = Schemas["FeedbackCreate"];
export type FeedbackType = NonNullable<FeedbackCreate["type"]>;
export type FeedbackReceipt = Schemas["FeedbackReceipt"];

export type ErrorResponse = Schemas["ErrorResponse"];
