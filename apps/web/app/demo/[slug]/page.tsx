import type { Metadata } from "next";
import { notFound } from "next/navigation";
import Link from "next/link";

const DEMOS: Record<string, { title: string; subject: string; description: string; video: string }> = {
  eigenvectors: {
    title: "What is an eigenvector?",
    subject: "Linear Algebra",
    description:
      "From a chapter on eigenvalues and eigenvectors. The video opens with a transformation, highlights vectors that don't rotate, and builds toward the characteristic polynomial.",
    video: "/demos/eigenvectors.mp4",
  },
  sorting: {
    title: "Why is merge sort O(n log n)?",
    subject: "Algorithms",
    description:
      "From a chapter on divide-and-conquer. The video uses a deck of cards to show why halving the input log n times — with linear work per level — gives the well-known bound.",
    video: "/demos/sorting.mp4",
  },
  fourier: {
    title: "Every signal is a chord",
    subject: "Fourier Analysis",
    description:
      "From an intro chapter on Fourier series. The video reconstructs a square wave from sines and uses the metaphor of chords to motivate the decomposition.",
    video: "/demos/fourier.mp4",
  },
};

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const demo = DEMOS[slug];
  if (!demo) return { title: "Demo — manim" };
  return {
    title: `${demo.title} — manim demo`,
    description: demo.description,
  };
}

export default async function DemoPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const demo = DEMOS[slug];
  if (!demo) notFound();

  return (
    <main className="min-h-screen px-4 sm:px-6 py-8 sm:py-12 max-w-3xl mx-auto">
      <Link
        href="/"
        className="text-sm text-gray-300 hover:text-white rounded focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-blue focus-visible:ring-offset-2 focus-visible:ring-offset-[color:var(--bg)] px-1"
      >
        ← back
      </Link>

      <header className="mt-6 sm:mt-8 mb-5 sm:mb-6">
        <div className="text-xs uppercase tracking-wide text-accent-blue mb-2">
          {demo.subject}
        </div>
        <h1 className="text-2xl sm:text-3xl font-bold break-words">{demo.title}</h1>
      </header>

      <p className="text-gray-200 mb-6 sm:mb-8 leading-relaxed text-sm sm:text-base">
        {demo.description}
      </p>

      <video
        controls
        poster={`/demos/${slug}.jpg`}
        className="w-full rounded border border-gray-800 mb-6 sm:mb-8"
        src={demo.video}
      />

      <div className="text-sm text-gray-300 mt-6 sm:mt-8 space-y-2">
        <p>
          This video was generated end-to-end from a public-domain PDF — no manual edits, no
          hand-written code. The pipeline planned the curriculum, wrote the script, generated
          Manim code per scene, and stitched the result.
        </p>
        <p>
          <Link
            href="/sign-in"
            className="text-accent-blue hover:underline rounded focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-blue"
          >
            Sign in
          </Link>{" "}
          to upload your own PDF.
        </p>
      </div>
    </main>
  );
}

export const dynamicParams = false;
export function generateStaticParams() {
  return Object.keys(DEMOS).map((slug) => ({ slug }));
}
