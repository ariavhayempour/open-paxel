import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchActiveJobs, fetchJob, type ProcessingJob } from "../lib/api";

const ACTIVE_JOB_KEY = "brain-dump-active-job-id";

export function getStoredJobId(): string | null {
  try {
    return localStorage.getItem(ACTIVE_JOB_KEY);
  } catch {
    return null;
  }
}

export function setStoredJobId(id: string | null) {
  try {
    if (id) localStorage.setItem(ACTIVE_JOB_KEY, id);
    else localStorage.removeItem(ACTIVE_JOB_KEY);
  } catch {
    /* ignore */
  }
}

function isActive(job: ProcessingJob) {
  return job.status === "queued" || job.status === "processing";
}

export function JobProgressBanner() {
  const queryClient = useQueryClient();
  const [storedId, setStoredId] = useState<string | null>(() => getStoredJobId());
  const [trackedJobId, setTrackedJobId] = useState<string | null>(() => getStoredJobId());

  useEffect(() => {
    const id = getStoredJobId();
    setStoredId(id);
    setTrackedJobId(id);
  }, []);

  const { data: activeJobs } = useQuery({
    queryKey: ["jobs", "active"],
    queryFn: fetchActiveJobs,
    refetchInterval: (query) => ((query.state.data?.length ?? 0) > 0 || !!storedId ? 2000 : false),
  });

  const { data: storedJob, error: storedJobError } = useQuery({
    queryKey: ["jobs", storedId],
    queryFn: () => fetchJob(storedId!),
    enabled: !!storedId,
    retry: false,
    refetchInterval: (query) => {
      const s = query.state.data?.status;
      return s === "queued" || s === "processing" ? 2000 : false;
    },
  });

  useEffect(() => {
    if (!storedId || !storedJobError) return;
    setStoredJobId(null);
    setStoredId(null);
    setTrackedJobId(null);
  }, [storedId, storedJobError]);

  const job =
    storedJob && trackedJobId === storedJob.id
      ? storedJob
      : activeJobs?.find((j) => j.id === trackedJobId) ?? activeJobs?.[0];

  const isDone = job?.status === "completed" || job?.status === "failed";
  const show = job && trackedJobId === job.id && (isActive(job) || isDone);

  useEffect(() => {
    if (!isDone || !job) return;
    queryClient.invalidateQueries({ queryKey: ["profile"] });
    queryClient.invalidateQueries({ queryKey: ["sessions"] });
    queryClient.invalidateQueries({ queryKey: ["uploads"] });
    queryClient.invalidateQueries({ queryKey: ["jobs"] });
    const timer = window.setTimeout(() => {
      setStoredJobId(null);
      setStoredId(null);
      setTrackedJobId(null);
    }, 15000);
    return () => window.clearTimeout(timer);
  }, [isDone, job?.id, queryClient]);

  if (!show || !job) return null;

  const done = job.succeeded + job.failed;
  const pct = job.total_count ? Math.round((done / job.total_count) * 100) : 0;

  return (
    <div
      className={`border-b-2 border-ink px-6 py-3 ${
        isDone
          ? job.failed && !job.succeeded
            ? "bg-cozy-red/10"
            : "bg-warm-yellow/30"
          : "bg-subdued-blue/10"
      }`}
    >
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="font-display text-sm font-bold">
            {isDone
              ? job.failed
                ? `Analysis finished with ${job.failed} error(s)`
                : `Analysis complete — ${job.succeeded} session(s) ready`
              : `Analyzing sessions (${done}/${job.total_count})`}
          </p>
          {!isDone && (
            <>
              <p className="truncate text-xs opacity-70">
                {job.current_file ? `${job.current_file}: ` : ""}
                {job.current_step ?? "Processing…"}
              </p>
              <div className="mt-2 h-2 w-full max-w-md border border-ink bg-cream">
                <div className="h-full bg-cozy-red transition-all" style={{ width: `${pct}%` }} />
              </div>
            </>
          )}
        </div>
        <Link to="/uploads" className="btn-brutal shrink-0 bg-card px-3 py-1 text-xs font-semibold">
          View details
        </Link>
      </div>
    </div>
  );
}
