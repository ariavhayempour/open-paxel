import { setStoredJobId } from "../components/JobProgressBanner";

const SERVER_INSTANCE_KEY = "open-paxel-server-instance";

export async function syncServerSession(): Promise<string | null> {
  try {
    const r = await fetch("/api/health");
    if (!r.ok) {
      setStoredJobId(null);
      return null;
    }
    const { instance_id } = (await r.json()) as { instance_id?: string };
    if (!instance_id) return null;

    const stored = localStorage.getItem(SERVER_INSTANCE_KEY);
    if (stored && stored !== instance_id) {
      setStoredJobId(null);
    }
    localStorage.setItem(SERVER_INSTANCE_KEY, instance_id);
    return instance_id;
  } catch {
    setStoredJobId(null);
    return null;
  }
}
