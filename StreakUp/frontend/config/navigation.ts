import { routes } from "./routes";

export const navigation = [
  { label: "Home", href: routes.home },
  { label: "Admin", href: routes.admin }
] as const;
