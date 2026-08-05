import { useState, useEffect, useCallback } from "react";
import { getClientDetail } from "../api";

export function useClientDetail(email, token) {
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const refresh = useCallback(async () => {
    if (!email || !token) {
      setDetail(null);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await getClientDetail(email, token);
      setDetail(data);
    } catch (err) {
      setError(err.message || "Failed to load client detail.");
    } finally {
      setLoading(false);
    }
  }, [email, token]);

  useEffect(() => {
    refresh();
  }, [email, token, refresh]);

  return { detail, loading, error, refresh };
}