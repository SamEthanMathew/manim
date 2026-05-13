import Link from "next/link";

export default function MarketingHome() {
  return (
    <main className="min-h-screen px-6 py-20 max-w-5xl mx-auto">
      <header className="flex items-center justify-between mb-24">
        <Link href="/" className="text-lg font-mono tracking-tight">manim</Link>
        <nav className="flex gap-6 text-sm text-gray-400">
          <Link href="/demo/eigenvectors" className="hover:text-white">Demos</Link>
          <Link href="/sign-in" className="hover:text-white">Sign in</Link>
        </nav>
      </header>

      <section className="space-y-8">
        <h1 className="text-5xl md:text-6xl font-bold tracking-tight leading-tight">
          Upload a PDF.
          <br />
          Get a 3Blue1Brown-style video.
        </h1>

        <p className="text-xl text-gray-300 max-w-2xl">
          Drop in a textbook chapter, paper, or set of lecture notes. We extract the math,
          plan a curriculum, write the script, generate Manim code per scene, and render
          the final video — automatically.
        </p>

        <div className="flex gap-4 pt-4">
          <Link
            href="/demo/eigenvectors"
            className="px-6 py-3 rounded-md bg-accent-blue text-white font-medium hover:opacity-90"
          >
            Try a sample
          </Link>
          <Link
            href="/sign-in"
            className="px-6 py-3 rounded-md border border-gray-700 text-gray-200 hover:bg-gray-800"
          >
            Sign in to upload your own
          </Link>
        </div>

        <p className="text-sm text-gray-500 pt-2">
          Free during beta · 50 pages max · 5-10 min videos · bring your own OpenAI or Anthropic key
        </p>
      </section>

      <section className="mt-32 grid md:grid-cols-3 gap-8">
        <Feature
          title="Math-aware extraction"
          body="We use Nougat for academic PDFs — equations come out as real LaTeX, not pixel garbage."
        />
        <Feature
          title="3b1b-style narration"
          body="The script aims for intuition first, formalism after. Visual metaphors carry the load."
        />
        <Feature
          title="Sandboxed render"
          body="Manim code is generated per scene and run in an isolated container. No data leaves your job."
        />
      </section>

      <footer className="mt-32 pt-8 border-t border-gray-800 text-sm text-gray-500">
        <p>An experimental tool. Not affiliated with 3Blue1Brown.</p>
      </footer>
    </main>
  );
}

function Feature({ title, body }: { title: string; body: string }) {
  return (
    <div className="space-y-2">
      <h3 className="text-lg font-semibold">{title}</h3>
      <p className="text-gray-400 leading-relaxed">{body}</p>
    </div>
  );
}
