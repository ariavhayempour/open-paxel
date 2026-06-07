import { useCallback, useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchJob, fetchRecentJobs, uploadSessionFiles } from "../lib/api";
import { getStoredJobId, setStoredJobId } from "./JobProgressBanner";

const ACCEPTED = [".jsonl", ".md", ".markdown", ".txt"];

function isAcceptedFile(name: string) {
  const lower = name.toLowerCase();
  return ACCEPTED.some((ext) => lower.endsWith(ext));
}

function isActiveJobStatus(status: string) {
  return status === "queued" || status === "processing";
}

export function SessionUpload() {
  const queryClient = useQueryClient();
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const [force, setForce] = useState(false);
  const [selected, setSelected] = useState<File[]>([]);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [trackedJobId, setTrackedJobId] = useState<string | null>(null);

  useEffect(() => {
    const id = getStoredJobId();
    if (id) {
      setActiveJobId(id);
      setTrackedJobId(id);
    }
  }, []);

  const { data: activeJob, error: jobError } = useQuery({
    queryKey: ["jobs", activeJobId],
    queryFn: () => fetchJob(activeJobId!),
    enabled: !!activeJobId,
    retry: false,
    refetchInterval: (q) => {
      const s = q.state.data?.status;
      return s === "queued" || s === "processing" ? 2000 : false;
    },
  });

  useEffect(() => {
    if (!activeJobId || !jobError) return;
    setActiveJobId(null);
    setTrackedJobId(null);
    setStoredJobId(null);
  }, [activeJobId, jobError]);

  const { data: recentJobs } = useQuery({
    queryKey: ["jobs", "recent"],
    queryFn: () => fetchRecentJobs(5),
    refetchInterval: (q) => {
      const jobs = q.state.data ?? [];
      return jobs.some((j) => isActiveJobStatus(j.status)) ? 2000 : false;
    },
  });

  const mutation = useMutation({
    mutationFn: (files: File[]) => uploadSessionFiles(files, force),
    onSuccess: (data) => {
      setSelected([]);
      if (data.job_id) {
        setActiveJobId(data.job_id);
        setTrackedJobId(data.job_id);
        setStoredJobId(data.job_id);
        queryClient.invalidateQueries({ queryKey: ["jobs"] });
      }
    },
  });

  const addFiles = useCallback((incoming: FileList | File[]) => {
    const accepted = Array.from(incoming).filter((f) => isAcceptedFile(f.name));
    if (!accepted.length) return;
    setSelected((prev) => {
      const names = new Set(prev.map((f) => f.name + f.size));
      return [...prev, ...accepted.filter((f) => !names.has(f.name + f.size))];
    });
  }, []);

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      if (e.dataTransfer.files.length) addFiles(e.dataTransfer.files);
    },
    [addFiles],
  );

  const handleUpload = () => {
    if (!selected.length || mutation.isPending) return;
    mutation.mutate(selected);
  };

  const showJob =
    activeJob &&
    trackedJobId === activeJob.id &&
    (isActiveJobStatus(activeJob.status) ||
      activeJob.status === "completed" ||
      activeJob.status === "failed");

  const activeRecentJobs = recentJobs?.filter((j) => isActiveJobStatus(j.status)) ?? [];

  return (
    <section className="card-brutal p-6">
      <h2 className="font-display text-xl font-bold">Upload sessions</h2>
      <p className="mt-1 text-sm opacity-70">
        Drop session files here:{" "}
        <code className="rounded bg-cream-dark px-1">.jsonl</code>,{" "}
        <code className="rounded bg-cream-dark px-1">.md</code>, or{" "}
        <code className="rounded bg-cream-dark px-1">.txt</code>.
        Processing continues in the background — you can navigate away.
      </p>

      <div
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === "Enter" && inputRef.current?.click()}
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        className={`mt-4 cursor-pointer border-2 border-dashed p-8 text-center transition-colors ${
          dragOver ? "border-cozy-red bg-cozy-red/5" : "border-ink/30 bg-cream-dark/50"
        }`}
      >
        <p className="font-semibold">Drag & drop session files</p>
        <p className="mt-1 text-sm opacity-60">.jsonl, .md, .txt — or click to browse</p>
        <input
          ref={inputRef}
          type="file"
          accept=".jsonl,.md,.markdown,.txt,text/plain,text/markdown,application/jsonl,application/x-ndjson"
          multiple
          className="hidden"
          onChange={(e) => {
            if (e.target.files) addFiles(e.target.files);
            e.target.value = "";
          }}
        />
      </div>

      {selected.length > 0 && (
        <ul className="mt-4 space-y-2">
          {selected.map((f, i) => (
            <li
              key={`${f.name}-${f.size}`}
              className="flex items-center justify-between gap-2 border-2 border-ink/20 bg-card px-3 py-2 text-sm"
            >
              <span className="truncate">{f.name}</span>
              <button
                type="button"
                onClick={() => setSelected((p) => p.filter((_, idx) => idx !== i))}
                className="shrink-0 opacity-60 hover:opacity-100"
                disabled={mutation.isPending}
              >
                Remove
              </button>
            </li>
          ))}
        </ul>
      )}

      <div className="mt-4 flex flex-wrap items-center gap-4">
        <label className="flex cursor-pointer items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={force}
            onChange={(e) => setForce(e.target.checked)}
            disabled={mutation.isPending}
            className="size-4 accent-cozy-red"
          />
          Re-analyze if already processed
        </label>

        <button
          type="button"
          onClick={handleUpload}
          disabled={!selected.length || mutation.isPending}
          className="btn-brutal bg-warm-yellow px-5 py-2 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-50"
        >
          {mutation.isPending ? "Starting…" : `Analyze ${selected.length || ""} session${selected.length === 1 ? "" : "s"}`}
        </button>
      </div>

      {mutation.isError && (
        <p className="mt-4 text-sm text-cozy-red">
          {(mutation.error as Error).message || "Upload failed"}
        </p>
      )}

      {mutation.isSuccess && mutation.data?.job_id && (
        <p className="mt-4 text-sm opacity-80">
          Job started — track progress in the banner above or below.
        </p>
      )}

      {showJob && activeJob && (
        <div className="mt-4 space-y-3 border-2 border-ink/20 bg-cream-dark/30 p-4 text-sm">
          <p className="font-semibold">
            {activeJob.status === "completed"
              ? `Done: ${activeJob.succeeded} succeeded${activeJob.failed ? `, ${activeJob.failed} failed` : ""}`
              : `Processing ${activeJob.succeeded + activeJob.failed}/${activeJob.total_count}`}
          </p>
          {activeJob.current_file && activeJob.status === "processing" && (
            <p className="opacity-70">
              {activeJob.current_file}: {activeJob.current_step}
            </p>
          )}
          <ul className="max-h-40 space-y-1 overflow-y-auto opacity-80">
            {activeJob.results.map((r) => (
              <li key={`${r.filename}-${r.session_id ?? r.error}`}>
                {r.status === "ok" ? `✓ ${r.filename}` : r.status === "error" ? `✗ ${r.filename}` : `… ${r.filename}`}
              </li>
            ))}
          </ul>
          {activeJob.logs.length > 0 && (
            <details className="text-xs opacity-70">
              <summary className="cursor-pointer font-semibold">Logs</summary>
              <ul className="mt-1 max-h-32 space-y-0.5 overflow-y-auto font-mono">
                {activeJob.logs.slice(-20).map((line, i) => (
                  <li key={i}>{line}</li>
                ))}
              </ul>
            </details>
          )}

          {activeJob.openai_calls && activeJob.openai_calls.length > 0 && (
            <details className="text-xs opacity-70" open>
              <summary className="cursor-pointer font-semibold">OpenAI API calls</summary>
              <ul className="mt-1 max-h-40 space-y-1 overflow-y-auto font-mono">
                {activeJob.openai_calls
                  .filter((c) => c.status !== "started")
                  .map((c, i) => (
                    <li key={i}>
                      {c.status === "completed" ? "✓" : "✗"} {c.phase}
                      {c.chunk_index ? ` (${c.chunk_index}/${c.chunk_total})` : ""} —{" "}
                      {c.duration_ms}ms
                      {c.total_tokens != null
                        ? ` · ${c.prompt_tokens ?? 0}+${c.completion_tokens ?? 0}=${c.total_tokens} tok`
                        : ""}
                    </li>
                  ))}
              </ul>
            </details>
          )}
        </div>
      )}

      {activeRecentJobs.length > 0 && (
        <div className="mt-6 border-t-2 border-ink/10 pt-4">
          <h3 className="font-display text-sm font-bold">Active jobs</h3>
          <ul className="mt-2 space-y-1 text-sm opacity-80">
            {activeRecentJobs.map((j) => (
              <li key={j.id}>
                <button
                  type="button"
                  className="text-left underline hover:opacity-100"
                  onClick={() => {
                    setActiveJobId(j.id);
                    setTrackedJobId(j.id);
                    setStoredJobId(j.id);
                  }}
                >
                  {new Date(j.created_at).toLocaleString()} — {j.status} ({j.succeeded}/{j.total_count})
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
