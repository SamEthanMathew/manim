import { redirect } from "next/navigation";

// Sign-in is no longer a separate step — the homepage signs visitors in
// anonymously on first visit. Redirect any old links here back to home.
export default function SignInPage() {
  redirect("/");
}
