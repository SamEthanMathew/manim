"use client";

import { useEffect } from "react";
import Link from "next/link";

// Route-level error boundary. Next.js automatically wraps children with this
// so any error thrown in a server or client component lands here.
// Reference: https://nextjs.org/docs/app/getting-started/error-handling
export default function RouteError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Surface the error to the browser console so it's not silently swallowed.
    // eslint-disable-next-line no-console
    console.error("Route error:", error);
  }, [error]);

  return (
    <main className="min-h-screen px-4 sm:px-6 py-12 max-w-xl mx-auto flex flex-col items-center justify-center text-center">
      <h1 className="text-2xl sm:text-3xl font-semibold mb-3">Something went wrong</h1>
      <p className="text-sm text-gray-300 mb-2 break-words max-w-md">
        {error.message || "An unexpected error occurred."}
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
          className="px-4 py-2 bg-accent-blue text-white rounded-md text-sm font-medium hover:opacity-90 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-blue focus-visible:ring-offset-2 focus-visible:ring-offset-[color:var(--bg)]"
        >
          Try again
        </button>
        <Link
          href="/"
          className="px-4 py-2 border border-gray-700 rounded-md text-sm hover:border-gray-600 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-blue"
        >
          Go home
        </Link>
      </div>
    </main>
  );
}
