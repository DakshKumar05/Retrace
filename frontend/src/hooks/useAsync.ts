import { useCallback, useEffect, useState } from 'react';
import { errorMessage } from '../services/api';

interface State<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

/** Loads data on mount and exposes a reload, so every page gets the same
 *  loading / error / empty behaviour without repeating it. */
export function useAsync<T>(loader: () => Promise<T>, deps: unknown[] = []) {
  const [state, setState] = useState<State<T>>({ data: null, loading: true, error: null });

  const run = useCallback(async () => {
    setState((prev) => ({ ...prev, loading: true, error: null }));
    try {
      const data = await loader();
      setState({ data, loading: false, error: null });
    } catch (error) {
      setState({ data: null, loading: false, error: errorMessage(error) });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => {
    void run();
  }, [run]);

  return { ...state, reload: run, setData: (data: T) => setState({ data, loading: false, error: null }) };
}
