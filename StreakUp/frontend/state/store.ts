import { initialAppState } from "./app.slice";

export const store = {
  app: initialAppState
};

export type RootState = typeof store;
