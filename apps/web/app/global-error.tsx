"use client";

import { useEffect } from "react";

// Global error boundary — wraps the root layout, so it must render its own
// <html> and <body>. Used only when an error escapes the route-level boundary.
// Reference: https://nextjs.org/docs/app/getting-started/error-handling
export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // eslint-disable-next-line no-console
    console.error("Global error:", error);
  }, [error]);

  return (
    <html lang="en">
      <body
        style={{ background: "#0B0E14", color: "#E5E7EB" }}
        className="font-sans antialiased"
      >
        <main className="min-h-screen px-4 sm:px-6 py-12 max-w-xl mx-auto flex flex-col items-center justify-center text-center">
          <h1 className="text-2xl sm:text-3xl font-semibold mb-3">
            Something went wrong
          </h1>
          <p className="text-sm text-gray-300 mb-2 break-words max-w-md">
            {error.message || "A critical error occurred."}
          </p>
          {error.digest && (
            <p className="text-xs text-gray-400 font-mono mb-6 break-all">
              ref: {error.digest}
            </p>
          )}
          <div className="flex flex-col sm:flex-row gap-2 mt-4">
            <button
              type="button"
              onClick={reset}
              style={{ background: "#3498DB" }}
              className="px-4 py-2 text-white rounded-md text-sm font-medium hover:opacity-90 focus:outline-none"
            >
              Try again
            </button>
            {/* eslint-disable-next-line @next/next/no-html-link-for-pages */}
            <a
              href="/"
              className="px-4 py-2 border border-gray-700 rounded-md text-sm hover:border-gray-600 focus:outline-none"
            >
              Go home
            </a>
          </div>
        </main>
      </body>
    </html>
  );
}
