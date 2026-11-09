"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import { I18nProvider } from "@/lib/i18n";
import { useHydrateAuth } from "@/stores";

function Hydrate() {
  useHydrateAuth();
  return null;
}

export default function Providers({ children }: { children: React.ReactNode }) {
  const [client] = useState(() => new QueryClient());
  return (
    <QueryClientProvider client={client}>
      <I18nProvider>
        <Hydrate />
        {children}
      </I18nProvider>
    </QueryClientProvider>
  );
}
