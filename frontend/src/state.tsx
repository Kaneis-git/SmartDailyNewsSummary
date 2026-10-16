import { createContext, useContext } from "react";
import type { Health, Job } from "./types";
export const AppContext = createContext<{
  health: Health | null;
  job: Job | null;
}>({ health: null, job: null });
export const useApp = () => useContext(AppContext);
