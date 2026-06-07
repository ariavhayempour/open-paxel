import { useQuery } from "@tanstack/react-query";
import { SessionUpload } from "../components/SessionUpload";
import { fetchUploads } from "../lib/api";

export function UploadsPage() {
  const { data, isLoading } = useQuery({ queryKey: ["uploads"], queryFn: fetchUploads });

  if (isLoading) return <p className="animate-pulse">Loading uploads…</p>;

  const uploads = data ?? [];
  const totalSessions = uploads.reduce((sum, u) => sum + u.session_count, 0);
  const lastUpload = uploads[0];

  return (
    <div className="space-y-8">
      <SessionUpload />

      <div className="space-y-4">
        <h2 className="font-display text-2xl font-bold">Upload history</h2>
        {uploads.length === 0 ? (
          <p className="opacity-70">No uploads yet.</p>
        ) : (
          <div className="card-brutal p-5">
            <p className="font-display text-2xl font-bold">
              {totalSessions} session{totalSessions === 1 ? "" : "s"} analyzed
            </p>
            <p className="mt-2 text-sm opacity-70">
              {uploads.length} upload{uploads.length === 1 ? "" : "s"}
              {lastUpload ? ` · last ${new Date(lastUpload.created_at).toLocaleString()}` : ""}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
