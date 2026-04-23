import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { fetchCandidateDetail, fetchCandidateSummary, fetchEmailDraft, fetchRoleAlignment } from "../services/api";

function CandidateDetail({ candidate }) {
  const [detail, setDetail] = useState(null);
  const [summary, setSummary] = useState(null);
  const [emailDraft, setEmailDraft] = useState(null);
  const [jobDescription, setJobDescription] = useState("");
  const [roleAlignment, setRoleAlignment] = useState(null);
  const [roleAlignmentStatus, setRoleAlignmentStatus] = useState("idle");

  useEffect(() => {
    if (!candidate?.id) {
      setDetail(null);
      setSummary(null);
      setEmailDraft(null);
      setRoleAlignment(null);
      setRoleAlignmentStatus("idle");
      return;
    }

    fetchCandidateDetail(candidate.id)
      .then(setDetail)
      .catch(() => setDetail(null));

    fetchCandidateSummary(candidate.id)
      .then(setSummary)
      .catch(() => setSummary(null));

    fetchEmailDraft(candidate.id)
      .then(setEmailDraft)
      .catch(() => setEmailDraft(null));
  }, [candidate]);

  const handleRoleAlignment = async () => {
    if (!candidate?.id) return;
    if (!jobDescription.trim()) {
      setRoleAlignment({ error: "Paste a job description first." });
      setRoleAlignmentStatus("error");
      return;
    }
    setRoleAlignmentStatus("loading");
    try {
      const data = await fetchRoleAlignment(candidate.id, jobDescription);
      setRoleAlignment(data?.alignment || null);
      setRoleAlignmentStatus("done");
    } catch (error) {
      setRoleAlignment({ error: "Failed to compute alignment." });
      setRoleAlignmentStatus("error");
    }
  };

  const parsedObject = useMemo(() => {
    if (!detail?.parsed_json) return null;
    if (typeof detail.parsed_json === "string") {
      try {
        return JSON.parse(detail.parsed_json);
      } catch (error) {
        return null;
      }
    }
    return detail.parsed_json;
  }, [detail]);

  const contactInfo = useMemo(() => {
    if (!parsedObject?.personal_info) return [];
    const info = parsedObject.personal_info;
    const items = [];
    if (info.email) items.push({ label: "Email", value: info.email });
    if (info.phone) items.push({ label: "Phone", value: info.phone });
    if (info.location) items.push({ label: "Location", value: info.location });
    if (info.linkedin) items.push({ label: "LinkedIn", value: info.linkedin });
    if (info.google_scholar) items.push({ label: "Google Scholar", value: info.google_scholar });
    return items;
  }, [parsedObject]);

  const missingFields = useMemo(() => {
    const missing = parsedObject?.missing_info;
    if (Array.isArray(missing)) {
      return missing.map((item) => String(item).trim()).filter(Boolean);
    }
    if (missing && Array.isArray(missing.missing_fields)) {
      return missing.missing_fields.map((item) => String(item).trim()).filter(Boolean);
    }
    return [];
  }, [parsedObject]);

  const timelineData = useMemo(() => {
    if (!parsedObject) return [];
    const parsed = parsedObject;
    const education = Array.isArray(parsed.education) ? parsed.education : [];
    const experience = Array.isArray(parsed.experience) ? parsed.experience : [];
    const gaps = Array.isArray(parsed["gaps in experience"]) ? parsed["gaps in experience"] : [];

    const items = [];

    const parseYear = (value) => {
      const year = Number.parseInt(String(value || "").trim(), 10);
      return Number.isFinite(year) ? year : null;
    };

    const monthMap = {
      jan: 0,
      feb: 1,
      mar: 2,
      apr: 3,
      may: 4,
      jun: 5,
      jul: 6,
      aug: 7,
      sep: 8,
      sept: 8,
      oct: 9,
      nov: 10,
      dec: 11,
    };

    const parseDateToken = (token, isEnd) => {
      if (!token) return null;
      const cleaned = token.trim().toLowerCase();
      if (!cleaned) return null;
      if (["present", "current", "now", "to date"].includes(cleaned)) {
        return new Date();
      }

      const yearOnly = parseYear(cleaned);
      if (yearOnly) {
        return isEnd ? new Date(yearOnly, 11, 31) : new Date(yearOnly, 0, 1);
      }

      const parts = cleaned.replace(/[()]/g, "").split(/[-/\s]+/).filter(Boolean);
      if (parts.length >= 2) {
        const monthToken = parts[0].slice(0, 3);
        const yearToken = parseYear(parts[1]);
        const month = monthMap[monthToken];
        if (Number.isFinite(yearToken) && month !== undefined) {
          return isEnd ? new Date(yearToken, month + 1, 0) : new Date(yearToken, month, 1);
        }
      }

      const parsed = new Date(token);
      return Number.isNaN(parsed.getTime()) ? null : parsed;
    };

    const parseDuration = (value) => {
      if (!value) return { start: null, end: null };
      const normalized = value.replace("–", "-");
      const parts = normalized.split(/\s+-\s+|\s+to\s+/i).map((part) => part.trim());
      if (parts.length === 1) {
        return { start: parseDateToken(parts[0], false), end: null };
      }
      return {
        start: parseDateToken(parts[0], false),
        end: parseDateToken(parts[1], true),
      };
    };

    education.forEach((entry, index) => {
      const year = parseYear(entry.passing_year);
      if (!year) return;
      items.push({
        id: `edu-${index}`,
        label: entry.degree || entry.institution || "Education",
        type: "education",
        start: new Date(year, 0, 1),
        end: new Date(year, 11, 31),
      });
    });

    experience.forEach((entry, index) => {
      const { start, end } = parseDuration(entry.duration_of_employment);
      if (!start) return;
      items.push({
        id: `exp-${index}`,
        label: entry.role || entry.organization || "Role",
        type: "experience",
        start,
        end: end || new Date(),
      });
    });

    gaps.forEach((gap, index) => {
      const start = gap.start_date ? new Date(gap.start_date) : null;
      const end = gap.end_date ? new Date(gap.end_date) : null;
      if (!start || !end) return;
      items.push({
        id: `gap-${index}`,
        label: "Gap",
        type: "gap",
        start,
        end,
      });
    });

    if (!items.length) return [];

    const MIN_YEAR = 1990;

    const isValidDate = (date) => {
      return date instanceof Date && !Number.isNaN(date.getTime());
    };

    const isAfterMinYear = (date) => {
      return date.getFullYear() >= MIN_YEAR;
    };

    // Filter out anomalous items
    const filteredItems = items.filter((item) => {
      if (!isValidDate(item.start) || !isValidDate(item.end)) return false;

      // Exclude anything that starts OR ends before 1990
      if (!isAfterMinYear(item.start) || !isAfterMinYear(item.end)) {
        return false;
      }

      return true;
    });

    // Sort items by start time
    filteredItems.sort((a, b) => a.start - b.start);

    // Helper to check if a gap exists between two dates
    const hasExplicitGap = (start, end) => {
      return filteredItems.some(
        (item) =>
          item.type === "gap" &&
          item.start <= end &&
          item.end >= start
      );
    };

    // Normalize gaps
    for (let i = 1; i < filteredItems.length; i++) {
      const prev = filteredItems[i - 1];
      const current = filteredItems[i];

      if (!prev.end || !current.start) continue;

      const gapExists = current.start > prev.end;

      if (gapExists && !hasExplicitGap(prev.end, current.start)) {
        // Extend current item backwards to connect
        current.start = new Date(prev.end);
      }
    }

    const minStart = Math.min(...filteredItems.map((item) => item.start.getTime()));
    const maxEnd = Math.max(...filteredItems.map((item) => item.end.getTime()));
    const colors = {
      education: "#0ea5e9",
      experience: "#10b981",
      gap: "#f97316",
    };

    return filteredItems.map((item) => ({
      ...item,
      offset: item.start.getTime() - minStart,
      duration: item.end.getTime() - item.start.getTime() || 1,
      minStart,
      maxEnd,
      color: colors[item.type] || "#94a3b8",
    }));
  }, [parsedObject]);

  const scoreTrend = useMemo(() => {
    if (!parsedObject) return [];
    const education = Array.isArray(parsedObject.education) ? parsedObject.education : [];
    return education
      .map((entry) => ({
        label: entry.degree || entry.institution || "Education",
        year: Number.parseInt(String(entry.passing_year || ""), 10) || null,
        normalized_score: Number(entry.normalized_score),
      }))
      .filter((item) => Number.isFinite(item.normalized_score))
      .sort((a, b) => (a.year || 0) - (b.year || 0));
  }, [parsedObject]);

  const coAuthors = useMemo(() => {
    if (!parsedObject) return [];
    const publications = Array.isArray(parsedObject.publications)
      ? parsedObject.publications
      : [];
    const candidateName = String(parsedObject.personal_info?.full_name || "").toLowerCase();
    const names = publications
      .flatMap((pub) =>
        String(pub["co-author"] || "")
          .split(/,|;|\band\b/gi)
          .map((name) => name.replace(/[*\d]/g, "").trim())
          .filter(Boolean)
      )
      .filter((name) => name.length > 1)
      .filter((name) => !candidateName || !name.toLowerCase().includes(candidateName));
    return Array.from(new Set(names));
  }, [parsedObject]);

  const formatTimelineTick = (value) => {
    if (!timelineData.length) return "";
    const base = timelineData[0].minStart;
    const date = new Date(base + value);
    return date.getFullYear();
  };

  const formatTimelineTooltip = ({ active, payload }) => {
    if (!active || !payload?.length) return null;
    const data = payload[0].payload;
    const start = data.start?.toLocaleDateString() || "-";
    const end = data.end?.toLocaleDateString() || "-";
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-3 text-xs shadow-lg">
        <p className="font-semibold text-slate-800">{data.label}</p>
        <p className="text-slate-500">{data.type}</p>
        <p className="mt-1 text-slate-700">
          {start} - {end}
        </p>
      </div>
    );
  };

  return (
    <section className="panel p-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="pill">Candidate Deep Dive</p>
          <h2 className="display-font text-xl font-semibold text-slate-900">
            Candidate Analysis + Email Draft
          </h2>
        </div>
        {candidate?.id ? (
          <Link
            to={`/analysis?candidate=${candidate.id}`}
            className="rounded-full border border-slate-200 bg-white/70 px-4 py-2 text-xs font-semibold uppercase tracking-wide text-slate-700 transition hover:bg-slate-900 hover:text-white"
          >
            Open Analysis Page
          </Link>
        ) : null}
      </div>
      {!candidate ? <p className="mt-3 text-sm text-slate-600">Select a candidate to view detail.</p> : null}
      {detail ? (
        <div className="mt-5">
          <div className="space-y-4">
            <div className="panel-muted p-4">
              <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-600">Summary</h3>
              <div className="mt-2 space-y-2 text-sm text-slate-700">
                <p className="font-semibold text-slate-900">
                  {parsedObject?.personal_info?.full_name || "Full name not available"}
                </p>
                {summary?.message ? (
                  <p className="text-sm text-slate-700 whitespace-pre-line">{summary.message}</p>
                ) : null}
                {summary?.status ? (
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Status: {summary.status}
                  </p>
                ) : null}
                {contactInfo.length > 0 ? (
                  <div className="grid gap-1">
                    {contactInfo.map((item) => (
                      <p key={item.label}>
                        <span className="font-semibold text-slate-600">{item.label}:</span> {item.value}
                      </p>
                    ))}
                  </div>
                ) : (
                  // <p className="text-slate-600">Contact information not available.</p>
                  null
                )}
              </div>
            </div>

            <div className="panel-muted p-4">
              <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-600">Job Role Alignment</h3>
              <p className="mt-2 text-sm text-slate-600">
                Paste a job description to score the candidate's extracted skills against it.
              </p>
              <textarea
                value={jobDescription}
                onChange={(event) => setJobDescription(event.target.value)}
                rows={5}
                className="mt-3 w-full rounded-xl border border-slate-200 bg-white/80 px-3 py-2 text-sm shadow-sm"
                placeholder="Job description / requirements..."
              />
              <div className="mt-3 flex items-center gap-3">
                <button
                  type="button"
                  onClick={handleRoleAlignment}
                  className="rounded-full border border-slate-200 bg-white/70 px-4 py-2 text-xs font-semibold uppercase tracking-wide text-slate-700 transition hover:bg-slate-900 hover:text-white"
                  disabled={roleAlignmentStatus === "loading"}
                >
                  {roleAlignmentStatus === "loading" ? "Scoring..." : "Score Alignment"}
                </button>
                {roleAlignment?.coverage ? (
                  <p className="text-xs text-slate-600">
                    Matched {roleAlignment.coverage.skills_matched_70_plus} / {roleAlignment.coverage.skills_considered} skills (70+)
                  </p>
                ) : null}
              </div>

              {roleAlignment?.top_matches?.length ? (
                <div className="mt-4 grid gap-2">
                  {roleAlignment.top_matches.slice(0, 8).map((match) => (
                    <div key={match.skill} className="flex items-center justify-between rounded-xl border border-slate-200 bg-white/70 px-3 py-2 text-sm">
                      <span className="font-semibold text-slate-700">{match.skill}</span>
                      <span className="text-slate-600">{match.job_match_score}</span>
                    </div>
                  ))}
                </div>
              ) : roleAlignment?.error ? (
                <p className="mt-3 text-sm text-rose-600">{roleAlignment.error}</p>
              ) : roleAlignmentStatus === "done" ? (
                <p className="mt-3 text-sm text-slate-600">No matches found.</p>
              ) : null}
            </div>

            <div className="panel-muted p-4">
              <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-600">
                Missing Information + Email Draft
              </h3>
              {missingFields.length === 0 ? (
                <p className="mt-2 text-sm text-slate-600">No missing fields detected.</p>
              ) : (
                <div className="mt-3">
                  <p className="text-sm text-slate-700 font-semibold">Missing fields:</p>
                  <ul className="mt-2 grid gap-1 text-sm text-slate-700 list-disc list-inside">
                    {missingFields.map((field) => (
                      <li key={field}>{field}</li>
                    ))}
                  </ul>
                </div>
              )}
              {emailDraft?.draft ? (
                <pre className="mt-4 whitespace-pre-wrap rounded-xl border border-slate-200 bg-white/70 p-3 text-xs text-slate-700">
                  {emailDraft.draft}
                </pre>
              ) : null}
            </div>

            <div className="panel-muted p-4">
              <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-600">
                Timeline: Education, Employment, and Gaps
              </h3>
              {timelineData.length === 0 ? (
                <p className="mt-2 text-sm text-slate-600">Timeline data not available.</p>
              ) : (
                <div className="mt-3 h-72">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={timelineData} layout="vertical" margin={{ left: 10, right: 20 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                      <XAxis
                        type="number"
                        tickFormatter={formatTimelineTick}
                        domain={[0, "dataMax"]}
                        tick={{ fontSize: 11 }}
                      />
                      <YAxis
                        type="category"
                        dataKey="label"
                        width={140}
                        tick={{ fontSize: 11 }}
                      />
                      <Tooltip content={formatTimelineTooltip} />
                      <Bar dataKey="offset" stackId="timeline" fill="transparent" />
                      <Bar dataKey="duration" stackId="timeline" radius={[6, 6, 6, 6]}>
                        {timelineData.map((entry) => (
                          <Cell key={entry.id} fill={entry.color} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}
              <div className="mt-3 flex flex-wrap gap-3 text-xs font-semibold uppercase tracking-wide text-slate-500">
                <span className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-sky-500" /> Education
                </span>
                <span className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-emerald-500" /> Employment
                </span>
                <span className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-orange-500" /> Gaps
                </span>
              </div>
            </div>

            <div className="panel-muted p-4">
              <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-600">Co-Author Spotlight</h3>
              {coAuthors.length === 0 ? (
                <p className="mt-2 text-sm text-slate-600">No co-author data available.</p>
              ) : (
                <div className="mt-3 flex flex-wrap gap-2">
                  {coAuthors.map((name) => (
                    <span
                      key={name}
                      className="rounded-full border border-slate-200 bg-white/70 px-3 py-1 text-xs font-semibold text-slate-700"
                    >
                      {name}
                    </span>
                  ))}
                </div>
              )}
            </div>

            <div className="panel-muted p-4">
              <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-600">
                Normalized Score Trend
              </h3>
              {scoreTrend.length === 0 ? (
                <p className="mt-2 text-sm text-slate-600">Normalized scores not available.</p>
              ) : (
                <div className="mt-3 h-56">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={scoreTrend} margin={{ left: 10, right: 20 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                      <XAxis dataKey="label" tick={{ fontSize: 10 }} interval={0} angle={-12} height={60} />
                      <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} />
                      <Tooltip />
                      <Line type="monotone" dataKey="normalized_score" stroke="#0f766e" strokeWidth={2} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              )}
            </div>
          </div>
        </div>
      ) : null}
    </section>
  );
}

export default CandidateDetail;
