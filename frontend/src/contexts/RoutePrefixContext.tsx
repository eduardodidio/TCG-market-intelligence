import { createContext, useContext, type ReactNode } from "react";

const RoutePrefixContext = createContext<string>("");

export function RoutePrefixProvider({
  prefix,
  children,
}: {
  prefix: string;
  children: ReactNode;
}) {
  return (
    <RoutePrefixContext.Provider value={prefix}>
      {children}
    </RoutePrefixContext.Provider>
  );
}

export function useRoutePrefix(): string {
  return useContext(RoutePrefixContext);
}
